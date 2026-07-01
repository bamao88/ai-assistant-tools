#!/usr/bin/env python3
"""生成张和口播视频封面(evc 宋体渐变风格)：3:4 人像帧 + 底部黑色渐变 + 思源宋体白字。

全部风格参数读 cover-kit-evc.json，脚本零硬编码。张和唯一认可的口播切片封面样式
(标杆 ZHC20260613_evc*)。SCOPE / 硬边界见 kit 的 usage.decision_gate。

单张:  python3 generate_evc_cover.py --title "第一行|第二行" [--base frameXX|--base-image PATH] [--output PATH]
批量:  python3 generate_evc_cover.py --batch manifest.json [--overview PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageColor, ImageDraw, ImageFont

ASSET_DIR = Path(__file__).resolve().parent
KIT_PATH = ASSET_DIR / "cover-kit-evc.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


# ---------- kit / paths ----------

def load_kit() -> Dict[str, Any]:
    with KIT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def shared_dir(kit: Dict[str, Any]) -> Path:
    return Path(kit["shared_assets_dir"])


def resolve_font(kit: Dict[str, Any]) -> Path:
    p = ASSET_DIR / kit["text"]["font_file"]
    if not p.exists():
        raise FileNotFoundError(f"Font not found: {p}")
    return p


def gradient_path(kit: Dict[str, Any]) -> Path:
    p = shared_dir(kit) / kit["gradient"]["file"]
    if not p.exists():
        raise FileNotFoundError(f"Gradient not found: {p}")
    return p


def hex_to_rgb(value: str):
    return ImageColor.getrgb(value)


# ---------- base image selection ----------

def list_pool(kit: Dict[str, Any]) -> List[Path]:
    pool_dir = shared_dir(kit) / kit.get("covers_dir", "covers")
    exclude = set(kit.get("rotation", {}).get("exclude", []))
    files = [p for p in sorted(pool_dir.iterdir())
             if p.suffix.lower() in IMAGE_EXTS and p.name not in exclude]
    if not files:
        raise FileNotFoundError(f"No usable base images in pool: {pool_dir}")
    return files


def pick_base(kit: Dict[str, Any], base_image: Optional[str] = None,
              base_name: Optional[str] = None, seq_index: Optional[int] = None) -> Path:
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
    if seq_index is not None:
        # 批量：按列表顺序取模，纯确定性，不碰游标 → 相邻条目必然不撞底图，可重跑一致
        return pool[seq_index % len(pool)]
    # 单张 round-robin：读写独立游标
    state_file = ASSET_DIR / kit.get("rotation", {}).get("state_file", ".rotation_state_evc.json")
    idx = 0
    if state_file.exists():
        try:
            idx = int(json.loads(state_file.read_text()).get("index", 0))
        except Exception:
            idx = 0
    chosen = pool[idx % len(pool)]
    state_file.write_text(json.dumps({"index": (idx + 1) % len(pool)}))
    return chosen


# ---------- render pipeline (kit-driven; mirrors approved prototype) ----------

def open_cover_frame(kit: Dict[str, Any], path: Path) -> Image.Image:
    """3:4 裁切 + 人物上移 lift(占裁切高比例；可 per-frame 覆盖)。"""
    W, H = kit["canvas"]["width"], kit["canvas"]["height"]
    bc = kit["base_crop"]
    im = Image.open(path).convert("RGB")
    sw, sh = im.size
    ch = min(int(round(sw * H / W)), sh)
    lift = bc.get("lift_overrides", {}).get(path.name, bc["lift_default"])
    max_lift = int(round(ch * lift))
    crop_top = max(0, min(max_lift, sh - ch))
    im = im.crop((0, crop_top, sw, crop_top + ch))
    return im.resize((W, H), Image.LANCZOS)


def apply_gradient(kit: Dict[str, Any], im: Image.Image) -> Image.Image:
    """白顶黑底素材 → alpha=255-L 叠加。"""
    W, H = kit["canvas"]["width"], kit["canvas"]["height"]
    g = Image.open(gradient_path(kit)).convert("L").resize((W, H), Image.LANCZOS)
    alpha = g.point(lambda v: 255 - v)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay.putalpha(alpha)
    im = im.convert("RGBA")
    im.alpha_composite(overlay)
    return im.convert("RGB")


def fit_font(kit: Dict[str, Any], draw: ImageDraw.ImageDraw, lines: List[str]):
    """字号由最长行像素宽驱动：最大的、最长行 stroke 后宽 ≤ max_line_width_px 的字号。"""
    tc = kit["text"]
    fp = str(resolve_font(kit))
    sw = tc["stroke_width"]
    for fs in range(tc["max_font_px"], tc["min_font_px"] - 1, -2):
        f = ImageFont.truetype(fp, fs)
        widths = [draw.textbbox((0, 0), ln, font=f, stroke_width=sw)[2] for ln in lines]
        if max(widths) <= tc["max_line_width_px"]:
            return f, fs
    return ImageFont.truetype(fp, tc["min_font_px"]), tc["min_font_px"]


def draw_title(kit: Dict[str, Any], im: Image.Image, lines: List[str]) -> Image.Image:
    W, H = kit["canvas"]["width"], kit["canvas"]["height"]
    tc = kit["text"]
    d = ImageDraw.Draw(im)
    font, fs = fit_font(kit, d, lines)
    sw = tc["stroke_width"]
    line_gap = max(tc["line_gap_min_px"], int(fs * tc["line_gap_frac"]))
    line_h = max(d.textbbox((0, 0), ln, font=font, stroke_width=sw)[3] for ln in lines)
    total_h = line_h * len(lines) + line_gap * (len(lines) - 1)
    fill = hex_to_rgb(tc["color"])
    stroke = hex_to_rgb(tc["stroke_color"])
    y = int(H * tc["center_y_frac"] - total_h / 2)
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=font, stroke_width=sw)
        x = (W - (bb[2] - bb[0])) // 2 - bb[0]
        d.text((x, y), ln, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke)
        y += line_h + line_gap
    return im


def split_lines(kit: Dict[str, Any], title: str) -> List[str]:
    raw = title.replace("\\n", "\n")
    parts = re.split(r"[\n|]+", raw)
    return [p.strip() for p in parts if p.strip()]


def render_one(kit: Dict[str, Any], base_path: Path, lines: List[str], output: Path) -> Dict[str, Any]:
    im = open_cover_frame(kit, base_path)
    im = apply_gradient(kit, im)
    im = draw_title(kit, im, lines)
    output.parent.mkdir(parents=True, exist_ok=True)
    im.save(output)
    return {"base_image": base_path.name, "lines": lines,
            "size": [kit["canvas"]["width"], kit["canvas"]["height"]], "output": str(output)}


# ---------- batch ----------

def build_overview(kit: Dict[str, Any], rows: List[Dict[str, Any]], overview_path: Path) -> None:
    W, H = kit["canvas"]["width"], kit["canvas"]["height"]
    tw = 200
    th = int(tw * H / W)
    lab = 34
    cols = 7
    n = len(rows)
    grid_rows = (n + cols - 1) // cols
    montage = Image.new("RGB", (tw * cols, (th + lab) * grid_rows), "white")
    d = ImageDraw.Draw(montage)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 16)
    except OSError:
        f = ImageFont.load_default()
    for i, r in enumerate(rows):
        im = Image.open(r["output"]).resize((tw, th))
        x = (i % cols) * tw
        y = (i // cols) * (th + lab)
        montage.paste(im, (x, y))
        d.text((x + 4, y + th + 6), f"#{i+1} {r.get('content_id','')} {r['base_image'].split('.')[0]}",
               fill=(0, 0, 0), font=f)
    overview_path.parent.mkdir(parents=True, exist_ok=True)
    montage.save(overview_path)


def run_batch(kit: Dict[str, Any], manifest_path: Path, overview_path: Optional[Path]) -> Dict[str, Any]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    items = {it["content_id"]: it for it in manifest["items"]}
    order = manifest.get("publish_order") or [it["content_id"] for it in manifest["items"]]

    rows: List[Dict[str, Any]] = []
    for seq, cid in enumerate(order):
        it = items[cid]
        base = pick_base(kit, seq_index=seq)
        lines = split_lines(kit, it["title"])
        res = render_one(kit, base, lines, Path(it["output"]).expanduser())
        res["content_id"] = cid
        rows.append(res)

    # 相邻不撞自检
    collisions = [(rows[i]["content_id"], rows[i + 1]["content_id"])
                  for i in range(len(rows) - 1)
                  if rows[i]["base_image"] == rows[i + 1]["base_image"]]

    if overview_path is None:
        overview_path = ASSET_DIR / "generated" / "overview.png"
    build_overview(kit, rows, overview_path)

    return {
        "count": len(rows),
        "mapping": [{"content_id": r["content_id"], "base": r["base_image"], "output": r["output"]} for r in rows],
        "adjacent_collisions": collisions,
        "overview": str(overview_path),
    }


# ---------- cli ----------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="张和口播视频封面(evc 宋体渐变)")
    ap.add_argument("--title", help="单张：2 行标题，用 | 或 \\n 分行")
    ap.add_argument("--base", help="从 covers/ 池按文件名选底图(不推进游标)")
    ap.add_argument("--base-image", help="外部绝对路径底图(覆盖轮换)")
    ap.add_argument("--output", help="单张输出 PNG 路径；省略写 generated/")
    ap.add_argument("--batch", help="批量模式 manifest.json")
    ap.add_argument("--overview", help="批量对比总览图输出路径")
    args = ap.parse_args(argv)

    try:
        kit = load_kit()
        if args.batch:
            result = run_batch(kit, Path(args.batch), Path(args.overview) if args.overview else None)
        else:
            if not args.title:
                raise ValueError("单张模式需要 --title（或用 --batch）")
            lines = split_lines(kit, args.title)
            if not lines:
                raise ValueError("标题为空")
            base = pick_base(kit, args.base_image, args.base)
            if args.output:
                output = Path(args.output).expanduser()
            else:
                safe = re.sub(r"[^\w一-鿿]+", "_", lines[0])[:40].strip("_")
                output = ASSET_DIR / "generated" / f"cover-{safe}.png"
            result = render_one(kit, base, lines, output)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
