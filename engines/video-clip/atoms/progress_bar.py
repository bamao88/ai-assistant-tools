#!/usr/bin/env python3
"""progress-bar —— 底部章节进度条（原子能力）。

复刻 C同学成长片(_camp4_chen_growth)的做法：分段条，当前及之前的幕填高亮色、
其余置灰，叠在画面底部。用 PIL 按视频宽度生成条 PNG，再 ffmpeg overlay 整段叠加。
幂等、不改原片。样式默认值后续再优化（用户已认可先用现有样式）。

用法:
  progress_bar.py IN.mp4 OUT.mp4 --chapters 4 --index 2
  progress_bar.py IN.mp4 OUT.mp4 --chapters 4 --index 2 --label "第二幕·被批评"
  progress_bar.py IN.mp4 OUT.mp4 --chapters 4 --index 2 --h 14 --margin 48 --color FF6B5C
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import run, probe, ensure_parent, x264  # noqa: E402

GAP = 8           # 段间距(px)
SIDE = 40         # 左右留白(px)
INACTIVE = (255, 255, 255, 64)   # 未到达：白色低透明
LABEL_FS = 34


# macOS 上能渲染中文的字体候选（按序尝试，TTC 指定 index=0）
_CJK_FONTS = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]


def _load_cjk_font(size):
    for p in _CJK_FONTS:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size, index=0)
            except Exception:
                continue
    return ImageFont.load_default()


def hexrgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def make_bar(w, h, bar_h, margin, chapters, index, color, label):
    """生成与视频同宽的透明 PNG：底部分段条 +（可选）章节文字。"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    active = hexrgb(color) + (255,)
    seg_w = (w - 2 * SIDE - (chapters - 1) * GAP) / chapters
    y = h - margin - bar_h
    for i in range(chapters):
        x0 = SIDE + i * (seg_w + GAP)
        fill = active if i < index else INACTIVE
        d.rounded_rectangle([x0, y, x0 + seg_w, y + bar_h], radius=bar_h / 2, fill=fill)
    if label:
        font = _load_cjk_font(LABEL_FS)
        tw = d.textlength(label, font=font)
        d.text(((w - tw) / 2, y - LABEL_FS - 14), label, font=font, fill=active)
    return img


def main():
    ap = argparse.ArgumentParser(description="底部章节进度条叠加")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--chapters", type=int, required=True, help="总幕数")
    ap.add_argument("--index", type=int, required=True, help="当前是第几幕(1-based，填满 1..index)")
    ap.add_argument("--label", default="", help="章节文字(可选，置于条上方)")
    ap.add_argument("--h", type=int, default=12, help="条高 px(默认12)")
    ap.add_argument("--margin", type=int, default=44, help="距底 px(默认44)")
    ap.add_argument("--color", default="FF6B5C", help="高亮色 hex(默认 coral FF6B5C)")
    a = ap.parse_args()

    if not Path(a.input).exists():
        raise SystemExit(f"输入不存在: {a.input}")
    if not (1 <= a.index <= a.chapters):
        raise SystemExit(f"--index 必须在 1..{a.chapters}")

    w, h, _dur, has_audio = probe(a.input)
    if w == 0:
        raise SystemExit(f"读不到视频尺寸: {a.input}")

    bar_png = ensure_parent(a.output).with_suffix(".bar.png")
    make_bar(w, h, a.h, a.margin, a.chapters, a.index, a.color, a.label).save(bar_png)

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", a.input, "-i", str(bar_png),
           "-filter_complex", "[0:v][1:v]overlay=0:0[v]", "-map", "[v]"]
    if has_audio:
        cmd += ["-map", "0:a"]
    cmd += [*x264(audio=has_audio), "-movflags", "+faststart", a.output]
    r = run(cmd)
    bar_png.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    print(f"DONE  {a.output}  第{a.index}/{a.chapters}幕进度条" + (f" · {a.label}" if a.label else ""))


if __name__ == "__main__":
    main()
