#!/usr/bin/env python3
"""subtitle-burn —— SRT 烧录为圆角药丸字幕（原子能力）。

SRT → ASS(居中圆角药丸底 + 白字) → ffmpeg libass 烧进画面。
源自 slicer.py::make_subtitles，几何从写死 720x1280 改为按视频实际尺寸自适应。
幂等、不改原片。术语纠错请先用 subtitle-ai-fix；本原子只负责排版烧录。

用法:
  subtitle_burn.py IN.mp4 OUT.mp4 --srt x.srt
  subtitle_burn.py IN.mp4 OUT.mp4 --srt x.srt --fs 36 --y 1150   # 字号/基线 y(默认 h-130)
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import run, probe, parse_srt, ensure_parent  # noqa: E402

PAD, H, R = 22, 60, 22   # 药丸内边距/高/圆角


def _cwid(c, FS):
    if '一' <= c <= '鿿' or c in "，。！？、；：—…“”（）《》": return 0.708 * FS
    if c.isascii() and c.isalpha(): return 0.472 * FS
    if c.isdigit(): return 0.431 * FS
    if c == ' ': return 0.25 * FS
    return 0.389 * FS


def _textw(s, FS): return sum(_cwid(c, FS) for c in s)


def _pill(W, H, r):
    k = round(r * 0.5523)
    return (f"m {r} 0 l {W-r} 0 b {W-r+k} 0 {W} {r-k} {W} {r} l {W} {H-r} "
            f"b {W} {H-r+k} {W-r+k} {H} {W-r} {H} l {r} {H} b {r-k} {H} 0 {H-r+k} 0 {H-r} "
            f"l 0 {r} b 0 {r-k} {r-k} 0 {r} 0")


def _asst(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _chunk(text, MAX=13.0):
    toks = re.findall(r"[A-Za-z0-9]+|[一-鿿]|[，。！？、；：]|\s+|.", text)
    def w(t):
        if re.match(r"[A-Za-z0-9]+", t): return max(len(t) * 0.6, 0.6)
        if t.isspace(): return 0.3
        return 1.0
    out, cur, cw = [], "", 0.0
    for t in toks:
        if cw + w(t) > MAX and cur.strip():
            out.append(cur.strip()); cur = ""; cw = 0.0
        cur += t; cw += w(t)
        if t in "，。！？；" and cw >= MAX * 0.6:
            out.append(cur.strip()); cur = ""; cw = 0.0
    if cur.strip():
        out.append(cur.strip())
    merged = []
    for p in out:
        if merged and len(re.sub(r"[^A-Za-z0-9一-鿿]", "", p)) < 2:
            merged[-1] += p
        else:
            merged.append(p)
    return merged or [text]


def build_ass(srt, w, h, fs, cy):
    ev = []
    for t0, t1, txt in parse_srt(srt):
        zh = [x for x in txt.split() if re.search(r"[一-鿿]", x)]
        keep = (zh[0] if zh else txt).strip()
        pcs = _chunk(keep); tot = sum(len(p) for p in pcs) or 1; cur = t0
        for p in pcs:
            seg = (t1 - t0) * len(p) / tot
            s, e = _asst(cur), _asst(cur + seg); cur += seg
            W = round(_textw(p, fs)) + 2 * PAD; PX = round((w - W) / 2); PYt = cy - H // 2
            ev.append(f"Dialogue: 0,{s},{e},Pill,,0,0,0,,{{\\pos({PX},{PYt})\\an7\\p1}}{_pill(W, H, R)}{{\\p0}}")
            ev.append(f"Dialogue: 1,{s},{e},Cap,,0,0,0,,{{\\pos({w//2},{cy})\\an5}}{p}")
    hdr = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\nScaledBorderAndShadow: yes\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           f"Style: Cap,PingFang SC,{fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n"
           f"Style: Pill,PingFang SC,{fs},&H00141414,&H000000FF,&H00141414,&H00141414,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    return hdr + "\n".join(ev) + "\n"


def main():
    ap = argparse.ArgumentParser(description="SRT 烧录圆角药丸字幕")
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--srt", required=True)
    ap.add_argument("--fs", type=int, default=36, help="字号(默认36)")
    ap.add_argument("--y", type=int, default=None, help="字幕基线 y(默认 h-130)")
    a = ap.parse_args()

    if not Path(a.input).exists():
        raise SystemExit(f"输入不存在: {a.input}")
    if not Path(a.srt).exists():
        raise SystemExit(f"SRT 不存在: {a.srt}")
    out = ensure_parent(a.output)
    w, h, _dur, has_audio = probe(a.input)
    if w == 0:
        raise SystemExit(f"读不到视频尺寸: {a.input}")
    cy = a.y if a.y is not None else h - 130
    ass = out.with_suffix(".zh.ass")
    ass.write_text(build_ass(a.srt, w, h, a.fs, cy), encoding="utf-8")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", a.input,
           "-vf", f"subtitles={ass}", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p"]
    if has_audio:
        cmd += ["-c:a", "copy"]
    cmd += ["-movflags", "+faststart", str(out)]
    r = run(cmd)
    ass.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    print(f"DONE  {out}  字幕烧录 fs={a.fs} y={cy}")


if __name__ == "__main__":
    main()
