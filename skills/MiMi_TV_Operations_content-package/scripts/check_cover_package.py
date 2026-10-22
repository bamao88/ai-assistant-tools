#!/usr/bin/env python3
"""Validate MiMi TV social-cover fields in an item or legacy manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CATEGORY_BY_TYPE = {
    "external_passive_video": "猫咪动画片",
    "external_video": "猫咪动画片",
    "passive_video": "猫咪动画片",
    "interactive_programme": "猫咪游戏",
}
FIXED_TEXT = {"MMTV", "猫猫电视机"}
FORBIDDEN_TEXT = {"30秒", "30 秒", "官方", "原创", "播放", "点击播放"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 MiMi TV Content Item 封面字段与图片。")
    parser.add_argument("items", nargs="+", help="一个或多个 item.json；也兼容历史封面 JSON 清单。")
    parser.add_argument(
        "--allow-high-res-3x4",
        action="store_true",
        help="探索稿允许任意不低于 1080x1440 的精确 3:4 图片；正式包必须为 1080x1440。",
    )
    return parser.parse_args()


def resolve_path(item_path: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return (item_path.parent / candidate).resolve()


def validate_manifest(path: Path, allow_high_res: bool) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"无法读取 JSON：{exc}"]

    required_item = [
        "item_id", "content_type", "source",
    ]
    for key in required_item:
        if key not in data:
            errors.append(f"缺少 item 字段：{key}")

    cover = data.get("cover", data)
    if not isinstance(cover, dict):
        errors.append("cover 必须是对象")
        return errors

    required_cover = [
        "template_version",
        "category_label",
        "cover_title",
        "channel_number",
        "background",
    ]
    for key in required_cover:
        if key not in cover:
            errors.append(f"缺少 cover 字段：{key}")
    if not cover.get("file", cover.get("output_image")):
        errors.append("缺少 cover.file")

    if errors:
        return errors

    content_type = data["content_type"]
    expected_category = CATEGORY_BY_TYPE.get(content_type)
    if expected_category is None:
        errors.append(f"未知 content_type：{content_type}")
    elif cover["category_label"] != expected_category:
        errors.append(
            f"品类映射错误：{content_type} 应为 {expected_category}，当前为 {cover['category_label']}"
        )

    raw_title = cover["cover_title"]
    title = raw_title.strip() if isinstance(raw_title, str) else ""
    if not title:
        errors.append("cover_title 必须为非空字符串")
    # Naming is open-ended. Length, punctuation and line layout are assessed
    # on the rendered cover, not rejected by a fixed character-count formula.

    channel = cover["channel_number"]
    if not isinstance(channel, int) or not 1 <= channel <= 99:
        errors.append("channel_number 必须是 1–99 的整数")
        channel_text = None
    else:
        channel_text = f"频道 {channel:02d}"

    visible = cover.get("visible_text")
    if visible is not None:
        if not isinstance(visible, list) or not all(isinstance(item, str) for item in visible):
            errors.append("cover.visible_text 必须是字符串数组")
        else:
            expected_visible = FIXED_TEXT | {cover["category_label"], title}
            if channel_text:
                expected_visible.add(channel_text)
            if set(visible) != expected_visible:
                errors.append(
                    "cover.visible_text 必须且只能包含：" + "、".join(sorted(expected_visible))
                )
            flattened = " ".join(visible)
            for forbidden in FORBIDDEN_TEXT:
                if forbidden in flattened:
                    errors.append(f"出现禁用文字：{forbidden}")

    background = cover["background"]
    if not isinstance(background, dict):
        errors.append("background 必须是对象")
    else:
        mode = background.get("mode")
        if mode not in {"real_frame", "ai_processed"}:
            errors.append("background.mode 必须为 real_frame 或 ai_processed")
        if not background.get("asset"):
            errors.append("background.asset 缺失")
        if mode == "ai_processed":
            for key in ("reference_assets", "prompt_log", "generator"):
                if not background.get(key):
                    errors.append(f"ai_processed 背景缺少：background.{key}")
        if mode == "real_frame" and background.get("frame_time") is None:
            errors.append("real_frame 背景缺少：background.frame_time")

    source = data["source"]
    if not isinstance(source, dict):
        errors.append("source 必须是对象")
    elif source.get("kind") == "external" or source.get("platform") == "youtube":
        author = source.get("channel", source.get("original_author"))
        url = source.get("url", source.get("original_url"))
        for key, value in (
            ("channel", author),
            ("url", url),
            ("usage_basis", source.get("usage_basis")),
            ("rights_status", source.get("rights_status")),
        ):
            if not value:
                errors.append(f"外部来源缺少：source.{key}")

    image_path = resolve_path(path, str(cover.get("file", cover.get("output_image"))))
    if not image_path.exists():
        errors.append(f"输出图片不存在：{image_path}")
        return errors

    try:
        from PIL import Image
    except ImportError:
        errors.append("图片尺寸检查需要 Pillow；不要自动安装，请改用 sips 并保留证据")
        return errors

    with Image.open(image_path) as image:
        width, height = image.size

    if width * 4 != height * 3:
        errors.append(f"图片不是精确 3:4：{width}x{height}")
    if allow_high_res:
        if width < 1080 or height < 1440:
            errors.append(f"探索稿尺寸不足：{width}x{height}")
    elif (width, height) != (1080, 1440):
        errors.append(f"正式上传图必须为 1080x1440，当前为 {width}x{height}")

    return errors


def main() -> None:
    args = parse_args()
    failed = False
    for raw in args.items:
        path = Path(raw).expanduser().resolve()
        errors = validate_manifest(path, args.allow_high_res_3x4)
        if errors:
            failed = True
            print(f"失败 {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"通过 {path}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
