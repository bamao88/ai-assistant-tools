"""时间戳解析、URL 站点识别等工具函数。"""

from __future__ import annotations

import re
from urllib.parse import urlparse


def parse_timestamp(ts: str) -> float:
    """把 "01:23" / "01:23:45" / "83" / "83.5" 解析为秒数（float）。

    - 纯数字 → 秒
    - MM:SS → 分:秒
    - HH:MM:SS → 时:分:秒
    """
    ts = ts.strip()
    if ":" not in ts:
        return float(ts)

    parts = ts.split(":")
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    raise ValueError(f"无法解析的时间戳: {ts}")


def format_timestamp(seconds: float, filename_safe: bool = False) -> str:
    """把秒数格式化为 HH:MM:SS（或文件名安全的 HH-MM-SS）。"""
    s = int(round(seconds))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    sep = "-" if filename_safe else ":"
    return f"{h:02d}{sep}{m:02d}{sep}{s:02d}"


# 站点域名 → platform 短名（给 video_id 做前缀）
_PLATFORM_MAP = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "m.youtube.com": "youtube",
    "bilibili.com": "bilibili",
    "www.bilibili.com": "bilibili",
    "b23.tv": "bilibili",
    "xiaohongshu.com": "xhs",
    "xhslink.com": "xhs",
    "www.xiaohongshu.com": "xhs",
    "douyin.com": "douyin",
    "www.douyin.com": "douyin",
    "v.douyin.com": "douyin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "vimeo.com": "vimeo",
}


def detect_platform(url: str) -> str:
    """根据 URL 返回 platform 短名（youtube/bilibili/xhs/douyin/twitter/...）。

    未知域名返回 "generic"。
    """
    host = urlparse(url).netloc.lower()
    return _PLATFORM_MAP.get(host, host.split(".")[-2] if "." in host else "generic")


def sanitize_filename(s: str, max_len: int = 80) -> str:
    """清洗字符串供文件名使用（保留中英文，替换非法字符）。"""
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", s)
    s = s.strip(". ")
    return s[:max_len] if len(s) > max_len else s
