#!/usr/bin/env python3
"""cover-frame —— 抽一帧做封面（原子能力）。

从视频指定时间抽一帧存为图片；可选叠一张标题/文案 PNG(透明)。幂等、不改原片。

用法:
  cover_frame.py IN.mp4 cover.png                      # 抽首帧
  cover_frame.py IN.mp4 cover.png --at 3.5             # 抽第3.5秒
  cover_frame.py IN.mp4 cover.png --at 2 --overlay title.png   # 叠标题
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import run, ffprobe_dur, ensure_parent  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="抽帧做封面")
    ap.add_argument("input"); ap.add_argument("output", help="输出图片(.png/.jpg)")
    ap.add_argument("--at", type=float, default=0.0, help="抽帧时间(秒,默认0=首帧)")
    ap.add_argument("--overlay", help="叠加的标题/文案 PNG(可透明,全画幅对齐)")
    a = ap.parse_args()

    if not Path(a.input).exists():
        raise SystemExit(f"输入不存在: {a.input}")
    out = ensure_parent(a.output)
    dur = ffprobe_dur(a.input)
    at = min(max(a.at, 0.0), max(dur - 0.05, 0.0))

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at}", "-i", a.input]
    if a.overlay:
        if not Path(a.overlay).exists():
            raise SystemExit(f"overlay 不存在: {a.overlay}")
        cmd += ["-i", a.overlay, "-filter_complex", "[0:v][1:v]overlay=0:0[v]", "-map", "[v]"]
    cmd += ["-frames:v", "1", str(out)]
    r = run(cmd)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    print(f"DONE  {out}  封面@{at:.2f}s" + (f" +overlay {Path(a.overlay).name}" if a.overlay else ""))


if __name__ == "__main__":
    main()
