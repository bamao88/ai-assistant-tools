#!/bin/zsh
# wechatsync 封装脚本 —— 在开源 @wechatsync/cli 外面包一层，固化稳定调用流程。
# 底层完全复用 wechatsync，本脚本不重写任何平台适配，只堵两个坑 + 加预检/白名单。
#
# 这次不稳定的真实根因（已定位）：
#   1. 命令中断会留下 node .../@wechatsync/cli/dist/index.js 进程占住桥接端口 9527/9528，
#      导致后续全部报「已有实例正在运行但 Chrome Extension 未连接」，且进程名不含 wechatsync、极难查。
#   2. 没有同步前的登录态预检，掉没掉要等同步失败才知道。
# 本脚本解决：跑前自动清残留+释放端口、先预检登录态、账号白名单、解析草稿链接、跑完清理。
#
# 不能解决（任何方案都不能）：登录态过期本身 —— 掉了得你去那个平台重新登录。
# 但脚本会第一时间精确告诉你"掉的是哪几个"，不用再盲查。
#
# 依赖：全局 wechatsync（npm i -g @wechatsync/cli）、环境变量 WECHATSYNC_TOKEN、
#       浏览器装好 wechatsync 扩展且设置里「CLI / MCP 连接」开关打开。
#
# 用法：
#   ./publish.sh check                          只做登录态预检，列出各平台状态（只读，不发）
#   ./publish.sh sync <article.md> [选项]        清残留→预检→自动选张和本人账号平台→同步草稿→报告→清理
#
# sync 选项：
#   --title "标题"        文章标题（建议显式给，否则 wechatsync 从文件首个 # 提取）
#   --cover <图片路径>    封面图本地路径或 URL
#   --platforms a,b,c     手动指定平台，覆盖白名单自动选择
#   --all-accounts        允许同步到非张和本人账号的平台（默认跳过）
#   --dry-run             只预览不实际写草稿

set -o pipefail

BRIDGE_PORT=9527
TIMEOUT_MS=180000
AUTH_TIMEOUT_MS=60000

# 张和本人账号白名单：平台 -> 期望账号名包含的关键词。
typeset -A ZHANGHE_ACCOUNTS
ZHANGHE_ACCOUNTS=(
  zhihu      "张和"
  juejin     "张和"
  csdn       "张和"
  jianshu    "张和"
  toutiao    "张和"
  baijiahao  "张和"
  sohu       "张和"
  weixin     "张和"
)

# 颜色用原始 ANSI 转义；数据通过 %s 传入，绝不参与格式解析（避免账号名里的 % 导致崩溃）。
c_red()    { printf '\033[31m%s\033[0m\n' "$1"; }
c_green()  { printf '\033[32m%s\033[0m\n' "$1"; }
c_yellow() { printf '\033[33m%s\033[0m\n' "$1"; }
c_dim()    { printf '\033[2m%s\033[0m\n' "$1"; }
die()      { c_red "✗ $1"; exit 1; }

preflight_clean() {
  c_dim "› 清残留进程 / 释放桥接端口 $BRIDGE_PORT ..."
  pkill -9 -f "@wechatsync/cli/dist" 2>/dev/null
  pkill -9 -f "bin/wechatsync" 2>/dev/null
  local pids
  pids=$(lsof -nP -iTCP:$BRIDGE_PORT -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $2}' | sort -u)
  [[ -n "$pids" ]] && print "$pids" | xargs kill -9 2>/dev/null
  sleep 1
  local left
  left=$(lsof -nP -iTCP:$BRIDGE_PORT -sTCP:LISTEN 2>/dev/null | grep -c LISTEN)
  [[ "$left" == "0" ]] && c_dim "  ✓ 干净" || c_yellow "  ⚠ 端口 $BRIDGE_PORT 仍被占用"
}

precheck_env() {
  command -v wechatsync >/dev/null 2>&1 || die "找不到 wechatsync，先 npm i -g @wechatsync/cli"
  [[ -n "${WECHATSYNC_TOKEN:-}" ]] || die "WECHATSYNC_TOKEN 未设置。扩展设置里复制 token 后 export。"
  c_dim "  WECHATSYNC_TOKEN: 已设置 (len=${#WECHATSYNC_TOKEN})"
}

run_auth() {
  local out="$1"
  c_dim "› 查询各平台登录态（需扩展 MCP 开关开着、Chrome 不关）..."
  wechatsync --timeout $AUTH_TIMEOUT_MS platforms --auth > "$out" 2>/dev/null
  if grep -qiE "需要安装|未连接|连接超时" "$out"; then
    c_red "✗ 桥接没连上：扩展「CLI / MCP 连接」开关没开，或 Chrome 没开。"
    c_yellow "  插件设置 → 同步桥接 → 打开「CLI / MCP 连接」(显示已连接) → 重试。"
    return 1
  fi
  return 0
}

is_zhanghe_account() {
  local plat="$1" acct="$2"
  local kw="${ZHANGHE_ACCOUNTS[$plat]}"
  [[ -n "$kw" ]] || return 1
  [[ "$acct" == *"$kw"* ]]
}

cmd_check() {
  precheck_env
  preflight_clean
  local out=$(mktemp)
  run_auth "$out" || { rm -f "$out"; exit 1; }
  echo
  c_green "各平台登录态："
  grep -E "✓ 已登录|✗ 未登录" "$out" | while read -r line; do print -r -- "  $line"; done
  echo
  c_green "其中可同步（张和本人账号、已登录）："
  local line plat acct
  grep "✓ 已登录" "$out" | while read -r line; do
    plat=$(print -r -- "$line" | awk '{print $1}')
    acct=$(print -r -- "$line" | sed -nE 's/.*\(([^)]*)\).*/\1/p')
    if is_zhanghe_account "$plat" "$acct"; then
      c_green "  ✓ $plat ($acct)"
    fi
  done
  rm -f "$out"
  c_dim "（check 只读，不发任何内容）"
}

cmd_sync() {
  local file="$1"; shift
  [[ -n "$file" && -f "$file" ]] || die "文章文件不存在：$file"

  local title="" cover="" platforms="" dryrun="" allacc=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title)        title="$2"; shift 2;;
      --cover)        cover="$2"; shift 2;;
      --platforms)    platforms="$2"; shift 2;;
      --dry-run)      dryrun="--dry-run"; shift;;
      --all-accounts) allacc="1"; shift;;
      *) die "未知参数：$1";;
    esac
  done

  precheck_env
  preflight_clean

  local out=$(mktemp)
  run_auth "$out" || { rm -f "$out"; exit 1; }

  if [[ -z "$platforms" ]]; then
    local picked=() line plat acct
    while read -r line; do
      plat=$(print -r -- "$line" | awk '{print $1}')
      acct=$(print -r -- "$line" | sed -nE 's/.*\(([^)]*)\).*/\1/p')
      [[ -n "${ZHANGHE_ACCOUNTS[$plat]}" ]] || continue
      if [[ -n "$allacc" ]] || is_zhanghe_account "$plat" "$acct"; then
        picked+=("$plat")
      else
        c_yellow "  ↷ 跳过 $plat（登录账号「$acct」不是张和本人）"
      fi
    done < <(grep "✓ 已登录" "$out")
    platforms="${(j:,:)picked}"
  fi
  rm -f "$out"

  [[ -n "$platforms" ]] || die "没有可同步的平台。先 ./publish.sh check 看看。"

  c_green "› 将同步到：$platforms"
  [[ -n "$dryrun" ]] && c_yellow "  （dry-run 预览，不实际写草稿）"

  local args=(--timeout $TIMEOUT_MS sync "$file" -p "$platforms")
  [[ -n "$title" ]] && args+=(-t "$title")
  [[ -n "$cover" ]] && args+=(--cover "$cover")
  [[ -n "$dryrun" ]] && args+=(--dry-run)

  local result=$(mktemp)
  wechatsync "${args[@]}" > "$result" 2>/dev/null
  echo
  cat "$result"
  echo
  c_green "草稿链接汇总："
  grep -oE 'https://[A-Za-z0-9./?=_&#:-]+' "$result" | sort -u | while read -r u; do print -r -- "  $u"; done
  if grep -qiE "未登录|登录已过期|session" "$result"; then
    echo
    c_yellow "以下平台登录态掉了，去对应平台重新登录后再补发："
    grep -E "✗" "$result" | grep -iE "未登录|过期|session" | while read -r l; do print -r -- "  $l"; done
  fi
  rm -f "$result"

  preflight_clean
  c_green "✓ 完成。所有平台均为草稿，最终发布请手动点。"
}

case "${1:-}" in
  check) shift; cmd_check "$@";;
  sync)  shift; cmd_sync "$@";;
  *)
    print "wechatsync 封装脚本 —— 底层用开源 wechatsync，外层加预检/清残留/白名单/链接解析。"
    print ""
    print "用法："
    print "  $0 check                       登录态预检（只读）"
    print "  $0 sync <article.md> [选项]      清残留→预检→同步草稿→报告→清理"
    print ""
    print "sync 选项：--title \"标题\"  --cover <图片>  --platforms a,b,c  --all-accounts  --dry-run"
    ;;
esac
