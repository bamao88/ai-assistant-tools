"""
employment.py — 就业回访 analyze flow（原 analyze.py，P3 收口）。

机器核（消息读取/规范化/增量窗口/staff 判定/call_llm 包装/JSON 围栏）已抽到
`capabilities.analyze.core`，本模块只保留就业回访的**输出契约**：
AnalysisResult / 未回访 stub / rerun reset / latest+per_student+runs 产物 / 报告。

任务卡 `cards/employment.md`（三要素）由 `capabilities.analyze.cards.load_card("employment")`
加载——提示词、输出契约、写回规矩、先过滤门都在卡里，编辑卡即生效。

用法（迁移后从 engine 根跑）：
  python3 -m capabilities.analyze.employment --dry-run
  python3 -m capabilities.analyze.employment --wxid <wxid>
  python3 -m capabilities.analyze.employment --sample 10
  python3 -m capabilities.analyze.employment --auto
  python3 -m capabilities.analyze.employment --bootstrap
  python3 -m capabilities.analyze.employment --force-rerun-all
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# engine 根（capabilities/analyze/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

# 统一机器核（增量窗口/消息规范化/staff 判定/call_llm/围栏剥离 + 通用 JSON IO）
from capabilities.analyze import core
from capabilities.analyze.core import load_json, save_json
from capabilities.analyze.cards import load_card

PROJECT_ROOT = config.PROJECT_ROOT

# --- 路径（经 config 收口）-------------------------------------------------

CHAT_DIR = config.CHAT_DIR
STUDENT_FILE = config.STUDENT_FILE
STAFF_FILE = config.STAFF_EXCLUDE_FILE
STATE_DIR = config.STATE_DIR
PROGRESS_FILE = config.EMPLOYMENT_PROGRESS_FILE
LATEST_FILE = config.EMPLOYMENT_LATEST_FILE
ANALYTICS_DIR = config.EMPLOYMENT_ANALYTICS_DIR
PER_STUDENT_DIR = config.EMPLOYMENT_PER_STUDENT_DIR
RUNS_DIR = config.EMPLOYMENT_RUNS_DIR

CARD_NAME = "employment"


# --- 配置 ---------------------------------------------------------------

MAX_TRANSCRIPT_CHARS = 80_000   # ~40K 中文 tokens
TRUNCATE_KEEP_EARLY = 3          # 截断时保留最早 N 条作为上下文
TRUNCATE_RECENT_DAYS = 180       # 保留最近 6 个月

FORCE_RERUN_DAYS = 60            # 距上次跑超过这个天数即使无新消息也重跑
LOW_CONFIDENCE_THRESHOLD = 0.7

INTER_CALL_SLEEP_SEC = 0.5       # LLM 调用之间的节流

TRANSITION_OUTCOMES = {
    "已成功入职", "已入职", "谈薪中", "进行中", "暂停", "放弃",
    "本身已是AI PM", "不打算转型", "不明", "未回访",
}

# 严格 exact match：助理对该学员发过这句开场白才算已回访（先过滤门，gate=follow_up_exact_match）
FOLLOW_UP_TRIGGER = "同学，回访一下，最近面试和求职情况怎么样呢？"


# --- 数据类 -------------------------------------------------------------

@dataclass
class AnalysisResult:
    wxid: str
    display_name: str
    run_id: str
    analyzed_at: str
    got_offer: bool
    transition_outcome: str
    customer_profile_append: str
    remark_append: str
    customer_profile_has_new_info: bool
    confidence: float
    evidence_message_count: int
    transcript_truncated: bool
    needs_review: bool
    changed_from_last_run: dict
    message_count: int


@dataclass
class SkipRecord:
    wxid: str
    reason: str
    detail: str = ""


@dataclass
class RunStats:
    run_id: str
    mode: str
    started_at: str
    universe_size: int = 0
    analyzed: int = 0
    skipped: int = 0
    parse_failed: int = 0
    low_confidence: int = 0
    llm_errors: int = 0
    elapsed_seconds: float = 0.0


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


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class RunLogger:
    """行级 run.log 写入器。"""

    def __init__(self, log_path: Path):
        self.path = log_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def log(self, level: str, event: str, **kwargs):
        ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        parts = [ts, f"{level:<5}", event]
        for k, v in kwargs.items():
            parts.append(f"{k}={v}")
        line = " ".join(str(p) for p in parts)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self):
        self._fh.close()


# --- 任务卡（提示词三块）-----------------------------------------------

def parse_prompt_template() -> tuple[str, str, str]:
    """从 cards/employment.md 抽出 SYSTEM、USER、PREVIOUS_CONTEXT 三块提示词。

    P3：改由任务卡加载器读取（原直接 re.findall fenced 块）。card 用
    `## SYSTEM_PROMPT / ## USER_PROMPT_TEMPLATE / ## ...PREVIOUS_CONTEXT...` 标记。
    """
    card = load_card(CARD_NAME)
    # 按文档顺序取前 3 个 fenced 块（SYSTEM / USER / PREVIOUS_CONTEXT），
    # 与旧 analyze.py 的 re.findall(r"```\n(.*?)\n```") 顺序一致（PREV 与 USER 同段）。
    ordered = card.ordered_blocks
    if len(ordered) < 3:
        raise RuntimeError(
            f"任务卡 {CARD_NAME} 需要 ≥3 个 fenced 提示词块"
            f"（SYSTEM、USER、PREVIOUS_CONTEXT），找到 {len(ordered)}"
        )
    return ordered[0], ordered[1], ordered[2]


# --- 学员档案 + 助理识别 ------------------------------------------------

def build_student_lookup() -> dict[str, dict]:
    """all_student.json 按 wxid 索引 + 按 其他名称.微信号 别名索引。"""
    students = load_json(STUDENT_FILE, [])
    if not isinstance(students, list):
        return {}
    lookup: dict[str, dict] = {}
    for s in students:
        wxid = s.get("wxid", "")
        if wxid:
            lookup[wxid] = s
        other = s.get("其他名称") or ""
        import re
        m = re.search(r"微信号[:：]([^\s|]+)", other)
        if m:
            lookup.setdefault(m.group(1), s)
    return lookup


def profile_subset_for_prompt(student: dict | None) -> dict:
    """挑出 LLM 真正需要的 hint 字段；剔除手机号/收货地址等不相关字段以降本。"""
    if not student:
        return {"备注": "无对应学员档案"}
    hint_fields = ["微信昵称", "学期", "加入的目的", "自我介绍", "offer情况",
                   "所属推广员", "所在群", "购买商品", "复训", "最近消费时间"]
    return {k: v for k, v in student.items() if k in hint_fields and v not in (None, "", [])}


# --- 消息读取（机器核 + 就业专用 universe）-----------------------------

def build_wxid_universe() -> list[str]:
    """扫 chat dir，返回所有 messages_user_<wxid>.json 的 wxid。"""
    import glob
    pattern = str(CHAT_DIR / "messages_user_*.json")
    wxids: list[str] = []
    for fpath in sorted(glob.glob(pattern)):
        name = Path(fpath).stem  # messages_user_xxx
        if name.startswith("messages_user_"):
            wxids.append(name[len("messages_user_"):])
    return wxids


def load_messages(wxid: str) -> dict | None:
    return core.load_messages_raw(CHAT_DIR / f"messages_user_{wxid}.json")


def normalize_messages(raw: list[dict], student_wxid: str, staff_wxids: set[str]) -> list[dict]:
    """就业回访的规范化口径：保留 < 30 字的媒体占位剔除（保留长内容）、不单条截断、不设 since 下限。

    机器核 normalize_messages 的字段名（ts_str/is_staff/sender_name）即就业旧实现的字段名。
    """
    return core.normalize_messages(
        raw, student_wxid, staff_wxids,
        min_ts=0, max_chars_per_msg=None, media_placeholder_max_len=30,
    )


def detect_follow_up_sent(normalized_messages: list[dict]) -> tuple[bool, str | None]:
    """先过滤门（gate）：助理是否对该学员发过回访开场白（严格 exact match）。

    返回 (sent, first_send_date)。first_send_date 是首次发送日期 YYYY-MM-DD。
    """
    for m in normalized_messages:
        if not m.get("is_staff"):
            continue
        if FOLLOW_UP_TRIGGER in (m.get("content") or ""):
            ts = m.get("createTime", 0)
            date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else None
            return True, date
    return False, None


def build_not_followed_up_result(
    *,
    wxid: str,
    display_name: str,
    msg_count: int,
    student: dict | None,
    prev_outcome: str | None,
    run_id: str,
    analyzed_at: str,
) -> AnalysisResult:
    """未回访学员的 stub 结果，不调 LLM（write_policy 语义：备注=append 时间线，画像=只在状态转移时首次写）。"""
    is_state_transition = prev_outcome != "未回访"

    remark = (
        f"[{analyzed_at} AI回访分析]\n"
        f"转型结果：未回访\n"
        f"求职阶段：不适用\n"
        f"收到 offer：未回访\n"
        f"卡点：无\n"
        f"副业/创业进展：不适用\n"
        f"情绪：中性\n"
        f"关键证据：本次扫描未匹配到回访开场白「{FOLLOW_UP_TRIGGER}」，视为未触达。"
    )

    if is_state_transition:
        purpose = (student or {}).get("加入的目的") or "未填写"
        profile = (
            f"[{analyzed_at} AI回访分析]\n"
            f"加入目的：{purpose}\n"
            f"背景画像：未回访，暂未触达画像信息\n"
            f"训练营归因：未明确表达\n"
            f"续报意愿：未表达\n"
            f"建议运营动作：唤醒触达"
        )
    else:
        profile = ""

    return AnalysisResult(
        wxid=wxid,
        display_name=display_name,
        run_id=run_id,
        analyzed_at=analyzed_at,
        got_offer=False,
        transition_outcome="未回访",
        customer_profile_append=profile,
        remark_append=remark,
        customer_profile_has_new_info=is_state_transition,
        confidence=1.0,
        evidence_message_count=0,
        transcript_truncated=False,
        needs_review=False,
        changed_from_last_run={},
        message_count=msg_count,
    )


def build_transcript(messages: list[dict]) -> tuple[str, bool, int]:
    """拼成 LLM 可读的 transcript。返回 (text, truncated, evidence_count)。"""
    if not messages:
        return "（无可用对话内容）", False, 0

    def format_one(m: dict) -> str:
        role = "助理" if m["is_staff"] else "学员"
        dt = datetime.fromtimestamp(m["createTime"])
        ts_display = dt.strftime("%Y-%m-%d %H:%M")
        return f"[{ts_display}] [{role}] {m['content']}"

    full_lines = [format_one(m) for m in messages]
    full_text = "\n".join(full_lines)
    if len(full_text) <= MAX_TRANSCRIPT_CHARS:
        return full_text, False, len(messages)

    # 需要截断：保留最早 N 条 + 最近 6 个月内尽可能多的消息
    cutoff_ts = int((datetime.now() - timedelta(days=TRUNCATE_RECENT_DAYS)).timestamp())
    early_msgs = messages[:TRUNCATE_KEEP_EARLY]
    recent_msgs = [m for m in messages[TRUNCATE_KEEP_EARLY:] if m["createTime"] >= cutoff_ts]

    early_text = "\n".join(format_one(m) for m in early_msgs)
    recent_text = "\n".join(format_one(m) for m in recent_msgs)

    while len(early_text) + len(recent_text) + 100 > MAX_TRANSCRIPT_CHARS and recent_msgs:
        cut_count = max(1, len(recent_msgs) // 10)
        recent_msgs = recent_msgs[cut_count:]
        recent_text = "\n".join(format_one(m) for m in recent_msgs)

    truncated_text = (
        f"{early_text}\n"
        f"\n[…中间省略 {len(messages) - len(early_msgs) - len(recent_msgs)} 条历史消息…]\n\n"
        f"{recent_text}"
    )
    return truncated_text, True, len(early_msgs) + len(recent_msgs)


# --- 增量判断 -----------------------------------------------------------

def should_skip_for_auto(wxid: str, msg_data: dict | None, progress: dict, mode: str) -> tuple[bool, str]:
    """返回 (skip, reason)。reason 用于 skipped.json。"""
    if mode in ("force_rerun_all", "bootstrap", "rerun_not_followed_up", "wxid"):
        return False, ""
    if msg_data is None:
        return True, "file_missing"

    last = progress.get(wxid)
    if not last:
        return False, ""

    last_count = last.get("last_message_count", 0)
    cur_count = msg_data.get("total", 0)
    cur_msgs = msg_data.get("messages") or []
    cur_latest_ts = max((m.get("createTime", 0) for m in cur_msgs), default=0)
    last_latest_ts = last.get("last_message_timestamp", 0)
    last_run_at = last.get("last_run_at", "")

    if last_run_at:
        try:
            last_dt = datetime.fromisoformat(last_run_at)
            if datetime.now(last_dt.tzinfo) - last_dt > timedelta(days=FORCE_RERUN_DAYS):
                return False, ""
        except ValueError:
            pass

    if cur_count == last_count:
        return True, "no_new_messages"
    if cur_latest_ts <= last_latest_ts and cur_count > 0:
        return True, "no_newer_messages"
    return False, ""


# --- LLM 解析 -----------------------------------------------------------

def parse_llm_response(raw: str) -> tuple[dict | None, str]:
    """返回 (parsed_dict, error_msg)。parsed_dict 为 None 时 error_msg 描述原因。"""
    if not raw or not raw.strip():
        return None, "empty response"
    text = core.strip_json_fence(raw)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"json decode: {e}"
    if not isinstance(obj, dict):
        return None, "response not an object"
    required = ["got_offer", "transition_outcome", "customer_profile_append",
                "remark_append", "customer_profile_has_new_info", "confidence"]
    for k in required:
        if k not in obj:
            return None, f"missing field: {k}"
    if obj["transition_outcome"] not in TRANSITION_OUTCOMES:
        obj["transition_outcome"] = "不明"
    try:
        obj["confidence"] = float(obj["confidence"])
    except (TypeError, ValueError):
        obj["confidence"] = 0.0
    obj["got_offer"] = bool(obj.get("got_offer"))
    obj["customer_profile_has_new_info"] = bool(obj.get("customer_profile_has_new_info"))
    obj.setdefault("evidence_message_count", 0)
    return obj, ""


# --- 主分析 -------------------------------------------------------------

def analyze_one(
    wxid: str,
    msg_data: dict,
    student: dict | None,
    last_result: dict | None,
    system_prompt: str,
    user_template: str,
    prev_context_template: str,
    staff_wxids: set[str],
    run_id: str,
    analyzed_at: str,
    logger: RunLogger,
    dry_run: bool,
) -> tuple[AnalysisResult | None, str]:
    """单人分析。返回 (result, error_msg)。dry_run 时不调 LLM，返回 None + "dry_run"。"""
    student_wxid = (student or {}).get("wxid") or wxid
    raw_msgs = msg_data.get("messages") or []
    norm = normalize_messages(raw_msgs, student_wxid, staff_wxids)  # 无损分层
    txt = core.text_layer(norm)  # L0 文字层：判断/transcript 仍只看文字（保留旧行为）
    display_name = msg_data.get("userName") or (student or {}).get("微信昵称") or wxid

    # 先过滤门：未发过回访开场白 → 不调 LLM，直接 stub
    followed_up, follow_up_date = detect_follow_up_sent(txt)
    if not followed_up:
        prev_outcome = (last_result or {}).get("transition_outcome")
        if dry_run:
            logger.log("INFO", "DRY_PLAN_NOT_FOLLOWED_UP", wxid=wxid, msg_count=len(txt))
            return None, "dry_run"
        result = build_not_followed_up_result(
            wxid=wxid, display_name=display_name, msg_count=len(txt),
            student=student, prev_outcome=prev_outcome,
            run_id=run_id, analyzed_at=analyzed_at,
        )
        logger.log("INFO", "NOT_FOLLOWED_UP", wxid=wxid, msg_count=len(txt),
                   prev_outcome=prev_outcome or "(none)")
        return result, ""

    transcript, truncated, ev_count = build_transcript(txt)
    # 自描述信息地图：让 LLM 知道还有图片/语音/系统事件等可调取（默认只喂了文字）
    transcript = core.build_info_map(norm) + "\n\n---\n\n" + transcript

    if dry_run:
        logger.log("INFO", "DRY_PLAN", wxid=wxid, msg_count=len(norm),
                   transcript_chars=len(transcript), truncated=truncated,
                   follow_up_date=follow_up_date or "(unknown)")
        return None, "dry_run"

    profile = profile_subset_for_prompt(student)
    is_first_time = not last_result
    if last_result:
        prev_context = prev_context_template.format(
            LAST_CUSTOMER_PROFILE=last_result.get("customer_profile_full", "(空)") or "(空)",
            LAST_REMARK=last_result.get("remark_full", "(空)") or "(空)",
            LAST_GOT_OFFER=last_result.get("got_offer", "未知"),
            LAST_TRANSITION_OUTCOME=last_result.get("transition_outcome", "未知"),
        )
    else:
        prev_context = (
            "本次为该学员首次分析，无历史画像可参照。\n"
            "`customer_profile_has_new_info` 必须设为 true。\n"
            "`customer_profile_append` 必须按完整模板输出（不要留空字符串）。"
        )

    user_prompt = user_template.format(
        STUDENT_PROFILE_JSON=json.dumps(profile, ensure_ascii=False, indent=2),
        PREVIOUS_CONTEXT_BLOCK=prev_context,
        TRANSCRIPT=transcript,
        ANALYZED_AT=analyzed_at,
    )
    system_prompt_filled = system_prompt.replace("{ANALYZED_AT}", analyzed_at)

    logger.log("INFO", "ANALYZE_START", wxid=wxid, msg_count=len(norm),
               transcript_chars=len(transcript), truncated=truncated)
    started = time.time()
    try:
        raw = core.call_llm(system_prompt_filled, user_prompt, temperature=0.2, json_mode=True)
    except core.LLMError as e:
        logger.log("ERROR", "LLM_FAIL", wxid=wxid, err=str(e)[:200])
        return None, f"llm: {e}"
    elapsed_ms = int((time.time() - started) * 1000)

    parsed, err = parse_llm_response(raw)
    if parsed is None:
        logger.log("WARN", "PARSE_FAIL", wxid=wxid, err=err, retry=1)
        try:
            raw2 = core.call_llm(system_prompt_filled, user_prompt, temperature=0.2, json_mode=True)
            parsed, err = parse_llm_response(raw2)
        except core.LLMError as e:
            return None, f"llm retry: {e}"
        if parsed is None:
            logger.log("ERROR", "PARSE_FAIL_FINAL", wxid=wxid, err=err)
            return None, f"parse: {err}"

    if is_first_time and parsed.get("customer_profile_append"):
        parsed["customer_profile_has_new_info"] = True

    changed = {}
    if last_result:
        if last_result.get("got_offer") != parsed["got_offer"]:
            changed["got_offer"] = {"from": last_result.get("got_offer"), "to": parsed["got_offer"]}
        if last_result.get("transition_outcome") != parsed["transition_outcome"]:
            changed["transition_outcome"] = {
                "from": last_result.get("transition_outcome"),
                "to": parsed["transition_outcome"],
            }

    confidence = parsed["confidence"]
    needs_review = confidence < LOW_CONFIDENCE_THRESHOLD

    result = AnalysisResult(
        wxid=wxid,
        display_name=display_name,
        run_id=run_id,
        analyzed_at=analyzed_at,
        got_offer=parsed["got_offer"],
        transition_outcome=parsed["transition_outcome"],
        customer_profile_append=parsed["customer_profile_append"] or "",
        remark_append=parsed["remark_append"] or "",
        customer_profile_has_new_info=parsed["customer_profile_has_new_info"],
        confidence=confidence,
        evidence_message_count=int(parsed.get("evidence_message_count") or ev_count),
        transcript_truncated=truncated,
        needs_review=needs_review,
        changed_from_last_run=changed,
        message_count=len(norm),
    )
    logger.log("INFO", "ANALYZE_OK", wxid=wxid, got_offer=parsed["got_offer"],
               outcome=parsed["transition_outcome"], confidence=f"{confidence:.2f}",
               elapsed_ms=elapsed_ms, outcome_changed=bool(changed))
    if needs_review:
        logger.log("WARN", "LOW_CONFIDENCE", wxid=wxid, confidence=f"{confidence:.2f}")
    return result, ""


# --- 状态更新 -----------------------------------------------------------

def handle_rerun_not_followed_up(
    *,
    wxid: str,
    msg_data: dict,
    student: dict | None,
    last_result: dict | None,
    staff_wxids: set[str],
    run_id: str,
    analyzed_at: str,
) -> tuple[AnalysisResult | None, SkipRecord | None]:
    """--rerun-not-followed-up 专用：判断是否走 reset 路径（write_policy.reset）。"""
    student_wxid = (student or {}).get("wxid") or wxid
    raw_msgs = msg_data.get("messages") or []
    txt = core.text_layer(normalize_messages(raw_msgs, student_wxid, staff_wxids))
    followed_up, _ = detect_follow_up_sent(txt)
    if followed_up:
        return None, SkipRecord(wxid=wxid, reason="already_followed_up")
    if (last_result or {}).get("transition_outcome") == "未回访":
        return None, SkipRecord(wxid=wxid, reason="already_marked_not_followed_up")
    display_name = msg_data.get("userName") or (student or {}).get("微信昵称") or wxid
    result = build_not_followed_up_result(
        wxid=wxid, display_name=display_name, msg_count=len(txt),
        student=student, prev_outcome=None,
        run_id=run_id, analyzed_at=analyzed_at,
    )
    return result, None


def reset_latest_entry(latest: dict, result: AnalysisResult) -> None:
    """rerun_not_followed_up 专用：直接覆盖 latest entry（write_policy.reset）。"""
    latest[result.wxid] = {
        "wxid": result.wxid,
        "display_name": result.display_name,
        "got_offer": False,
        "transition_outcome": "未回访",
        "confidence": 1.0,
        "last_run_id": result.run_id,
        "last_analyzed_at": result.analyzed_at,
        "needs_review": False,
        "customer_profile_full": result.customer_profile_append,
        "remark_full": result.remark_append,
    }


def update_progress_entry(progress: dict, wxid: str, result: AnalysisResult,
                          msg_data: dict, last_msg_ts: int) -> None:
    progress[wxid] = {
        "last_run_id": result.run_id,
        "last_run_at": result.analyzed_at + "T00:00:00",
        "last_message_count": msg_data.get("total", 0),
        "last_message_timestamp": last_msg_ts,
        "last_got_offer": result.got_offer,
        "last_transition_outcome": result.transition_outcome,
        "last_confidence": result.confidence,
        "total_runs": progress.get(wxid, {}).get("total_runs", 0) + 1,
    }


def update_latest_entry(latest: dict, wxid: str, result: AnalysisResult) -> None:
    """latest.json 累积维度：full append 文本（按时间序拼接）+ 当前快照（write_policy.append）。"""
    prev = latest.get(wxid, {})
    prev_profile_full = prev.get("customer_profile_full", "")
    prev_remark_full = prev.get("remark_full", "")

    new_profile = prev_profile_full
    if result.customer_profile_has_new_info and result.customer_profile_append:
        sep = "\n\n" if prev_profile_full else ""
        new_profile = prev_profile_full + sep + result.customer_profile_append

    new_remark = prev_remark_full
    if result.remark_append:
        sep = "\n\n" if prev_remark_full else ""
        new_remark = prev_remark_full + sep + result.remark_append

    latest[wxid] = {
        "wxid": result.wxid,
        "display_name": result.display_name,
        "got_offer": result.got_offer,
        "transition_outcome": result.transition_outcome,
        "confidence": result.confidence,
        "last_run_id": result.run_id,
        "last_analyzed_at": result.analyzed_at,
        "needs_review": result.needs_review,
        "customer_profile_full": new_profile,
        "remark_full": new_remark,
    }


def write_per_student_history(result: AnalysisResult, msg_count_delta: int,
                              prev_got_offer: bool | None, prev_outcome: str | None) -> None:
    line = {
        "run_id": result.run_id,
        "analyzed_at": result.analyzed_at,
        "message_count": result.message_count,
        "message_count_delta": msg_count_delta,
        "got_offer": result.got_offer,
        "got_offer_changed_from": prev_got_offer,
        "transition_outcome": result.transition_outcome,
        "transition_outcome_changed_from": prev_outcome,
        "confidence": result.confidence,
        "customer_profile_append_chars": len(result.customer_profile_append),
        "remark_append_chars": len(result.remark_append),
        "transcript_truncated": result.transcript_truncated,
        "needs_review": result.needs_review,
    }
    append_jsonl(PER_STUDENT_DIR / f"{result.wxid}.jsonl", line)


# --- 报告 ---------------------------------------------------------------

import re

OFFER_COMPANY_RE = re.compile(r"收到\s*offer[:：]\s*(.+?)(?:\n|$)", re.IGNORECASE)


def extract_offer_companies(remark: str) -> list[str]:
    """从 remark_append 的"收到 offer：..." 行解析公司列表。"""
    m = OFFER_COMPANY_RE.search(remark or "")
    if not m:
        return []
    seg = m.group(1).strip()
    if seg in ("暂无", "无", "未透露公司", "对话未提及", "未回访"):
        return []
    parts = re.split(r"[,，、;；]+", seg)
    out = []
    for p in parts:
        p = re.sub(r"^[\d个]+\s*[（(]?", "", p).strip(" ()（）。")
        if p and p not in out:
            out.append(p)
    return out


def write_changes_md(run_dir: Path, results: list[AnalysisResult],
                     latest_before: dict, skipped: list[SkipRecord]) -> None:
    sections = {
        "new_offers": [],
        "offer_lost": [],
        "outcome_changes": [],
        "new_needs_review": [],
        "new_dormant": [],
        "new_not_followed_up": [],
        "newly_followed_up": [],
    }

    for r in results:
        prev = latest_before.get(r.wxid, {})
        prev_offer = prev.get("got_offer")
        prev_outcome = prev.get("transition_outcome")
        if prev_outcome != "未回访" and r.transition_outcome == "未回访":
            sections["new_not_followed_up"].append(r)
        elif prev_outcome == "未回访" and r.transition_outcome != "未回访":
            sections["newly_followed_up"].append((r, prev_outcome))
        elif prev_offer is False and r.got_offer is True:
            sections["new_offers"].append(r)
        elif prev_offer is True and r.got_offer is False:
            sections["offer_lost"].append(r)
        elif prev_outcome and prev_outcome != r.transition_outcome:
            sections["outcome_changes"].append((r, prev_outcome))
        if r.needs_review and not prev.get("needs_review"):
            sections["new_needs_review"].append(r)

    lines = [f"# {run_dir.name} 增量分析变更摘要", "",
             f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

    lines.append("## 转型成功新发现（got_offer: false → true）")
    if sections["new_offers"]:
        for r in sections["new_offers"]:
            offers = extract_offer_companies(r.remark_append)
            company_str = f"（{', '.join(offers)}）" if offers else ""
            lines.append(f"- `{r.wxid}` {r.display_name} — {r.transition_outcome}{company_str}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## got_offer 反向变化（true → false，需复核）")
    if sections["offer_lost"]:
        for r in sections["offer_lost"]:
            lines.append(f"- `{r.wxid}` {r.display_name} — outcome: {r.transition_outcome}, confidence: {r.confidence:.2f}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 转型结果细分变化")
    if sections["outcome_changes"]:
        for r, prev_outcome in sections["outcome_changes"]:
            lines.append(f"- `{r.wxid}` {r.display_name}：{prev_outcome} → {r.transition_outcome}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 本次新进低置信名单")
    if sections["new_needs_review"]:
        for r in sections["new_needs_review"]:
            lines.append(f"- `{r.wxid}` {r.display_name} — confidence: {r.confidence:.2f}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 本次新增「未回访」标记（首次被识别为未发过回访开场白）")
    if sections["new_not_followed_up"]:
        for r in sections["new_not_followed_up"]:
            lines.append(f"- `{r.wxid}` {r.display_name}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 本次从「未回访」转为已回访")
    if sections["newly_followed_up"]:
        for r, prev_outcome in sections["newly_followed_up"]:
            lines.append(f"- `{r.wxid}` {r.display_name}：未回访 → {r.transition_outcome}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 本次跳过统计")
    if skipped:
        by_reason: dict[str, int] = {}
        for s in skipped:
            by_reason[s.reason] = by_reason.get(s.reason, 0) + 1
        for reason, cnt in sorted(by_reason.items(), key=lambda x: -x[1]):
            lines.append(f"- {reason}: {cnt}")
    else:
        lines.append("- 无")
    lines.append("")

    (run_dir / "changes.md").write_text("\n".join(lines), encoding="utf-8")


def write_summary_md(run_dir: Path, latest: dict, stats: RunStats) -> None:
    total = len(latest)
    got_offer_count = sum(1 for v in latest.values() if v.get("got_offer"))
    not_followed_up = [v for v in latest.values() if v.get("transition_outcome") == "未回访"]
    outcome_dist: dict[str, int] = {}
    needs_review: list[dict] = []
    for v in latest.values():
        outcome = v.get("transition_outcome", "不明")
        outcome_dist[outcome] = outcome_dist.get(outcome, 0) + 1
        if v.get("needs_review"):
            needs_review.append(v)

    company_count: dict[str, int] = {}
    for v in latest.values():
        full_remark = v.get("remark_full", "") or ""
        last_block = full_remark.split("\n\n")[-1] if full_remark else ""
        for c in extract_offer_companies(last_block):
            company_count[c] = company_count.get(c, 0) + 1

    lines = [
        f"# 学员就业情况追踪累积统计",
        "",
        f"run_id：`{stats.run_id}` | 分析时间：{stats.started_at}",
        f"模式：{stats.mode} | 本轮 analyzed：{stats.analyzed} | skipped：{stats.skipped}",
        "",
        f"## 累积视图（共 {total} 人）",
        "",
        f"- 拿到 offer (got_offer=true)：**{got_offer_count}** 人（{got_offer_count/max(total,1):.1%}）",
        f"- 未回访 (transition_outcome=未回访)：**{len(not_followed_up)}** 人（{len(not_followed_up)/max(total,1):.1%}）",
        f"- 需复核 (confidence < {LOW_CONFIDENCE_THRESHOLD})：{len(needs_review)} 人",
        "",
        "## 转型结果分布",
        "",
        "| 转型结果 | 人数 |",
        "|---|---:|",
    ]
    for outcome, cnt in sorted(outcome_dist.items(), key=lambda x: -x[1]):
        lines.append(f"| {outcome} | {cnt} |")
    lines.append("")

    lines.append("## Offer 公司 Top 20")
    lines.append("")
    if company_count:
        lines.append("| 公司 | 学员数 |")
        lines.append("|---|---:|")
        for c, n in sorted(company_count.items(), key=lambda x: -x[1])[:20]:
            lines.append(f"| {c} | {n} |")
    else:
        lines.append("- 暂无")
    lines.append("")

    lines.append("## 需复核名单")
    lines.append("")
    if needs_review:
        for v in needs_review[:50]:
            lines.append(f"- `{v['wxid']}` {v.get('display_name','')} — confidence {v.get('confidence',0):.2f} | outcome: {v.get('transition_outcome','')}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append(f"## 未回访名单（共 {len(not_followed_up)} 人，建议下一轮回访优先处理）")
    lines.append("")
    if not_followed_up:
        for v in not_followed_up[:100]:
            lines.append(f"- `{v['wxid']}` {v.get('display_name','')}")
        if len(not_followed_up) > 100:
            lines.append(f"- …还有 {len(not_followed_up) - 100} 人")
    else:
        lines.append("- 无")
    lines.append("")

    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


# --- 主流程 -------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    kb_paths = core.default_paths()
    core.load_env(kb_paths.env_file)
    if not (os.environ.get("MINIMAX_API_KEY") or os.environ.get("KIMI_API_KEY")):
        print("[ERROR] 未配置 MINIMAX_API_KEY 或 KIMI_API_KEY", file=sys.stderr)
        return 1

    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    analyzed_at = datetime.now().strftime("%Y-%m-%d")
    started_at_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    mode = (
        "force_rerun_all" if args.force_rerun_all
        else "rerun_not_followed_up" if args.rerun_not_followed_up
        else "bootstrap" if args.bootstrap
        else "wxid" if args.wxid
        else "sample" if args.sample
        else "auto"
    )

    if args.dry_run:
        run_dir = RUNS_DIR / f"{run_id}_dryrun"
    else:
        run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "pending").mkdir(exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)
    logger = RunLogger(run_dir / "logs" / "run.log")
    logger.log("INFO", "RUN_START", run_id=run_id, mode=mode, dry_run=args.dry_run)

    progress = load_json(PROGRESS_FILE, {})
    latest_before = load_json(LATEST_FILE, {})
    import copy
    latest_snapshot = copy.deepcopy(latest_before)
    staff_wxids = core.load_staff_wxids()
    student_lookup = build_student_lookup()
    universe = build_wxid_universe()

    non_staff_universe = [w for w in universe if w not in staff_wxids]

    targets = non_staff_universe
    if args.wxid:
        if args.wxid not in universe:
            print(f"[ERROR] wxid {args.wxid} 不在 chat 目录里", file=sys.stderr)
            logger.close()
            return 1
        if args.wxid in staff_wxids:
            print(f"[WARN] wxid {args.wxid} 是 staff_exclude 里的自己人，单人模式仍允许跑（人工核验）", file=sys.stderr)
        targets = [args.wxid]
    elif args.sample:
        random.seed(args.run_id or run_id)
        targets = random.sample(non_staff_universe, min(args.sample, len(non_staff_universe)))

    try:
        system_prompt, user_template, prev_context_template = parse_prompt_template()
    except RuntimeError as e:
        print(f"[ERROR] 任务卡解析失败: {e}", file=sys.stderr)
        logger.close()
        return 1

    logger.log("INFO", "UNIVERSE", total=len(universe),
               non_staff=len(non_staff_universe), excluded_staff=len(universe) - len(non_staff_universe),
               targets=len(targets), staff_wxids=len(staff_wxids),
               known_students=len(student_lookup))

    started = time.time()
    results: list[AnalysisResult] = []
    skipped: list[SkipRecord] = []
    parse_failures: list[dict] = []
    low_conf: list[dict] = []
    llm_error_count = 0

    for i, wxid in enumerate(targets, 1):
        msg_data = load_messages(wxid)
        skip, reason = should_skip_for_auto(wxid, msg_data, progress, mode)
        if skip:
            skipped.append(SkipRecord(wxid=wxid, reason=reason,
                                      detail=f"msg_count={msg_data.get('total',0) if msg_data else 0}"))
            logger.log("INFO", "SKIP", wxid=wxid, reason=reason,
                       msg_count=msg_data.get("total", 0) if msg_data else 0)
            continue
        if msg_data is None:
            skipped.append(SkipRecord(wxid=wxid, reason="file_missing"))
            logger.log("WARN", "SKIP", wxid=wxid, reason="file_missing")
            continue

        student = student_lookup.get(wxid)
        last_result = latest_before.get(wxid)

        if mode == "rerun_not_followed_up":
            result, skip_rec = handle_rerun_not_followed_up(
                wxid=wxid, msg_data=msg_data, student=student,
                last_result=last_result, staff_wxids=staff_wxids,
                run_id=run_id, analyzed_at=analyzed_at,
            )
            if skip_rec:
                skipped.append(skip_rec)
                logger.log("INFO", "SKIP", wxid=wxid, reason=skip_rec.reason)
                continue
            assert result is not None
            results.append(result)
            cur_msgs = msg_data.get("messages") or []
            last_msg_ts = max((m.get("createTime", 0) for m in cur_msgs), default=0)
            prev_count = progress.get(wxid, {}).get("last_message_count", 0)
            msg_count_delta = msg_data.get("total", 0) - prev_count
            prev_got_pre = latest_before.get(wxid, {}).get("got_offer")
            prev_outcome_pre = latest_before.get(wxid, {}).get("transition_outcome")
            write_per_student_history(result, msg_count_delta, prev_got_pre, prev_outcome_pre)
            update_progress_entry(progress, wxid, result, msg_data, last_msg_ts)
            reset_latest_entry(latest_before, result)
            logger.log("INFO", "RESET_NOT_FOLLOWED_UP", wxid=wxid,
                       prev_outcome=prev_outcome_pre or "(none)")
            if len(results) % 50 == 0:
                save_json(PROGRESS_FILE, progress)
                save_json(LATEST_FILE, latest_before)
                logger.log("INFO", "STATE_FLUSH", completed=len(results))
            if args.limit and len(results) >= args.limit:
                logger.log("INFO", "LIMIT_REACHED", limit=args.limit)
                break
            continue

        result, err = analyze_one(
            wxid=wxid,
            msg_data=msg_data,
            student=student,
            last_result=last_result,
            system_prompt=system_prompt,
            user_template=user_template,
            prev_context_template=prev_context_template,
            staff_wxids=staff_wxids,
            run_id=run_id,
            analyzed_at=analyzed_at,
            logger=logger,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            continue
        if result is None:
            if err.startswith("llm"):
                llm_error_count += 1
                logger.log("ERROR", "LLM_GIVE_UP", wxid=wxid, err=err)
            else:
                parse_failures.append({"wxid": wxid, "error": err})
            continue

        results.append(result)
        if result.needs_review:
            low_conf.append({
                "wxid": result.wxid,
                "display_name": result.display_name,
                "confidence": result.confidence,
                "transition_outcome": result.transition_outcome,
                "remark_append": result.remark_append,
            })

        if args.wxid:
            print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
            continue

        cur_msgs = msg_data.get("messages") or []
        last_msg_ts = max((m.get("createTime", 0) for m in cur_msgs), default=0)
        prev_count = progress.get(wxid, {}).get("last_message_count", 0)
        msg_count_delta = msg_data.get("total", 0) - prev_count
        prev_got = latest_before.get(wxid, {}).get("got_offer")
        prev_outcome = latest_before.get(wxid, {}).get("transition_outcome")
        write_per_student_history(result, msg_count_delta, prev_got, prev_outcome)
        update_progress_entry(progress, wxid, result, msg_data, last_msg_ts)
        update_latest_entry(latest_before, wxid, result)

        time.sleep(INTER_CALL_SLEEP_SEC)

        if len(results) % 10 == 0:
            save_json(PROGRESS_FILE, progress)
            save_json(LATEST_FILE, latest_before)
            logger.log("INFO", "STATE_FLUSH", completed=len(results))

        if args.limit and len(results) >= args.limit:
            logger.log("INFO", "LIMIT_REACHED", limit=args.limit)
            break

    elapsed = time.time() - started

    if args.dry_run:
        skipped_count = len(skipped)
        plan_lines = [
            f"# DRY RUN — {run_id}", "",
            f"模式：{mode}",
            f"universe: {len(universe)}",
            f"targets: {len(targets)}",
            f"will skip: {skipped_count}",
            f"will analyze: {len(targets) - skipped_count}",
            "",
            "## 跳过原因统计",
        ]
        by_reason: dict[str, int] = {}
        for s in skipped:
            by_reason[s.reason] = by_reason.get(s.reason, 0) + 1
        for reason, cnt in sorted(by_reason.items(), key=lambda x: -x[1]):
            plan_lines.append(f"- {reason}: {cnt}")
        (run_dir / "plan.md").write_text("\n".join(plan_lines), encoding="utf-8")
        logger.log("INFO", "RUN_END", elapsed_s=int(elapsed), dry=True,
                   analyzed=0, skipped=skipped_count)
        print(f"[DRY RUN] universe={len(universe)} targets={len(targets)} "
              f"will_skip={skipped_count} will_analyze={len(targets)-skipped_count}")
        print(f"  plan written: {run_dir/'plan.md'}")
        logger.close()
        return 0

    if args.wxid:
        logger.log("INFO", "RUN_END_SINGLE", wxid=args.wxid)
        logger.close()
        return 0

    save_json(run_dir / "analysis.json", [asdict(r) for r in results])
    save_json(run_dir / "skipped.json", [asdict(s) for s in skipped])
    if parse_failures:
        save_json(run_dir / "pending" / "parse_failures.json", parse_failures)
    if low_conf:
        save_json(run_dir / "pending" / "decisions.json", low_conf)

    save_json(PROGRESS_FILE, progress)
    save_json(LATEST_FILE, latest_before)

    stats = RunStats(
        run_id=run_id, mode=mode, started_at=started_at_iso,
        universe_size=len(universe), analyzed=len(results), skipped=len(skipped),
        parse_failed=len(parse_failures), low_confidence=len(low_conf),
        llm_errors=llm_error_count, elapsed_seconds=round(elapsed, 1),
    )
    write_changes_md(run_dir, results, latest_snapshot, skipped)
    write_summary_md(run_dir, latest_before, stats)
    save_json(run_dir / "run_stats.json", asdict(stats))

    logger.log("INFO", "RUN_END", **asdict(stats))
    logger.close()

    print(f"[run {run_id}] analyzed={len(results)} skipped={len(skipped)} "
          f"low_conf={len(low_conf)} parse_fail={len(parse_failures)} "
          f"llm_err={llm_error_count} elapsed={elapsed:.1f}s")
    print(f"  → {run_dir}")
    return 0


def main():
    p = argparse.ArgumentParser(description="学员就业情况追踪 — AI 抽取与同步（任务卡: employment）")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--bootstrap", action="store_true", help="忽略 progress 跑全量（含已有学员）")
    g.add_argument("--auto", action="store_true", help="增量模式（默认推荐）")
    g.add_argument("--force-rerun-all", action="store_true", help="忽略所有 checkpoint 重跑全量")
    g.add_argument("--rerun-not-followed-up", action="store_true",
                   help="一次性修复：把所有未发过回访开场白的学员 reset 成「未回访」（不调 LLM）")
    g.add_argument("--sample", type=int, default=0, help="抽 N 人")
    g.add_argument("--wxid", type=str, default="", help="只跑单个 wxid（stdout 输出）")
    p.add_argument("--dry-run", action="store_true", help="不调 LLM，只输出 plan")
    p.add_argument("--run-id", type=str, default="", help="自定义 run_id")
    p.add_argument("--limit", type=int, default=0, help="本轮最多分析 N 人后停")
    args = p.parse_args()

    if not any([args.bootstrap, args.auto, args.force_rerun_all,
                args.rerun_not_followed_up, args.sample, args.wxid]):
        args.auto = True

    sys.exit(run(args))


if __name__ == "__main__":
    main()
