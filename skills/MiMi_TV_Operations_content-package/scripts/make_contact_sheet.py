#!/usr/bin/env python3
"""Create large and mobile-size contact sheets for MiMi TV social covers."""

from __future__ import annotations

import argparse
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 MiMi TV 社交封面系列审查图。")
    parser.add_argument("images", nargs="+", help="封面图片路径。")
    parser.add_argument("--output", required=True, help="输出 JPG 或 PNG。")
    parser.add_argument("--columns", type=int, default=0, help="列数；默认自动计算。")
    parser.add_argument("--thumb-width", type=int, default=240, help="大缩略图宽度。")
    parser.add_argument("--mini-width", type=int, default=120, help="手机缩略图模拟宽度。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("生成 contact sheet 需要 Pillow；不要自动安装，改为逐张检查。") from exc

    entries = []
    for raw in args.images:
        path = Path(raw).expanduser()
        if not path.exists():
            raise SystemExit(f"图片不存在：{path}")
        entries.append((path, Image.open(path).convert("RGB")))

    columns = args.columns or min(4, max(1, math.ceil(math.sqrt(len(entries)))))
    rows = math.ceil(len(entries) / columns)
    thumb_height = round(args.thumb_width * 4 / 3)
    mini_height = round(args.mini_width * 4 / 3)
    gap = 24
    label_height = 28
    cell_width = max(args.thumb_width, args.mini_width)
    cell_height = thumb_height + mini_height + label_height + gap
    canvas = Image.new(
        "RGB",
        (gap + columns * (cell_width + gap), gap + rows * (cell_height + gap)),
        "#EEEAE2",
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    for index, (path, image) in enumerate(entries):
        row, column = divmod(index, columns)
        x = gap + column * (cell_width + gap)
        y = gap + row * (cell_height + gap)
        large = image.resize((args.thumb_width, thumb_height), Image.Resampling.LANCZOS)
        mini = image.resize((args.mini_width, mini_height), Image.Resampling.LANCZOS)
        canvas.paste(large, (x, y))
        canvas.paste(mini, (x, y + thumb_height + 10))
        draw.text((x, y + thumb_height + mini_height + 18), path.stem[:38], fill="#222222", font=font)

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() in {".jpg", ".jpeg"}:
        canvas.save(output, quality=92)
    else:
        canvas.save(output)
    print(output)


if __name__ == "__main__":
    main()

