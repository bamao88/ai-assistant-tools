"""关键帧抽取：三种模式。

1. --at "00:30,01:45,03:20"  指定时间戳
2. --interval 60             每 N 秒一帧
3. --scene-change            ffmpeg 场景切换检测

实现：yt-dlp 下载低分辨率临时副本 → ffmpeg 抽帧 → 删除临时视频。
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

import yt_dlp

from .info import fetch_info
from .storage import video_dir_from_url
from .utils import format_timestamp, parse_timestamp
from .ydl import merge_ydl_opts

logger = logging.getLogger(__name__)


def extract_keyframes(
    url: str,
    mode: str,
    at_list: list[str] | None = None,
    interval: float | None = None,
    scene_threshold: float = 0.3,
    max_frames: int = 60,
) -> dict:
    """抽关键帧。

    Args:
        mode: "at" | "interval" | "scene-change"
        at_list: mode=="at" 时的时间戳列表（字符串，parse_timestamp 可解析）
        interval: mode=="interval" 时的秒数
        scene_threshold: mode=="scene-change" 时的场景切换阈值 (0-1)
        max_frames: 总帧数上限，防止一长条视频抽几百张
    """
    meta = fetch_info(url, download_thumbnail=False)
    d = video_dir_from_url(url, meta["video_id"])
    kf_dir = d / "keyframes"
    kf_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vr_kf_") as tmp:
        video_path = _download_low_res(url, Path(tmp))

        if mode == "at":
            if not at_list:
                raise ValueError("mode=at 需要 --at 参数")
            frames = _extract_at_timestamps(video_path, at_list, kf_dir)
        elif mode == "interval":
            if not interval:
                raise ValueError("mode=interval 需要 --interval 参数")
            frames = _extract_interval(video_path, interval, kf_dir, max_frames)
        elif mode == "scene-change":
            frames = _extract_scene_change(
                video_path, kf_dir, scene_threshold, max_frames
            )
        else:
            raise ValueError(f"未知 mode: {mode}")

    return {
        "success": True,
        "video_id": meta["video_id"],
        "platform": meta["platform"],
        "mode": mode,
        "keyframes_dir": str(kf_dir),
        "frame_count": len(frames),
        "frames": frames,
    }


def _download_low_res(url: str, tmp: Path) -> Path:
    """下低分辨率临时副本（抽帧用，用完即删）。"""
    outtmpl = str(tmp / "%(id)s.%(ext)s")
    # 优先 <=480p，退化到 worst
    ydl_opts = merge_ydl_opts({
        "format": "bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480]/worst",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
    })
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    files = [f for f in tmp.iterdir() if f.suffix.lower() in {".mp4", ".mkv", ".webm"}]
    if not files:
        raise RuntimeError("低分辨率视频下载失败")
    return files[0]


def _extract_at_timestamps(video: Path, ts_list: list[str], out_dir: Path) -> list[dict]:
    """在指定时间戳抽帧。"""
    results = []
    for ts in ts_list:
        seconds = parse_timestamp(ts)
        name = f"{format_timestamp(seconds, filename_safe=True)}.png"
        out = out_dir / name
        _run_ffmpeg_single_frame(video, seconds, out)
        results.append({"timestamp": format_timestamp(seconds), "path": str(out)})
    return results


def _run_ffmpeg_single_frame(video: Path, seconds: float, out: Path) -> None:
    """在 `seconds` 处抽一帧 PNG。-ss 放在 -i 前用 fast seek。"""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{seconds}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 抽帧失败（{out.name}）: {proc.stderr[-500:]}")


def _extract_interval(
    video: Path, interval: float, out_dir: Path, max_frames: int
) -> list[dict]:
    """每 interval 秒抽一帧。"""
    duration = _probe_duration(video)
    count = min(int(duration // interval) + 1, max_frames)
    results = []
    for i in range(count):
        seconds = i * interval
        if seconds >= duration:
            break
        name = f"{format_timestamp(seconds, filename_safe=True)}.png"
        out = out_dir / name
        _run_ffmpeg_single_frame(video, seconds, out)
        results.append({"timestamp": format_timestamp(seconds), "path": str(out)})
    return results


def _extract_scene_change(
    video: Path, out_dir: Path, threshold: float, max_frames: int
) -> list[dict]:
    """场景切换检测 + 抽帧。先用 showinfo 拿时间戳，再按时间戳抽帧。"""
    # Step 1: 让 ffmpeg 报告场景变化时间戳
    cmd = [
        "ffmpeg",
        "-i",
        str(video),
        "-vf",
        f"select='gt(scene,{threshold})',showinfo",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # showinfo 输出形如：[Parsed_showinfo_1 @ 0x...] n:   0 pts:    0 pts_time:5.04 ...
    pattern = re.compile(r"pts_time:([\d.]+)")
    timestamps = [float(m) for m in pattern.findall(proc.stderr)]
    timestamps = timestamps[:max_frames]

    results = []
    for seconds in timestamps:
        name = f"{format_timestamp(seconds, filename_safe=True)}.png"
        out = out_dir / name
        try:
            _run_ffmpeg_single_frame(video, seconds, out)
            results.append({"timestamp": format_timestamp(seconds), "path": str(out)})
        except RuntimeError as e:
            logger.warning("抽帧跳过 %s: %s", seconds, e)
    return results


def _probe_duration(video: Path) -> float:
    """ffprobe 读视频时长（秒）。"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {proc.stderr}")
    return float(proc.stdout.strip())


def extract_keyframes_from_local(
    video_key: str,
    at_list: list[str],
) -> dict:
    """针对已下载过 transcript 的视频，用本地临时重下再抽帧（给 search → keyframes 组合用）。

    当前实现与 extract_keyframes(mode=at) 一致（都要重新下低分辨率副本），
    仅是调用口更友好：给 video-id 而不是 URL。
    """
    from .storage import video_dir_from_key

    d = video_dir_from_key(video_key, create=False)
    info_path = d / "info.json"
    if not info_path.exists():
        raise RuntimeError(f"未找到 info.json：{info_path}，先运行 info 或 quick-research")
    import json

    meta = json.loads(info_path.read_text(encoding="utf-8"))
    url = meta.get("webpage_url")
    if not url:
        raise RuntimeError("info.json 缺少 webpage_url")
    return extract_keyframes(url, mode="at", at_list=at_list)
