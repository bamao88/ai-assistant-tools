#!/usr/bin/env python3
"""title-bar —— 顶部标题叠加（原子能力，两种样式）。

style=bar（默认）：在画面顶部叠一条纯色底（默认黑 #202020、整宽），上面排白色粗宋标题，
  几何/配色照搬"标题黑色底色.png"参照：顶部留白 3.85%H、条高 14.06%H、整宽。
style=label：在顶部「黑色信箱块」里居中放一枚白底圆角标签（默认白底 + 黑字），
  标签宽度按文字+内边距自适应、水平+垂直居中；信箱块默认自动探测（首帧顶部连续黑边），
  也可 --block-h-frac 手动指定。框架页竖版口播片的"贴纸式标题"就是这种。

两种样式都：中文按字宽自动换行/居中，字体默认 思源宋体超粗体（SourceHanSerifCN-Heavy）。
排版交给 PIL（拿真实字宽，懂"DIfy"不拆、"。，、？"不放行首），
ffmpeg 只把渲好的透明 PNG 整片叠上去（全程显示，不裁不改原片，幂等）。
标题文字是内容，由调用方 --text 提供——引擎不内置任何选题标题。

用法:
  title_bar.py IN.mp4 OUT.mp4 --text "2026，企业AI落地还用 DIfy、扣子？纯属浪费钱"
  title_bar.py IN.mp4 OUT.mp4 --text "..." --fs 56            # 固定字号（默认自动撑满）
  title_bar.py IN.mp4 OUT.mp4 --text "上行\n下行"              # \n 手动换行
  title_bar.py IN.mp4 OUT.mp4 --style label --text "给还在观望的AI人：认知差就是机会"
  title_bar.py IN.mp4 OUT.mp4 --style label --text "..." --block-h-frac 0.128  # 手动指定信箱块高
"""
from __future__ import annotations
import argparse, sys, tempfile
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


def render_overlay(W, H, text, font_path, args):
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


def detect_top_block(video, H, dark=50, min_frac=0.03):
    """探测顶部「黑色信箱块」高度：抽首帧，从顶往下走连续暗行，返回块高(px)。

    每行横向取样 20 点求平均亮度，<dark 视为暗行；首个亮行处停。
    暗行不足 min_frac*H（没有信箱块）则返回 None，交给调用方走默认比例。
    """
    with tempfile.TemporaryDirectory() as td:
        f1 = Path(td) / "f1.png"
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
                 "-frames:v", "1", str(f1)])
        if r.returncode != 0 or not f1.exists():
            return None
        im = Image.open(f1).convert("RGB")
        W, fh = im.size
        px = im.load()
        xs = [int(W * (i + 0.5) / 20) for i in range(20)]
        bottom = 0
        for y in range(min(fh, H)):
            r, g, b = px[x, y] if False else (0, 0, 0)  # placeholder; replaced below
            lum = sum(px[xx, y][c] for xx in xs for c in range(3)) / (3 * len(xs))
            if lum >= dark:
                break
            bottom = y
    return bottom + 1 if bottom + 1 >= min_frac * H else None


def render_label_overlay(W, H, text, font_path, a, block_top, block_h):
    """白底圆角标签：宽按文字+内边距自适应，水平+垂直居中于 [block_top, block_top+block_h]。"""
    side = round(a.side_frac * W)
    maxw = W - 2 * side                       # 标签外框最大宽
    inner_maxw = maxw - 2 * a.pad_x           # 文字最大宽
    max_box_h = block_h - 2 * a.block_pad     # 标签最大高（块内上下留边）
    fs, font, lines = _fit(text, font_path, inner_maxw,
                           max_box_h - 2 * a.pad_y, a.fs, a.max_lines)

    line_h = fs * 1.32
    tw = max(font.getlength(ln) for ln in lines)
    th = len(lines) * line_h
    box_w = round(tw + 2 * a.pad_x)
    box_h = round(th + 2 * a.pad_y)
    cx, cy = W // 2, round(block_top + block_h / 2)
    bx0, by0 = cx - box_w // 2, cy - box_h // 2

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    br, bg, bb = (int(a.bar_color[i:i + 2], 16) for i in (0, 2, 4))
    d.rounded_rectangle([bx0, by0, bx0 + box_w, by0 + box_h],
                        radius=a.radius, fill=(br, bg, bb, 255))
    tr, tg, tb = (int(a.text_color[i:i + 2], 16) for i in (0, 2, 4))
    y = by0 + a.pad_y
    for ln in lines:
        x = (W - font.getlength(ln)) / 2
        d.text((x, y), ln, font=font, fill=(tr, tg, tb, 255))
        y += line_h
    return img, fs, lines


def main():
    ap = argparse.ArgumentParser(description="顶部标题叠加（bar 整条 / label 居中标签）")
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--text", required=True, help="标题文字（\\n 手动换行）")
    ap.add_argument("--style", choices=["bar", "label"], default="bar",
                    help="bar=顶部整条(默认) | label=信箱块内白底圆角标签")
    ap.add_argument("--font", default=None, help="字体路径（默认思源宋体超粗体）")
    ap.add_argument("--fs", type=int, default=None, help="字号(默认自动撑满)")
    ap.add_argument("--top-frac", dest="top_frac", type=float, default=0.0385, help="[bar]条顶距画面顶比例")
    ap.add_argument("--bar-h-frac", dest="bar_h_frac", type=float, default=0.1406, help="[bar]条高占画面高比例")
    ap.add_argument("--side-frac", dest="side_frac", type=float, default=0.055, help="左右安全边比例")
    ap.add_argument("--bar-color", dest="bar_color", default=None,
                    help="底色 RRGGBB(bar 默认202020 / label 默认FFFFFF)")
    ap.add_argument("--text-color", dest="text_color", default=None,
                    help="字色 RRGGBB(bar 默认FFFFFF / label 默认000000)")
    ap.add_argument("--max-lines", dest="max_lines", type=int, default=2, help="自动字号时目标最多行数")
    # label 专用
    ap.add_argument("--block-h-frac", dest="block_h_frac", type=float, default=None,
                    help="[label]信箱块高占画面高比例（默认自动探测顶部黑边）")
    ap.add_argument("--block-top-frac", dest="block_top_frac", type=float, default=0.0,
                    help="[label]信箱块顶距画面顶比例（默认0=画面最顶）")
    ap.add_argument("--radius", type=int, default=18, help="[label]标签圆角半径")
    ap.add_argument("--pad-x", dest="pad_x", type=int, default=34, help="[label]文字到标签左右内边距")
    ap.add_argument("--pad-y", dest="pad_y", type=int, default=18, help="[label]文字到标签上下内边距")
    ap.add_argument("--block-pad", dest="block_pad", type=int, default=12, help="[label]标签到信箱块上下留边")
    a = ap.parse_args()

    # 按样式补色彩默认（None=未显式指定）
    if a.bar_color is None:
        a.bar_color = "FFFFFF" if a.style == "label" else "202020"
    if a.text_color is None:
        a.text_color = "000000" if a.style == "label" else "FFFFFF"

    src = Path(a.input)
    if not src.exists():
        raise SystemExit(f"输入不存在: {src}")
    out = ensure_parent(a.output)
    w, h, dur, has_audio = probe(src)
    if w == 0 or dur <= 0:
        raise SystemExit(f"读不到视频: {src}")

    font_path = _font_path(a.font)
    if a.style == "label":
        block_top = round(a.block_top_frac * h)
        if a.block_h_frac is not None:
            block_h = round(a.block_h_frac * h)
        else:
            block_h = detect_top_block(src, h)
            if block_h is None:
                block_h = round(0.128 * h)   # 没探到信箱块时的兜底（竖版常见值）
                print(f"  ⚠ 未探到顶部黑边，按默认块高 {block_h}px（约12.8%H）")
            else:
                print(f"  顶部信箱块自动探测：{block_h}px（约{block_h/h*100:.1f}%H）")
        overlay, fs, lines = render_label_overlay(w, h, a.text, font_path, a, block_top, block_h)
    else:
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
