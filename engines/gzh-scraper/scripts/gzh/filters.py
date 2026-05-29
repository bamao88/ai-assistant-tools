"""指标筛选逻辑。"""

from __future__ import annotations

import time
from typing import Any

from .types import Article, FilterCriteria


def matches_filter(article: Article, criteria: FilterCriteria) -> bool:
    """检查文章是否满足筛选条件。"""
    # 阅读量筛选
    if criteria.min_reads > 0 and article.read_num < criteria.min_reads:
        return False

    # 点赞筛选
    if criteria.min_likes > 0 and article.like_num < criteria.min_likes:
        return False

    # 时间筛选
    if criteria.since_days > 0 and article.create_time > 0:
        cutoff = time.time() - criteria.since_days * 86400
        if article.create_time < cutoff:
            return False

    # 关键词筛选（标题或摘要包含任一关键词）
    if criteria.keywords:
        text = (article.title + " " + article.digest).lower()
        if not any(kw.lower() in text for kw in criteria.keywords):
            return False

    return True


def filter_articles(
    articles: list[dict[str, Any]], criteria: FilterCriteria, account_name: str = ""
) -> list[Article]:
    """从原始文章数据中筛选符合条件的文章。"""
    result = []
    for raw in articles:
        article = Article.from_api(raw, account_name=account_name)
        if matches_filter(article, criteria):
            result.append(article)
    return result
