#!/usr/bin/env python3
"""给被动节目成片叠加「给猫看」的提示字，并把结果写回 item.json。

文字是写给主人的提醒（「快叫猫猫过来看！」），让主人把猫叫到屏幕前；不是字幕，也不是游戏宣传。
画面顶部居中，黄色粗体加深色描边，轻轻上下跳动，淡入淡出；只在开篇出现一次。
避开左右上角的作者标识。音频原样复制；未叠字的原片保存在 work/video-no-overlay.mp4，
重复运行始终从它出发，不会叠两层。只写本地 item 目录，不上传、不发布。

每条 item 先写 video.overlay_phrases（一句，不超过12个字），再运行：
  python3 add_overlay.py content/items/item-0xx/item.json [更多 item.json]
  python3 add_overlay.py --check item.json      # 只核对哈希与记录，不改文件
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = Path("/System/Library/Fonts/STHeiti Medium.ttc")
FONT_SIZE = 76
FILL = (255, 217, 61, 255)       # 暖黄
STROKE = (43, 30, 20, 255)       # 深棕描边，白底、黑底都清楚
STROKE_WIDTH = 7
SHADOW = (0, 0, 0, 110)
TOP_MARGIN = 44                  # 文字块顶边到画面顶边
BOUNCE_PX = 7                    # 上下跳动幅度
SHOW_LENGTH = 3.4                # 每次出现多久
FIRST_START = 1.0
LATER_STARTS: tuple[float, ...] = ()  # 只在开篇出现；如需后续出现，在此填成片时长比例
END_TAIL_GAP = 0.5
FADE = 0.4
PHRASE_COUNT = 1
PHRASE_MAX_CHARS = 12
CLEAN_NAME = "work/video-no-overlay.mp4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def has_audio(path: Path) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout
    return bool(out.strip())


def render_text(text: str, target: Path) -> None:
    font = ImageFont.truetype(str(FONT), FONT_SIZE)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=font, stroke_width=STROKE_WIDTH)
    pad = 14
    width, height = int(right - left) + 2 * pad, int(bottom - top) + 2 * pad
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    origin = (pad - left, pad - top)
    draw.text((origin[0] + 4, origin[1] + 5), text, font=font, fill=SHADOW,
              stroke_width=STROKE_WIDTH, stroke_fill=SHADOW)
    draw.text(origin, text, font=font, fill=FILL, stroke_width=STROKE_WIDTH, stroke_fill=STROKE)
    image.save(target)


def windows(duration: float) -> list[tuple[float, float]]:
    starts = [FIRST_START] + [round(duration * ratio, 1) for ratio in LATER_STARTS]
    out = []
    for start in starts:
        end = round(min(start + SHOW_LENGTH, duration - END_TAIL_GAP), 2)
        out.append((start, end))
    return out


def fade_chain(index: int, start: float, end: float) -> str:
    return (f"[{index}:v]format=rgba,fade=t=in:st={start}:d={FADE}:alpha=1,"
            f"fade=t=out:st={round(end - FADE, 2)}:d={FADE}:alpha=1")


def read_phrases(item: dict, item_path: Path) -> list[str]:
    phrases = item["video"].get("overlay_phrases")
    if (not isinstance(phrases, list) or len(phrases) != PHRASE_COUNT
            or not all(isinstance(p, str) and p.strip() for p in phrases)):
        raise SystemExit(f"{item_path}: 先在 video.overlay_phrases 写 {PHRASE_COUNT} 句开篇提醒主人叫猫过来看的话")
    for phrase in phrases:
        if len(phrase) > PHRASE_MAX_CHARS:
            raise SystemExit(f"{item_path}: 「{phrase}」超过 {PHRASE_MAX_CHARS} 个字")
    return phrases


def build(item_path: Path) -> None:
    item = json.loads(item_path.read_text(encoding="utf-8"))
    base = item_path.parent
    video = item["video"]
    phrases = read_phrases(item, item_path)
    final = base / video["file"]
    clean = base / CLEAN_NAME
    clean.parent.mkdir(exist_ok=True)
    if not clean.exists():
        shutil.copy2(final, clean)  # 首次运行：当前成片就是未叠字的原片
    duration = probe_duration(clean)
    if not has_audio(clean):
        raise SystemExit(f"{item_path}: 原片没有音轨，拒绝处理")

    wins = windows(duration)
    images = []
    for number, phrase in enumerate(phrases, start=1):
        target = base / "work" / f"overlay-{number}.png"
        render_text(phrase, target)
        images.append(target)

    chains, last = [], "0:v"
    for number, (start, end) in enumerate(wins, start=1):
        chains.append(fade_chain(number, start, end) + f"[t{number}]")
        out_label = "v" if number == len(wins) else f"o{number}"
        chains.append(f"[{last}][t{number}]overlay=x=(W-w)/2:y={TOP_MARGIN}+{BOUNCE_PX}*sin(7*t):"
                      f"eof_action=pass[{out_label}]")
        last = out_label
    out = base / "work" / "video-with-overlay.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(clean)]
    for image in images:
        cmd += ["-loop", "1", "-framerate", "30", "-t", f"{duration:.3f}", "-i", str(image)]
    cmd += ["-filter_complex", ";".join(chains), "-map", "[v]", "-map", "0:a", "-c:v", "libx264",
            "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "copy",
            "-movflags", "+faststart", "-t", f"{duration:.3f}", str(out)]
    subprocess.run(cmd, check=True)

    new_duration = probe_duration(out)
    if abs(new_duration - duration) > 0.15 or not has_audio(out):
        raise SystemExit(f"{item_path}: 叠字后时长或音轨异常（{duration:.2f}→{new_duration:.2f}）")
    shutil.move(out, final)

    video["sha256"] = sha256(final)
    video["duration_seconds"] = round(new_duration, 1)
    video["clean_file"] = CLEAN_NAME
    video["clean_sha256"] = sha256(clean)
    video["overlay"] = {
        "tool": "scripts/add_overlay.py",
        "purpose": "开篇提醒主人叫猫过来看，不是字幕，也不是游戏宣传",
        "position": "画面顶部居中，避开左右上角的作者标识",
        "style": f"暖黄粗体 {FONT_SIZE}px、深棕描边、轻微上下跳动，淡入淡出 {FADE} 秒；音频原样复制",
        "texts": [{"role": "cat-prompt", "start": s, "end": e, "text": t}
                  for (s, e), t in zip(wins, phrases)],
    }
    old = video.get("edit", "")
    head = (old.split("；仅增加")[0] if "；仅增加" in old
            else old.split("；无新增字幕")[0] if "；无新增字幕" in old else old.rstrip("。"))
    video["edit"] = head + "；仅在开篇增加一处提醒主人叫猫过来看的顶部叠字，无循环、拼接或变速。"
    item_path.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{item['item_id']}: {duration:.1f}s  " + "  ".join(f"{s}-{e}s「{t}」" for (s, e), t in zip(wins, phrases)))


def check(item_path: Path) -> list[str]:
    item = json.loads(item_path.read_text(encoding="utf-8"))
    video, base = item["video"], item_path.parent
    overlay = video.get("overlay")
    if not overlay:
        return ["缺少 video.overlay 记录"]
    errors = []
    final, clean = base / video["file"], base / video.get("clean_file", CLEAN_NAME)
    if not final.exists() or sha256(final) != video.get("sha256"):
        errors.append("成片哈希与 item.video.sha256 不一致")
    if not clean.exists() or sha256(clean) != video.get("clean_sha256"):
        errors.append("未叠字原片缺失或哈希不一致")
    duration = video.get("duration_seconds", 0)
    texts = overlay.get("texts", [])
    if len(texts) != PHRASE_COUNT:
        errors.append(f"叠字应有 {PHRASE_COUNT} 处")
    if [t.get("text") for t in texts] != video.get("overlay_phrases"):
        errors.append("叠字记录与 overlay_phrases 不一致，需重新运行")
    for entry in texts:
        if not 0 <= entry["start"] < entry["end"] <= duration:
            errors.append(f"叠字时间超出成片时长：{entry['text']}")
        if any(word in entry["text"] for word in ("游戏", "评论", "链接")):
            errors.append(f"叠字是提醒主人叫猫过来看，不写游戏或评论引导：{entry['text']}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("items", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true", help="只核对，不改文件")
    args = parser.parse_args()
    failed = False
    for path in args.items:
        if args.check:
            errors = check(path)
            failed |= bool(errors)
            print(("失败 " if errors else "通过 ") + str(path))
            for error in errors:
                print("  - " + error)
        else:
            build(path)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
