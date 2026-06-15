#!/usr/bin/env python3
"""
llm_enrich.py — Kimi per-student 增量富化

读 all_student.json,扫每个学员私聊新消息(createTime > state 里记的 last_seen),
调 Kimi 按 FIELD_SPEC.md 规则给出 field_actions,本地 Python 应用 actions 到记录上。
低置信(< 0.7) 的 action 进 pending/decisions.json。
state/enrich_progress.json 记 per-student 断点,下次只扫新消息。

用法:
    python3 -m student_manage.llm_enrich           # 增量,只跑有新消息的学员
    python3 -m student_manage.llm_enrich --bootstrap  # 全量 LLM (首次或 state 损坏)
    python3 -m student_manage.llm_enrich --limit 5    # 只跑前 5 个有新消息的(测试用)
    python3 -m student_manage.llm_enrich --wxid X     # 只跑指定 wxid (调试)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 复用 knowledge_base/ingest 的 Kimi client
sys.path.insert(0, "/Volumes/ExtSSD2601/AI_Assistant/assistant_zh")
from workflow.knowledge_ingest.core import call_kimi, load_env, default_paths, KimiError

BASE_DIR = Path("/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/student_manage")
DATA_DIR = Path("/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/raw/chat")

STUDENT_FILE     = BASE_DIR / "all_student.json"
SPEC_FILE        = BASE_DIR / "FIELD_SPEC.md"
CONFIG_FILE      = BASE_DIR / "feishu_config.json"
PROGRESS_FILE    = BASE_DIR / "state" / "enrich_progress.json"
PENDING_FILE     = BASE_DIR / "pending" / "decisions.json"
PARSE_FAIL_FILE  = BASE_DIR / "pending" / "parse_failures.json"
LOG_DIR          = BASE_DIR / "logs"

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

# 文本字段的 separator
TEXT_SEPARATORS = {
    "其他名称":  ";",
    "手机号":    ";",
    "购买商品":  ";",
    "自我介绍":  "\n---\n",
    "offer情况": "\n---\n",
}

LIST_FIELDS = {"所在群", "复训", "加入的目的"}

# 学期升级允许的转移
SEMESTER_ORDER = {"1期":1, "2期":2, "3期":3, "4期":4, "4.5期":4.5, "5期":5, "AI产品训练营":0}

# enum 集合(超出枚举的 list 值会被丢弃)
LIST_ENUM = {
    "复训":      {"1期","2期","3期","4期","4.5期","AI产品训练营"},
    "加入的目的": {"转型AI PM","副业","创业","AI PM提升"},
}

PHONE_RE = re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)')

_FENCE_RE = re.compile(r'^```(?:json)?\s*\n?(.*?)\n?```\s*$', re.DOTALL)


def strip_markdown_fence(s: str) -> str:
    """有时 Kimi 把 JSON 包在 ```json ... ``` 围栏里,剥掉。"""
    s = (s or "").strip()
    m = _FENCE_RE.match(s)
    return m.group(1).strip() if m else s

# Confidence 阈值
APPLY_THRESHOLD = 0.7

# 上下文预算:每学员最多带多少条新消息 + 每条最多多少字
MAX_MSGS_PER_STUDENT = 60
MAX_CHARS_PER_MSG = 800

# 默认起始日期: 只看 2026-04-01 之后的消息(避免老消息上下文成本/低价值)
# 可用 --since YYYY-MM-DD 覆盖
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


# --- 私聊消息文件索引 ---------------------------------------------------

def load_staff_wxids() -> set[str]:
    """从 staff_exclude.json 加载所有助理/张和的 wxid。
    用于在 load_new_messages 里识别 senderWxid (因为 isSelf 字段在 WeFlow 抽取时全是 0,失效)。
    """
    p = BASE_DIR / "staff_exclude.json"
    if not p.exists():
        return set()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {s["wxid"] for s in d.get("staff", []) if s.get("wxid")}
    except Exception:
        return set()


def build_message_index() -> dict[str, Path]:
    """index by userId(可能是 wxid 或 微信号)"""
    idx: dict[str, Path] = {}
    for fpath in glob.glob(str(DATA_DIR / "messages_user_*.json")):
        try:
            d = json.loads(Path(fpath).read_text(encoding="utf-8"))
            uid = d.get("userId", "")
            if uid:
                idx[uid] = Path(fpath)
        except Exception:
            continue
    return idx


def find_message_file(student: dict, msg_index: dict[str, Path]) -> Path | None:
    """优先按 wxid 找,其次按 其他名称 里的微信号找"""
    wxid = student.get("wxid", "")
    if wxid in msg_index:
        return msg_index[wxid]
    other = student.get("其他名称") or ""
    m = re.search(r'微信号:([^\s|]+)', other)
    if m and m.group(1) in msg_index:
        return msg_index[m.group(1)]
    return None


# --- 消息读取与过滤 -----------------------------------------------------

def try_decode_hex(content: str) -> str:
    if not content or len(content) < 20:
        return content
    if not re.match(r'^[0-9a-fA-F]+$', content) or len(content) % 2 != 0:
        return content
    try:
        return bytes.fromhex(content).decode('utf-8')
    except Exception:
        return content


def load_new_messages(msg_file: Path, last_seen_ts: int, min_ts: int = 0,
                      student_wxid: str = "", staff_wxids: set[str] | None = None) -> list[dict]:
    """返回 createTime > max(last_seen_ts, min_ts) 的消息(按时间升序),过滤系统消息/媒体占位。
    min_ts 用于硬截断老消息(节流 + 关注最近上下文)。

    is_staff 判定: WeFlow 抽出来的 isSelf 字段全是 0(失效),所以靠 senderWxid 判:
    - senderWxid == student_wxid → 学员自己
    - senderWxid in staff_wxids → 助理/张和
    - 其他 → 默认按学员处理(防误判)
    """
    staff_wxids = staff_wxids or set()
    try:
        d = json.loads(msg_file.read_text(encoding="utf-8"))
    except Exception:
        return []
    msgs = d.get("messages", [])
    threshold = max(last_seen_ts, min_ts)
    out = []
    for m in msgs:
        ts = m.get("createTime", 0)
        if not isinstance(ts, (int, float)) or ts <= threshold:
            continue
        msg_type = str(m.get("type", "1"))
        if msg_type not in ("1",):
            continue
        content = m.get("content", "")
        if not content or not isinstance(content, str):
            continue
        if content.startswith("[") and content.endswith("]"):
            continue
        content = try_decode_hex(content)
        if len(content) > MAX_CHARS_PER_MSG:
            content = content[:MAX_CHARS_PER_MSG] + "...[截断]"
        sender_wxid = m.get("senderWxid", "")
        if sender_wxid in staff_wxids:
            is_staff = 1
        elif student_wxid and sender_wxid == student_wxid:
            is_staff = 0
        else:
            # senderWxid 不明 (老数据/微信号 vs wxid 混用) → 用 senderName 关键词兜底
            sn = m.get("senderName", "") or ""
            is_staff = 1 if ("助理" in sn or "babamao" in sn.lower() or "张和" in sn) else 0
        out.append({
            "createTime": int(ts),
            "ts": m.get("createTimeStr", ""),
            "isSelf": is_staff,
            "sender": m.get("senderName", ""),
            "content": content,
        })
    out.sort(key=lambda x: x["createTime"])
    return out


# --- Prompt 构造 --------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """你是一个学员 CRM 数据补全助手。任务:读一个学员的当前画像 + 本周新私聊消息,
按下面的字段规范决定哪些字段需要更新。

规则:
1. 默认 keep,只在新消息里出现明确、相关、可核实的信号才返回 append/replace。
2. 信号模糊就 keep + 写较低 confidence,不要硬猜(让人工 triage 决定)。
3. confidence 必须 0.0-1.0,reason ≤ 30 字。
4. 严格遵循 FIELD_SPEC 里每个字段允许的 action 集合;超出范围的会被拒绝。
5. 必须只返回合法 JSON,不要任何解释性文本。

FIELD_SPEC:
{spec}

输出 JSON Schema:
{{
  "wxid": "<wxid>",
  "field_actions": {{
    "<字段名>": {{"action": "append"|"replace"|"keep", "value": <str|list>, "confidence": 0.0-1.0, "reason": "<≤30字>"}}
  }}
}}
"""


def build_user_prompt(student: dict, new_messages: list[dict]) -> str:
    # 当前画像(只挑相关字段,不带 wxid 噪音)
    profile_view = {k: v for k, v in student.items() if k != "wxid"}
    msgs_text = "\n".join(
        f"[{m['ts']}] [{'张和/助理' if m['isSelf'] else '学员'}:{m['sender']}] {m['content']}"
        for m in new_messages
    )
    return f"""学员 wxid: {student.get('wxid','')}

当前画像:
```json
{json.dumps(profile_view, ensure_ascii=False, indent=2)}
```

本周新私聊消息(共 {len(new_messages)} 条):
{msgs_text}

请输出 field_actions JSON。
"""


# --- Action 应用 --------------------------------------------------------

def apply_text_append(current: str, new_value: str, sep: str) -> str:
    """文本字段追加(去重子串)"""
    new_value = (new_value or "").strip()
    if not new_value:
        return current
    current = (current or "").strip()
    if not current:
        return new_value
    # 子串去重(简单)
    if new_value in current:
        return current
    return current + sep + new_value


def apply_phone_append(current: str, new_value: Any) -> str:
    """手机号字段:严格匹配 + 去重"""
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
    """list 字段 union(可选 enum 校验)"""
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
            continue  # 丢弃 enum 外的值
        if v not in out:
            out.append(v)
    return out


def apply_replace(field: str, current: Any, new_value: Any) -> Any:
    """覆盖语义,但学期字段做升级保护"""
    if field == "学期":
        cur_order = SEMESTER_ORDER.get(current or "", -1)
        new_order = SEMESTER_ORDER.get(str(new_value) or "", -1)
        if new_order < 0:
            return current
        if cur_order >= 0 and new_order < cur_order:
            return current  # 降级禁止
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
    """应用一个 action,返回 (是否真的改了, 描述)"""
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
        print(f"[ERROR] {STUDENT_FILE} 不存在,先跑 extract_students.py", file=sys.stderr)
        return 1
    if not SPEC_FILE.exists():
        print(f"[ERROR] {SPEC_FILE} 不存在", file=sys.stderr)
        return 1

    # 加载 Kimi env
    kb_paths = default_paths()
    load_env(kb_paths.env_file)
    if not os.environ.get("KIMI_API_KEY"):
        print("[ERROR] KIMI_API_KEY 未配置", file=sys.stderr)
        return 1

    spec_text = SPEC_FILE.read_text(encoding="utf-8")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(spec=spec_text)

    students = json.loads(STUDENT_FILE.read_text(encoding="utf-8"))
    progress = load_json(PROGRESS_FILE, {}) if not args.bootstrap else {}
    msg_index = build_message_index()
    staff_wxids = load_staff_wxids()
    print(f"[llm_enrich] 加载助理 wxid: {len(staff_wxids)} 个 (用于 senderWxid 判定)")

    # 解析 since 截断时间
    min_ts = 0
    if args.since:
        try:
            min_ts = int(datetime.strptime(args.since, "%Y-%m-%d").timestamp())
        except ValueError:
            print(f"[ERROR] --since 格式错误: {args.since!r}, 期望 YYYY-MM-DD", file=sys.stderr)
            return 1

    print(f"[llm_enrich] 学员: {len(students)} | 私聊文件: {len(msg_index)}")
    print(f"[llm_enrich] mode: {'bootstrap' if args.bootstrap else 'incremental'} | limit: {args.limit or '∞'} | since: {args.since or '不限'}")
    if args.dry_run:
        print(f"[llm_enrich] DRY RUN — 不调 Kimi,不写盘")

    # 过滤目标学员
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

        msg_file = find_message_file(student, msg_index)
        if not msg_file:
            stats["no_msg_file"] += 1
            continue

        last_seen = progress.get(wxid, {}).get("last_message_createTime", 0)
        new_msgs = load_new_messages(msg_file, last_seen, min_ts=min_ts,
                                     student_wxid=wxid, staff_wxids=staff_wxids)

        if not new_msgs:
            stats["no_new_msgs"] += 1
            continue

        # 取最近 N 条(尾部 = 最新)
        if len(new_msgs) > MAX_MSGS_PER_STUDENT:
            new_msgs = new_msgs[-MAX_MSGS_PER_STUDENT:]

        if args.dry_run:
            print(f"  [{wxid}] {len(new_msgs)} 条新消息(DRY RUN, 不调 Kimi)")
            processed += 1
            if args.limit and processed >= args.limit:
                break
            continue

        user_prompt = build_user_prompt(student, new_msgs)
        stats["llm_called"] += 1

        try:
            raw = call_kimi(system_prompt, user_prompt, temperature=0.2, json_mode=True)
        except KimiError as e:
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
            response = json.loads(strip_markdown_fence(raw))
        except json.JSONDecodeError as e:
            stats["parse_failed"] += 1
            queue_parse_failure(wxid, raw, str(e))
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
            queue_pending(wxid, low_conf, raw)

        # 推进 progress
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
            print(f"[llm_enrich] reached --limit {args.limit}, stopping")
            break

        # 节流:每学员之间 sleep,避免 Kimi rate limit
        time.sleep(0.3)

    # 落盘
    if not args.dry_run:
        save_json(STUDENT_FILE, students)
        save_json(PROGRESS_FILE, progress)

    print(f"\n[llm_enrich] DONE")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    append_log(f"[SUMMARY] {json.dumps(stats, ensure_ascii=False)}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Kimi per-student 增量富化")
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
