from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tvp.item import load_item_publish_copy, parse_checked_title, parse_shipinhao_tags


def test_parse_checked_title_with_leading_checkmark() -> None:
    markdown = """## 标题候选（小红书 · ≤20字 · 多句式）

- ✅ **推荐**：评测报告，早该做成能对话的网页了
- 还在用Excel看评测报告？该升级了

## 正文
body
"""

    assert parse_checked_title(markdown) == "评测报告，早该做成能对话的网页了"


def test_parse_checked_title_with_trailing_checkmark() -> None:
    markdown = """## 标题候选

- **推荐**：传统脚本已死，Agent看护永生
- 这三样东西组合，自动化基本无敌 ✅

## 封面标题候选
- 想让自动化不崩，靠的就是这三样东西的组合 ✅
"""

    assert parse_checked_title(markdown) == "这三样东西组合，自动化基本无敌"


def test_parse_shipinhao_tags_prefers_compact_line() -> None:
    markdown = """## 中文关键词

#ai产品经理 #aiagent #自动化 #computeruse #ai自动化 #agent开发

视频号精简（5 个）：#ai产品经理 #aiagent #自动化 #computeruse #aicoding
"""

    assert parse_shipinhao_tags(markdown) == ["ai产品经理", "aiagent", "自动化", "computeruse", "aicoding"]


def test_load_item_publish_copy_defaults_to_local_assets(tmp_path: Path) -> None:
    item_dir = tmp_path / "ZHC20260613_evc04_001"
    item_dir.mkdir()
    (item_dir / "成片.mp4").write_bytes(b"video")
    (item_dir / "cover.png").write_bytes(b"image")
    (item_dir / "publish_copy.md").write_text(
        """# 发布物料

## 标题候选

- 这三样东西组合，自动化基本无敌 ✅

## 正文

纯脚本自动化最大的问题，不是不会跑。

## 中文关键词

#ai产品经理 #aiagent #自动化 #computeruse #ai自动化

视频号精简（5 个）：#ai产品经理 #aiagent #自动化 #computeruse #aicoding
""",
        encoding="utf-8",
    )

    item = load_item_publish_copy(item_dir)

    assert item.title == "这三样东西组合，自动化基本无敌"
    assert item.desc == "纯脚本自动化最大的问题，不是不会跑。"
    assert item.tags == ["ai产品经理", "aiagent", "自动化", "computeruse", "aicoding"]
    assert item.video_path == item_dir / "成片.mp4"
    assert item.thumbnail_path == item_dir / "cover.png"
