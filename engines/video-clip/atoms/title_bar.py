#!/usr/bin/env python3
"""title-bar —— 顶部黑底标题条叠加（原子能力）。

在画面顶部叠一条纯色底（默认黑 #202020、整宽），上面排白色粗宋标题，
中文自动换行 + 按字宽居中，几何/配色照搬"标题黑色底色.png"参照：
顶部留白 3.85%H、条高 14.06%H、整宽。字体默认 思源宋体超粗体（SourceHanSerifCN-Heavy）。

排版交给 PIL（拿真实字宽，懂"DIfy"不拆、"。，、？"不放行首），
ffmpeg 只把渲好的透明 PNG 整片叠上去（全程显示，不裁不改原片，幂等）。
标题文字是内容，由调用方 --text 提供——引擎不内置任何选题标题。

用法:
  title_bar.py IN.mp4 OUT.mp4 --text "2026，企业AI落地还用 DIfy、扣子？纯属浪费钱"
  title_bar.py IN.mp4 OUT.mp4 --text "..." --fs 56            # 固定字号（默认自动撑满）
  title_bar.py IN.mp4 OUT.mp4 --text "上行\n下行"              # \n 手动换行
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from vutil import run, probe, ensure_parent, x264  # noqa: E402

FONT_DEFAULT = HERE.parent / "assets" / "fonts" / "SourceHanSerifCN-Heavy.otf"
# 备选（思源缺失时）：宋体超粗 → 苹方粗
FONT_FALLBACKS = ["/System/Library/Fonts/Supplemental/Songti.ttc",
                  "/System/Library/Fonts/PingFang.ttc"]
# 不可作为行首的标点（中文排版：闭合/收尾标点跟随上一行）
NO_LEAD = set("。，、；：？！）》”」』%…—-")


def _font_path(p: str | None) -> str:
    for cand in ([p] if p else []) + [str(FONT_DEFAULT)] + FONT_FALLBACKS:
        if cand and Path(cand).exists():
            return cand
    raise SystemExit("找不到可用字体；用 --font 指定一个 .otf/.ttf")


def _tokens(s: str):
    """切 token：ASCII 字母数字连成一段（不拆词），其余逐字符。"""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c.isascii() and c.isalnum():
            j = i
            while j < n and s[j].isascii() and s[j].isalnum():
                j += 1
            out.append(s[i:j]); i = j
        else:
            out.append(c); i += 1
    return out


def _wrap(text: str, font, maxw: int):
    """按真实字宽贪心换行；闭合标点不放行首；尊重手写 \\n。返回行列表。"""
    lines = []
    for para in text.replace("\\n", "\n").split("\n"):
        cur = ""
        for tok in _tokens(para):
            trial = cur + tok
            if cur and font.getlength(trial) > maxw and tok not in NO_LEAD:
                lines.append(cur); cur = tok
            else:
                cur += tok
        lines.append(cur)
    return [ln for ln in lines if ln != ""] or [text]


def _fit(text, font_path, maxw, max_block_h, fs_hint, max_lines):
    """选字号：给定就用给定（仍换行）；否则从大往小自动撑满条高与行宽。"""
    rng = [fs_hint] if fs_hint else range(160, 17, -2)
    chosen = None
    for fs in rng:
        font = ImageFont.truetype(font_path, fs)
        lines = _wrap(text, font, maxw)
        widest = max(font.getlength(ln) for ln in lines)
        block_h = len(lines) * fs * 1.32
        if fs_hint or (widest <= maxw and block_h <= max_block_h and len(lines) <= max_lines):
            chosen = (fs, font, lines); break
    if not chosen:
        font = ImageFont.truetype(font_path, 18)
        chosen = (18, font, _wrap(text, font, maxw))
    return chosen


def render_overlay(W, H, text, font_path, args) -> Image.Image:
    top = round(args.top_frac * H)
    bar_h = round(args.bar_h_frac * H)
    side = round(args.side_frac * W)
    maxw = W - 2 * side
    vpad = round(bar_h * 0.16)
    fs, font, lines = _fit(text, font_path, maxw, bar_h - 2 * vpad, args.fs, args.max_lines)

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    br, bg, bb = (int(args.bar_color[i:i + 2], 16) for i in (0, 2, 4))
    d.rectangle([0, top, W, top + bar_h], fill=(br, bg, bb, 255))

    line_h = fs * 1.32
    block_h = len(lines) * line_h
    y = top + (bar_h - block_h) / 2
    tr, tg, tb = (int(args.text_color[i:i + 2], 16) for i in (0, 2, 4))
    for ln in lines:
        x = (W - font.getlength(ln)) / 2
        d.text((x, y), ln, font=font, fill=(tr, tg, tb, 255))
        y += line_h
    return img, fs, lines


def main():
    ap = argparse.ArgumentParser(description="顶部黑底标题条叠加")
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--text", required=True, help="标题文字（\\n 手动换行）")
    ap.add_argument("--font", default=None, help="字体路径（默认思源宋体超粗体）")
    ap.add_argument("--fs", type=int, default=None, help="字号(默认自动撑满条高)")
    ap.add_argument("--top-frac", dest="top_frac", type=float, default=0.0385, help="条顶距画面顶比例")
    ap.add_argument("--bar-h-frac", dest="bar_h_frac", type=float, default=0.1406, help="条高占画面高比例")
    ap.add_argument("--side-frac", dest="side_frac", type=float, default=0.055, help="左右安全边比例")
    ap.add_argument("--bar-color", dest="bar_color", default="202020", help="底色 RRGGBB(默认202020)")
    ap.add_argument("--text-color", dest="text_color", default="FFFFFF", help="字色 RRGGBB(默认白)")
    ap.add_argument("--max-lines", dest="max_lines", type=int, default=2, help="自动字号时目标最多行数")
    a = ap.parse_args()

    src = Path(a.input)
    if not src.exists():
        raise SystemExit(f"输入不存在: {src}")
    out = ensure_parent(a.output)
    w, h, dur, has_audio = probe(src)
    if w == 0 or dur <= 0:
        raise SystemExit(f"读不到视频: {src}")

    font_path = _font_path(a.font)
    overlay, fs, lines = render_overlay(w, h, a.text, font_path, a)
    png = out.with_suffix(".titlebar.png")
    overlay.save(png)

    fc = "[0:v][1:v]overlay=0:0:eof_action=pass[v]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
           "-loop", "1", "-t", f"{dur}", "-i", str(png),
           "-filter_complex", fc, "-map", "[v]"]
    if has_audio:
        cmd += ["-map", "0:a"]
    cmd += ["-shortest", *x264(audio=has_audio), "-movflags", "+faststart", str(out)]
    r = run(cmd)
    png.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    print(f"DONE  {out}  标题条 fs={fs} 行数={len(lines)} 字体={Path(font_path).name}")
    for i, ln in enumerate(lines, 1):
        print(f"      行{i}: {ln}")


if __name__ == "__main__":
    main()
