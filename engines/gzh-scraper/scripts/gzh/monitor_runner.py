"""监控执行逻辑，供 cli.py run-monitor 和 monitor.py 调用。"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from .api_client import APIError, ExporterClient
from .config import get_auth_key, get_exporter_url
from .filters import matches_filter
from .storage import article_exists, save_article
from .types import Article, WatchItem
from .watchlist import get_watchlist, update_last_checked

logger = logging.getLogger("gzh-monitor")


def run_monitor(base_url: str = "", dry_run: bool = False) -> dict[str, Any]:
    """执行一次完整监控。

    遍历 watchlist 中所有启用的公众号，获取文章列表，
    按筛选条件过滤，下载符合条件的文章。
    """
    url = base_url or get_exporter_url()
    auth_key = get_auth_key()

    if not auth_key:
        return {"success": False, "error": "未配置 auth-key，请先登录"}

    client = ExporterClient(base_url=url, auth_key=auth_key)

    # 先检查登录状态
    auth_result = client.check_auth()
    if not auth_result.get("authenticated"):
        return {
            "success": False,
            "error": "登录已过期，请重新扫码登录",
            "auth_result": auth_result,
        }

    watchlist = get_watchlist()
    enabled = [w for w in watchlist if w.enabled]

    if not enabled:
        return {"success": True, "message": "监控列表为空", "checked": 0, "downloaded": 0}

    total_checked = 0
    total_downloaded = 0
    results: list[dict[str, Any]] = []

    for watch_item in enabled:
        logger.info("检查公众号: %s (fakeid=%s)", watch_item.name, watch_item.fakeid)
        item_result = _check_account(client, watch_item, dry_run)
        results.append(item_result)
        total_checked += 1
        total_downloaded += item_result.get("downloaded", 0)

        # 更新最后检查时间
        now = datetime.now(timezone.utc).isoformat()
        update_last_checked(watch_item.fakeid, now)

    return {
        "success": True,
        "checked": total_checked,
        "downloaded": total_downloaded,
        "dry_run": dry_run,
        "results": results,
    }


def _check_account(
    client: ExporterClient, watch: WatchItem, dry_run: bool
) -> dict[str, Any]:
    """检查单个公众号的文章。"""
    matched_articles: list[dict[str, Any]] = []
    downloaded = 0

    try:
        # 获取文章列表（最多取 100 篇）
        all_articles: list[dict[str, Any]] = []
        begin = 0
        page_size = 10
        max_pages = 10  # 最多 100 篇

        for _ in range(max_pages):
            result = client.list_articles(
                fakeid=watch.fakeid,
                begin=begin,
                size=page_size,
            )
            articles = result.get("articles", [])
            if not articles:
                break
            all_articles.extend(articles)
            begin += page_size

            # 如果已经超过筛选时间窗口，提前停止
            last_article = Article.from_api(articles[-1])
            cutoff = time.time() - watch.filters.since_days * 86400
            if last_article.create_time and last_article.create_time < cutoff:
                break

        # 筛选
        for raw in all_articles:
            article = Article.from_api(raw, account_name=watch.name, account_fakeid=watch.fakeid)
            if not matches_filter(article, watch.filters):
                continue

            if article_exists(article):
                continue

            matched_articles.append(article.to_dict())

            if not dry_run:
                try:
                    html = client.download_article_html(article.link)
                    save_article(article, html, fmt="html")
                    downloaded += 1
                    logger.info("已下载: %s", article.title)
                except APIError as e:
                    logger.warning("下载失败 [%s]: %s", article.title, e)

    except APIError as e:
        return {
            "account": watch.name,
            "fakeid": watch.fakeid,
            "error": str(e),
            "matched": 0,
            "downloaded": 0,
        }

    return {
        "account": watch.name,
        "fakeid": watch.fakeid,
        "total_fetched": len(all_articles),
        "matched": len(matched_articles),
        "downloaded": downloaded,
        "articles": matched_articles,
    }
