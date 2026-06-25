#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from wcf.core import (  # noqa: E402
    BrowserOptions,
    ChannelsFetchError,
    WECHAT_WINDOWS_UA,
    account_payload,
    diagnose,
    get_feed_detail,
    list_comments,
    list_feeds,
    search_accounts,
)


def output(data: dict, exit_code: int = 0) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def options_from_args(args: argparse.Namespace) -> BrowserOptions:
    return BrowserOptions(
        account=args.account or "",
        headless=not args.headed,
        timeout_ms=args.timeout_ms,
        api_timeout_ms=args.api_timeout_ms,
        init_url=args.init_url or "",
        user_agent="" if args.chrome_ua else args.user_agent,
    )


def run(coro) -> dict:
    try:
        return asyncio.run(coro)
    except ChannelsFetchError as exc:
        return exc.to_payload()
    except Exception as exc:
        return {"success": False, "status": "failed", "message": str(exc)}


def cmd_accounts(args: argparse.Namespace) -> None:
    from wcf.core import tvp_accounts

    output(
        {
            "success": True,
            "accounts": tvp_accounts.list_accounts(),
            "default_account": account_payload(""),
        }
    )


def cmd_diagnose(args: argparse.Namespace) -> None:
    if args.api_base:
        from wcf import local_api

        result = local_api.diagnose(args.api_base)
        output(result, 0 if result.get("success") else 1)
    result = run(diagnose(options_from_args(args)))
    output(result, 0 if result.get("success") else 1)


def cmd_search_accounts(args: argparse.Namespace) -> None:
    if args.api_base:
        from wcf import local_api

        result = local_api.search_accounts(
            args.api_base,
            keyword=args.keyword,
            search_type=args.type,
            next_marker=args.next_marker or "",
        )
        output(result, 0 if result.get("success") else 1)
    result = run(
        search_accounts(
            options_from_args(args),
            keyword=args.keyword,
            search_type=args.type,
            next_marker=args.next_marker or "",
        )
    )
    output(result, 0 if result.get("success") else 1)


def cmd_list_feeds(args: argparse.Namespace) -> None:
    if args.api_base:
        from wcf import local_api

        result = local_api.list_feeds(
            args.api_base,
            username=args.username,
            next_marker=args.next_marker or "",
            max_pages=args.max_pages,
            limit=args.limit,
            out_dir=Path(args.out_dir).expanduser() if args.out_dir else None,
        )
        output(result, 0 if result.get("success") else 1)
    result = run(
        list_feeds(
            options_from_args(args),
            username=args.username,
            next_marker=args.next_marker or "",
            max_pages=args.max_pages,
            limit=args.limit,
            delay_seconds=args.delay,
            out_dir=Path(args.out_dir).expanduser() if args.out_dir else None,
        )
    )
    output(result, 0 if result.get("success") else 1)


def cmd_get_feed_detail(args: argparse.Namespace) -> None:
    if args.api_base:
        from wcf import local_api

        result = local_api.get_feed_detail(
            args.api_base,
            object_id=args.object_id or "",
            nonce_id=args.nonce_id or "",
            url=args.url or "",
        )
        output(result, 0 if result.get("success") else 1)
    result = run(
        get_feed_detail(
            options_from_args(args),
            object_id=args.object_id or "",
            nonce_id=args.nonce_id or "",
            url=args.url or "",
        )
    )
    output(result, 0 if result.get("success") else 1)


def cmd_list_comments(args: argparse.Namespace) -> None:
    if args.api_base:
        from wcf import local_api

        result = local_api.list_comments(
            args.api_base,
            object_id=args.object_id,
            nonce_id=args.nonce_id or "",
            comment_id=args.comment_id or "",
            next_marker=args.next_marker or "",
        )
        output(result, 0 if result.get("success") else 1)
    result = run(
        list_comments(
            options_from_args(args),
            object_id=args.object_id,
            nonce_id=args.nonce_id or "",
            comment_id=args.comment_id or "",
            next_marker=args.next_marker or "",
        )
    )
    output(result, 0 if result.get("success") else 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch public WeChat Channels account feeds")
    parser.add_argument("--account", default="aipm", help="account slot from tencent-video-publish")
    parser.add_argument("--headed", action="store_true", help="show Chrome instead of headless mode")
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--api-timeout-ms", type=int, default=15000)
    parser.add_argument("--init-url", default="", help="override page URL used to initialize WXU APIs")
    parser.add_argument("--user-agent", default=WECHAT_WINDOWS_UA, help="browser UA; defaults to Windows WeChat")
    parser.add_argument("--chrome-ua", action="store_true", help="use Chrome default UA instead of WeChat UA")
    parser.add_argument(
        "--api-base",
        default="",
        help="use a running wx_channel-compatible HTTP API, e.g. http://127.0.0.1:2026",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("accounts", help="list reusable video account slots")
    p.set_defaults(func=cmd_accounts)

    p = sub.add_parser("diagnose", help="check login/page API readiness")
    p.set_defaults(func=cmd_diagnose)

    p = sub.add_parser("search-accounts", help="search WeChat Channels accounts")
    p.add_argument("--keyword", required=True)
    p.add_argument("--type", type=int, default=1, choices=[1, 2, 3], help="1=user, 2=live, 3=video")
    p.add_argument("--next-marker", default="")
    p.set_defaults(func=cmd_search_accounts)

    p = sub.add_parser("list-feeds", help="fetch a WeChat Channels account feed list")
    p.add_argument("--username", required=True, help="finder username from search result, not nickname")
    p.add_argument("--next-marker", default="")
    p.add_argument("--max-pages", type=int, default=1)
    p.add_argument("--limit", type=int, default=0, help="maximum normalized items; 0 means no explicit limit")
    p.add_argument("--delay", type=float, default=0.8, help="seconds between paginated requests")
    p.add_argument("--out-dir", default="")
    p.set_defaults(func=cmd_list_feeds)

    p = sub.add_parser("get-feed-detail", help="fetch one feed detail")
    p.add_argument("--object-id", default="", help="feed object id")
    p.add_argument("--nonce-id", default="")
    p.add_argument("--url", default="", help="reserved for share/video URL based lookup")
    p.set_defaults(func=cmd_get_feed_detail)

    p = sub.add_parser("list-comments", help="fetch one page of comments")
    p.add_argument("--object-id", required=True)
    p.add_argument("--nonce-id", default="")
    p.add_argument("--comment-id", default="", help="root comment id for replies")
    p.add_argument("--next-marker", default="")
    p.set_defaults(func=cmd_list_comments)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
