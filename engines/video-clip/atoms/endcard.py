#!/usr/bin/env python3
"""endcard —— 片尾钩子卡叠加（原子能力，通用版）。

把一张卡片叠在视频【最后 N 秒】(淡入后保持)，透明卡压暗画面透出、海报铺满。
幂等、不改原片。引擎只收卡片路径——具体卡片内容(试听课/海报/二维码)是业务数据，
由调用方提供，不内置任何账号专属卡。

--card 支持:
  .png/.jpg → contain 居中叠(不裁不变形)
  .html     → 先用 assets/render_transparent.js 渲成透明 PNG(适合带 scrim 的设计卡)

用法:
  endcard.py IN.mp4 OUT.mp4 --card /abs/poster.jpg
  endcard.py IN.mp4 OUT.mp4 --card /abs/endcard.html --seconds 3 --fade 0.5
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from vutil import run, probe, ensure_parent, x264  # noqa: E402

RENDER_HTML = HERE.parent / "assets" / "render_transparent.js"


def ensure_png(card: Path, work: Path) -> Path:
    if card.suffix.lower() == ".html":
        if not RENDER_HTML.exists():
            raise SystemExit(f"渲染 html 需要 {RENDER_HTML}")
        # 必须传绝对路径：render_transparent.js 把相对路径按它自己的 __dirname 解析，
        # 相对路径会被写到引擎 assets/ 而非这里，导致找不到产物。
        out = work.with_suffix(".card.png").resolve()
        r = run(["node", str(RENDER_HTML), str(card.resolve()), str(out)])
        if r.returncode != 0 or not out.exists():
            raise SystemExit(f"渲染 html 失败：{r.stderr[-400:]}")
        return out
    return card


def main():
    ap = argparse.ArgumentParser(description="片尾钩子卡叠加(末N秒淡入)")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--card", required=True, help="卡片路径 .png/.jpg/.html")
    ap.add_argument("--seconds", type=float, default=3.0, help="片尾停留秒数(默认3)")
    ap.add_argument("--fade", type=float, default=0.5, help="淡入秒数(默认0.5)")
    ap.add_argument("--pos", default="center", help="位置 'x:y' 或 center(默认center)")
    a = ap.parse_args()

    src, card = Path(a.input), Path(a.card)
    if not src.exists():
        raise SystemExit(f"输入不存在: {src}")
    if not card.exists():
        raise SystemExit(f"卡片不存在: {card}")
    out = ensure_parent(a.output)
    w, h, dur, has_audio = probe(src)
    if dur <= 0:
        raise SystemExit(f"读不到视频时长: {src}")

    png = ensure_png(card, out)
    seconds = min(a.seconds, dur)
    fade = min(a.fade, seconds)
    st = round(max(0.0, dur - seconds), 3)
    pos = "(main_w-overlay_w)/2:(main_h-overlay_h)/2" if a.pos == "center" else a.pos
    px, py = pos.split(":")
    fc = (f"[1:v]format=rgba,scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"fade=t=in:st={st}:d={fade}:alpha=1[ec];"
          f"[0:v][ec]overlay=x='{px}':y='{py}':enable='gte(t,{st})':eof_action=pass[v]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
           "-loop", "1", "-t", f"{dur}", "-i", str(png),
           "-filter_complex", fc, "-map", "[v]"]
    if has_audio:
        cmd += ["-map", "0:a"]
    cmd += ["-shortest", *x264(audio=has_audio), "-movflags", "+faststart", str(out)]
    r = run(cmd)
    if png.suffix == ".png" and png.name.endswith(".card.png"):
        png.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    print(f"DONE  {out}  卡片={card.name} 末{seconds:.1f}s(淡入{fade:.1f}s)")


if __name__ == "__main__":
    main()
