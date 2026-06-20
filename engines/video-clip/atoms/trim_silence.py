#!/usr/bin/env python3
"""trim_silence —— ③3c 去长静音：把超过 --min-sil 的停顿压短，自然停顿保留。★承重墙关键螺丝。

六环阶段化升级 WS-2（产品化 var/zh_main/0618test/trim_silence.py）+ WS-6 伴随轨。
在 REF 音频上做静音检测 → 算出「保留区间 keeps」(assembled 时间轴)，把同一套 keeps 应用到 IN(身子)，
可选 --apply-to 同步应用到别的同轴文件(如干净人声 wav)，保证多文件同步。
★WS-6：字幕便签(.srt)也用**同一份 keeps**裁（--srt-in/--srt-out）——落删除段的字幕跟着删、跨切口的
  裁到保留段，永不显示已删内容；画/音/字幕同一把刀（INV-2）。
keeps 仍吐进剪辑账本(cut manifest)给门检用。

REF 与 IN 必须同一时间轴(同长度)。用法:
  trim_silence.py --ref 人声.wav --in 身子.mp4 --out 身子_去静音.mp4 --manifest m.json \
                  [--apply-to 人声.wav:人声_去静音.wav] [--srt-in clip.srt --srt-out trimmed.srt] \
                  [--min-sil 1.5] [--keep-pad 0.4] [--noise -30dB]
"""
from __future__ import annotations
import argparse, re, subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _manifest  # noqa: E402

ENC_V = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
ENC_A = ["-c:a", "aac", "-ar", "48000", "-ac", "2"]


def _run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败:\n{' '.join(map(str, cmd))}\n{r.stderr[-800:]}")
    return r


def _dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0)


def _has_video(p):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=codec_type", "-of", "csv=p=0", str(p)],
                               capture_output=True, text=True).stdout.strip())


def detect_silences(ref, noise, min_sil):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(ref), "-af",
                          f"silencedetect=noise={noise}:d={min_sil}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    sils = []; s = None
    for m in re.finditer(r"silence_(start|end):\s*([0-9.]+)", out):
        if m.group(1) == "start":
            s = float(m.group(2))
        elif s is not None:
            sils.append((s, float(m.group(2)))); s = None
    return sils


def keep_intervals(dur, sils, min_sil, keep_pad):
    cuts = []
    for s, e in sils:
        if e - s > min_sil:                       # 只切超长停顿的「多余」部分，两端各留 keep_pad/2
            cuts.append((s + keep_pad / 2, e - keep_pad / 2))
    keeps = []; cur = 0.0
    for cs, ce in sorted(cuts):
        if cs > cur:
            keeps.append((cur, cs))
        cur = max(cur, ce)
    if cur < dur:
        keeps.append((cur, dur))
    return keeps


def apply_keeps(inp, outp, keeps):
    vid = _has_video(inp)
    F = []
    for i, (s, e) in enumerate(keeps):
        if vid:
            F.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{i}];")
        F.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS[a{i}];")
    n = len(keeps)
    aenc = ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"] if str(outp).lower().endswith(".wav") else ENC_A
    if vid:
        F.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
        maps = ["-map", "[v]", "-map", "[a]"]; enc = ENC_V + ENC_A
    else:
        F.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]")
        maps = ["-map", "[a]"]; enc = aenc
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(inp), "-filter_complex", "".join(F),
          *maps, *enc, str(outp)])


# ── 字幕便签同刀裁（WS-6 INV-2）：用裁视频/音频的同一份 keeps 裁 .srt ──
_SRT_RE = re.compile(r"(\d+):(\d+):(\d+[.,]\d+)\s*-->\s*(\d+):(\d+):(\d+[.,]\d+)")


def _srt_secs(x):
    h, m, s = x.strip().replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _srt_t(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _parse_srt(path):
    cues = []
    for blk in re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8").strip()):
        L = [x for x in blk.split("\n") if x.strip()]
        mm = next((i for i, x in enumerate(L) if "-->" in x), None)
        if mm is None:
            continue
        g = _SRT_RE.search(L[mm])
        if not g:
            continue
        b = _srt_secs(":".join(g.groups()[0:3])); e = _srt_secs(":".join(g.groups()[3:6]))
        cues.append((b, e, " ".join(L[mm + 1:]).strip()))
    return cues


def cut_srt(cues, keeps):
    """用同一份 keeps 把字幕便签裁到 trimmed 时间轴：
    每条 cue 与各保留段求交，落删除段→丢；跨切口→裁到保留段；删去的静音让相邻片段在输出轴上天然接续。"""
    out = []
    for (cb, ce, text) in cues:
        nb = ne = None; off = 0.0
        for s, e in keeps:
            ov_s = max(cb, s); ov_e = min(ce, e)
            if ov_s < ov_e:
                ob = off + (ov_s - s); oe = off + (ov_e - s)
                if nb is None:
                    nb = ob
                ne = oe
            off += (e - s)
        if nb is not None and ne is not None and ne > nb:
            out.append((nb, ne, text))
    return out


def write_srt(cues, out):
    lines = []
    for i, (b, e, text) in enumerate(cues, 1):
        lines += [str(i), f"{_srt_t(b)} --> {_srt_t(e)}", text, ""]
    Path(out).write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="静音检测参考音频(同轴)")
    ap.add_argument("--in", dest="inp", required=True, help="身子(视频)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--apply-to", action="append", default=[], help='"src:dst" 同步应用同一 keeps(可多次)')
    ap.add_argument("--srt-in", dest="srt_in", default=None, help="字幕便签(assembled 轴)，同刀裁到 trimmed 轴")
    ap.add_argument("--srt-out", dest="srt_out", default=None, help="裁后字幕便签(trimmed 轴)")
    ap.add_argument("--min-sil", type=float, default=1.5)
    ap.add_argument("--keep-pad", type=float, default=0.4)
    ap.add_argument("--noise", default="-30dB")
    a = ap.parse_args()

    dur = _dur(a.inp)
    sils = detect_silences(a.ref, a.noise, a.min_sil)
    keeps = keep_intervals(dur, sils, a.min_sil, a.keep_pad)
    removed = dur - sum(e - s for s, e in keeps)

    apply_keeps(a.inp, a.out, keeps)
    for pair in a.apply_to:
        src, dst = pair.split(":", 1)
        apply_keeps(src, dst, keeps)
    if a.srt_in and a.srt_out:                       # 字幕便签同刀裁（INV-2）
        cut = cut_srt(_parse_srt(a.srt_in), keeps)
        write_srt(cut, a.srt_out)
        print(f"  字幕同刀裁 {Path(a.srt_in).name}→{Path(a.srt_out).name}  {len(cut)}条")

    out_dur = _dur(a.out)
    man = _manifest.load(a.manifest) if Path(a.manifest).exists() else _manifest.new(a.inp)
    _manifest.add_keep_op(man, "trim_silence", "assembled", "trimmed", keeps,
                          removed_sec=round(removed, 3),
                          params={"min_sil": a.min_sil, "keep_pad": a.keep_pad, "noise": a.noise})
    man["durations"]["trimmed"] = round(out_dur, 3)
    _manifest.save(man, a.manifest)
    print(f"DONE trim_silence  {a.out}  保留{len(keeps)}段 去长静音{removed:.2f}s  {dur:.3f}s→{out_dur:.3f}s  | 账本+1")


if __name__ == "__main__":
    main()
