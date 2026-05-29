"""微信公众号文章采集 CLI 入口。

全局选项: --base-url
输出: JSON（ensure_ascii=False）
退出码: 0=成功, 1=未认证, 2=错误
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import webbrowser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("gzh-cli")

# 确保 gzh 包可导入
sys.path.insert(0, os.path.dirname(__file__))


def _output(data: dict, exit_code: int = 0) -> None:
    """输出 JSON 并退出。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def _make_client(args: argparse.Namespace):
    from gzh.api_client import ExporterClient
    from gzh.config import get_auth_key, get_exporter_url

    base_url = getattr(args, "base_url", "") or get_exporter_url()
    auth_key = get_auth_key()
    return ExporterClient(base_url=base_url, auth_key=auth_key)


def _ensure_exporter(args: argparse.Namespace) -> None:
    """Auto-start exporter for commands that need the local service."""
    if getattr(args, "no_auto_start", False):
        return

    from gzh.config import get_exporter_url
    from gzh.exporter_service import ensure_exporter_running

    base_url = getattr(args, "base_url", "") or get_exporter_url()
    result = ensure_exporter_running(
        base_url=base_url,
        wait_seconds=getattr(args, "wait_exporter", 45),
    )
    if not result.get("success"):
        _output(
            {
                "success": False,
                "error": result.get("error", "exporter 服务启动失败"),
                "exporter": result,
            },
            2,
        )


# ========== 子命令实现 ==========


def cmd_check_auth(args: argparse.Namespace) -> None:
    """检查登录状态。"""
    client = _make_client(args)
    result = client.check_auth()
    exit_code = 0 if result.get("authenticated") else 1
    _output(result, exit_code)


def cmd_login(args: argparse.Namespace) -> None:
    """打开浏览器进行扫码登录。"""
    from gzh.config import get_exporter_url

    base_url = getattr(args, "base_url", "") or get_exporter_url()
    url = base_url.rstrip("/")
    webbrowser.open(url)
    print(json.dumps({
        "success": True,
        "message": f"已打开浏览器 {url}，请扫码登录。登录成功后，从浏览器 Cookie 中复制 auth-key 值，然后运行：",
        "next_step": "python cli.py set-auth-key --key <你的auth-key>",
    }, ensure_ascii=False, indent=2))
    sys.exit(0)


def cmd_set_auth_key(args: argparse.Namespace) -> None:
    """保存 auth-key。"""
    from gzh.config import set_auth_key

    key = args.key.strip()
    if not key:
        _output({"success": False, "error": "auth-key 不能为空"}, 2)
    set_auth_key(key)
    _output({"success": True, "message": f"auth-key 已保存"})


def cmd_search_accounts(args: argparse.Namespace) -> None:
    """搜索公众号。"""
    from gzh.api_client import APIError

    client = _make_client(args)
    try:
        accounts = client.search_accounts(
            keyword=args.keyword,
            begin=args.begin,
            size=args.size,
        )
        _output({"success": True, "count": len(accounts), "accounts": accounts})
    except APIError as e:
        _output({"success": False, "error": str(e)}, 2)


def cmd_list_articles(args: argparse.Namespace) -> None:
    """列出指定公众号的文章。"""
    from gzh.api_client import APIError

    client = _make_client(args)
    try:
        result = client.list_articles(
            fakeid=args.fakeid,
            keyword=args.keyword or "",
            begin=args.begin,
            size=args.size,
        )
        _output({
            "success": True,
            "total": result["total"],
            "count": len(result["articles"]),
            "articles": result["articles"],
        })
    except APIError as e:
        _output({"success": False, "error": str(e)}, 2)


def cmd_download_article(args: argparse.Namespace) -> None:
    """下载单篇文章。"""
    from gzh.api_client import APIError, ExporterClient
    from gzh.storage import save_article
    from gzh.types import Article

    client = _make_client(args)

    try:
        html = client.download_article_html(args.url)
    except APIError as e:
        _output({"success": False, "error": str(e)}, 2)
        return

    # 从 HTML 提取标题
    title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "untitled"

    # 简单的 HTML → Markdown 转换（保留原始 HTML 也可以）
    fmt = args.format or "html"

    article = Article(
        aid="",
        title=title,
        link=args.url,
        create_time=int(time.time()),
        account_name=args.account_name or "manual",
    )

    content = html
    if fmt == "md":
        # 基础转换：去 HTML 标签
        content = _html_to_basic_md(html)

    path = save_article(article, content, fmt=fmt)
    _output({"success": True, "path": path, "title": title})


def _html_to_basic_md(html: str) -> str:
    """简单的 HTML → Markdown 转换。"""
    import re

    # 提取正文区域
    body_match = re.search(
        r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*(?:<div|$)',
        html, re.DOTALL
    )
    text = body_match.group(1) if body_match else html

    # 替换常见标签
    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", text, flags=re.DOTALL)
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r'<img[^>]*data-src="([^"]*)"[^>]*/?>',  r"![](\1)", text)
    text = re.sub(r"<[^>]+>", "", text)  # 去剩余标签
    text = re.sub(r"\n{3,}", "\n\n", text)  # 合并空行
    return text.strip()


def cmd_add_watch(args: argparse.Namespace) -> None:
    """添加监控公众号。"""
    from gzh.watchlist import add_watch

    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
    try:
        item = add_watch(
            fakeid=args.fakeid,
            name=args.name,
            min_reads=args.min_reads,
            min_likes=args.min_likes,
            keywords=keywords,
            since_days=args.since_days,
        )
        _output({"success": True, "message": f"已添加监控: {args.name}", "watch": item.to_dict()})
    except ValueError as e:
        _output({"success": False, "error": str(e)}, 2)


def cmd_remove_watch(args: argparse.Namespace) -> None:
    """移除监控公众号。"""
    from gzh.watchlist import remove_watch

    if remove_watch(args.fakeid):
        _output({"success": True, "message": f"已移除监控: {args.fakeid}"})
    else:
        _output({"success": False, "error": f"未找到 fakeid={args.fakeid} 的监控条目"}, 2)


def cmd_list_watch(args: argparse.Namespace) -> None:
    """查看监控列表。"""
    from gzh.watchlist import get_watchlist

    items = get_watchlist()
    _output({
        "success": True,
        "count": len(items),
        "watchlist": [item.to_dict() for item in items],
    })


def cmd_run_monitor(args: argparse.Namespace) -> None:
    """执行一次监控。"""
    from gzh.monitor_runner import run_monitor

    try:
        result = run_monitor(
            base_url=getattr(args, "base_url", ""),
            dry_run=args.dry_run,
        )
        _output(result)
    except Exception as e:
        _output({"success": False, "error": str(e)}, 2)


# ========== 主入口 ==========


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="微信公众号文章采集 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-url", default="", help="exporter 服务地址（默认 http://localhost:3000）"
    )
    parser.add_argument(
        "--no-auto-start",
        action="store_true",
        help="不自动启动本地 exporter 服务",
    )
    parser.add_argument(
        "--wait-exporter",
        type=int,
        default=45,
        help="自动启动 exporter 后等待的秒数",
    )

    sub = parser.add_subparsers(dest="command", help="子命令")

    # check-auth
    sub.add_parser("check-auth", help="检查登录状态")

    # login
    sub.add_parser("login", help="打开浏览器扫码登录")

    # set-auth-key
    p = sub.add_parser("set-auth-key", help="保存 auth-key")
    p.add_argument("--key", required=True, help="auth-key 值")

    # search-accounts
    p = sub.add_parser("search-accounts", help="搜索公众号")
    p.add_argument("--keyword", required=True, help="搜索关键词")
    p.add_argument("--begin", type=int, default=0, help="起始位置")
    p.add_argument("--size", type=int, default=5, help="返回数量")

    # list-articles
    p = sub.add_parser("list-articles", help="列出公众号文章")
    p.add_argument("--fakeid", required=True, help="公众号 fakeid")
    p.add_argument("--keyword", default="", help="关键词过滤")
    p.add_argument("--begin", type=int, default=0, help="起始位置")
    p.add_argument("--size", type=int, default=5, help="返回数量")

    # download-article
    p = sub.add_parser("download-article", help="下载单篇文章")
    p.add_argument("--url", required=True, help="文章 URL")
    p.add_argument("--format", choices=["html", "md"], default="html", help="保存格式")
    p.add_argument("--account-name", default="", help="所属公众号名称")

    # add-watch
    p = sub.add_parser("add-watch", help="添加监控公众号")
    p.add_argument("--fakeid", required=True, help="公众号 fakeid")
    p.add_argument("--name", required=True, help="公众号名称")
    p.add_argument("--min-reads", type=int, default=0, help="最低阅读量")
    p.add_argument("--min-likes", type=int, default=0, help="最低点赞数")
    p.add_argument("--keywords", default="", help="关键词过滤（逗号分隔）")
    p.add_argument("--since-days", type=int, default=7, help="只看最近 N 天的文章")

    # remove-watch
    p = sub.add_parser("remove-watch", help="移除监控")
    p.add_argument("--fakeid", required=True, help="公众号 fakeid")

    # list-watch
    sub.add_parser("list-watch", help="查看监控列表")

    # run-monitor
    p = sub.add_parser("run-monitor", help="执行一次监控采集")
    p.add_argument("--dry-run", action="store_true", help="模拟运行，不下载文章")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(2)

    cmd_map = {
        "check-auth": cmd_check_auth,
        "login": cmd_login,
        "set-auth-key": cmd_set_auth_key,
        "search-accounts": cmd_search_accounts,
        "list-articles": cmd_list_articles,
        "download-article": cmd_download_article,
        "add-watch": cmd_add_watch,
        "remove-watch": cmd_remove_watch,
        "list-watch": cmd_list_watch,
        "run-monitor": cmd_run_monitor,
    }

    handler = cmd_map.get(args.command)
    if handler:
        if args.command in {"check-auth", "login", "search-accounts", "list-articles", "run-monitor"}:
            _ensure_exporter(args)
        handler(args)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
