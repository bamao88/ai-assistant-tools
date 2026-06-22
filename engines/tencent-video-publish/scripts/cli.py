#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from tvp import accounts


def output(data: dict, exit_code: int = 0) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def parse_schedule(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid schedule datetime: {value}") from exc


def normalize_tags(values: list[str] | None) -> list[str]:
    if not values:
        return []
    tags: list[str] = []
    for value in values:
        for part in value.replace("，", ",").split(","):
            part = part.strip().lstrip("#")
            if part:
                tags.append(part)
    return tags


def storage_state_for(args: argparse.Namespace) -> Path:
    return accounts.account_state_path(getattr(args, "account", None))


def cmd_list_accounts(args: argparse.Namespace) -> None:
    items = accounts.list_accounts()
    default_state = accounts.account_state_path(None)
    output(
        {
            "success": True,
            "accounts": items,
            "count": len(items),
            "default_account": {
                "slot": "default",
                **accounts.storage_state_summary(default_state),
            },
            "state_dir": str(accounts.STATE_DIR),
        }
    )


def cmd_add_account(args: argparse.Namespace) -> None:
    output({"success": True, "account": accounts.add_account(args.slot, args.description or "")})


def cmd_remove_account(args: argparse.Namespace) -> None:
    output({"success": True, "removed": accounts.remove_account(args.slot)})


def cmd_set_default_account(args: argparse.Namespace) -> None:
    output({"success": True, "account": accounts.set_default_account(args.slot)})


def cmd_check_login(args: argparse.Namespace) -> None:
    from tvp.core import check_login

    result = asyncio.run(check_login(storage_state_for(args), headless=not args.headed))
    output(result, 0 if result.get("logged_in") else 1)


def cmd_login(args: argparse.Namespace) -> None:
    from tvp.core import login

    result = asyncio.run(
        login(
            storage_state_for(args),
            qrcode_dir=accounts.STATE_DIR / "qrcode",
            timeout=args.timeout,
            headless=not args.headed,
        )
    )
    output(result, 0 if result.get("logged_in") else 1)


def cmd_upload_video(args: argparse.Namespace) -> None:
    from tvp.core import UploadVideoRequest, upload_video, validate_image_file, validate_video_file

    request = UploadVideoRequest(
        storage_state=storage_state_for(args),
        file_path=validate_video_file(args.file),
        title=args.title,
        desc=args.desc or "",
        tags=normalize_tags(args.tags),
        publish=args.publish,
        schedule_at=parse_schedule(args.schedule_at),
        thumbnail_path=validate_image_file(args.thumbnail) if args.thumbnail else None,
        short_title=args.short_title,
        category=args.category,
        fill_only=args.fill_only,
        hold_open_seconds=args.hold_open,
        upload_timeout=args.upload_timeout,
        cover_timeout=args.cover_timeout,
        headless=not args.headed,
    )
    result = asyncio.run(upload_video(request))
    output(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Video publisher for WeChat Channels")
    parser.add_argument("--account", default="", help="named account slot; omit to use default account")
    parser.add_argument("--headed", action="store_true", help="show browser window instead of headless mode")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sub = subparsers.add_parser("list-accounts", help="list named accounts")
    sub.set_defaults(func=cmd_list_accounts)

    sub = subparsers.add_parser("add-account", help="add a named account slot")
    sub.add_argument("--slot", required=True)
    sub.add_argument("--description", default="")
    sub.set_defaults(func=cmd_add_account)

    sub = subparsers.add_parser("remove-account", help="remove a named account slot")
    sub.add_argument("--slot", required=True)
    sub.set_defaults(func=cmd_remove_account)

    sub = subparsers.add_parser("set-default-account", help="set default account slot")
    sub.add_argument("--slot", required=True)
    sub.set_defaults(func=cmd_set_default_account)

    sub = subparsers.add_parser("check-login", help="check login state")
    sub.set_defaults(func=cmd_check_login)

    sub = subparsers.add_parser("login", help="scan login qrcode and save storage state")
    sub.add_argument("--timeout", type=int, default=180)
    sub.set_defaults(func=cmd_login)

    sub = subparsers.add_parser("upload-video", help="upload a video; default action saves draft")
    sub.add_argument("--file", required=True, help="absolute video file path")
    sub.add_argument("--title", required=True)
    sub.add_argument("--desc", default="")
    sub.add_argument("--tags", nargs="*", default=[])
    sub.add_argument("--thumbnail", default="")
    sub.add_argument("--short-title", default="")
    sub.add_argument("--category", default="", help="original category, only used when declaring original")
    sub.add_argument("--schedule-at", default="", help='local time, e.g. "2026-05-27 21:30"; requires --publish')
    sub.add_argument("--publish", action="store_true", help="click publish; omit to save draft")
    sub.add_argument("--fill-only", action="store_true", help="fill the publish form and stop before saving draft/publishing")
    sub.add_argument(
        "--hold-open",
        type=int,
        default=0,
        help="seconds to keep the browser open after --fill-only; use -1 to keep it open until interrupted",
    )
    sub.add_argument("--upload-timeout", type=int, default=300, help="seconds to wait for video upload completion")
    sub.add_argument("--cover-timeout", type=int, default=60, help="seconds to wait for official cover generation before custom cover upload")
    sub.set_defaults(func=cmd_upload_video)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        output({"success": False, "error": "interrupted"}, 130)
    except Exception as exc:
        output({"success": False, "error": str(exc)}, 2)


if __name__ == "__main__":
    main()
