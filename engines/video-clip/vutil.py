"""video-clip 引擎共享工具。把散在各脚本里的 run()/ffprobe 探测去重成一份。

只放通用、无业务耦合的小工具。原子脚本 `from vutil import ...`。
"""
from __future__ import annotations
import subprocess
from pathlib import Path


def run(cmd, **kw):
    """跑命令，捕获输出（text）。返回 CompletedProcess。"""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def ffprobe_dur(path) -> float:
    """视频/音频时长（秒）。读不到返回 0。"""
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path])
    return float(r.stdout.strip() or 0)


def probe(video) -> tuple[int, int, float, bool]:
    """返回 (width, height, duration, has_audio)。"""
    v = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", video])
    parts = (v.stdout.strip().split("x") + ["0", "0"])[:2]
    w, h = int(parts[0] or 0), int(parts[1] or 0)
    dur = ffprobe_dur(video)
    a = run(["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=index", "-of", "csv=p=0", video]).stdout.strip()
    return w, h, dur, bool(a)


def ensure_parent(path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def x264(crf=18, preset="medium", audio=True):
    """统一的 x264 输出参数列表（原子间一致）。"""
    out = ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p"]
    if audio:
        out += ["-c:a", "aac", "-b:a", "128k"]
    return out
