#!/usr/bin/env python3
"""Generate AI PM assistant WeChat cover images from the local cover kit."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFont


ASSET_DIR = Path(__file__).resolve().parent
KIT_PATH = ASSET_DIR / "cover-kit.json"

TITLE_SEGMENT_LIMIT = 10
CHINESE_KEYWORD_LIMIT = 3


def load_kit() -> Dict[str, Any]:
    with KIT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def is_cjk(ch: str) -> bool:
    code = ord(ch)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x20000 <= code <= 0x2A6DF
        or 0x2A700 <= code <= 0x2B73F
        or 0x2B740 <= code <= 0x2B81F
        or 0x2B820 <= code <= 0x2CEAF
    )


def display_units(text: str) -> int:
    """Count Chinese-equivalent units for rule enforcement.

    CJK characters count as 1. A contiguous ASCII word counts as 2 so English
    product names stay intact without consuming their raw letter count.
    """
    units = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if is_cjk(ch):
            units += 1
            i += 1
        elif ch.isascii() and ch.isalnum():
            while i < len(text) and text[i].isascii() and (
                text[i].isalnum() or text[i] in ".+#-"
            ):
                i += 1
            units += 2
        else:
            i += 1
    return units


def tokenize_display(text: str) -> List[str]:
    tokens: List[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isascii() and (ch.isalnum() or ch in ".+#-"):
            start = i
            while i < len(text) and text[i].isascii() and (
                text[i].isalnum() or text[i] in ".+#-"
            ):
                i += 1
            tokens.append(text[start:i])
        else:
            tokens.append(ch)
            i += 1
    return tokens


def trim_to_units(text: str, limit: int) -> str:
    out: List[str] = []
    used = 0
    for token in tokenize_display(text.strip()):
        token_units = display_units(token)
        if token.isspace() or token in "：:，,。.!！?？-—_|/":
            if out and out[-1] != " ":
                out.append(" ")
            continue
        if used + token_units > limit:
            break
        out.append(token)
        used += token_units
    return re.sub(r"\s+", " ", "".join(out)).strip()


def compact_title_piece(text: str) -> str:
    replacements = [
        ("到底在干什么", "在干嘛"),
        ("到底是干什么的", "干什么"),
        ("到底有什么用", "有啥用"),
        ("那一层", "那层"),
        ("这一层", "这层"),
        ("外面的一层", "外面那层"),
        ("里面的一层", "里面那层"),
        ("到底", ""),
        ("究竟", ""),
        ("到底是", "是"),
    ]
    out = text.strip(" \t\r\n:：,，。.!！?？-—_|")
    for old, new in replacements:
        out = out.replace(old, new)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def split_title(title: str) -> Tuple[str, str]:
    clean = compact_title_piece(title)
    parts = [p for p in re.split(r"[：:|｜\n]+", clean, maxsplit=1) if p.strip()]
    if len(parts) == 2:
        primary, secondary = parts[0], parts[1]
    else:
        dash_parts = [p for p in re.split(r"\s+[—-]\s+|[—]", clean, maxsplit=1) if p.strip()]
        if len(dash_parts) == 2:
            primary, secondary = dash_parts[0], dash_parts[1]
        else:
            primary = trim_to_units(clean, TITLE_SEGMENT_LIMIT)
            remainder = clean[len(primary) :].strip(" ，,。.!！?？-—")
            secondary = remainder or clean

    primary = compact_title_piece(primary)
    secondary = compact_title_piece(secondary)
    if display_units(primary) > TITLE_SEGMENT_LIMIT:
        primary = trim_to_units(primary, TITLE_SEGMENT_LIMIT)
    if display_units(secondary) > TITLE_SEGMENT_LIMIT:
        compressed = compact_title_piece(secondary)
        secondary = trim_to_units(compressed, TITLE_SEGMENT_LIMIT)
    return primary, secondary


def first_chinese_keyword(text: str, exclude: Iterable[str]) -> str:
    exclude_set = set(exclude)
    domain_candidates = [
        "模型",
        "智能体",
        "提示词",
        "工作流",
        "框架",
        "工具",
        "架构",
        "评测",
        "产品",
        "设计",
        "运营",
        "增长",
        "内容",
        "自动化",
    ]
    for candidate in domain_candidates:
        if candidate in text and candidate not in exclude_set:
            return candidate[:CHINESE_KEYWORD_LIMIT]

    stripped = re.sub(r"[A-Za-z][A-Za-z0-9.+#-]*", "", text)
    for phrase in ["是什么", "为什么", "怎么做", "干什么", "在干嘛", "那层", "这一层", "外面", "里面", "到底"]:
        stripped = stripped.replace(phrase, "")
    chars = [ch for ch in stripped if is_cjk(ch)]
    return "".join(chars[:CHINESE_KEYWORD_LIMIT]) or "AI"


def normalize_keyword(value: str) -> str:
    value = value.strip(" \t\r\n:：,，。.!！?？-—_|/")
    english = re.fullmatch(r"[A-Za-z][A-Za-z0-9.+#-]*", value)
    if english:
        return value
    chars = [ch for ch in value if is_cjk(ch)]
    if chars:
        return "".join(chars[:CHINESE_KEYWORD_LIMIT])
    return value[:12]


def extract_keywords(title: str) -> Tuple[str, str]:
    english_words = re.findall(r"[A-Za-z][A-Za-z0-9.+#-]*", title)
    stop_words = {"AI", "PM", "AIPM", "the", "and", "for", "with"}
    primary = ""
    for word in english_words:
        if word.upper() not in stop_words and word.lower() not in stop_words:
            primary = word
            break
    if not primary and english_words:
        primary = english_words[0]

    secondary = first_chinese_keyword(title, [primary])
    if not primary:
        primary = secondary
        secondary = first_chinese_keyword(title.replace(secondary, "", 1), [primary])
    return normalize_keyword(primary), normalize_keyword(secondary)


def format_date_label(raw: Optional[str]) -> str:
    if not raw:
        today = dt.date.today()
        return f"{today.month}月{today.day}日"
    value = raw.strip()
    iso = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", value)
    if iso:
        return f"{int(iso.group(2))}月{int(iso.group(3))}日"
    zh = re.fullmatch(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]", value)
    if zh:
        return f"{int(zh.group(1))}月{int(zh.group(2))}日"
    raise ValueError(f"Unsupported date format: {raw}. Use YYYY-MM-DD or M月D日.")


def resolve_font(slot: Dict[str, Any]) -> Path:
    candidates = [ASSET_DIR / slot["font_file"]]
    fallback = slot.get("font_fallback_file")
    if fallback:
        candidates.append(ASSET_DIR / fallback)
    candidates.extend(
        [
            ASSET_DIR / "fonts/HYWenHei-85W.otf",
            ASSET_DIR / "fonts/AlibabaPuHuiTi-3-85-Bold.ttf",
            ASSET_DIR / "fonts/SourceHanSansSC-Heavy.otf",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No usable font file found for slot {slot['id']}")


def text_bbox(font: ImageFont.FreeTypeFont, text: str) -> Tuple[int, int, int, int]:
    probe = Image.new("L", (4, 4), 0)
    draw = ImageDraw.Draw(probe)
    return draw.textbbox((0, 0), text, font=font)


def fit_font(
    font_path: Path,
    text: str,
    box_w: int,
    box_h: int,
    min_size: float,
    max_size: float,
) -> Tuple[ImageFont.FreeTypeFont, int, Tuple[int, int, int, int]]:
    max_i = int(math.floor(max_size))
    min_i = int(math.floor(min_size))
    best_font = ImageFont.truetype(str(font_path), min_i)
    best_bbox = text_bbox(best_font, text)
    for size in range(max_i, min_i - 1, -1):
        font = ImageFont.truetype(str(font_path), size)
        bbox = text_bbox(font, text)
        if bbox[2] - bbox[0] <= box_w and bbox[3] - bbox[1] <= box_h:
            return font, size, bbox
        best_font, best_bbox = font, bbox
    return best_font, min_i, best_bbox


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    return ImageColor.getrgb(value)


def build_gradient(size: Tuple[int, int], fill: Dict[str, Any]) -> Image.Image:
    width, height = size
    start = hex_to_rgb(fill["from"])
    end = hex_to_rgb(fill["to"])
    gradient = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = gradient.load()
    horizontal = fill.get("direction") != "vertical"
    steps = max(width - 1 if horizontal else height - 1, 1)
    for y in range(height):
        for x in range(width):
            pos = (x if horizontal else y) / steps
            color = tuple(round(start[i] + (end[i] - start[i]) * pos) for i in range(3))
            pixels[x, y] = (*color, 255)
    return gradient


def rotated_origin_bbox_offset(width: int, height: int, visual_degrees: float) -> Tuple[float, float]:
    """Return the bbox min offset for a rect rotated around its top-left point."""
    radians = math.radians(visual_degrees)
    cos_v = math.cos(radians)
    sin_v = math.sin(radians)
    corners = [
        (0, 0),
        (width * cos_v, width * sin_v),
        (-height * sin_v, height * cos_v),
        (width * cos_v - height * sin_v, width * sin_v + height * cos_v),
    ]
    min_x = min(x for x, _ in corners)
    min_y = min(y for _, y in corners)
    return min_x, min_y


def slot_inner_box(slot: Dict[str, Any]) -> Tuple[int, int, int, int]:
    padding = slot.get("padding", {})
    left = int(round(padding.get("left", 0)))
    top = int(round(padding.get("top", 0)))
    right = int(round(padding.get("right", 0)))
    bottom = int(round(padding.get("bottom", 0)))
    width = int(round(slot["width"])) - left - right
    height = int(round(slot["height"])) - top - bottom
    return left, top, max(width, 1), max(height, 1)


def draw_text_slot(
    base: Image.Image,
    slot: Dict[str, Any],
    text: str,
) -> Dict[str, Any]:
    slot_w = int(round(slot["width"]))
    slot_h = int(round(slot["height"]))
    layer = Image.new("RGBA", (slot_w, slot_h), (0, 0, 0, 0))
    mask = Image.new("L", (slot_w, slot_h), 0)
    mask_draw = ImageDraw.Draw(mask)

    inner_x, inner_y, inner_w, inner_h = slot_inner_box(slot)
    font_path = resolve_font(slot)
    font, font_size, bbox = fit_font(
        font_path=font_path,
        text=text,
        box_w=inner_w,
        box_h=inner_h,
        min_size=slot["min_font_size"],
        max_size=slot["max_font_size"],
    )
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    align = slot.get("align", "left")
    if align == "right":
        text_x = inner_x + inner_w - text_w - bbox[0]
    elif align == "center":
        text_x = inner_x + (inner_w - text_w) / 2 - bbox[0]
    else:
        text_x = inner_x - bbox[0]

    vertical = slot.get("vertical_align", "top")
    if vertical == "middle":
        text_y = inner_y + (inner_h - text_h) / 2 - bbox[1]
    elif vertical == "bottom":
        text_y = inner_y + inner_h - text_h - bbox[1]
    else:
        text_y = inner_y - bbox[1]

    mask_draw.text((text_x, text_y), text, font=font, fill=255)

    fill = slot.get("fill", {"type": "solid", "color": "#000000"})
    if fill.get("type") == "linear-gradient":
        colored = build_gradient((slot_w, slot_h), fill)
        layer.alpha_composite(colored)
        layer.putalpha(mask)
    else:
        color = (*hex_to_rgb(fill.get("color", "#000000")), 255)
        color_layer = Image.new("RGBA", (slot_w, slot_h), color)
        color_layer.putalpha(mask)
        layer.alpha_composite(color_layer)

    x = float(slot["x"])
    y = float(slot["y"])
    rotation = float(slot.get("rotation", 0) or 0)
    if rotation:
        # Kit uses CSS/SVG visual degrees: positive is clockwise. Pillow's
        # positive angle is counter-clockwise, so invert it.
        rotated = layer.rotate(-rotation, resample=Image.Resampling.BICUBIC, expand=True)
        offset_x, offset_y = rotated_origin_bbox_offset(slot_w, slot_h, rotation)
        paste_x = int(round(x + offset_x))
        paste_y = int(round(y + offset_y))
        base.alpha_composite(rotated, (paste_x, paste_y))
    else:
        base.alpha_composite(layer, (int(round(x)), int(round(y))))

    return {
        "slot": slot["id"],
        "text": text,
        "font_file": str(font_path.relative_to(ASSET_DIR)),
        "font_size": font_size,
        "text_bbox": [bbox[0], bbox[1], bbox[2], bbox[3]],
    }


def render_cover(kind: str, fields: Dict[str, str], output: Path) -> Dict[str, Any]:
    kit = load_kit()
    cover = kit["covers"][kind]
    base_path = ASSET_DIR / cover["base_image"]
    if not base_path.exists():
        raise FileNotFoundError(f"Base image not found: {base_path}")

    image = Image.open(base_path).convert("RGBA")
    rendered_slots = []
    for slot in cover["text_slots"]:
        source = slot["source"]
        text = fields.get(source, "")
        if not text:
            continue
        rendered_slots.append(draw_text_slot(image, slot, text))

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output)
    return {
        "cover": kind,
        "output": str(output),
        "fields": fields,
        "rendered_slots": rendered_slots,
    }


def article_fields(args: argparse.Namespace) -> Dict[str, str]:
    if args.title_primary or args.title_secondary:
        title_primary = args.title_primary or ""
        title_secondary = args.title_secondary or ""
        if not title_secondary and args.title:
            _, title_secondary = split_title(args.title)
    else:
        if not args.title:
            raise ValueError("article cover requires --title or explicit title segments")
        title_primary, title_secondary = split_title(args.title)

    if args.keyword_top or args.keyword_bottom:
        keyword_top = args.keyword_top or ""
        keyword_bottom = args.keyword_bottom or ""
        if args.title and (not keyword_top or not keyword_bottom):
            inferred_top, inferred_bottom = extract_keywords(args.title)
            keyword_top = keyword_top or inferred_top
            keyword_bottom = keyword_bottom or inferred_bottom
    else:
        if not args.title:
            raise ValueError("article cover requires --title or explicit keywords")
        keyword_top, keyword_bottom = extract_keywords(args.title)

    return {
        "title_primary": title_primary,
        "title_secondary": title_secondary,
        "keyword_top": normalize_keyword(keyword_top),
        "keyword_bottom": normalize_keyword(keyword_bottom),
    }


def daily_fields(args: argparse.Namespace) -> Dict[str, str]:
    return {"date": format_date_label(args.date)}


def default_output(kind: str, fields: Dict[str, str]) -> Path:
    if kind == "daily":
        stem = fields["date"]
    else:
        stem = f"{fields['title_primary']}-{fields['title_secondary']}"
    safe = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", stem).strip("_")[:80]
    return ASSET_DIR / "generated" / f"{kind}-{safe}.png"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate AI PM assistant WeChat cover images.",
    )
    subparsers = parser.add_subparsers(dest="kind", required=True)

    article = subparsers.add_parser("article", help="Generate regular article cover")
    article.add_argument("--title", help="Original article title")
    article.add_argument("--title-primary", help="Override top title segment")
    article.add_argument("--title-secondary", help="Override bottom title segment")
    article.add_argument("--keyword-top", help="Override top square keyword")
    article.add_argument("--keyword-bottom", help="Override bottom square keyword")
    article.add_argument("--output", help="Output PNG path")

    daily = subparsers.add_parser("daily", help="Generate daily cover")
    daily.add_argument("--date", help="Date as YYYY-MM-DD or M月D日. Defaults to today.")
    daily.add_argument("--output", help="Output PNG path")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.kind == "article":
            fields = article_fields(args)
        elif args.kind == "daily":
            fields = daily_fields(args)
        else:
            raise ValueError(f"Unsupported cover kind: {args.kind}")
        output = Path(args.output).expanduser() if args.output else default_output(args.kind, fields)
        result = render_cover(args.kind, fields, output)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
