#!/bin/bash
# calendar-task: 往 Apple 日历添加任务事件
# 所有 assistant 共用，统一在日历中给用户安排待办
#
# 用法:
#   calendar-task.sh --title "标题" [--notes "备注"] [--time "2026-04-08 14:00"] [--remind 15] [--all-day] [--agent "assistant_zh"]
#
# 参数:
#   --title     事件标题（必填）
#   --notes     事件备注（选填）
#   --time      事件时间，格式 "YYYY-MM-DD HH:MM"（选填，默认当前时间+1小时）
#   --remind    提前提醒分钟数（选填，默认15）
#   --all-day   全天事件（选填）
#   --agent     来源 agent 名称，会追加到标题前缀（选填）

CALENDAR_NAME="工作"

# 解析参数
TITLE=""
NOTES=""
EVENT_TIME=""
REMIND=15
ALL_DAY=false
AGENT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --title) TITLE="$2"; shift 2 ;;
        --notes) NOTES="$2"; shift 2 ;;
        --time) EVENT_TIME="$2"; shift 2 ;;
        --remind) REMIND="$2"; shift 2 ;;
        --all-day) ALL_DAY=true; shift ;;
        --agent) AGENT="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

if [ -z "$TITLE" ]; then
    echo '{"success": false, "error": "缺少 --title 参数"}'
    exit 1
fi

# 加 agent 前缀
if [ -n "$AGENT" ]; then
    TITLE="[$AGENT] $TITLE"
fi

# 处理时间
if [ -z "$EVENT_TIME" ]; then
    # 默认1小时后
    START_DATE=$(date -v+1H "+%Y-%m-%d %H:%M")
else
    START_DATE="$EVENT_TIME"
fi

# 构造 AppleScript
if [ "$ALL_DAY" = true ]; then
    # 全天事件
    APPLESCRIPT=$(cat <<OSASCRIPT
tell application "Calendar"
    tell calendar "$CALENDAR_NAME"
        set newEvent to make new event with properties {summary:"$TITLE", start date:date "$START_DATE", allday event:true}
        tell newEvent
            set description to "$NOTES"
            make new display alarm at end of display alarms with properties {trigger interval:-${REMIND}}
        end tell
    end tell
end tell
return "ok"
OSASCRIPT
)
else
    # 定时事件（1小时时长）
    APPLESCRIPT=$(cat <<OSASCRIPT
tell application "Calendar"
    tell calendar "$CALENDAR_NAME"
        set startDate to date "$START_DATE"
        set endDate to startDate + 60 * 60
        set newEvent to make new event with properties {summary:"$TITLE", start date:startDate, end date:endDate}
        tell newEvent
            set description to "$NOTES"
            make new display alarm at end of display alarms with properties {trigger interval:-${REMIND}}
        end tell
    end tell
end tell
return "ok"
OSASCRIPT
)
fi

result=$(osascript -e "$APPLESCRIPT" 2>&1)

if [ "$result" = "ok" ]; then
    echo "{\"success\": true, \"title\": \"$TITLE\", \"time\": \"$START_DATE\", \"calendar\": \"$CALENDAR_NAME\", \"remind_minutes\": $REMIND}"
else
    echo "{\"success\": false, \"error\": \"$result\"}"
    exit 1
fi
