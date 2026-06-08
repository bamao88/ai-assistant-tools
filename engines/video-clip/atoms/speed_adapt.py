#!/usr/bin/env python3
"""speed-adapt —— 按逐字稿语速自适应变速（原子能力）。

读 SRT，逐句算字符语速(cps)：慢句加速、快句保护、句间停顿压缩；atempo 保音调。
源自 assistant_zh/workflow/video_framework_slicer/slicer.py::accelerate，去耦合成通用原子。
幂等、不改原片。可选输出变速分段映射(给 name-mask 之类做时间换算)。

用法:
  speed_adapt.py IN.mp4 OUT.mp4 --srt x.srt
  speed_adapt.py IN.mp4 OUT.mp4 --srt x.srt --target_cps 8 --max_speed 2.0 --gap_speed 2.0 --min_speed 1.0
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import run, ffprobe_dur, parse_srt, ensure_parent  # noqa: E402


def build_segments(srt, dur, tgt, mx, gap, mn):
    cues = []
    for t0, t1, txt in parse_srt(srt):
        nn = len(re.sub(r"[^一-鿿A-Za-z0-9]", "", txt))
        cues.append([t0, min(t1, dur), nn])
    cues.sort()
    segs, cur = [], 0.0
    for t0, t1, nn in cues:
        if t0 > cur + 0.05:
            segs.append((cur, t0, gap))       # 句间停顿压缩
        d = t1 - t0
        cps = nn / d if d > 0 else tgt
        sp = min(max(tgt / cps if cps > 0 else mn, mn), mx)
        segs.append((t0, t1, sp)); cur = t1
    if cur < dur - 0.05:
        segs.append((cur, dur, gap))
    return segs


def main():
    ap = argparse.ArgumentParser(description="按语速自适应变速")
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--srt", required=True)
    ap.add_argument("--target_cps", type=float, default=8.0)
    ap.add_argument("--max_speed", type=float, default=2.0)
    ap.add_argument("--gap_speed", type=float, default=2.0)
    ap.add_argument("--min_speed", type=float, default=1.0)
    ap.add_argument("--dump-filter", action="store_true", help="把分段变速 filter 落盘(同名 .accel_filter.txt)")
    a = ap.parse_args()

    if not Path(a.input).exists():
        raise SystemExit(f"输入不存在: {a.input}")
    if not Path(a.srt).exists():
        raise SystemExit(f"SRT 不存在: {a.srt}")
    out = ensure_parent(a.output)
    dur = ffprobe_dur(a.input)
    if dur <= 0:
        raise SystemExit(f"读不到时长: {a.input}")
    segs = build_segments(a.srt, dur, a.target_cps, a.max_speed, a.gap_speed, a.min_speed)
    if not segs:
        raise SystemExit("SRT 解析后无分段")

    F, vc, ac = [], [], []
    for i, (s, e, sp) in enumerate(segs):
        F.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=(PTS-STARTPTS)/{sp:.4f}[v{i}];")
        F.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,atempo={sp:.4f}[a{i}];")
        vc.append(f"[v{i}]"); ac.append(f"[a{i}]")
    F.append("".join(f"{vc[i]}{ac[i]}" for i in range(len(segs))) +
             f"concat=n={len(segs)}:v=1:a=1[v][a]")
    flt = out.with_suffix(".accel_filter.txt")
    flt.write_text("\n".join(F), encoding="utf-8")
    od = sum((e - s) / sp for s, e, sp in segs)

    r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.input,
             "-filter_complex_script", str(flt), "-map", "[v]", "-map", "[a]",
             "-r", "25", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(out)])
    if not a.dump_filter:
        flt.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    print(f"DONE  {out}  {len(segs)}段 目标{a.target_cps}cps  {dur:.0f}s→{od:.0f}s (均速{dur/od:.2f}x)")


if __name__ == "__main__":
    main()
