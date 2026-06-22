#!/bin/zsh
set -euo pipefail

TOOL_DIR="${0:A:h:h}"
DOMAIN_FILE="${XHS_ROUTE_DOMAIN_FILE:-$TOOL_DIR/domains.txt}"
STATE_DIR="${XHS_ROUTE_STATE_DIR:-$HOME/.xhs-route-bypass}"
STATE_FILE="$STATE_DIR/managed-ips.txt"
STATE_NET_FILE="$STATE_DIR/managed-nets.txt"
SERVICE="${XHS_ROUTE_SERVICE:-Wi-Fi}"
STATIC_IPS="${XHS_ROUTE_STATIC_IPS:-23.59.252.178 23.59.252.200 23.59.252.201 23.59.252.202 23.59.252.203 96.7.244.134 96.7.244.142 96.7.244.153 96.7.244.158 184.27.185.201 184.27.185.213 212.129.158.241}"
STATIC_NETS="${XHS_ROUTE_STATIC_NETS:-23.59.252.0/24 23.52.128.0/24 96.7.244.0/24 184.27.185.0/24 212.129.158.0/24}"
PRUNE_STALE="${XHS_ROUTE_PRUNE_STALE:-0}"
MANAGE_HOSTS="${XHS_ROUTE_MANAGE_HOSTS:-1}"
HOSTS_FILE="${XHS_ROUTE_HOSTS_FILE:-/etc/hosts}"
HOST_OVERRIDE_DOMAINS="${XHS_ROUTE_HOST_OVERRIDE_DOMAINS:-www.xiaohongshu.com edith.xiaohongshu.com ros-upload.xiaohongshu.com}"
HOST_OVERRIDE_STATIC="${XHS_ROUTE_HOST_OVERRIDE_STATIC:-}"
HOSTS_BEGIN="# BEGIN xhs-route-bypass managed hosts"
HOSTS_END="# END xhs-route-bypass managed hosts"

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
  XHS_ROUTE_MANAGE_HOSTS  Set to 0 to skip managed /etc/hosts overrides
  XHS_ROUTE_HOST_OVERRIDE_DOMAINS
                          Domains resolved via local gateway DNS into a managed hosts block
  XHS_ROUTE_HOST_OVERRIDE_STATIC
                          Static managed hosts, space-separated domain=ip pairs
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

shell_join() {
  local -a quoted
  quoted=()
  local arg
  for arg in "$@"; do
    quoted+=("${(q)arg}")
  done
  print -r -- "${(j: :)quoted}"
}

run_admin_shell() {
  local command="$1"
  local escaped="${command//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  osascript -e "do shell script \"$escaped\" with administrator privileges"
}

privileged_cmd() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    "$@"
  elif sudo -n true >/dev/null 2>&1; then
    sudo "$@"
  elif [[ -t 0 ]]; then
    sudo "$@"
  else
    run_admin_shell "$(shell_join "$@")"
  fi
}

privileged_shell() {
  local command="$1"
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    eval "$command"
  elif sudo -n true >/dev/null 2>&1; then
    sudo /bin/zsh -c "$command"
  elif [[ -t 0 ]]; then
    sudo /bin/zsh -c "$command"
  else
    run_admin_shell "$command"
  fi
}

route_cmd() {
  privileged_cmd /sbin/route "$@"
}

append_route_line() {
  local script="$1"
  shift
  print -r -- "$*" >>"$script"
}

run_route_script() {
  local script="$1"
  [[ -s "$script" ]] || return 0
  privileged_cmd /bin/zsh "$script"
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

resolve_domain_via_gateway() {
  local gw="$1"
  local domain="$2"
  [[ -n "$gw" ]] || return 0
  dig @"$gw" +time=2 +tries=1 +short A "$domain" 2>/dev/null \
    | awk '/^[0-9]+(\.[0-9]+){3}$/ { print }' \
    | sort -u
}

host_probe_url() {
  local domain="$1"
  if [[ "$domain" == "www.xiaohongshu.com" ]]; then
    print "https://$domain/explore"
  else
    print "https://$domain/"
  fi
}

host_ip_connects() {
  local domain="$1"
  local ip="$2"
  local url
  url="$(host_probe_url "$domain")"
  curl --connect-timeout 2 --max-time 5 -sS -o /dev/null \
    --resolve "$domain:443:$ip" "$url" >/dev/null 2>&1
}

managed_host_lines() {
  local gw="$1"
  local pair domain ip selected candidates

  for pair in ${(z)HOST_OVERRIDE_STATIC}; do
    [[ "$pair" == *=* ]] || continue
    domain="${pair%%=*}"
    ip="${pair#*=}"
    [[ -n "$domain" && -n "$ip" ]] || continue
    if [[ "$ip" =~ '^[0-9]+(\.[0-9]+){3}$' ]]; then
      printf '%-15s %s\n' "$ip" "$domain"
    fi
  done

  for domain in ${(z)HOST_OVERRIDE_DOMAINS}; do
    [[ -n "$domain" ]] || continue
    candidates="$(resolve_domain_via_gateway "$gw" "$domain")"
    selected=""
    while read -r ip; do
      [[ -n "$ip" ]] || continue
      if host_ip_connects "$domain" "$ip"; then
        selected="$ip"
        break
      fi
      [[ -n "$selected" ]] || selected="$ip"
    done <<<"$candidates"
    [[ -n "$selected" ]] || continue
    printf '%-15s %s\n' "$selected" "$domain"
  done
}

strip_managed_hosts() {
  awk -v begin="$HOSTS_BEGIN" -v end="$HOSTS_END" '
    $0 == begin { skip = 1; next }
    $0 == end { skip = 0; next }
    !skip { print }
  ' "$HOSTS_FILE"
}

write_hosts_file() {
  local src="$1"
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    cat "$src" >"$HOSTS_FILE"
  else
    privileged_shell "cat ${(q)src} > ${(q)HOSTS_FILE}"
  fi
}

flush_dns_cache() {
  dscacheutil -flushcache >/dev/null 2>&1 || true
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    killall -HUP mDNSResponder >/dev/null 2>&1 || true
  else
    privileged_cmd killall -HUP mDNSResponder >/dev/null 2>&1 || true
  fi
}

apply_managed_hosts() {
  [[ "$MANAGE_HOSTS" == "1" ]] || return 0
  require_cmd curl

  local gw="$1"
  local lines base block new_hosts
  lines="$(mktemp)"
  base="$(mktemp)"
  block="$(mktemp)"
  new_hosts="$(mktemp)"

  managed_host_lines "$gw" >"$lines"
  strip_managed_hosts >"$base"

  if [[ -s "$lines" ]]; then
    {
      print "$HOSTS_BEGIN"
      cat "$lines"
      print "$HOSTS_END"
    } >"$block"

    print "applying managed host overrides:"
    sed 's/^/  /' "$lines"
    {
      cat "$base"
      print ""
      cat "$block"
    } >"$new_hosts"
  else
    print "no managed host overrides resolved"
    cat "$base" >"$new_hosts"
  fi

  write_hosts_file "$new_hosts"
  flush_dns_cache
  rm -f "$lines" "$base" "$block" "$new_hosts"
}

remove_managed_hosts() {
  [[ -f "$HOSTS_FILE" ]] || return 0
  local base
  base="$(mktemp)"
  strip_managed_hosts >"$base"
  write_hosts_file "$base"
  flush_dns_cache
  rm -f "$base"
}

route_targets() {
  local gw="$1"
  shift
  local tmp
  tmp="$(mktemp)"

  resolve_domains "$gw" "$@" >"$tmp"
  if [[ -n "$STATIC_IPS" && "$STATIC_IPS" != "__none__" ]]; then
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

write_state_file() {
  local target="$1"
  local tmp
  tmp="$(mktemp)"
  sort -u >"$tmp"
  mkdir -p "$STATE_DIR"
  if { cat "$tmp" >"$target" } 2>/dev/null; then
    rm -f "$tmp"
    return
  fi

  local owner_group
  owner_group="$(id -un):$(id -gn)"
  privileged_shell "mkdir -p ${(q)STATE_DIR} && cat ${(q)tmp} > ${(q)target} && chown ${(q)owner_group} ${(q)target} ${(q)STATE_DIR}"
  rm -f "$tmp"
}

write_state_ips() {
  write_state_file "$STATE_FILE"
}

read_state_nets() {
  if [[ -f "$STATE_NET_FILE" ]]; then
    awk '/^[0-9]+(\.[0-9]+){3}\/[0-9]+$/ { print }' "$STATE_NET_FILE" | sort -u
  fi
}

write_state_nets() {
  write_state_file "$STATE_NET_FILE"
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
  local route_script
  route_script="$(mktemp)"
  print "set -e" >"$route_script"

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
      append_route_line "$route_script" "/sbin/route -n delete -host ${(q)ip} >/dev/null 2>&1 || true"
    done <"$stale"
  elif [[ "$PRUNE_STALE" != "1" ]]; then
    print "retaining stale managed routes (set XHS_ROUTE_PRUNE_STALE=1 to prune)"
  fi

  print "applying routes:"
  while read -r ip; do
    [[ -n "$ip" ]] || continue
    print "  $ip -> $gw"
    append_route_line "$route_script" "/sbin/route -n add -host ${(q)ip} ${(q)gw} >/dev/null 2>&1 || /sbin/route -n change -host ${(q)ip} ${(q)gw} >/dev/null"
  done <"$new"

  if [[ -n "$STATIC_NETS" && "$STATIC_NETS" != "__none__" ]]; then
    print "applying static network routes:"
    local nets old_nets
    nets="$(mktemp)"
    old_nets="$(mktemp)"
    printf '%s\n' ${(z)STATIC_NETS} | awk '/^[0-9]+(\.[0-9]+){3}\/[0-9]+$/ { print }' | sort -u >"$nets"
    read_state_nets >"$old_nets"
    while read -r net; do
      [[ -n "$net" ]] || continue
      print "  $net -> $gw"
      append_route_line "$route_script" "/sbin/route -n add -net ${(q)net} ${(q)gw} >/dev/null 2>&1 || /sbin/route -n change -net ${(q)net} ${(q)gw} >/dev/null"
    done <"$nets"
    rm -f "$nets" "$old_nets"
  fi

  run_route_script "$route_script"

  cat "$old" "$new" | write_state_ips
  if [[ -n "$STATIC_NETS" && "$STATIC_NETS" != "__none__" ]]; then
    local nets_for_state old_nets_for_state
    nets_for_state="$(mktemp)"
    old_nets_for_state="$(mktemp)"
    printf '%s\n' ${(z)STATIC_NETS} | awk '/^[0-9]+(\.[0-9]+){3}\/[0-9]+$/ { print }' | sort -u >"$nets_for_state"
    read_state_nets >"$old_nets_for_state"
    cat "$old_nets_for_state" "$nets_for_state" | write_state_nets
    rm -f "$nets_for_state" "$old_nets_for_state"
  fi

  apply_managed_hosts "$gw"

  print "route decisions:"
  while read -r ip; do
    [[ -n "$ip" ]] || continue
    route_summary "$ip"
  done <"$new"

  rm -f "$new" "$old" "$stale" "$route_script"
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

  print "managed host overrides:"
  local host_state
  host_state="$(mktemp)"
  awk -v begin="$HOSTS_BEGIN" -v end="$HOSTS_END" '
    $0 == begin { in_block = 1; next }
    $0 == end { in_block = 0; next }
    in_block && NF { print }
  ' "$HOSTS_FILE" 2>/dev/null >"$host_state" || true
  if [[ -s "$host_state" ]]; then
    sed 's/^/  /' "$host_state"
  else
    print "  none"
  fi
  rm -f "$host_state"

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
    remove_managed_hosts
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
  remove_managed_hosts
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
