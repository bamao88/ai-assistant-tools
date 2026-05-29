#!/bin/zsh
set -euo pipefail

TOOL_DIR="${0:A:h:h}"
DOMAIN_FILE="${XHS_ROUTE_DOMAIN_FILE:-$TOOL_DIR/domains.txt}"
STATE_DIR="${XHS_ROUTE_STATE_DIR:-$HOME/.xhs-route-bypass}"
STATE_FILE="$STATE_DIR/managed-ips.txt"
SERVICE="${XHS_ROUTE_SERVICE:-Wi-Fi}"

usage() {
  cat <<USAGE
Usage:
  $0 apply [domain ...]    Resolve domains and apply local host routes
  $0 status [domain ...]   Show resolved IPs and route decisions
  $0 resolve [domain ...]  Print resolved IPv4 addresses only
  $0 remove                Remove routes managed by this tool

Environment:
  XHS_ROUTE_SERVICE       Network service name, default: Wi-Fi
  XHS_ROUTE_DOMAIN_FILE   Domain list file, default: $DOMAIN_FILE
  XHS_ROUTE_STATE_DIR     State directory, default: $STATE_DIR
USAGE
}

die() {
  print -u2 "error: $*"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

route_cmd() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    /sbin/route "$@"
  else
    sudo /sbin/route "$@"
  fi
}

local_gateway() {
  networksetup -getinfo "$SERVICE" | awk -F': ' '/^Router:/{print $2; exit}'
}

interface_for_gateway() {
  local gw="$1"
  /sbin/route -n get "$gw" 2>/dev/null | awk '/interface:/{print $2; exit}'
}

load_domains() {
  if [[ "$#" -gt 0 ]]; then
    printf '%s\n' "$@"
    return
  fi

  [[ -f "$DOMAIN_FILE" ]] || die "domain file not found: $DOMAIN_FILE"
  awk '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    { gsub(/^[[:space:]]+|[[:space:]]+$/, ""); print }
  ' "$DOMAIN_FILE"
}

resolve_domains() {
  local gw="$1"
  shift
  local tmp
  tmp="$(mktemp)"

  for domain in "$@"; do
    dig +time=2 +tries=1 +short A "$domain" >>"$tmp" 2>/dev/null || true
    if [[ -n "$gw" ]]; then
      dig @"$gw" +time=2 +tries=1 +short A "$domain" >>"$tmp" 2>/dev/null || true
    fi
  done

  awk '/^[0-9]+(\.[0-9]+){3}$/ { print }' "$tmp" | sort -u
  rm -f "$tmp"
}

route_summary() {
  local ip="$1"
  local out
  out="$(/sbin/route -n get "$ip" 2>/dev/null || true)"
  local gateway interface destination
  destination="$(printf '%s\n' "$out" | awk '/destination:/{print $2; exit}')"
  gateway="$(printf '%s\n' "$out" | awk '/gateway:/{print $2; exit}')"
  interface="$(printf '%s\n' "$out" | awk '/interface:/{print $2; exit}')"
  [[ -n "$gateway" ]] || gateway="-"
  [[ -n "$interface" ]] || interface="-"
  [[ -n "$destination" ]] || destination="-"
  printf '%-15s destination=%-15s gateway=%-15s interface=%s\n' "$ip" "$destination" "$gateway" "$interface"
}

read_state_ips() {
  if [[ -f "$STATE_FILE" ]]; then
    awk '/^[0-9]+(\.[0-9]+){3}$/ { print }' "$STATE_FILE" | sort -u
  fi
}

write_state_ips() {
  mkdir -p "$STATE_DIR"
  sort -u >"$STATE_FILE"
}

apply_routes() {
  require_cmd networksetup
  require_cmd dig

  local gw iface
  gw="$(local_gateway)"
  [[ -n "$gw" ]] || die "no router found for network service: $SERVICE"
  iface="$(interface_for_gateway "$gw")"
  [[ -n "$iface" ]] || die "cannot determine interface for gateway: $gw"

  local -a domains
  domains=("${(@f)$(load_domains "$@")}")
  [[ "${#domains[@]}" -gt 0 ]] || die "no domains configured"

  local new old stale
  new="$(mktemp)"
  old="$(mktemp)"
  stale="$(mktemp)"

  resolve_domains "$gw" "${domains[@]}" >"$new"
  [[ -s "$new" ]] || die "no IPv4 addresses resolved; refusing to change routes"

  read_state_ips >"$old"
  comm -23 "$old" "$new" >"$stale" || true

  print "service=$SERVICE gateway=$gw interface=$iface"
  print "domains:"
  printf '  %s\n' "${domains[@]}"

  if [[ -s "$stale" ]]; then
    print "removing stale managed routes:"
    while read -r ip; do
      [[ -n "$ip" ]] || continue
      print "  $ip"
      route_cmd -n delete -host "$ip" >/dev/null 2>&1 || true
    done <"$stale"
  fi

  print "applying routes:"
  while read -r ip; do
    [[ -n "$ip" ]] || continue
    print "  $ip -> $gw"
    route_cmd -n add -host "$ip" "$gw" >/dev/null 2>&1 || route_cmd -n change -host "$ip" "$gw" >/dev/null
  done <"$new"

  write_state_ips <"$new"

  print "route decisions:"
  while read -r ip; do
    [[ -n "$ip" ]] || continue
    route_summary "$ip"
  done <"$new"

  rm -f "$new" "$old" "$stale"
}

status_routes() {
  require_cmd networksetup
  require_cmd dig

  local gw iface
  gw="$(local_gateway)"
  iface="$(interface_for_gateway "$gw")"
  print "service=$SERVICE gateway=${gw:-unknown} interface=${iface:-unknown}"

  local -a domains
  domains=("${(@f)$(load_domains "$@")}")
  print "domains:"
  printf '  %s\n' "${domains[@]}"

  print "currently resolved IPv4:"
  local resolved
  resolved="$(mktemp)"
  resolve_domains "$gw" "${domains[@]}" >"$resolved"
  if [[ -s "$resolved" ]]; then
    cat "$resolved" | sed 's/^/  /'
  else
    print "  none"
  fi

  print "managed state:"
  local state
  state="$(mktemp)"
  read_state_ips >"$state"
  if [[ -s "$state" ]]; then
    cat "$state" | sed 's/^/  /'
  else
    print "  none"
  fi

  print "route decisions for resolved IPv4:"
  if [[ -s "$resolved" ]]; then
    while read -r ip; do
      [[ -n "$ip" ]] || continue
      route_summary "$ip"
    done <"$resolved"
  else
    print "  none"
  fi

  rm -f "$resolved" "$state"
}

remove_routes() {
  local state
  state="$(mktemp)"
  read_state_ips >"$state"
  [[ -s "$state" ]] || {
    print "no managed routes recorded at $STATE_FILE"
    rm -f "$state"
    return
  }

  print "removing managed routes:"
  while read -r ip; do
    [[ -n "$ip" ]] || continue
    print "  $ip"
    route_cmd -n delete -host "$ip" >/dev/null 2>&1 || true
  done <"$state"

  rm -f "$STATE_FILE" "$state"
}

resolve_only() {
  require_cmd networksetup
  require_cmd dig

  local gw
  gw="$(local_gateway)"
  local -a domains
  domains=("${(@f)$(load_domains "$@")}")
  resolve_domains "$gw" "${domains[@]}"
}

cmd="${1:-status}"
if [[ "$#" -gt 0 ]]; then
  shift
fi

case "$cmd" in
  apply)
    apply_routes "$@"
    ;;
  status)
    status_routes "$@"
    ;;
  resolve)
    resolve_only "$@"
    ;;
  remove)
    remove_routes
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    die "unknown command: $cmd"
    ;;
esac
