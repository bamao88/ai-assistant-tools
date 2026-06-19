#!/usr/bin/env python3
"""speed-adapt —— 变速原子。两档：

1) 自适应档(默认)：读 SRT 逐句算字符语速(cps)，慢句加速/快句保护/句间停顿压缩；atempo 保音调。
   源自 assistant_zh/workflow/video_framework_slicer/slicer.py::accelerate（PPT 风格内置变速同源）。
2) 固定档 --fixed F（③3d 裁剪版用）：整体匀速 F 倍，变速不变调；可选 --replace-audio 换干净人声轨。
   ★承重墙：把变速 factor 记一笔进剪辑账本(cut manifest)，④ subtitle_align 重放字幕时间。

幂等、不改原片。用法:
  speed_adapt.py IN.mp4 OUT.mp4 --srt x.srt                        # 自适应档
  speed_adapt.py IN.mp4 OUT.mp4 --fixed 1.2 [--replace-audio 人声.wav] --manifest m.json   # 固定档
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from vutil import run, ffprobe_dur, parse_srt, ensure_parent  # noqa: E402
import _manifest  # noqa: E402

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-ar", "48000", "-ac", "2"]


def _atempo_chain(factor: float) -> str:
    """atempo 单级仅支持 0.5–2.0；超范围拆成多级连乘。"""
    f = float(factor); parts = []
    while f > 2.0:
        parts.append("atempo=2.0"); f /= 2.0
    while f < 0.5:
        parts.append("atempo=0.5"); f /= 0.5
    parts.append(f"atempo={f:.4f}")
    return ",".join(parts)


def run_fixed(inp, out, factor, replace_audio, manifest_path):
    """固定倍速 F：视频 setpts/F、音频 atempo F(变速不变调)；--replace-audio 换轨。记账本 speed op。"""
    out = ensure_parent(out)
    dur = ffprobe_dur(inp)
    atempo = _atempo_chain(factor)
    if replace_audio:
        fc = f"[0:v]setpts=PTS/{factor}[v];[1:a]{atempo}[a]"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(inp), "-i", str(replace_audio),
               "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-shortest",
               *ENC, "-movflags", "+faststart", str(out)]
    else:
        fc = f"[0:v]setpts=PTS/{factor}[v];[0:a]{atempo}[a]"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(inp),
               "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
               *ENC, "-movflags", "+faststart", str(out)]
    r = run(cmd)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    od = ffprobe_dur(out)
    if manifest_path:
        man = _manifest.load(manifest_path) if Path(manifest_path).exists() else _manifest.new(inp)
        _manifest.add_speed_op(man, "trimmed", "final", factor,
                               replace_audio=str(replace_audio) if replace_audio else None)
        man["durations"]["final"] = round(od, 3)
        _manifest.save(man, manifest_path)
    print(f"DONE speed_adapt(fixed {factor}x)  {out}  {dur:.3f}s→{od:.3f}s"
          f"{'  换轨' if replace_audio else ''}{'  | 账本+1' if manifest_path else ''}")


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
