#!/bin/bash
# 检查 gzh_scraper 微信 Cookie 是否过期
# 由系统 crontab 每3天调用一次

EXPORTER_URL="http://localhost:3000"
ROOT="/Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper"
CLI="$ROOT/scripts/cli.py"
CALENDAR_TASK="/Volumes/ExtSSD2601/AI_Assistant/tools/engines/calendar-task/calendar-task.sh"
LOG="/tmp/gzh-cookie-check.log"

notify() {
    local title="$1"
    local notes="$2"
    if [ -x "$CALENDAR_TASK" ]; then
        "$CALENDAR_TASK" --title "$title" --notes "$notes" --remind 5 --agent "system"
    else
        echo "$(date): $title - $notes" >> "$LOG"
    fi
}

# 确保 exporter 服务在运行
if ! python3 "$ROOT/scripts/gzh/exporter_service.py" --base-url "$EXPORTER_URL" >> "$LOG" 2>&1; then
    notify \
      "启动 exporter 服务失败" \
      "wechat-article-exporter 自动启动失败。日志: $ROOT/.runtime/exporter.log"
    echo "$(date): exporter 自动启动失败" >> "$LOG"
    exit 1
fi

# 检查认证状态
result=$(python3 "$CLI" check-auth 2>&1)
authenticated=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('authenticated', False))" 2>/dev/null)

if [ "$authenticated" != "True" ]; then
    notify \
      "公众号采集 Cookie 续期" \
      "微信 Cookie 已过期。步骤: 1. 打开 http://localhost:3000 扫码登录 2. 从浏览器 Cookie 拿 auth-key 3. 运行 set-auth-key"
    echo "$(date): Cookie 已过期，已创建日历提醒" >> "$LOG"
    exit 1
fi

echo "$(date): Cookie 有效" >> "$LOG"
