#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://mcp.meeting.tencent.com/mcp/wemeet-open/v1"
DEFAULT_SKILL_VERSION = "v1.0.8"
DEFAULT_DOWNLOAD_REFERER = "https://meeting.tencent.com/"
DEFAULT_DOWNLOAD_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)
PROXY_ENV_KEYS = (
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "ftp_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "FTP_PROXY",
)
URL_RE = re.compile(r"https?://[^\s\"'<>，。；、）)]+")
MEDIA_SUFFIXES = {".mp4", ".m4a", ".mp3", ".wav", ".aac", ".flac", ".mov", ".mkv", ".webm"}
DOWNLOAD_HOST_HINTS = ("cos", "qcloud", "myqcloud", "tencent-cloud", "video.tencent", "meeting.tencent")


def parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("JSON value must be an object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Thin JSON-RPC bridge for the official Tencent Meeting MCP service."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TENCENT_MEETING_MCP_BASE_URL", DEFAULT_BASE_URL),
        help=f"MCP endpoint. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--skill-version",
        default=os.environ.get("TENCENT_MEETING_SKILL_VERSION", DEFAULT_SKILL_VERSION),
        help=f"X-Skill-Version header. Default: {DEFAULT_SKILL_VERSION}",
    )
    parser.add_argument(
        "--token-env",
        default="TENCENT_MEETING_TOKEN",
        help="Environment variable that holds the Tencent Meeting MCP token.",
    )
    parser.add_argument(
        "--agent",
        default=os.environ.get("TENCENT_MEETING_CLIENT_AGENT", "Codex"),
        help="Client info agent name sent to MCP tools.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("TENCENT_MEETING_CLIENT_MODEL", "GPT-5"),
        help="Client info model name sent to MCP tools.",
    )
    parser.add_argument(
        "--use-proxy",
        action="store_true",
        help="Honor proxy environment variables. Default ignores proxies so Tencent Meeting uses local network routes.",
    )

    output_parent = argparse.ArgumentParser(add_help=False)
    output_parent.add_argument(
        "--text",
        action="store_true",
        help="Print text content from MCP tool responses instead of the raw JSON-RPC envelope.",
    )
    output_parent.add_argument(
        "--output",
        type=Path,
        help="Write the response to a file instead of stdout.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "tools-list",
        parents=[output_parent],
        help="List tools exposed by the official Tencent Meeting MCP service.",
    )

    call = subparsers.add_parser(
        "call",
        parents=[output_parent],
        help="Call an MCP tool by name with a JSON arguments object.",
    )
    call.add_argument("tool_name")
    call.add_argument("--args", type=parse_json_object, default={}, help="JSON arguments object.")

    records = subparsers.add_parser(
        "records",
        parents=[output_parent],
        help="Call get_records_list.",
    )
    records.add_argument("--meeting-id")
    records.add_argument("--meeting-code")
    records.add_argument("--start-time")
    records.add_argument("--end-time")
    records.add_argument("--page-size", type=int)
    records.add_argument("--page-token")

    addresses = subparsers.add_parser(
        "record-addresses",
        parents=[output_parent],
        help="Call get_record_addresses.",
    )
    addresses.add_argument("--meeting-record-id", required=True)
    addresses.add_argument("--page-token")
    addresses.add_argument("--page-size", type=int)

    transcript = subparsers.add_parser(
        "transcript",
        parents=[output_parent],
        help="Call get_transcripts_details.",
    )
    transcript.add_argument("--record-file-id", required=True)
    transcript.add_argument("--meeting-id")
    transcript.add_argument("--pid")
    transcript.add_argument("--limit")

    paragraphs = subparsers.add_parser(
        "transcript-paragraphs",
        parents=[output_parent],
        help="Call get_transcripts_paragraphs.",
    )
    paragraphs.add_argument("--record-file-id", required=True)
    paragraphs.add_argument("--meeting-id")

    search = subparsers.add_parser(
        "search-transcript",
        parents=[output_parent],
        help="Call search_transcripts.",
    )
    search.add_argument("--record-file-id", required=True)
    search.add_argument("--text-query", required=True)
    search.add_argument("--meeting-id")

    minutes = subparsers.add_parser(
        "smart-minutes",
        parents=[output_parent],
        help="Call get_smart_minutes.",
    )
    minutes.add_argument("--record-file-id", required=True)
    minutes.add_argument("--lang", choices=("default", "zh", "en", "ja"))
    minutes.add_argument("--pwd")

    version = subparsers.add_parser(
        "check-version",
        parents=[output_parent],
        help="Call check_skill_version.",
    )
    version.add_argument("--current-version")

    timestamp = subparsers.add_parser(
        "convert-timestamp",
        parents=[output_parent],
        help="Call convert_timestamp.",
    )
    timestamp.add_argument("--parse-time-str")
    timestamp.add_argument("--parse-time-unix")
    timestamp.add_argument("--timezone")

    download_url = subparsers.add_parser(
        "download-url",
        help="Download one recording URL with proxy bypass, Tencent Meeting Referer, and browser UA.",
    )
    download_url.add_argument("url")
    download_url.add_argument("--dest", type=Path, required=True)
    download_url.add_argument("--referer", default=DEFAULT_DOWNLOAD_REFERER)
    download_url.add_argument("--user-agent", default=DEFAULT_DOWNLOAD_UA)
    download_url.add_argument("--connect-timeout", type=int, default=30)
    download_url.add_argument("--max-time", type=int, default=0, help="0 means no total timeout.")
    download_url.add_argument("--no-resume", action="store_true")
    download_url.add_argument("--dry-run", action="store_true")

    download_addresses = subparsers.add_parser(
        "download-addresses",
        help="Extract recording URLs from a get_record_addresses JSON response and download them locally.",
    )
    download_addresses.add_argument("--input", type=Path, required=True)
    download_addresses.add_argument("--output-dir", type=Path, required=True)
    download_addresses.add_argument("--all-urls", action="store_true", help="Download every URL found, not just media-looking URLs.")
    download_addresses.add_argument("--referer", default=DEFAULT_DOWNLOAD_REFERER)
    download_addresses.add_argument("--user-agent", default=DEFAULT_DOWNLOAD_UA)
    download_addresses.add_argument("--connect-timeout", type=int, default=30)
    download_addresses.add_argument("--max-time", type=int, default=0, help="0 means no total timeout.")
    download_addresses.add_argument("--no-resume", action="store_true")
    download_addresses.add_argument("--dry-run", action="store_true")

    return parser


def compact_arguments(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def client_info(args: argparse.Namespace) -> dict[str, str]:
    system = platform.system() or "Unknown"
    release = platform.release()
    machine = platform.machine()
    os_label = " ".join(part for part in (system, release, machine) if part)
    return {
        "os": os_label,
        "agent": args.agent,
        "model": args.model,
    }


def call_rpc(args: argparse.Namespace, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    token = os.environ.get(args.token_env, "")
    if not token:
        raise SystemExit(
            f"Missing {args.token_env}. Get a token from https://meeting.tencent.com/ai-skill "
            f"and export {args.token_env}=..."
        )

    body = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }
    request = urllib.request.Request(
        args.base_url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Tencent-Meeting-Token": token,
            "X-Skill-Version": args.skill_version,
        },
        method="POST",
    )
    opener = urllib.request.build_opener() if args.use_proxy else urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"MCP HTTP error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"MCP request failed: {exc}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"MCP response was not valid JSON: {payload[:500]}") from exc


def call_tool(args: argparse.Namespace, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    arguments = dict(arguments)
    arguments.setdefault("_client_info", client_info(args))
    return call_rpc(
        args,
        "tools/call",
        {
            "name": tool_name,
            "arguments": arguments,
        },
    )


def response_text(result: dict[str, Any]) -> str:
    inner = result.get("result")
    if not isinstance(inner, dict):
        return json.dumps(result, ensure_ascii=False, indent=2)
    content = inner.get("content")
    if not isinstance(content, list):
        return json.dumps(result, ensure_ascii=False, indent=2)
    texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
    return "\n".join(text for text in texts if text)


def proxy_bypass_env(use_proxy: bool) -> dict[str, str]:
    env = os.environ.copy()
    if use_proxy:
        return env
    for key in PROXY_ENV_KEYS:
        env.pop(key, None)
    env["NO_PROXY"] = "*"
    env["no_proxy"] = "*"
    return env


def safe_filename(value: str, fallback: str) -> str:
    decoded = urllib.parse.unquote(value or "")
    cleaned = re.sub(r'[\\/:*?"<>|\r\n]+', "_", decoded).strip(" ._")
    return cleaned[:160] or fallback


def filename_from_url(url: str, fallback: str) -> str:
    path_name = Path(urllib.parse.urlparse(url).path).name
    filename = safe_filename(path_name, fallback)
    if "." not in Path(filename).name:
        filename += ".bin"
    return filename


def looks_like_download_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    suffix = Path(parsed.path).suffix.lower()
    return suffix in MEDIA_SUFFIXES or any(hint in host for hint in DOWNLOAD_HOST_HINTS)


def extract_urls(value: Any) -> list[str]:
    urls: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for child in item.values():
                visit(child)
            return
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if not isinstance(item, str):
            return

        text = item.strip()
        if text.startswith(("{", "[")):
            try:
                visit(json.loads(text))
            except json.JSONDecodeError:
                pass
        for match in URL_RE.finditer(text):
            urls.append(match.group(0).rstrip(".,;，。；"))

    visit(value)
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def curl_download(args: argparse.Namespace, url: str, dest: Path) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl",
        "-q",
        "-L",
        "--fail",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "--retry-connrefused",
        "--noproxy",
        "*" if not args.use_proxy else "",
        "--connect-timeout",
        str(args.connect_timeout),
        "-e",
        args.referer,
        "-A",
        args.user_agent,
        "-o",
        str(dest),
    ]
    if args.max_time > 0:
        cmd.extend(["--max-time", str(args.max_time)])
    if not args.no_resume:
        cmd.extend(["-C", "-"])
    cmd.append(url)
    if args.use_proxy:
        cmd = [part for part in cmd if part != "--noproxy" and part != ""]

    result = {
        "url": url,
        "file": str(dest),
        "proxy_bypass": not args.use_proxy,
        "dry_run": bool(args.dry_run),
    }
    if args.dry_run:
        result["command"] = cmd
        return result

    completed = subprocess.run(cmd, env=proxy_bypass_env(args.use_proxy), check=False)
    result["returncode"] = completed.returncode
    result["bytes"] = dest.stat().st_size if dest.exists() else 0
    if completed.returncode != 0:
        result["error"] = "curl download failed"
    return result


def download_addresses(args: argparse.Namespace) -> dict[str, Any]:
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    urls = extract_urls(payload)
    if not args.all_urls:
        urls = [url for url in urls if looks_like_download_url(url)]

    downloads = []
    used_names: set[str] = set()
    for index, url in enumerate(urls, start=1):
        name = filename_from_url(url, f"tencent_record_{index}.bin")
        if name in used_names:
            stem = Path(name).stem
            suffix = Path(name).suffix or ".bin"
            name = f"{stem}_{index}{suffix}"
        used_names.add(name)
        downloads.append(curl_download(args, url, args.output_dir / name))
    return {"input": str(args.input), "count": len(downloads), "downloads": downloads}


def emit(args: argparse.Namespace, result: dict[str, Any]) -> None:
    content = response_text(result) if getattr(args, "text", False) else json.dumps(result, ensure_ascii=False, indent=2)
    output = getattr(args, "output", None)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content + "\n", encoding="utf-8")
        print(str(output))
        return
    print(content)


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "tools-list":
        return call_rpc(args, "tools/list")
    if args.command == "call":
        return call_tool(args, args.tool_name, args.args)
    if args.command == "records":
        return call_tool(
            args,
            "get_records_list",
            compact_arguments(
                {
                    "meeting_id": args.meeting_id,
                    "meeting_code": args.meeting_code,
                    "start_time": args.start_time,
                    "end_time": args.end_time,
                    "page_size": args.page_size,
                    "page_token": args.page_token,
                }
            ),
        )
    if args.command == "record-addresses":
        return call_tool(
            args,
            "get_record_addresses",
            compact_arguments(
                {
                    "meeting_record_id": args.meeting_record_id,
                    "page_size": args.page_size,
                    "page_token": args.page_token,
                }
            ),
        )
    if args.command == "transcript":
        return call_tool(
            args,
            "get_transcripts_details",
            compact_arguments(
                {
                    "record_file_id": args.record_file_id,
                    "meeting_id": args.meeting_id,
                    "pid": args.pid,
                    "limit": args.limit,
                }
            ),
        )
    if args.command == "transcript-paragraphs":
        return call_tool(
            args,
            "get_transcripts_paragraphs",
            compact_arguments(
                {
                    "record_file_id": args.record_file_id,
                    "meeting_id": args.meeting_id,
                }
            ),
        )
    if args.command == "search-transcript":
        return call_tool(
            args,
            "search_transcripts",
            compact_arguments(
                {
                    "record_file_id": args.record_file_id,
                    "text": args.text_query,
                    "meeting_id": args.meeting_id,
                }
            ),
        )
    if args.command == "smart-minutes":
        return call_tool(
            args,
            "get_smart_minutes",
            compact_arguments(
                {
                    "record_file_id": args.record_file_id,
                    "lang": args.lang,
                    "pwd": args.pwd,
                }
            ),
        )
    if args.command == "check-version":
        return call_tool(
            args,
            "check_skill_version",
            compact_arguments({"current_version": args.current_version}),
        )
    if args.command == "convert-timestamp":
        return call_tool(
            args,
            "convert_timestamp",
            compact_arguments(
                {
                    "parse_time_str": args.parse_time_str,
                    "parse_time_unix": args.parse_time_unix,
                    "timezone": args.timezone,
                }
            ),
        )
    if args.command == "download-url":
        return {"count": 1, "downloads": [curl_download(args, args.url, args.dest)]}
    if args.command == "download-addresses":
        return download_addresses(args)
    raise SystemExit(f"Unsupported command: {args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = dispatch(args)
    emit(args, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
