from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".flv", ".wmv")


@dataclass(frozen=True)
class ItemPublishCopy:
    item_dir: Path
    publish_copy: Path
    title: str
    desc: str
    tags: list[str]
    video_path: Path
    thumbnail_path: Path


def read_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}(?:\s|[（(]|$).*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def strip_markdown_inline(value: str) -> str:
    value = value.strip()
    value = value.replace("✅", "").strip()
    value = re.sub(r"^\s*[-*]\s+", "", value).strip()
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"^推荐\s*[：:]\s*", "", value).strip()
    value = re.sub(r"^[：:]\s*", "", value).strip()
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_checked_title(markdown: str) -> str:
    title_section = read_section(markdown, "标题候选")
    if not title_section:
        raise ValueError("publish_copy.md missing ## 标题候选 section")

    checked_lines = [
        line.strip()
        for line in title_section.splitlines()
        if "✅" in line and re.match(r"^\s*[-*]\s+", line)
    ]
    if not checked_lines:
        raise ValueError("publish_copy.md has no ✅ title candidate")
    if len(checked_lines) > 1:
        raise ValueError("publish_copy.md has multiple ✅ title candidates")

    title = strip_markdown_inline(checked_lines[0])
    if not title:
        raise ValueError("checked title candidate is empty")
    return title


def parse_body(markdown: str) -> str:
    body = read_section(markdown, "正文").strip()
    if not body:
        raise ValueError("publish_copy.md missing ## 正文 section")
    return body


def parse_shipinhao_tags(markdown: str) -> list[str]:
    for line in markdown.splitlines():
        if "视频号精简" not in line:
            continue
        tags = [tag.strip().lstrip("#") for tag in re.findall(r"#([\w\u4e00-\u9fff-]+)", line)]
        if tags:
            return tags

    keyword_section = read_section(markdown, "中文关键词")
    tags = [tag.strip().lstrip("#") for tag in re.findall(r"#([\w\u4e00-\u9fff-]+)", keyword_section)]
    if tags:
        return tags[:5]
    raise ValueError("publish_copy.md missing 视频号精简 tags")


def default_video_path(item_dir: Path) -> Path:
    preferred = item_dir / "成片.mp4"
    if preferred.exists():
        return preferred
    videos = sorted(path for path in item_dir.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)
    if len(videos) == 1:
        return videos[0]
    if not videos:
        raise ValueError(f"no video file found in item dir: {item_dir}")
    raise ValueError(f"multiple video files found in item dir, pass --file explicitly: {item_dir}")


def default_thumbnail_path(item_dir: Path) -> Path:
    for name in ("cover.png", "cover.jpg", "cover.jpeg", "封面.png", "封面.jpg", "封面.jpeg"):
        path = item_dir / name
        if path.exists():
            return path
    raise ValueError(f"no cover image found in item dir: {item_dir}")


def load_item_publish_copy(
    item_dir: Path,
    *,
    video_path: Path | None = None,
    thumbnail_path: Path | None = None,
    copy_filename: str = "publish_copy.md",
) -> ItemPublishCopy:
    item_dir = item_dir.expanduser().resolve()
    publish_copy = item_dir / copy_filename
    if not publish_copy.exists():
        # 兼容 publish-prep 的 publish_<account>.md 命名：copy_filename 缺失时回落 publish_copy.md
        fallback = item_dir / "publish_copy.md"
        if copy_filename != "publish_copy.md" and fallback.exists():
            publish_copy = fallback
        else:
            raise ValueError(f"{copy_filename} not found: {publish_copy}")

    markdown = publish_copy.read_text(encoding="utf-8")
    return ItemPublishCopy(
        item_dir=item_dir,
        publish_copy=publish_copy,
        title=parse_checked_title(markdown),
        desc=parse_body(markdown),
        tags=parse_shipinhao_tags(markdown),
        video_path=(video_path.expanduser().resolve() if video_path else default_video_path(item_dir)),
        thumbnail_path=(
            thumbnail_path.expanduser().resolve() if thumbnail_path else default_thumbnail_path(item_dir)
        ),
    )
