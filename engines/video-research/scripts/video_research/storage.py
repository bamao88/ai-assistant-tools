"""data/ 目录管理：根据 URL 或 video_id 定位工作目录。"""

from __future__ import annotations

from pathlib import Path

from .utils import detect_platform

TOOL_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = TOOL_ROOT / "data"


def video_dir(platform: str, video_id: str, create: bool = True) -> Path:
    """返回 data/{platform}_{video_id}/ 路径。"""
    d = DATA_ROOT / f"{platform}_{video_id}"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def parse_video_key(key: str) -> tuple[str, str]:
    """把 "youtube_abcDEF" 解析为 (platform, video_id)。"""
    if "_" not in key:
        raise ValueError(f"video-id 格式应为 platform_videoid，收到: {key}")
    platform, vid = key.split("_", 1)
    return platform, vid


def video_dir_from_url(url: str, extracted_id: str) -> Path:
    """根据 URL 和 yt-dlp 提取的 id 生成目录。"""
    return video_dir(detect_platform(url), extracted_id)


def video_dir_from_key(key: str, create: bool = True) -> Path:
    """根据 "platform_videoid" 字符串定位目录。"""
    platform, vid = parse_video_key(key)
    return video_dir(platform, vid, create=create)
