#!/usr/bin/env python3
"""concat —— 直接拼接多个视频片段为一条（原子能力）。

幂等、不改原片。参数一致(同分辨率/帧率/编码)时走 concat demuxer 零重编、最快；
有差异时统一缩放铺到目标尺寸(contain+pad,黑边)再重编拼接。

用法:
  concat.py OUT.mp4 --inputs a.mp4 b.mp4 c.mp4
  concat.py OUT.mp4 --inputs a.mp4 b.mp4 --target 720x1280 --fps 25   # 强制目标规格重编
  concat.py OUT.mp4 --inputs a.mp4 b.mp4 --reencode                   # 强制重编(不尝试零重编)
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import run, probe, ensure_parent, x264  # noqa: E402


def uniform(specs):
    """所有片段 (w,h) 是否一致（帧率差异交给重编兜底，这里只看尺寸）。"""
    return len({(w, h) for w, h, _, _ in specs}) == 1


def concat_copy(inputs, out):
    """同规格：concat demuxer + stream copy。"""
    lst = ensure_parent(out).with_suffix(".concat.txt")
    lst.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in inputs), encoding="utf-8")
    r = run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)])
    lst.unlink(missing_ok=True)
    return r


def concat_reencode(inputs, out, tw, th, fps):
    """异规格：每段 scale(contain)+pad 到目标，统一重编后 filter concat。"""
    n = len(inputs)
    parts, labels = [], []
    for i in range(n):
        parts.append(
            f"[{i}:v]scale={tw}:{th}:force_original_aspect_ratio=decrease,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{i}];"
            f"[{i}:a]aresample=async=1[a{i}];")
        labels.append(f"[v{i}][a{i}]")
    fc = "".join(parts) + "".join(labels) + f"concat=n={n}:v=1:a=1[v][a]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p in inputs:
        cmd += ["-i", str(p)]
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]",
            *x264(), "-movflags", "+faststart", str(out)]
    return run(cmd)


def main():
    ap = argparse.ArgumentParser(description="直接拼接多个视频为一条")
    ap.add_argument("output")
    ap.add_argument("--inputs", nargs="+", required=True, help="≥2 个输入视频，按此顺序拼接")
    ap.add_argument("--target", help="目标尺寸 WxH（重编时用；默认取第一个输入）")
    ap.add_argument("--fps", type=int, default=25, help="重编目标帧率（默认25）")
    ap.add_argument("--reencode", action="store_true", help="强制重编，不尝试零重编")
    a = ap.parse_args()

    inputs = [p for p in a.inputs if Path(p).exists()]
    missing = [p for p in a.inputs if not Path(p).exists()]
    if missing:
        raise SystemExit(f"输入不存在: {missing}")
    if len(inputs) < 2:
        raise SystemExit("至少需要 2 个输入")

    specs = [probe(p) for p in inputs]
    if not a.reencode and not a.target and uniform(specs):
        r = concat_copy(inputs, a.output)
        if r.returncode == 0:
            print(f"DONE(copy)  {a.output}  拼接 {len(inputs)} 段，零重编")
            return
        print("  零重编失败，回退重编…", file=sys.stderr)

    if a.target:
        tw, th = (int(x) for x in a.target.lower().split("x"))
    else:
        tw, th = specs[0][0], specs[0][1]
    r = concat_reencode(inputs, a.output, tw, th, a.fps)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    print(f"DONE(reencode)  {a.output}  拼接 {len(inputs)} 段 @ {tw}x{th}/{a.fps}fps")


if __name__ == "__main__":
    main()
