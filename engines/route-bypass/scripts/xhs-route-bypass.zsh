#!/bin/zsh
set -euo pipefail

TOOL_DIR="${0:A:h:h}"
DOMAIN_FILE="${XHS_ROUTE_DOMAIN_FILE:-$TOOL_DIR/domains.txt}"
STATE_DIR="${XHS_ROUTE_STATE_DIR:-$HOME/.xhs-route-bypass}"
STATE_FILE="$STATE_DIR/managed-ips.txt"
STATE_NET_FILE="$STATE_DIR/managed-nets.txt"
SERVICE="${XHS_ROUTE_SERVICE:-Wi-Fi}"
STATIC_IPS="${XHS_ROUTE_STATIC_IPS:-23.59.252.178 23.59.252.200 23.59.252.201 23.59.252.202 23.59.252.203 184.27.185.201 184.27.185.213 212.129.158.241}"
STATIC_NETS="${XHS_ROUTE_STATIC_NETS:-23.59.252.0/24 23.52.128.0/24 184.27.185.0/24 212.129.158.0/24}"
PRUNE_STALE="${XHS_ROUTE_PRUNE_STALE:-0}"

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
  XHS_ROUTE_STATIC_IPS    Extra IPv4 host routes to always manage
  XHS_ROUTE_STATIC_NETS   Extra IPv4 CIDR routes to always manage
  XHS_ROUTE_PRUNE_STALE   Set to 1 to delete managed routes absent from the latest resolve
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

route_targets() {
  local gw="$1"
  shift
  local tmp
  tmp="$(mktemp)"

  resolve_domains "$gw" "$@" >"$tmp"
  if [[ -n "$STATIC_IPS" ]]; then
    printf '%s\n' ${(z)STATIC_IPS} >>"$tmp"
  fi

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

read_state_nets() {
  if [[ -f "$STATE_NET_FILE" ]]; then
    awk '/^[0-9]+(\.[0-9]+){3}\/[0-9]+$/ { print }' "$STATE_NET_FILE" | sort -u
  fi
}

write_state_nets() {
  mkdir -p "$STATE_DIR"
  sort -u >"$STATE_NET_FILE"
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

  route_targets "$gw" "${domains[@]}" >"$new"
  [[ -s "$new" ]] || die "no IPv4 addresses resolved; refusing to change routes"

  read_state_ips >"$old"
  if [[ "$PRUNE_STALE" == "1" ]]; then
    comm -23 "$old" "$new" >"$stale" || true
  else
    : >"$stale"
  fi

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
  elif [[ "$PRUNE_STALE" != "1" ]]; then
    print "retaining stale managed routes (set XHS_ROUTE_PRUNE_STALE=1 to prune)"
  fi

  print "applying routes:"
  while read -r ip; do
    [[ -n "$ip" ]] || continue
    print "  $ip -> $gw"
    route_cmd -n add -host "$ip" "$gw" >/dev/null 2>&1 || route_cmd -n change -host "$ip" "$gw" >/dev/null
  done <"$new"

  cat "$old" "$new" | write_state_ips

  if [[ -n "$STATIC_NETS" ]]; then
    print "applying static network routes:"
    local nets old_nets
    nets="$(mktemp)"
    old_nets="$(mktemp)"
    printf '%s\n' ${(z)STATIC_NETS} | awk '/^[0-9]+(\.[0-9]+){3}\/[0-9]+$/ { print }' | sort -u >"$nets"
    read_state_nets >"$old_nets"
    while read -r net; do
      [[ -n "$net" ]] || continue
      print "  $net -> $gw"
      route_cmd -n add -net "$net" "$gw" >/dev/null 2>&1 || route_cmd -n change -net "$net" "$gw" >/dev/null
    done <"$nets"
    cat "$old_nets" "$nets" | write_state_nets
    rm -f "$nets" "$old_nets"
  fi

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

  print "route target IPv4:"
  local resolved
  resolved="$(mktemp)"
  route_targets "$gw" "${domains[@]}" >"$resolved"
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

  print "managed network state:"
  local net_state
  net_state="$(mktemp)"
  read_state_nets >"$net_state"
  if [[ -s "$net_state" ]]; then
    cat "$net_state" | sed 's/^/  /'
  else
    print "  none"
  fi

  print "route decisions for route target IPv4:"
  if [[ -s "$resolved" ]]; then
    while read -r ip; do
      [[ -n "$ip" ]] || continue
      route_summary "$ip"
    done <"$resolved"
  else
    print "  none"
  fi

  rm -f "$resolved" "$state" "$net_state"
}

remove_routes() {
  local state
  state="$(mktemp)"
  read_state_ips >"$state"
  local net_state
  net_state="$(mktemp)"
  read_state_nets >"$net_state"
  [[ -s "$state" || -s "$net_state" ]] || {
    print "no managed routes recorded at $STATE_FILE"
    rm -f "$state" "$net_state"
    return
  }

  if [[ -s "$state" ]]; then
    print "removing managed routes:"
    while read -r ip; do
      [[ -n "$ip" ]] || continue
      print "  $ip"
      route_cmd -n delete -host "$ip" >/dev/null 2>&1 || true
    done <"$state"
  fi

  if [[ -s "$net_state" ]]; then
    print "removing managed network routes:"
    while read -r net; do
      [[ -n "$net" ]] || continue
      print "  $net"
      route_cmd -n delete -net "$net" >/dev/null 2>&1 || true
    done <"$net_state"
  fi

  rm -f "$STATE_FILE" "$STATE_NET_FILE" "$state" "$net_state"
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
