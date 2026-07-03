#!/usr/bin/env python3
"""关键词构造器（确定性，不调模型）。读 skill 的 keyword_pool.yaml（config.KEYWORD_POOL）。

三层优先级：trending(热词监控预留) > topical(正文命中正则) > fixed(固定盘) → fill_pool 补满。
数量按平台取 fill_to_by_platform[platform]（小红书10/视频号5/抖音5/default10）。

用法:
    python3 build_keywords.py <text_file|-> [--platform xiaohongshu|shipinhao|douyin]
    或 import：from build_keywords import build_keywords; build_keywords(text, "shipinhao")
"""
import sys
import re
import argparse
from pathlib import Path

import yaml

import config


def build_keywords(text: str, platform: str = "default", pool_file: Path | None = None) -> list[str]:
    pool = yaml.safe_load(Path(pool_file or config.KEYWORD_POOL).read_text(encoding="utf-8"))
    low = text.lower()
    out: list[str] = []

    def add(tags):
        for t in tags:
            if t not in out:
                out.append(t)

    add(pool.get("trending", []))                                  # 1) 热词监控（最高优先级）
    for pattern, tags in pool.get("topical", {}).items():          # 2) 正文命中
        if any(re.search(alias, low) for alias in pattern.split("|")):
            add(tags)
    add(pool.get("fixed", []))                                     # 3) 固定盘兜底
    add(pool.get("fill_pool", []))                                 # 4) 补满

    ft = pool.get("fill_to_by_platform", {})
    n = ft.get(platform, ft.get("default", 10))
    return out[:n]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("text_file", help="正文文件路径，或 - 读 stdin")
    ap.add_argument("--platform", default="default")
    args = ap.parse_args()
    txt = sys.stdin.read() if args.text_file == "-" else Path(args.text_file).read_text(encoding="utf-8")
    tags = build_keywords(txt, args.platform)
    print(" ".join("#" + t for t in tags))
