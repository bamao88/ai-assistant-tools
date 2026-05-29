"""元数据 + 封面下载（yt-dlp extract_info）。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests
import yt_dlp

from .storage import video_dir_from_url
from .utils import detect_platform
from .ydl import merge_ydl_opts

logger = logging.getLogger(__name__)


def fetch_info(url: str, download_thumbnail: bool = True) -> dict:
    """抽取视频元数据，可选下载封面。

    返回 dict 包含：
      - success, video_id, platform, video_dir（绝对路径）
      - title, uploader, duration, upload_date, webpage_url, description
      - thumbnail_path（下载成功时）
      - subtitles, automatic_captions（lang code 列表）
      - info_path（info.json 写入路径）
    """
    ydl_opts = merge_ydl_opts({
        "skip_download": True,
        "writesubtitles": False,
    })
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    video_id = info.get("id") or "unknown"
    platform = detect_platform(url)
    d = video_dir_from_url(url, video_id)

    core = {
        "success": True,
        "video_id": video_id,
        "platform": platform,
        "video_dir": str(d),
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "duration": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "webpage_url": info.get("webpage_url") or url,
        "description": info.get("description"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "subtitles": sorted((info.get("subtitles") or {}).keys()),
        "automatic_captions": sorted((info.get("automatic_captions") or {}).keys()),
    }

    info_path = d / "info.json"
    info_path.write_text(json.dumps(core, ensure_ascii=False, indent=2), encoding="utf-8")
    core["info_path"] = str(info_path)

    if download_thumbnail:
        thumb_url = info.get("thumbnail")
        if thumb_url:
            try:
                core["thumbnail_path"] = _download_thumbnail(thumb_url, d)
            except Exception as e:
                logger.warning("封面下载失败: %s", e)
                core["thumbnail_error"] = str(e)

    return core


def _download_thumbnail(url: str, d: Path) -> str:
    """下载封面到 d/thumbnail.{ext}，返回路径。"""
    r = requests.get(url, timeout=30, stream=True)
    r.raise_for_status()
    ext = "jpg"
    ctype = r.headers.get("content-type", "").lower()
    if "webp" in ctype:
        ext = "webp"
    elif "png" in ctype:
        ext = "png"
    out = d / f"thumbnail.{ext}"
    with open(out, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
    return str(out)
