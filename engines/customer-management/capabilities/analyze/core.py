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
    "try_decode_zstd",
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


def try_decode_zstd(content: str) -> str | None:
    """微信把部分消息正文存成 zstd 压缩的 hex（magic 28 b5 2f fd）——**是压缩不是加密**。

    实测这些行 ~100% 能解出可读文本，且大多是真人对话（群发课程/回放链接、学员反馈、试听询问），
    旧 try_decode_hex 只做 bytes.fromhex().decode() 对压缩数据必失败 → 这些消息一直被当乱码丢掉。
    本函数补回解压。`zstandard` 惰性 import，缺库则返回 None 优雅退回（不在 import 期硬依赖）。
    返回解出的文本，或 None（不是 zstd / 解不出 / 无库）。
    """
    if not content or not re.match(r"^[0-9a-fA-F]+$", content) or len(content) % 2 != 0:
        return None
    try:
        raw = bytes.fromhex(content)
    except Exception:
        return None
    if raw[:4] != b"\x28\xb5\x2f\xfd":
        return None
    try:
        import zstandard as zstd  # 惰性
    except Exception:
        return None
    try:
        try:
            data = zstd.ZstdDecompressor().decompress(raw)
        except zstd.ZstdError:
            import io
            data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)).read()
        text = data.decode("utf-8", "replace").strip()
        return text or None
    except Exception:
        return None


def is_staff_sender(msg: dict, student_wxid: str, staff_wxids: set[str]) -> bool:
    """WeFlow 抽出的 isSelf 全是 0 不可信。靠 senderWxid + senderName 推断。"""
    sender_wxid = msg.get("senderWxid", "") or ""
    if sender_wxid in staff_wxids:
        return True
    if student_wxid and sender_wxid == student_wxid:
        return False
    sname = (msg.get("senderName") or "").lower()
    return any(k in sname for k in STAFF_NAME_KEYWORDS)


# --- 消息分层/分类（无损：一条都不删，按层标注）-----------------------------
# 设计真源见 doc/plan/customer-management-media-visibility-plan.md（无损分层 + 信息地图）。
# 没有"垃圾"，只有"当前用不上的层"：取舍发生在消费端（喂哪一层 + 信息地图），不在入库端。
#   L0 = text   默认喂 LLM 初判（旧 analyze 行为）
#   L1 = 媒体/链接/系统事件  默认只在 info_map 里"列出存在"，不灌正文
#   L2 = 重解析（图片内容/语音转录）  按需取（图片走现成读图；语音不提供工具，AI 自行处理）

# 加好友 / 入群等系统事件（有业务价值，单列；"你已添加了X"≈加好友日期）
_FRIEND_EVENT_PAT = ("你已添加了", "通过了你的朋友验证", "现在我们可以开始聊天", "现在可以开始聊天")
_GROUP_EVENT_PAT = ("邀请你加入群聊", "加入了群聊", "你邀请")


def classify_message(msg: dict, decoded_content: str) -> tuple[str, str, str | None]:
    """无损分类：所有消息都给出 (kind, layer, handle)，由消费端按 layer 决定默认看不看。

    kind: text / image / voice / video / link / system_event / sticker / control / system
    layer: L0(默认看) / L1(元信息,默认只在地图列出) / L2 内容(按需,这里不在入库阶段解析)
    handle: 图片等可定位句柄（供按需读图），无则 None。
    """
    c = decoded_content or ""
    msg_type = str(msg.get("type", "1"))
    # 系统事件（加好友/入群）——优先于通用系统提示，因为它有业务价值
    if any(p in c for p in _FRIEND_EVENT_PAT) or any(p in c for p in _GROUP_EVENT_PAT):
        return "system_event", "L1", None
    # 图片：保留 [图片 后的引用串作为 handle（供 L2 按需读图）
    if c.startswith("[图片") or msg_type == "3":
        h = c[len("[图片"):].strip(" ]").strip() or None
        return "image", "L1", h
    if c.startswith("[语音]") or msg_type == "34":
        return "voice", "L1", None
    if c.startswith("[视频]") or msg_type == "43":
        return "video", "L1", None
    if c.startswith("[表情"):
        return "sticker", "L1", None
    if "拍了拍" in c:
        return "system", "L1", None
    if c.startswith("[链接]") or c.startswith("[文件]") or c.startswith("[名片]"):
        return "link", "L1", None
    # zstd 解压失败的真二进制残留（仍是纯 hex）→ 控制层，不喂正文但不丢
    if re.match(r"^[0-9a-fA-F]{20,}$", c):
        return "control", "L1", None
    # 解压出的 XML 系统消息（sysmsg/appmsg 等）→ 系统层
    if c.startswith("<") and ("</" in c or "/>" in c):
        return "system", "L1", None
    # 纯系统提示（打招呼汇总等）
    if msg_type == "10000":
        return "system", "L1", None
    # 其余皆为文字（含引用回复、解压出的真人对话等被旧逻辑误删的真文本）
    return "text", "L0", None


def normalize_messages(
    raw: list[dict],
    student_wxid: str,
    staff_wxids: set[str],
    *,
    min_ts: int = 0,
    max_chars_per_msg: int | None = None,
    media_placeholder_max_len: int | None = None,
) -> list[dict]:
    """无损规范化：保留每条消息（不再按 type 丢弃、不再删媒体占位），按 layer 分层标注。

    - `min_ts`：硬截断老消息（llm_enrich 的 since 下限）；0 = 不限。
    - `max_chars_per_msg`：单条截断（仅作用于 L0 文字；None = 不截）。
    - `media_placeholder_max_len`：**已退役**（旧"媒体占位剔除"阈值）。保留入参仅为兼容旧调用，
      其值被忽略——媒体不再删除，改由 layer 标注 + 消费端 text_layer/info_map 取舍。

    返回每条：{createTime, ts_str, is_staff, sender_name, content, kind, layer, handle}。
    """
    out: list[dict] = []
    for m in raw or []:
        ts = m.get("createTime", 0)
        if not isinstance(ts, (int, float)) or ts <= 0 or ts <= min_ts:
            continue
        content = m.get("content", "")
        if not content or not isinstance(content, str) or not content.strip():
            continue
        content = try_decode_hex(content).strip()
        if not content:
            continue
        # zstd 压缩正文（28b52ffd…，是压缩不是加密）→ 解压恢复真实文本
        if content[:8].lower() == "28b52ffd":
            z = try_decode_zstd(content)
            if z:
                content = z
        kind, layer, handle = classify_message(m, content)
        if layer == "L0" and max_chars_per_msg is not None and len(content) > max_chars_per_msg:
            content = content[:max_chars_per_msg] + "...[截断]"
        out.append({
            "createTime": int(ts),
            "ts_str": m.get("createTimeStr", ""),
            "is_staff": is_staff_sender(m, student_wxid, staff_wxids),
            "sender_name": m.get("senderName", "") or "",
            "content": content,
            "kind": kind,
            "layer": layer,
            "handle": handle,
        })
    out.sort(key=lambda x: x["createTime"])
    return out


def text_layer(normalized: list[dict]) -> list[dict]:
    """默认喂 LLM 的 L0 文字层（保留旧 analyze 行为：只读文字做初判）。"""
    return [m for m in normalized if m.get("layer") == "L0"]


# kind → (中文名, 用途/取法提示)。决定 info_map 怎么向 AI 描述每一层。
_KIND_DESC = {
    "image": ("图片", "内容未读；按需读图：python3 -m capabilities.acquire.resolve_images --wxid <wxid>（本机解密后用视觉看）"),
    "voice": ("语音", "本系统不提供转录，需要时请自行处理"),
    "video": ("视频", "未解析；需要时自行处理"),
    "link": ("链接/文件/名片", "标签已在对话中"),
    "system_event": ("系统事件", "加好友/入群等，含可派生的加好友日期"),
    "sticker": ("表情", "通常无判断价值"),
    "control": ("控制消息", "二进制/不可读，已忽略正文"),
    "system": ("系统提示", "打招呼等"),
}


def friend_add_date(normalized: list[dict]) -> str | None:
    """从系统事件（你已添加了X / 通过好友验证）派生加好友日期；回退最早一条消息日期。

    返回 'YYYY-MM-DD' 或 None。确定性派生，无需 LLM（recognize 能力复用本函数）。
    """
    import datetime as _dt
    for m in normalized:
        if m.get("kind") == "system_event" and any(p in m.get("content", "") for p in _FRIEND_EVENT_PAT):
            ts = m.get("createTime")
            if ts:
                return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    if normalized:
        ts = normalized[0].get("createTime")
        if ts:
            return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    return None


def build_info_map(normalized: list[dict]) -> str:
    """自描述信息地图：告诉 AI ①有哪些信息 ②现在看的是哪部分 ③其他能做什么用、怎么取。

    这是"无损分层"对外的灵魂：默认只把 L0 文字喂给 LLM，但用这张地图让它知道全貌，
    卡住时能自主回头挖（图片读图、其余自行处理）。
    """
    from collections import Counter
    if not normalized:
        return "【本段对话信息清单】无可用消息"
    kinds: Counter[str] = Counter(str(m.get("kind") or "system") for m in normalized)
    n_text = kinds.get("text", 0)
    total = len(normalized)
    lines = [f"【本段对话信息清单】共 {total} 条消息"]
    lines.append(f"  · 文字 {n_text} 条        ← 你现在看的就是这部分（L0）")
    for kind, n in kinds.most_common():
        if kind == "text" or n == 0:
            continue
        zh, use = _KIND_DESC.get(kind, (kind, ""))
        extra = ""
        if kind == "system_event":
            d = friend_add_date(normalized)
            if d:
                extra = f"；加好友日期：{d}"
        lines.append(f"  · {zh} {n} 条        ← {use}{extra}")
    lines.append(f"【你当前看到的】L0 文字层（共 {n_text} 条文字）")
    lines.append("【卡住时】图片可读图取证；语音/其它无工具，自行处理；其余 L1 仅在上方清单列出")
    return "\n".join(lines)


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
