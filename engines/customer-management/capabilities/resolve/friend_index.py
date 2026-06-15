"""共享：好友名单加载器 + 账号角色预设。

供 sync_friends_to_feishu / audit_duplicate_creates / merge_duplicate_creates 复用，
让"助理号""张和2号"等多个数据源走同一套同步/去重逻辑。

支持两种 friend 源 schema，统一规约成英文键 dict：
  1. analytics/friends_index/friends.json
     英文键: {wxid, alias, nick_name, remark, first_chat_date, has_messages}
  2. knowledge_base/client/raw/chat/friends_<role>.json（sync_groups.js dump）
     中文键: {wxid, 昵称, 备注名, 微信号}（无 first_chat_date）

账号角色 → 飞书"添加微信"多选选项名：
  assistant = 助理号  → 小助理
  zh2       = 张和2号 / 微信号 henrygpt2024（wxid_vvkd7ex3oa3122）→ 张和2号
"""

from __future__ import annotations

import glob
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_CHAT = PROJECT_ROOT / "knowledge_base" / "client" / "raw" / "chat"
FRIENDS_INDEX = PROJECT_ROOT / "analytics" / "friends_index" / "friends.json"
TZ_CN = timezone(timedelta(hours=8))

# role → (默认 friend 源, 飞书"添加微信"选项名)
ROLE_PRESETS: dict[str, tuple[Path, str]] = {
    "assistant": (FRIENDS_INDEX, "小助理"),
    "zh2": (RAW_CHAT / "friends_zh2.json", "张和2号"),
}


def resolve_role(role: str | None, friends: str | None, add_by: str | None) -> tuple[Path, str]:
    """把 --role / --friends / --add-by 解析成 (源路径, 添加微信选项名)。
    --friends / --add-by 显式给值时覆盖 role 预设。默认 role=assistant（向后兼容）。
    """
    preset_path, preset_add_by = ROLE_PRESETS.get(role or "assistant", ROLE_PRESETS["assistant"])
    src = Path(friends) if friends else preset_path
    label = add_by if add_by else preset_add_by
    return src, label


def _normalize(fr: dict) -> dict:
    """把任一 schema 的一条好友规约成英文键。"""
    if "alias" in fr or "nick_name" in fr:  # friends_index 英文 schema
        return {
            "wxid": fr.get("wxid", ""),
            "alias": (fr.get("alias") or "").strip(),
            "nick_name": (fr.get("nick_name") or "").strip(),
            "remark": (fr.get("remark") or "").strip(),
            "first_chat_date": fr.get("first_chat_date"),
        }
    # raw/chat dump 中文 schema
    return {
        "wxid": fr.get("wxid", ""),
        "alias": (fr.get("微信号") or "").strip(),
        "nick_name": (fr.get("昵称") or "").strip(),
        "remark": (fr.get("备注名") or "").strip(),
        "first_chat_date": fr.get("first_chat_date"),  # raw dump 无 → None
    }


def _build_first_chat_date_index(raw_chat_dir: Path = RAW_CHAT) -> dict[str, str]:
    """扫 raw/chat/messages_user_*.json，对每个 wxid 算最早消息日期 (YYYY-MM-DD, +08:00)。
    供 sync_friends 给"加好友日期"字段填值；没消息文件的好友拿不到日期 → 留 None。"""
    idx: dict[str, str] = {}
    for fp in glob.glob(str(raw_chat_dir / "messages_user_*.json")):
        try:
            d = json.loads(Path(fp).read_text(encoding="utf-8"))
            uid = d.get("userId", "")
            msgs = d.get("messages", []) or []
            if not uid or not msgs:
                continue
            min_ts = min((int(m.get("createTime") or 0) for m in msgs), default=0)
            if min_ts > 0:
                idx[uid] = datetime.fromtimestamp(min_ts, tz=TZ_CN).strftime("%Y-%m-%d")
        except Exception:
            continue
    return idx


def load_friend_index(path: str | Path) -> list[dict]:
    """读 friend 源，返回规约后的英文键 dict 列表（过滤掉空 wxid）。
    若 first_chat_date 缺失，会扫 raw/chat/messages_user_*.json 补一份（取最早消息）。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    friends = data.get("friends") if isinstance(data, dict) else data
    normalized = [_normalize(f) for f in (friends or []) if f.get("wxid")]

    # 补 first_chat_date：raw 中文 schema dump 没这字段，从私聊文件最早消息补。
    needs_date = [n for n in normalized if not n.get("first_chat_date")]
    if needs_date:
        date_idx = _build_first_chat_date_index()
        for n in needs_date:
            d = date_idx.get(n["wxid"])
            if d:
                n["first_chat_date"] = d
    return normalized
