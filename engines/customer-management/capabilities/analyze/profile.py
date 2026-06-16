#!/usr/bin/env python3
"""
profile.py — 客户画像富化 analyze flow（原 llm_enrich.py，P3 收口）。

机器核（消息索引/规范化/增量窗口/staff 判定/call_kimi 包装/JSON 围栏）已抽到
`capabilities.analyze.core`，本模块只保留 profile 富化的**输出契约**：
按 FIELD_SPEC 应用 LLM 返回的 field_actions 到 all_student.json（append/replace/keep），
低置信进 pending/decisions.json。

任务卡 `cards/profile.md`（三要素）由 `capabilities.analyze.cards.load_card("profile")`
加载——SYSTEM_PROMPT 含 `{spec}` 占位，运行时注入 FIELD_SPEC.md（留 assistant_zh，经 config 读）。
编辑卡或 FIELD_SPEC 即生效。

用法（迁移后从 engine 根跑）:
    python3 -m capabilities.analyze.profile             # 增量,只跑有新消息的学员
    python3 -m capabilities.analyze.profile --bootstrap  # 全量 LLM (首次或 state 损坏)
    python3 -m capabilities.analyze.profile --limit 5    # 只跑前 5 个有新消息的(测试用)
    python3 -m capabilities.analyze.profile --wxid X     # 只跑指定 wxid (调试)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# engine 根（capabilities/analyze/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

# 统一机器核（增量窗口/消息索引+规范化/staff 判定/call_kimi/围栏剥离）
from capabilities.analyze import core
from capabilities.analyze.cards import load_card

BASE_DIR = config.BASE_DIR
DATA_DIR = config.DATA_DIR

STUDENT_FILE     = config.STUDENT_FILE
SPEC_FILE        = config.FIELD_SPEC_FILE
PROGRESS_FILE    = config.ENRICH_PROGRESS_FILE
PENDING_FILE     = config.DECISIONS_FILE
PARSE_FAIL_FILE  = config.PARSE_FAILURES_FILE
LOG_DIR          = config.LOG_DIR

CARD_NAME = "profile"

# 字段允许的 action(超出此范围的 LLM 建议会被拒绝)
FIELD_ACTIONS = {
    "wxid":            {"keep"},
    "微信昵称":         {"keep"},
    "其他名称":         {"append", "keep"},
    "手机号":           {"append", "keep"},
    "收货地址":         {"replace", "keep"},
    "所在群":           {"keep"},
    "学期":             {"replace", "keep"},
    "渠道":             {"replace", "keep"},
    "所属推广员":       {"replace", "keep"},
    "购买商品":         {"append", "keep"},
    "累计消费次数":     {"keep"},
    "累计有效消费金额": {"keep"},
    "最近消费时间":     {"replace", "keep"},
    "自我介绍":         {"append", "keep"},
    "复训":             {"append", "keep"},
    "加入的目的":       {"append", "keep"},
    "offer情况":        {"append", "keep"},
}

TEXT_SEPARATORS = {
    "其他名称":  ";",
    "手机号":    ";",
    "购买商品":  ";",
    "自我介绍":  "\n---\n",
    "offer情况": "\n---\n",
}

LIST_FIELDS = {"所在群", "复训", "加入的目的"}

SEMESTER_ORDER = {"1期":1, "2期":2, "3期":3, "4期":4, "4.5期":4.5, "5期":5, "AI产品训练营":0}

LIST_ENUM = {
    "复训":      {"1期","2期","3期","4期","4.5期","AI产品训练营"},
    "加入的目的": {"转型AI PM","副业","创业","AI PM提升"},
}

PHONE_RE = re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)')

# Confidence 阈值
APPLY_THRESHOLD = 0.7

# 上下文预算:每学员最多带多少条新消息 + 每条最多多少字（增量窗口参数）
MAX_MSGS_PER_STUDENT = 60
MAX_CHARS_PER_MSG = 800

# 默认起始日期: 只看 2026-04-01 之后的消息(避免老消息上下文成本/低价值)
DEFAULT_SINCE = "2026-04-01"


# --- I/O 工具 -----------------------------------------------------------

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_log(text: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    ts = datetime.now().strftime("%H:%M:%S")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {text}\n")


# --- Prompt 构造（任务卡 cards/profile.md）-----------------------------

def build_system_prompt() -> str:
    """卡里的 SYSTEM_PROMPT（含 {spec} 占位）→ 注入 FIELD_SPEC.md 全文。"""
    card = load_card(CARD_NAME)
    template = card.block("SYSTEM_PROMPT")
    spec_text = SPEC_FILE.read_text(encoding="utf-8")
    return template.format(spec=spec_text)


def build_user_prompt(student: dict, new_messages: list[dict], user_template: str, info_map: str = "") -> str:
    """卡里的 USER_PROMPT_TEMPLATE → 注入当前画像 + 增量窗口消息（前置自描述信息地图）。"""
    profile_view = {k: v for k, v in student.items() if k != "wxid"}
    msgs_text = "\n".join(
        f"[{m['ts_str']}] [{'张和/助理' if m['is_staff'] else '学员'}:{m['sender_name']}] {m['content']}"
        for m in new_messages
    )
    if info_map:
        msgs_text = info_map + "\n\n---\n\n" + msgs_text
    profile_json = "```json\n" + json.dumps(profile_view, ensure_ascii=False, indent=2) + "\n```"
    return user_template.format(
        WXID=student.get("wxid", ""),
        PROFILE_JSON=profile_json,
        MSG_COUNT=len(new_messages),
        MESSAGES=msgs_text,
    )


# --- Action 应用 --------------------------------------------------------

def apply_text_append(current: str, new_value: str, sep: str) -> str:
    new_value = (new_value or "").strip()
    if not new_value:
        return current
    current = (current or "").strip()
    if not current:
        return new_value
    if new_value in current:
        return current
    return current + sep + new_value


def apply_phone_append(current: str, new_value: Any) -> str:
    if isinstance(new_value, list):
        candidates = [str(v) for v in new_value]
    else:
        candidates = [str(new_value)]
    valid_new = []
    for c in candidates:
        for m in PHONE_RE.findall(c):
            if m not in valid_new:
                valid_new.append(m)
    if not valid_new:
        return current
    existing = []
    if current:
        for m in PHONE_RE.findall(current):
            if m not in existing:
                existing.append(m)
    for v in valid_new:
        if v not in existing:
            existing.append(v)
    return ";".join(existing)


def apply_list_append(current: list | None, new_value: Any, enum: set[str] | None) -> list:
    if isinstance(current, list):
        out = list(current)
    elif isinstance(current, str) and current:
        out = [current]
    else:
        out = []
    new_items = new_value if isinstance(new_value, list) else [new_value]
    for v in new_items:
        v = str(v).strip()
        if not v:
            continue
        if enum is not None and v not in enum:
            continue
        if v not in out:
            out.append(v)
    return out


def apply_replace(field: str, current: Any, new_value: Any) -> Any:
    if field == "学期":
        cur_order = SEMESTER_ORDER.get(current or "", -1)
        new_order = SEMESTER_ORDER.get(str(new_value) or "", -1)
        if new_order < 0:
            return current
        if cur_order >= 0 and new_order < cur_order:
            return current
        return str(new_value)
    if field == "最近消费时间":
        new_str = str(new_value).strip()
        if not re.match(r'^\d{4}-\d{2}-\d{2}', new_str):
            return current
        if current and current >= new_str[:10]:
            return current
        return new_str[:10]
    return new_value


def apply_action(student: dict, field: str, action_obj: dict) -> tuple[bool, str]:
    action = action_obj.get("action", "keep")
    if action == "keep":
        return False, "keep"
    allowed = FIELD_ACTIONS.get(field, set())
    if action not in allowed:
        return False, f"action={action} 不允许 (allowed: {allowed})"
    value = action_obj.get("value")
    if value is None or (isinstance(value, str) and not value.strip()):
        return False, "value 为空"
    current = student.get(field)
    if action == "append":
        if field == "手机号":
            new_val = apply_phone_append(current or "", value)
        elif field in LIST_FIELDS:
            new_val = apply_list_append(current, value, LIST_ENUM.get(field))
        else:
            sep = TEXT_SEPARATORS.get(field, ";")
            new_val = apply_text_append(current or "", str(value), sep)
    elif action == "replace":
        new_val = apply_replace(field, current, value)
    else:
        return False, f"未知 action={action}"
    if new_val == current:
        return False, "应用后无变化"
    student[field] = new_val
    return True, f"{action} → {repr(new_val)[:60]}"


# --- Pending 队列 -------------------------------------------------------

def queue_pending(wxid: str, low_conf: dict, raw_response: str) -> None:
    items = load_json(PENDING_FILE, [])
    items.append({
        "wxid": wxid,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "low_confidence_actions": low_conf,
        "raw_response_excerpt": raw_response[:1000],
    })
    save_json(PENDING_FILE, items)


def queue_parse_failure(wxid: str, raw_response: str, error: str) -> None:
    items = load_json(PARSE_FAIL_FILE, [])
    items.append({
        "wxid": wxid,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
        "raw_response": raw_response[:2000],
    })
    save_json(PARSE_FAIL_FILE, items)


# --- 主流程 -------------------------------------------------------------

def enrich(args: argparse.Namespace) -> int:
    if not STUDENT_FILE.exists():
        print(f"[ERROR] {STUDENT_FILE} 不存在,先跑 capabilities.recognize", file=sys.stderr)
        return 1
    if not SPEC_FILE.exists():
        print(f"[ERROR] {SPEC_FILE} 不存在", file=sys.stderr)
        return 1

    kb_paths = core.default_paths()
    core.load_env(kb_paths.env_file)
    if not os.environ.get("KIMI_API_KEY"):
        print("[ERROR] KIMI_API_KEY 未配置", file=sys.stderr)
        return 1

    # 任务卡：system（含 FIELD_SPEC）+ user 模板
    system_prompt = build_system_prompt()
    user_template = load_card(CARD_NAME).block("USER_PROMPT_TEMPLATE")

    students = json.loads(STUDENT_FILE.read_text(encoding="utf-8"))
    progress = load_json(PROGRESS_FILE, {}) if not args.bootstrap else {}
    msg_index = core.build_message_index()
    staff_wxids = core.load_staff_wxids()
    print(f"[profile] 加载助理 wxid: {len(staff_wxids)} 个 (用于 senderWxid 判定)")

    # 解析 since 截断时间（增量窗口下限）
    min_ts = 0
    if args.since:
        try:
            min_ts = int(datetime.strptime(args.since, "%Y-%m-%d").timestamp())
        except ValueError:
            print(f"[ERROR] --since 格式错误: {args.since!r}, 期望 YYYY-MM-DD", file=sys.stderr)
            return 1

    print(f"[profile] 学员: {len(students)} | 私聊文件: {len(msg_index)}")
    print(f"[profile] mode: {'bootstrap' if args.bootstrap else 'incremental'} | limit: {args.limit or '∞'} | since: {args.since or '不限'}")
    if args.dry_run:
        print(f"[profile] DRY RUN — 不调 Kimi,不写盘")

    targets = students
    if args.wxid:
        targets = [s for s in students if s["wxid"] == args.wxid]
        if not targets:
            print(f"[ERROR] 找不到 wxid={args.wxid}", file=sys.stderr)
            return 1

    stats = {"scanned": 0, "no_msg_file": 0, "no_new_msgs": 0, "llm_called": 0,
             "applied_changes": 0, "low_conf_queued": 0, "parse_failed": 0, "errors": 0}
    processed = 0

    for student in targets:
        wxid = student.get("wxid", "")
        if not wxid:
            continue
        stats["scanned"] += 1

        msg_file = core.find_message_file(student, msg_index)
        if not msg_file:
            stats["no_msg_file"] += 1
            continue

        # 增量窗口：last_seen + since 下限 + 最近 N 条（统一走机器核）
        last_seen = progress.get(wxid, {}).get("last_message_createTime", 0)
        raw = core.load_messages_raw(msg_file)
        all_msgs = (raw or {}).get("messages") or []
        normalized = core.normalize_messages(
            all_msgs, wxid, staff_wxids,
            min_ts=min_ts, max_chars_per_msg=MAX_CHARS_PER_MSG,
        )
        # L0 文字层做增量窗口/判断（保留旧行为）；信息地图描述全貌（含媒体/系统事件）
        new_msgs = core.select_increment_window(
            core.text_layer(normalized), last_seen_ts=last_seen, max_recent=MAX_MSGS_PER_STUDENT,
        )

        if not new_msgs:
            stats["no_new_msgs"] += 1
            continue

        if args.dry_run:
            print(f"  [{wxid}] {len(new_msgs)} 条新消息(DRY RUN, 不调 Kimi)")
            processed += 1
            if args.limit and processed >= args.limit:
                break
            continue

        user_prompt = build_user_prompt(student, new_msgs, user_template)
        stats["llm_called"] += 1

        try:
            raw_resp = core.call_kimi(system_prompt, user_prompt, temperature=0.2, json_mode=True)
        except core.KimiError as e:
            stats["errors"] += 1
            append_log(f"[ERROR] {wxid}: Kimi 调用失败 {e}")
            print(f"  [{wxid}] Kimi 失败: {e}", file=sys.stderr)
            continue
        except Exception as e:
            stats["errors"] += 1
            append_log(f"[ERROR] {wxid}: 未预期异常 {e}")
            print(f"  [{wxid}] 异常: {e}", file=sys.stderr)
            continue

        try:
            response = json.loads(core.strip_json_fence(raw_resp))
        except json.JSONDecodeError as e:
            stats["parse_failed"] += 1
            queue_parse_failure(wxid, raw_resp, str(e))
            append_log(f"[PARSE_FAIL] {wxid}: {e}")
            continue

        field_actions = response.get("field_actions", {})
        low_conf = {}
        applied_log = []
        for field, action_obj in field_actions.items():
            if not isinstance(action_obj, dict):
                continue
            conf = float(action_obj.get("confidence", 0))
            if conf < APPLY_THRESHOLD:
                if action_obj.get("action") != "keep":
                    low_conf[field] = action_obj
                continue
            changed, desc = apply_action(student, field, action_obj)
            if changed:
                stats["applied_changes"] += 1
                applied_log.append(f"{field}: {desc}")

        if low_conf:
            stats["low_conf_queued"] += 1
            queue_pending(wxid, low_conf, raw_resp)

        progress[wxid] = {
            "last_message_createTime": new_msgs[-1]["createTime"],
            "last_enriched_at": datetime.now(timezone.utc).isoformat(),
            "messages_seen": progress.get(wxid, {}).get("messages_seen", 0) + len(new_msgs),
        }

        if applied_log:
            append_log(f"[OK] {wxid}: " + " | ".join(applied_log))
            print(f"  [{wxid}] applied: {len(applied_log)} fields")

        processed += 1
        if args.limit and processed >= args.limit:
            print(f"[profile] reached --limit {args.limit}, stopping")
            break

        time.sleep(0.3)

    if not args.dry_run:
        save_json(STUDENT_FILE, students)
        save_json(PROGRESS_FILE, progress)

    print(f"\n[profile] DONE")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    append_log(f"[SUMMARY] {json.dumps(stats, ensure_ascii=False)}")
    return 0


def main():
    p = argparse.ArgumentParser(description="客户画像富化 — Kimi per-student 增量富化（任务卡: profile）")
    p.add_argument("--bootstrap", action="store_true", help="忽略 progress,全量重新跑")
    p.add_argument("--dry-run", action="store_true", help="不调 Kimi,只统计目标学员")
    p.add_argument("--limit", type=int, default=0, help="只跑前 N 个有新消息的学员(测试)")
    p.add_argument("--wxid", type=str, default="", help="只跑指定 wxid")
    p.add_argument("--since", type=str, default=DEFAULT_SINCE,
                   help=f"只看此日期之后的消息 YYYY-MM-DD (default: {DEFAULT_SINCE});传空字符串 '' 则不限")
    args = p.parse_args()
    sys.exit(enrich(args))


if __name__ == "__main__":
    main()
