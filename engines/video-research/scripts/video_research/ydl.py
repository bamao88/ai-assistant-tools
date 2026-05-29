"""yt-dlp 选项公共构造器。

集中处理 YouTube 机器人检测规避：
- curl-cffi impersonation（TLS/JA3 指纹伪装）
- 多 player_client fallback
- cookies.txt 自动读取
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_COOKIE_PATHS = [
    Path.home() / ".config" / "yt-dlp" / "cookies.txt",
    Path.home() / ".config" / "video-research" / "cookies.txt",
]

_YT_PLAYER_CLIENTS = ["mweb", "web_safari", "tv_embedded", "android_vr"]


def _detect_cookiefile() -> str | None:
    override = os.environ.get("VIDEO_RESEARCH_COOKIES")
    if override and Path(override).exists():
        return override
    for p in _DEFAULT_COOKIE_PATHS:
        if p.exists():
            return str(p)
    return None


def _impersonate_target():
    """挑一个 yt-dlp 认可的 impersonate target；不可用时返回 None。

    按优先级回退 chrome → safari → 字符串 "chrome"（兜底），确保 YoutubeDL 能实例化。
    环境变量 VIDEO_RESEARCH_IMPERSONATE 可指定具体字符串（如 "chrome-136:macos-15"）。
    """
    override = os.environ.get("VIDEO_RESEARCH_IMPERSONATE")
    if override:
        return override

    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
    except ImportError:
        return None

    try:
        from yt_dlp.YoutubeDL import YoutubeDL
        ydl = YoutubeDL({"quiet": True, "no_warnings": True})
        director = ydl._request_director
        available: list[ImpersonateTarget] = []
        for rh in director.handlers.values():
            m = getattr(rh, "_SUPPORTED_IMPERSONATE_TARGET_MAP", None)
            if m:
                available.extend(m.keys())
        ydl.close()
    except Exception as e:
        logger.debug("impersonate 探测失败: %s", e)
        return None

    if not available:
        return None

    preferred_clients = ("chrome", "safari", "firefox", "edge")
    for client in preferred_clients:
        for t in available:
            if (t.client or "").lower().startswith(client):
                return t
    return available[0]


def base_ydl_opts() -> dict:
    """所有子命令共用的 yt-dlp 选项基底。"""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        # YouTube：把 player_client 串起来，默认命中率更高
        "extractor_args": {"youtube": {"player_client": list(_YT_PLAYER_CLIENTS)}},
        # 轻量 rate-limit，降低被识别为爬虫的概率
        "sleep_interval_requests": 1,
        "max_sleep_interval_requests": 3,
    }

    cookiefile = _detect_cookiefile()
    if cookiefile:
        opts["cookiefile"] = cookiefile
        logger.debug("yt-dlp cookies: %s", cookiefile)

    target = _impersonate_target()
    if target is not None:
        opts["impersonate"] = target

    return opts


def merge_ydl_opts(*extras: dict) -> dict:
    """把额外选项合并到 base。后面的覆盖前面的，dict 值做浅合并。"""
    merged = base_ydl_opts()
    for extra in extras:
        if not extra:
            continue
        for k, v in extra.items():
            if k == "extractor_args" and isinstance(v, dict) and isinstance(merged.get(k), dict):
                # 深合并 extractor_args
                for ek, ev in v.items():
                    merged[k][ek] = ev
            else:
                merged[k] = v
    return merged
