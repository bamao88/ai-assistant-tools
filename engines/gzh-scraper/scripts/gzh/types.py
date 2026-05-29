"""数据类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Account:
    """公众号账号信息。"""
    fakeid: str
    nickname: str
    alias: str = ""
    round_head_img: str = ""
    service_type: int = 0

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Account:
        return cls(
            fakeid=data.get("fakeid", ""),
            nickname=data.get("nickname", ""),
            alias=data.get("alias", ""),
            round_head_img=data.get("round_head_img", ""),
            service_type=data.get("service_type", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fakeid": self.fakeid,
            "nickname": self.nickname,
            "alias": self.alias,
            "round_head_img": self.round_head_img,
            "service_type": self.service_type,
        }


@dataclass
class Article:
    """公众号文章信息。"""
    aid: str
    title: str
    link: str
    cover: str = ""
    digest: str = ""
    create_time: int = 0
    update_time: int = 0
    read_num: int = 0
    like_num: int = 0
    old_like_num: int = 0  # 点赞（旧版）
    comment_num: int = 0
    # 所属公众号
    account_name: str = ""
    account_fakeid: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any], account_name: str = "", account_fakeid: str = "") -> Article:
        """从 exporter API 返回的数据构造。"""
        return cls(
            aid=data.get("aid", data.get("id", "")),
            title=data.get("title", ""),
            link=data.get("link", ""),
            cover=data.get("cover", ""),
            digest=data.get("digest", ""),
            create_time=data.get("create_time", 0),
            update_time=data.get("update_time", 0),
            read_num=data.get("read_num", 0),
            like_num=data.get("like_num", 0),
            old_like_num=data.get("old_like_num", 0),
            comment_num=data.get("comment_num", 0),
            account_name=account_name,
            account_fakeid=account_fakeid,
        )

    @property
    def create_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.create_time) if self.create_time else datetime.min

    def to_dict(self) -> dict[str, Any]:
        d = {
            "aid": self.aid,
            "title": self.title,
            "link": self.link,
            "cover": self.cover,
            "digest": self.digest,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "read_num": self.read_num,
            "like_num": self.like_num,
            "old_like_num": self.old_like_num,
            "comment_num": self.comment_num,
            "account_name": self.account_name,
            "account_fakeid": self.account_fakeid,
        }
        if self.create_time:
            d["create_date"] = self.create_datetime.strftime("%Y-%m-%d %H:%M")
        return d


@dataclass
class FilterCriteria:
    """筛选条件。"""
    min_reads: int = 0
    min_likes: int = 0
    keywords: list[str] = field(default_factory=list)
    since_days: int = 7

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_reads": self.min_reads,
            "min_likes": self.min_likes,
            "keywords": self.keywords,
            "since_days": self.since_days,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterCriteria:
        return cls(
            min_reads=data.get("min_reads", 0),
            min_likes=data.get("min_likes", 0),
            keywords=data.get("keywords", []),
            since_days=data.get("since_days", 7),
        )


@dataclass
class WatchItem:
    """监控列表中的一个条目。"""
    fakeid: str
    name: str
    enabled: bool = True
    filters: FilterCriteria = field(default_factory=FilterCriteria)
    last_checked: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fakeid": self.fakeid,
            "name": self.name,
            "enabled": self.enabled,
            "filters": self.filters.to_dict(),
            "last_checked": self.last_checked,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WatchItem:
        return cls(
            fakeid=data.get("fakeid", ""),
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            filters=FilterCriteria.from_dict(data.get("filters", {})),
            last_checked=data.get("last_checked", ""),
        )
