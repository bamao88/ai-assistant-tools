#!/usr/bin/env python3
"""Generate 张和 video covers: black block + yellow title over a 9:16 base frame.

Base image comes from the covers/ pool (round-robin) or an explicit --base-image.
The black block's BOTTOM edge is fixed (block.bottom_frac * H); the block grows
UPWARD with the number of title lines. One font size, sized so the widest line
fills the side-margin width. All geometry is expressed as fractions of the base
frame so any 9:16 size renders consistently.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFont

ASSET_DIR = Path(__file__).resolve().parent
KIT_PATH = ASSET_DIR / "cover-kit.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def load_kit() -> Dict[str, Any]:
    with KIT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    return ImageColor.getrgb(value)


# ---------- base image selection ----------

def list_pool(kit: Dict[str, Any]) -> List[Path]:
    pool_dir = ASSET_DIR / kit.get("covers_dir", "covers")
    files = [p for p in sorted(pool_dir.iterdir()) if p.suffix.lower() in IMAGE_EXTS]
    if not files:
        raise FileNotFoundError(f"No base images in pool: {pool_dir}")
    return files


def pick_base(kit: Dict[str, Any], base_image: Optional[str], base_name: Optional[str]) -> Path:
    if base_image:
        p = Path(base_image).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"--base-image not found: {p}")
        return p
    pool = list_pool(kit)
    if base_name:
        for p in pool:
            if p.name == base_name or p.stem == base_name:
                return p
        raise FileNotFoundError(f"--base '{base_name}' not in pool")
    # round-robin
    state_file = ASSET_DIR / kit.get("rotation", {}).get("state_file", ".rotation_state.json")
    idx = 0
    if state_file.exists():
        try:
            idx = int(json.loads(state_file.read_text()).get("index", 0))
        except Exception:
            idx = 0
    chosen = pool[idx % len(pool)]
    state_file.write_text(json.dumps({"index": (idx + 1) % len(pool)}))
    return chosen


# ---------- title layout ----------

def split_lines(title: str, wrap_units: int) -> List[str]:
    """Explicit breaks on newline / literal \\n / | win. Else wrap by display units."""
    raw = title.replace("\\n", "\n")
    if "\n" in raw or "|" in raw:
        parts = re.split(r"[\n|]+", raw)
        return [p.strip() for p in parts if p.strip()]
    if wrap_units and display_units(raw) > wrap_units:
        return wrap_by_units(raw, wrap_units)
    return [raw.strip()]


def is_cjk(ch: str) -> bool:
    return 0x3400 <= ord(ch) <= 0x9FFF or 0xF900 <= ord(ch) <= 0xFAFF


def display_units(text: str) -> int:
    """CJK = 1 unit; a contiguous ASCII run = 1 unit (keeps English words intact)."""
    units, i = 0, 0
    while i < len(text):
        if is_cjk(text[i]):
            units += 1
            i += 1
        elif text[i].isascii() and not text[i].isspace():
            while i < len(text) and text[i].isascii() and not text[i].isspace():
                i += 1
            units += 1
        else:
            i += 1
    return units


def wrap_by_units(text: str, limit: int) -> List[str]:
    lines: List[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if display_units(cur) >= limit and is_cjk(ch):
            lines.append(cur.strip())
            cur = ""
    if cur.strip():
        lines.append(cur.strip())
    return lines


def line_width(font: ImageFont.FreeTypeFont, text: str) -> int:
    probe = ImageDraw.Draw(Image.new("L", (4, 4)))
    box = probe.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def fit_font(font_path: Path, lines: List[str], box_w: int, min_size: int, max_size: int) -> Tuple[ImageFont.FreeTypeFont, int]:
    """Largest size in [min, max] where every line fits box_w."""
    best = ImageFont.truetype(str(font_path), min_size)
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(str(font_path), size)
        if all(line_width(font, ln) <= box_w for ln in lines):
            return font, size
        best = font
    return best, min_size


def resolve_font(kit: Dict[str, Any]) -> Path:
    p = ASSET_DIR / kit["text"]["font_file"]
    if not p.exists():
        raise FileNotFoundError(f"Font not found: {p}")
    return p


# ---------- render ----------

def render(kit: Dict[str, Any], base_path: Path, lines: List[str], output: Path,
           wrote_crop: bool = True) -> Dict[str, Any]:
    block = kit["block"]
    tcfg = kit["text"]

    img = Image.open(base_path).convert("RGBA")
    W, H = img.size

    side_margin = round(tcfg["side_margin_frac"] * W)
    text_area_w = W - 2 * side_margin
    max_font = round(tcfg["max_font_frac"] * H)
    min_font = round(tcfg["min_font_frac"] * H)

    font_path = resolve_font(kit)
    font, font_size = fit_font(font_path, lines, text_area_w, min_font, max_font)

    line_h = font_size * tcfg["line_spacing"]
    n = len(lines)
    top_pad = tcfg["top_pad_frac"] * H
    bottom_pad = tcfg["bottom_pad_frac"] * H

    block_bottom_y = block["bottom_frac"] * H
    text_total_h = n * line_h
    block_top_y = block_bottom_y - bottom_pad - text_total_h - top_pad

    # black block
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    alpha = int(round(block.get("opacity", 1.0) * 255))
    od.rectangle([0, round(block_top_y), W, round(block_bottom_y)],
                 fill=(*hex_to_rgb(block["color"]), alpha))
    img.alpha_composite(overlay)

    # yellow lines, centered, each centered within its line slot
    draw = ImageDraw.Draw(img)
    color = (*hex_to_rgb(tcfg["color"]), 255)
    cx = W / 2
    for i, ln in enumerate(lines):
        cy = block_top_y + top_pad + i * line_h + line_h / 2
        draw.text((cx, cy), ln, font=font, fill=color, anchor="mm")

    output.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output)

    result = {
        "base_image": str(base_path),
        "size": [W, H],
        "lines": lines,
        "font_size": font_size,
        "block_top_y": round(block_top_y),
        "block_bottom_y": round(block_bottom_y),
        "output_9_16": str(output),
    }

    # optional 3:4 center crop (keep full width, crop height around block bottom)
    if wrote_crop and kit.get("output", {}).get("crop_3_4"):
        crop_h = round(W * 4 / 3)
        if crop_h <= H:
            # anchor so the block bottom sits comfortably inside the crop
            bottom = min(H, round(block_bottom_y + (H - block_bottom_y) * 0.35))
            top = bottom - crop_h
            if top < 0:
                top, bottom = 0, crop_h
            crop = img.convert("RGB").crop((0, top, W, bottom))
            crop_path = output.with_name(output.stem + "_3x4" + output.suffix)
            crop.save(crop_path)
            result["output_3_4"] = str(crop_path)
            result["crop_box"] = [0, top, W, bottom]
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate 张和 video cover.")
    parser.add_argument("--title", required=True,
                        help="标题；用换行 / \\n / | 分行，不分则按 --wrap 自动折行")
    parser.add_argument("--base-image", help="指定底图绝对路径（覆盖轮换）")
    parser.add_argument("--base", help="从池中按文件名选底图")
    parser.add_argument("--wrap", type=int, default=0, help="单行未手动分行时的每行字数上限")
    parser.add_argument("--output", help="输出 PNG 路径")
    parser.add_argument("--no-crop", action="store_true", help="不额外输出 3:4 裁切")
    args = parser.parse_args(argv)

    try:
        kit = load_kit()
        base = pick_base(kit, args.base_image, args.base)
        lines = split_lines(args.title, args.wrap)
        if not lines:
            raise ValueError("标题为空")
        if args.output:
            output = Path(args.output).expanduser()
        else:
            safe = re.sub(r"[^\w一-鿿-]+", "_", lines[0])[:40].strip("_")
            output = ASSET_DIR / "generated" / f"cover-{safe}.png"
        result = render(kit, base, lines, output, wrote_crop=not args.no_crop)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
