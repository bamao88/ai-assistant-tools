#!/usr/bin/env python3
"""core.py — analyze 能力的统一机器核（§2③「一台机器换卡干活」+ §2 横切「增量窗口」）。

P3 收口：`llm_enrich.py`（客户画像富化）和 `analyze.py`（就业回访）原本各抄一份
消息读取 / 增量窗口 / staff 判定 / call_llm 包装 / JSON 围栏剥离。这里把这套
**机器**收成一份，两个 flow 各自带一张任务卡（cards/*.md）来「换卡干活」，
但各自的写回契约（field_actions 应用 vs AnalysisResult/stub/reset）仍留在
对应 flow 模块（profile.py / employment.py），以满足 §12「保留 per-卡输出契约」。

收口的四块机器
--------------
1. 消息索引 + 读取（messages_user_*.json）
2. 规范化（hex 解码、文本-only 过滤、媒体占位剔除、staff/学员判定）
3. 增量窗口（last_seen + 最近 N 条 / since 下限 —— analyze 调用契约的单一来源）
4. LLM 调用包装（call_llm，复用 knowledge_ingest.core）+ JSON 围栏剥离

staff 判定
----------
WeFlow 抽取的 isSelf 字段全是 0（失效），所以靠 senderWxid + senderName 推断：
senderWxid ∈ staff_wxids → staff；== student_wxid → 学员；否则 senderName 关键词兜底。
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path
from typing import Any

# engine 根（capabilities/analyze/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

# 复用 assistant_zh 的 knowledge_ingest LLM client（依赖留 assistant_zh，经 config.DATA_ROOT 解析）
sys.path.insert(0, str(config.DATA_ROOT))
from workflow.knowledge_ingest.core import (  # noqa: E402
    call_llm,
    call_kimi,
    load_env,
    default_paths,
    LLMError,
    KimiError,
)

__all__ = [
    "call_llm",
    "call_kimi",
    "load_env",
    "default_paths",
    "LLMError",
    "KimiError",
    "load_staff_wxids",
    "build_message_index",
    "find_message_file",
    "load_messages_raw",
    "try_decode_hex",
    "is_staff_sender",
    "classify_message",
    "normalize_messages",
    "text_layer",
    "build_info_map",
    "friend_add_date",
    "select_increment_window",
    "strip_json_fence",
    "STAFF_NAME_KEYWORDS",
]

# --- staff 名称关键词兜底（senderWxid 不明时）-------------------------------
STAFF_NAME_KEYWORDS = ("助理", "babamao", "bamao", "张和")

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


# --- staff 名单 -------------------------------------------------------------

def load_staff_wxids() -> set[str]:
    """从 staff_exclude.json 加载所有助理/张和的 wxid。"""
    p = config.STAFF_EXCLUDE_FILE
    if not p.exists():
        return set()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {s["wxid"] for s in d.get("staff", []) if s.get("wxid")}
    except Exception:
        return set()


# --- 消息索引 + 读取 --------------------------------------------------------

def build_message_index(data_dir: Path | None = None) -> dict[str, Path]:
    """index by userId（可能是 wxid 或 微信号）→ messages_user_*.json 路径。"""
    data_dir = data_dir or config.DATA_DIR
    idx: dict[str, Path] = {}
    for fpath in glob.glob(str(data_dir / "messages_user_*.json")):
        try:
            d = json.loads(Path(fpath).read_text(encoding="utf-8"))
            uid = d.get("userId", "")
            if uid:
                idx[uid] = Path(fpath)
        except Exception:
            continue
    return idx


def find_message_file(student: dict, msg_index: dict[str, Path]) -> Path | None:
    """优先按 wxid 找，其次按 其他名称 里的微信号找。"""
    wxid = student.get("wxid", "")
    if wxid in msg_index:
        return msg_index[wxid]
    other = student.get("其他名称") or ""
    m = re.search(r"微信号[:：]([^\s|]+)", other)
    if m and m.group(1) in msg_index:
        return msg_index[m.group(1)]
    return None


def load_messages_raw(path: Path) -> dict | None:
    """读一个 messages_user_*.json，失败返回 None。"""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# --- 规范化 -----------------------------------------------------------------

def try_decode_hex(content: str) -> str:
    """有些 WeChat 文件把内容存成 hex；尝试解码。"""
    if not content or len(content) < 20:
        return content
    if not re.match(r"^[0-9a-fA-F]+$", content) or len(content) % 2 != 0:
        return content
    try:
        return bytes.fromhex(content).decode("utf-8")
    except Exception:
        return content


def is_staff_sender(msg: dict, student_wxid: str, staff_wxids: set[str]) -> bool:
    """WeFlow 抽出的 isSelf 全是 0 不可信。靠 senderWxid + senderName 推断。"""
    sender_wxid = msg.get("senderWxid", "") or ""
    if sender_wxid in staff_wxids:
        return True
    if student_wxid and sender_wxid == student_wxid:
        return False
    sname = (msg.get("senderName") or "").lower()
    return any(k in sname for k in STAFF_NAME_KEYWORDS)


def normalize_messages(
    raw: list[dict],
    student_wxid: str,
    staff_wxids: set[str],
    *,
    min_ts: int = 0,
    max_chars_per_msg: int | None = None,
    media_placeholder_max_len: int | None = None,
) -> list[dict]:
    """过滤系统消息/媒体占位、hex 解码、按 createTime 升序、识别是否 staff。

    统一两套旧实现：
    - `min_ts`：硬截断老消息（llm_enrich 的 since 下限）；0 = 不限。
    - `max_chars_per_msg`：单条截断（llm_enrich 用 800；None = 不截）。
    - `media_placeholder_max_len`：`[...]` 媒体占位的剔除阈值。
      None → 任意 `[...]` 都剔（llm_enrich 行为）；
      int  → 仅 `[...]` 且长度 < 阈值时剔（analyze 行为，保留长内容）。

    返回每条：{createTime, ts_str, is_staff, sender_name, content}。
    """
    out: list[dict] = []
    for m in raw or []:
        ts = m.get("createTime", 0)
        if not isinstance(ts, (int, float)) or ts <= 0 or ts <= min_ts:
            continue
        msg_type = str(m.get("type", "1"))
        if msg_type != "1":  # 只保留文本
            continue
        content = m.get("content", "")
        if not content or not isinstance(content, str) or not content.strip():
            continue
        # 媒体占位剔除
        if content.startswith("[") and content.endswith("]"):
            if media_placeholder_max_len is None or len(content) < media_placeholder_max_len:
                continue
        content = try_decode_hex(content).strip()
        if max_chars_per_msg is not None and len(content) > max_chars_per_msg:
            content = content[:max_chars_per_msg] + "...[截断]"
        out.append({
            "createTime": int(ts),
            "ts_str": m.get("createTimeStr", ""),
            "is_staff": is_staff_sender(m, student_wxid, staff_wxids),
            "sender_name": m.get("senderName", "") or "",
            "content": content,
        })
    out.sort(key=lambda x: x["createTime"])
    return out


# --- 增量窗口（analyze 调用契约的单一来源，§2 横切）------------------------

def select_increment_window(
    messages: list[dict],
    *,
    last_seen_ts: int = 0,
    max_recent: int | None = None,
) -> list[dict]:
    """从规范化消息里选增量窗口：createTime > last_seen 的 + 最近 N 条尾部。

    - `last_seen_ts`：上次处理过的最新消息 createTime（state 断点）。0 = 全量。
    - `max_recent`：尾部最多保留 N 条（None = 不限）。

    返回按时间升序的窗口消息（尾部 = 最新）。
    """
    window = [m for m in messages if m.get("createTime", 0) > last_seen_ts]
    if max_recent is not None and len(window) > max_recent:
        window = window[-max_recent:]
    return window


# --- LLM 输出 -----------------------------------------------------------------

def strip_json_fence(s: str) -> str:
    """剥掉 LLM 偶尔包在 ```json ... ``` 围栏里的 JSON。"""
    s = (s or "").strip()
    m = _FENCE_RE.match(s)
    return m.group(1).strip() if m else s
