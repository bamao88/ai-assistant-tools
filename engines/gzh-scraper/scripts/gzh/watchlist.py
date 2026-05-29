"""监控列表 CRUD。"""

from __future__ import annotations

from typing import Any

from .config import load_config, save_config
from .types import FilterCriteria, WatchItem


def get_watchlist() -> list[WatchItem]:
    """获取监控列表。"""
    cfg = load_config()
    return [WatchItem.from_dict(item) for item in cfg.get("watchlist", [])]


def add_watch(
    fakeid: str,
    name: str,
    min_reads: int = 0,
    min_likes: int = 0,
    keywords: list[str] | None = None,
    since_days: int = 7,
) -> WatchItem:
    """添加监控公众号。"""
    cfg = load_config()
    watchlist = cfg.get("watchlist", [])

    # 检查是否已存在
    for item in watchlist:
        if item.get("fakeid") == fakeid:
            raise ValueError(f"公众号 {name} (fakeid={fakeid}) 已在监控列表中")

    new_item = WatchItem(
        fakeid=fakeid,
        name=name,
        filters=FilterCriteria(
            min_reads=min_reads,
            min_likes=min_likes,
            keywords=keywords or [],
            since_days=since_days,
        ),
    )
    watchlist.append(new_item.to_dict())
    cfg["watchlist"] = watchlist
    save_config(cfg)
    return new_item


def remove_watch(fakeid: str) -> bool:
    """移除监控公众号。"""
    cfg = load_config()
    watchlist = cfg.get("watchlist", [])
    new_list = [item for item in watchlist if item.get("fakeid") != fakeid]
    if len(new_list) == len(watchlist):
        return False
    cfg["watchlist"] = new_list
    save_config(cfg)
    return True


def update_last_checked(fakeid: str, timestamp: str) -> None:
    """更新最后检查时间。"""
    cfg = load_config()
    for item in cfg.get("watchlist", []):
        if item.get("fakeid") == fakeid:
            item["last_checked"] = timestamp
            break
    save_config(cfg)
