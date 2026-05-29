"""文章存储与去重。

存储结构：
    data/{公众号名称}/{YYYY-MM}/{文章标题}.md
    data/{公众号名称}/{YYYY-MM}/{文章标题}.json  # 元数据
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from .types import Article

# 默认存储目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    """清理文件名，移除不安全字符。"""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(". ")
    return name[:max_len] if name else "untitled"


def _article_dir(article: Article, base_dir: str = "") -> str:
    """计算文章的存储目录。"""
    base = base_dir or DATA_DIR
    account = _sanitize_filename(article.account_name or "unknown")
    month = article.create_datetime.strftime("%Y-%m") if article.create_time else "unknown"
    return os.path.join(base, account, month)


def article_exists(article: Article, base_dir: str = "") -> bool:
    """检查文章是否已下载（去重）。"""
    d = _article_dir(article, base_dir)
    fname = _sanitize_filename(article.title)
    return os.path.exists(os.path.join(d, f"{fname}.json"))


def save_article(
    article: Article,
    content: str,
    base_dir: str = "",
    fmt: str = "md",
) -> str:
    """保存文章内容和元数据，返回保存路径。"""
    d = _article_dir(article, base_dir)
    os.makedirs(d, exist_ok=True)

    fname = _sanitize_filename(article.title)

    # 保存内容
    content_path = os.path.join(d, f"{fname}.{fmt}")
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 保存元数据
    meta_path = os.path.join(d, f"{fname}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(article.to_dict(), f, ensure_ascii=False, indent=2)

    return content_path


def list_saved_articles(base_dir: str = "") -> list[dict[str, Any]]:
    """列出所有已保存的文章元数据。"""
    base = base_dir or DATA_DIR
    result = []
    if not os.path.exists(base):
        return result

    for account_dir in sorted(os.listdir(base)):
        account_path = os.path.join(base, account_dir)
        if not os.path.isdir(account_path):
            continue
        for month_dir in sorted(os.listdir(account_path)):
            month_path = os.path.join(account_path, month_dir)
            if not os.path.isdir(month_path):
                continue
            for fname in sorted(os.listdir(month_path)):
                if fname.endswith(".json"):
                    meta_path = os.path.join(month_path, fname)
                    with open(meta_path, encoding="utf-8") as f:
                        result.append(json.load(f))
    return result
