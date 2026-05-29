#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import csv
import json
import random
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests


COMMON_INFO_URL = (
    "https://meeting.tencent.com/wemeet-tapi/v2/meetlog/public/detail/common-record-info"
)
MINUTES_DETAIL_URL = (
    "https://meeting.tencent.com/wemeet-tapi/v2/wemeet-cloudrecording-webapi/v1/minutes/detail"
)
SHARE_URL_RE = re.compile(r"https?://meeting\.tencent\.com/(?:crm|cw)/([A-Za-z0-9]+)")
TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<date>[^|]+?)\s*\|\s*(?P<title>[^|]+?)\s*\|\s*(?P<url>https?://meeting\.tencent\.com/(?:crm|cw)/(?P<code>[A-Za-z0-9]+))\s*\|$"
)
TIME_RE = re.compile(r"^(?:\d{2}:)?\d{2}:\d{2}$")
ROW_TIME_RE = re.compile(r"\n(?:\d{2}:)?\d{2}:\d{2}\n")


class DownloadError(RuntimeError):
    pass


ERROR_REASON_BY_CODE = {
    30002: "公开链路未返回逐字稿",
    30017: "创建者已关闭转写查看和下载",
    40339: "共享未开启纪要或纪要不可见",
    91001: "录制转写导出失败",
}

FAILURE_TYPE_BY_CODE = {
    30002: "link_not_supported",
    30017: "transcript_disabled_by_owner",
    40339: "share_not_enabled",
    91001: "transcript_export_failed",
}

CHROME_REASON_BY_STATUS = {
    "ok": "Chrome 页面逐字稿抽取成功",
    "no_access": "当前登录态没有页面访问权限",
    "disabled_by_owner": "创建者已关闭转写查看和下载",
    "no_text_detected": "页面未检测到文字内容",
    "export_failed": "录制转写导出失败",
    "meeting_id_missing": "分享页未返回 meeting_id",
    "unknown": "未能从页面提取逐字稿",
}

UNSUPPORTED_FAILURE_TYPES = {
    "link_not_supported",
    "transcript_disabled_by_owner",
    "share_not_enabled",
    "permission_denied",
}


@dataclass
class Entry:
    index: int
    source: str
    batch: str
    date_text: str
    title: str
    url: str
    short_code: str


@dataclass
class ApiRecordingTarget:
    entry: Entry
    recording_index: int
    total_recordings: int
    share_id: str
    is_single: bool
    meeting_id: str
    recording_id: str
    record_name: str
    meeting_subject: str
    meeting_date_text: str
    meeting_code: str
    creator_name: str
    pwd: str
    minutes_status: Any


@dataclass
class ChromeRecordingMeta:
    sharing_id: str
    recording_id: str
    name: str
    minutes_status: int | None
    minutes_exportable: int | None


def compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def format_datetime_from_millis(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return ""


def safe_filename_text(text: str, fallback: str) -> str:
    cleaned = compact_text(text)
    cleaned = re.sub(r'[\\/:*?"<>|\r\n]+', "_", cleaned)
    cleaned = cleaned.strip(" ._")
    return cleaned[:120] or fallback


def date_prefix(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[:8]


def meeting_stem(title: str, date_text: str, fallback: str) -> str:
    safe_title = safe_filename_text(title, fallback)
    day = date_prefix(date_text)
    return f"{day}_{safe_title}" if day else safe_title


def reason_from_code(code: int | None, fallback: str = "") -> str:
    if code in ERROR_REASON_BY_CODE:
        return ERROR_REASON_BY_CODE[code]
    return compact_text(fallback) or "未知原因"


def parse_error_details(error: str) -> dict[str, Any]:
    text = compact_text(error)
    code_match = re.search(r"code=(\d+)", text)
    code = int(code_match.group(1)) if code_match else None

    message = ""
    msg_match = re.search(r"(?:msg|message)=([^,)]+)", text)
    if msg_match:
        message = compact_text(msg_match.group(1))
    if message.lower() in {"none", "null"}:
        message = ""

    status = None
    status_match = re.match(r"([a-z_]+):\s*(.+)$", text)
    if status_match and not code_match:
        status = status_match.group(1)
        message = compact_text(status_match.group(2))

    if code is not None:
        failure_type = FAILURE_TYPE_BY_CODE.get(code, "api_error")
        reason = reason_from_code(code, message)
        return {
            "error_code": code,
            "reason": reason,
            "failure_type": failure_type,
            "status": None,
            "detail": message or reason,
        }

    if status is not None:
        if status == "no_access":
            failure_type = "permission_denied"
        elif status in {"disabled_by_owner", "no_text_detected"}:
            failure_type = "link_not_supported"
        elif status == "meeting_id_missing":
            failure_type = "share_metadata_missing"
        elif status == "export_failed":
            failure_type = "transcript_export_failed"
        else:
            failure_type = "chrome_error"
        return {
            "error_code": None,
            "reason": CHROME_REASON_BY_STATUS.get(status, message or status),
            "failure_type": failure_type,
            "status": status,
            "detail": message or text,
        }

    return {
        "error_code": None,
        "reason": text or "未知原因",
        "failure_type": "unknown_error",
        "status": None,
        "detail": text or "未知原因",
    }


def build_failure_record(
    entry: Entry,
    *,
    method: str,
    error: str,
    recording_index: int | None,
    recording_id: str | None,
    record_name: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = parse_error_details(error)
    row: dict[str, Any] = {
        "index": entry.index,
        "date_text": entry.date_text,
        "title": entry.title,
        "short_code": entry.short_code,
        "url": entry.url,
        "method": method,
        "recording_index": recording_index,
        "recording_id": recording_id,
        "record_name": record_name,
        "error": compact_text(error),
        "error_code": parsed["error_code"],
        "reason": parsed["reason"],
        "failure_type": parsed["failure_type"],
        "status": parsed["status"],
        "detail": parsed["detail"],
    }
    if extra:
        row.update(extra)
    return row


def chrome_recording_failures(export_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for idx, export_result in enumerate(export_results, start=1):
        payload = export_result.get("payload") or {}
        code_raw = payload.get("code")
        try:
            code = int(code_raw)
        except Exception:  # noqa: BLE001
            code = None
        if code in {None, 0}:
            continue
        message = compact_text(payload.get("message") or payload.get("msg") or "")
        failures.append(
            {
                "recording_index": idx,
                "recording_name": export_result.get("recording_name") or f"recording{idx}",
                "recording_id": export_result.get("recording_id") or "",
                "sharing_id": export_result.get("sharing_id") or "",
                "error_code": code,
                "reason": reason_from_code(code, message),
                "detail": message or reason_from_code(code, ""),
                "failure_type": FAILURE_TYPE_BY_CODE.get(code, "api_error"),
            }
        )
    return failures


def format_failure_item(item: dict[str, Any]) -> str:
    scope = ""
    recording_index = item.get("recording_index")
    record_name = compact_text(item.get("record_name") or item.get("recording_name") or "")
    if recording_index is not None:
        scope = f"录制{recording_index}"
        if record_name and record_name not in {scope, f"recording{recording_index}"} and not record_name.startswith(scope):
            scope += f" {record_name}"
    elif item.get("method") == "api_resolve":
        scope = "链接解析"
    elif item.get("method") == "chrome":
        scope = "Chrome 页面"

    reason = compact_text(item.get("reason") or item.get("detail") or item.get("error") or "未知原因")
    code = item.get("error_code")
    if code is not None:
        reason = f"{reason} (code={code})"
    return f"{scope}: {reason}" if scope else reason


def unique_failure_items(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for failure in failures:
        nested = failure.get("recording_failures") or []
        if nested:
            for nested_item in nested:
                merged = {
                    "method": failure.get("method"),
                    "recording_index": nested_item.get("recording_index"),
                    "record_name": nested_item.get("recording_name"),
                    "recording_id": nested_item.get("recording_id"),
                    "error_code": nested_item.get("error_code"),
                    "reason": nested_item.get("reason"),
                    "detail": nested_item.get("detail"),
                    "failure_type": nested_item.get("failure_type"),
                }
                key = (
                    merged.get("recording_index"),
                    merged.get("recording_id"),
                    merged.get("error_code"),
                    merged.get("reason"),
                    merged.get("failure_type"),
                )
                if key in seen:
                    continue
                seen.add(key)
                items.append(merged)
            continue

        key = (
            failure.get("recording_index"),
            failure.get("recording_id"),
            failure.get("error_code"),
            failure.get("reason"),
            failure.get("failure_type"),
            failure.get("method"),
        )
        if key in seen:
            continue
        seen.add(key)
        items.append(failure)

    return items


def summarize_entry(
    entry: Entry,
    manifest_rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    diagnostic: dict[str, Any],
) -> dict[str, Any]:
    api_successes = {
        row["recording_index"]
        for row in manifest_rows
        if row.get("method") == "api" and row.get("recording_index") is not None
    }
    chrome_saved = any(row.get("method") == "chrome_dom" for row in manifest_rows)
    resolved_recordings = list((diagnostic.get("api") or {}).get("resolved_recordings") or [])
    chrome_recordings = list((diagnostic.get("chrome") or {}).get("recordings") or [])
    total_recordings = len(resolved_recordings) or len(chrome_recordings)

    failure_items = unique_failure_items(failures)
    failure_briefs = [format_failure_item(item) for item in failure_items]
    failure_types = {item.get("failure_type") for item in failure_items if item.get("failure_type")}

    if total_recordings:
        success_recordings = len(api_successes)
        if success_recordings == 0 and chrome_saved:
            success_recordings = 1
    else:
        success_recordings = 1 if manifest_rows else 0

    if manifest_rows and not failures:
        status = "ok"
    elif manifest_rows and failures:
        status = "partial"
    elif failure_items and failure_types and failure_types.issubset(UNSUPPORTED_FAILURE_TYPES):
        status = "unsupported"
    elif failure_items:
        status = "error"
    else:
        status = "unknown"

    if status == "ok":
        if total_recordings:
            summary_text = f"共 {total_recordings} 段录制，逐字稿均可获取"
        else:
            summary_text = "逐字稿获取成功"
    elif status == "partial":
        if total_recordings:
            summary_text = (
                f"共 {total_recordings} 段录制，成功 {success_recordings} 段，"
                f"失败 {len(failure_items)} 段；" + "；".join(failure_briefs)
            )
        else:
            summary_text = "部分结果成功；" + "；".join(failure_briefs)
    elif status == "unsupported":
        summary_text = "链接不支持完整逐字稿导出；" + "；".join(failure_briefs)
    elif status == "error":
        summary_text = "处理失败；" + "；".join(failure_briefs)
    else:
        summary_text = "未能确定链接状态"

    return {
        "index": entry.index,
        "date_text": entry.date_text,
        "title": entry.title,
        "short_code": entry.short_code,
        "url": entry.url,
        "status": status,
        "artifact_count": len(manifest_rows),
        "failure_record_count": len(failures),
        "total_recordings": total_recordings,
        "successful_recordings": success_recordings,
        "failure_items": failure_items,
        "summary": summary_text,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stable Tencent Meeting transcript downloader. "
            "It tries the public transcript API first, then falls back to "
            "the visible Google Chrome login session to extract transcript text from the page."
        )
    )
    parser.add_argument(
        "sources",
        nargs="*",
        help="Tencent Meeting share URLs, or local files that contain those URLs.",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Additional URL or file path. Can be repeated.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "tencent_meeting_transcripts_stable",
        help="Directory for transcripts, manifests, and diagnostics.",
    )
    parser.add_argument(
        "--strategy",
        choices=("auto", "api", "chrome"),
        default="auto",
        help="auto=API first then Chrome fallback, api=API only, chrome=Chrome only.",
    )
    parser.add_argument(
        "--initial-limit",
        type=int,
        default=120,
        help="Paragraph count requested on the first public transcript API page.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds for Tencent API calls.",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=3.0,
        help="Seconds to wait after opening each page in Chrome.",
    )
    parser.add_argument(
        "--codes",
        nargs="*",
        help="Optional subset of short codes to process.",
    )
    args = parser.parse_args()
    if not args.sources and not args.input:
        parser.error("Provide at least one URL or input file.")
    return args


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def short_code_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1]


def normalize_url(url: str) -> str:
    match = SHARE_URL_RE.search(url.strip())
    if not match:
        raise DownloadError(f"Not a Tencent Meeting share URL: {url}")
    return f"https://meeting.tencent.com/crm/{match.group(1)}"


def build_entries_from_text(text: str, source: str, start_index: int) -> list[Entry]:
    entries: list[Entry] = []
    batch = ""
    seen_urls: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            batch = line[3:].strip()
            continue

        table_match = TABLE_ROW_RE.match(line)
        if table_match:
            date_text = table_match.group("date").strip()
            if date_text == "日期":
                continue
            url = normalize_url(table_match.group("url").strip())
            if url in seen_urls:
                continue
            seen_urls.add(url)
            entries.append(
                Entry(
                    index=start_index + len(entries),
                    source=source,
                    batch=batch,
                    date_text=date_text,
                    title=table_match.group("title").strip(),
                    url=url,
                    short_code=short_code_from_url(url),
                )
            )
            continue

        for match in SHARE_URL_RE.finditer(line):
            url = normalize_url(match.group(0))
            if url in seen_urls:
                continue
            seen_urls.add(url)
            entries.append(
                Entry(
                    index=start_index + len(entries),
                    source=source,
                    batch=batch,
                    date_text="",
                    title="",
                    url=url,
                    short_code=short_code_from_url(url),
                )
            )
    return entries


def load_entries(raw_sources: list[str]) -> list[Entry]:
    entries: list[Entry] = []
    seen_urls: set[str] = set()

    for raw_source in raw_sources:
        candidate = Path(raw_source).expanduser()
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            source_entries = build_entries_from_text(text, str(candidate), len(entries) + 1)
            for entry in source_entries:
                if entry.url in seen_urls:
                    continue
                seen_urls.add(entry.url)
                entry.index = len(entries) + 1
                if not entry.title:
                    entry.title = entry.short_code
                entries.append(entry)
            continue

        url = normalize_url(raw_source)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        entries.append(
            Entry(
                index=len(entries) + 1,
                source="argv",
                batch="",
                date_text="",
                title=short_code_from_url(url),
                url=url,
                short_code=short_code_from_url(url),
            )
        )

    return entries


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://meeting.tencent.com/",
            "Origin": "https://meeting.tencent.com",
        }
    )
    return session


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: int = 30,
    attempts: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = session.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(1.2 * attempt)
    raise DownloadError(f"Request failed after {attempts} attempts: {url} ({last_error})")


def parse_share_meta(long_url: str) -> tuple[str, bool]:
    query = parse_qs(long_url, keep_blank_values=True)
    share_id = (query.get("id") or [""])[0]
    is_single_raw = (query.get("is-single") or ["false"])[0]
    return share_id, is_single_raw.lower() == "true"


def maybe_decode_subject(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if re.fullmatch(r"[A-Za-z0-9+/=]+", text) and len(text) % 4 == 0:
        try:
            decoded = base64.b64decode(text).decode("utf-8").strip()
            if decoded:
                return decoded
        except Exception:  # noqa: BLE001
            pass
    return text


def resolve_recordings(
    session: requests.Session,
    entry: Entry,
    *,
    timeout: int,
) -> list[ApiRecordingTarget]:
    params = {
        "pk_meeting_info_id": "",
        "sharing_id": "",
        "is_single": "false",
        "cover_image_style": "meetlog_detail_webp_1000",
        "ticket": "",
        "randstr": "",
        "pwd": "",
        "activity_uid": "",
        "lang": "zh-CN",
        "is_origin_content": "true",
        "is_cve": "true",
        "forward_cgi_path": "shares",
        "enter_from": "share",
        "short_url_code": entry.short_code,
    }
    payload = request_json(
        session,
        "GET",
        COMMON_INFO_URL,
        params=params,
        timeout=timeout,
    )
    if payload.get("code") != 0:
        raise DownloadError(
            f"Resolve share failed: code={payload.get('code')} msg={payload.get('msg') or payload.get('message')}"
        )

    data = payload.get("data") or {}
    long_url = ((data.get("short_url_info") or {}).get("long_url")) or ""
    share_id, is_single = parse_share_meta(long_url)
    meeting_info = data.get("meeting_info") or {}
    recordings = data.get("recordings") or []
    creator_name = ((data.get("record_creator") or {}).get("creator_name")) or ""
    meeting_id = str(meeting_info.get("meeting_id") or "")
    meeting_date_text = format_datetime_from_millis(meeting_info.get("start_time"))

    if not share_id:
        raise DownloadError(f"Share id missing for {entry.short_code}")
    if not meeting_id:
        raise DownloadError(f"Meeting id missing for {entry.short_code}")
    if not recordings:
        raise DownloadError(f"No recordings found for {entry.short_code}")

    targets: list[ApiRecordingTarget] = []
    for idx, recording in enumerate(recordings, start=1):
        recording_id = str(recording.get("id") or "")
        if not recording_id:
            continue
        targets.append(
            ApiRecordingTarget(
                entry=entry,
                recording_index=idx,
                total_recordings=len(recordings),
                share_id=share_id,
                is_single=is_single,
                meeting_id=meeting_id,
                recording_id=recording_id,
                record_name=str(recording.get("name") or f"recording{idx}"),
                meeting_subject=maybe_decode_subject(
                    str(meeting_info.get("origin_subject") or meeting_info.get("subject") or entry.title)
                ),
                meeting_date_text=meeting_date_text or entry.date_text,
                meeting_code=str(meeting_info.get("meeting_code") or ""),
                creator_name=creator_name,
                pwd=str(data.get("pwd") or ""),
                minutes_status=recording.get("minutes_status"),
            )
        )

    if not targets:
        raise DownloadError(f"No usable recording ids found for {entry.short_code}")
    return targets


def build_client_params() -> dict[str, str]:
    return {
        "c_token": "",
        "c_os": "web",
        "c_os_version": "1",
        "c_os_model": "web",
        "c_timestamp": str(int(time.time() * 1000)),
        "c_instance_id": "5",
        "c_nonce": uuid.uuid4().hex[:8],
        "c_app_version": "1",
        "c_lang": "zh-CN",
        "c_district": "0",
    }


def fetch_minutes_page(
    session: requests.Session,
    params: dict[str, Any],
    *,
    timeout: int,
) -> dict[str, Any]:
    payload = request_json(
        session,
        "GET",
        MINUTES_DETAIL_URL,
        params=params,
        timeout=timeout,
    )
    code = payload.get("code")
    if code != 0:
        raise DownloadError(
            f"Transcript request failed: code={code} message={payload.get('message') or payload.get('msg')}"
        )
    return payload


def fetch_full_transcript(
    session: requests.Session,
    target: ApiRecordingTarget,
    *,
    initial_limit: int,
    timeout: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    common = {
        "meeting_id": target.meeting_id,
        "recording_id": target.recording_id,
        "lang": "zh",
        "return_ori": "0",
        **build_client_params(),
    }
    first_params = {
        **common,
        "share_id": target.share_id,
        "is_single": str(target.is_single).lower(),
        "is_meetlog": "false",
        "short_url_code": target.entry.short_code,
        "limit": str(initial_limit),
        "pwd": target.pwd,
        "activity_uid": "",
        "enter_from": "share",
    }
    first_page = fetch_minutes_page(session, first_params, timeout=timeout)
    minutes = first_page.get("minutes") or {}
    all_paragraphs = list(minutes.get("paragraphs") or [])
    more = bool(first_page.get("more"))
    page_count = 1

    while more:
        if not all_paragraphs:
            break
        last_pid = all_paragraphs[-1].get("pid")
        if last_pid is None:
            break
        next_page = fetch_minutes_page(
            session,
            {
                **common,
                "pid": str(last_pid),
            },
            timeout=timeout,
        )
        next_paragraphs = list((next_page.get("minutes") or {}).get("paragraphs") or [])
        if next_paragraphs and all_paragraphs[-1].get("pid") == next_paragraphs[0].get("pid"):
            next_paragraphs = next_paragraphs[1:]
        if not next_paragraphs:
            break
        all_paragraphs.extend(next_paragraphs)
        more = bool(next_page.get("more"))
        page_count += 1

    minutes["paragraphs"] = all_paragraphs
    minutes["_page_count"] = page_count
    return first_page, all_paragraphs


def ms_to_hms(value: Any) -> str:
    try:
        total_seconds = int(float(value) / 1000)
    except Exception:  # noqa: BLE001
        return "00:00:00"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def paragraph_text(paragraph: dict[str, Any]) -> str:
    chunks: list[str] = []
    for sentence in paragraph.get("sentences") or []:
        for word in sentence.get("words") or []:
            text = word.get("text")
            if text:
                chunks.append(str(text))
    return "".join(chunks).strip()


def api_base_name(target: ApiRecordingTarget) -> str:
    stem = meeting_stem(
        target.meeting_subject or target.entry.title or target.entry.short_code,
        target.meeting_date_text or target.entry.date_text,
        target.entry.short_code,
    )
    if target.total_recordings > 1:
        stem += f"_录制{target.recording_index}"
    return stem


def chrome_base_name(entry: Entry, chrome_result: dict[str, Any]) -> str:
    stem = meeting_stem(
        chrome_result.get("title") or entry.title or entry.short_code,
        chrome_result.get("date_text") or entry.date_text,
        entry.short_code,
    )
    if len(chrome_result.get("recordings") or []) > 1:
        stem += "_页面逐字稿"
    return stem


def write_api_transcript_markdown(
    path: Path,
    target: ApiRecordingTarget,
    first_page: dict[str, Any],
    paragraphs: list[dict[str, Any]],
) -> None:
    minutes = first_page.get("minutes") or {}
    lines = [
        f"# {target.meeting_subject or target.entry.title or target.entry.short_code}",
        "",
        f"- 原始日期：{target.entry.date_text}",
        f"- 批次：{target.entry.batch}",
        f"- 原始链接：{target.entry.url}",
        f"- 短链编码：{target.entry.short_code}",
        f"- 会议主题：{target.meeting_subject}",
        f"- 会议号：{target.meeting_code or '未知'}",
        f"- 创建者：{target.creator_name or '未知'}",
        f"- 录制名称：{target.record_name}",
        f"- share_id：{target.share_id}",
        f"- meeting_id：{target.meeting_id}",
        f"- recording_id：{target.recording_id}",
        f"- 提取方式：公开 minutes/detail API",
        f"- 转录语言：{minutes.get('lang') or 'zh'}",
        f"- 段落数：{len(paragraphs)}",
        f"- 分页请求次数：{minutes.get('_page_count') or 1}",
        "",
        "## 逐字稿",
        "",
    ]

    for paragraph in paragraphs:
        text = paragraph_text(paragraph)
        if not text:
            continue
        speaker = ((paragraph.get("speaker") or {}).get("user_name")) or "未知发言人"
        ts = ms_to_hms(paragraph.get("start_time"))
        lines.append(f"### [{ts}] {speaker}")
        lines.append("")
        lines.append(text)
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


class ChromeBridge:
    def __init__(self, settle_seconds: float = 3.0) -> None:
        self.settle_seconds = settle_seconds

    @staticmethod
    def _run_applescript(script: str) -> str:
        result = subprocess.run(
            ["osascript"],
            input=script,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise DownloadError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    @staticmethod
    def _quote(text: str) -> str:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'

    def js(self, code: str) -> str:
        script = (
            'tell application "Google Chrome"\n'
            f"  execute active tab of front window javascript {self._quote(code)}\n"
            "end tell\n"
        )
        return self._run_applescript(script)

    def open_url(self, url: str, max_wait: float = 15.0) -> dict[str, Any]:
        script = (
            'tell application "Google Chrome"\n'
            "  activate\n"
            "  if (count of windows) = 0 then\n"
            "    set targetWindow to make new window\n"
            "  else\n"
            "    set targetWindow to front window\n"
            "  end if\n"
            f"  set URL of active tab of targetWindow to {self._quote(url)}\n"
            "end tell\n"
        )
        self._run_applescript(script)
        return self.wait_ready(max_wait=max_wait)

    def wait_ready(self, max_wait: float = 15.0) -> dict[str, Any]:
        deadline = time.time() + max_wait
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                raw = self.js(
                    """JSON.stringify({
                      ready: document.readyState,
                      url: location.href,
                      title: document.title,
                      body: (document.body && document.body.innerText || '').slice(0, 2000)
                    })"""
                )
                info = json.loads(raw)
                if info.get("ready") == "complete" and info.get("url"):
                    time.sleep(self.settle_seconds)
                    return info
            except Exception as exc:  # noqa: BLE001
                last_error = exc
            time.sleep(0.4)
        if last_error:
            raise DownloadError(f"Chrome page did not become ready: {last_error}")
        raise DownloadError("Chrome page did not become ready before timeout")


def page_info(bridge: ChromeBridge) -> dict[str, str]:
    raw = bridge.js(
        """JSON.stringify({
          url: location.href,
          title: document.title,
          body: (document.body && document.body.innerText || '').slice(0, 2500)
        })"""
    )
    return json.loads(raw)


def get_script_blob(bridge: ChromeBridge, attempts: int = 20) -> str:
    for _ in range(attempts):
        blob = bridge.js(
            """(function() {
              const scripts = Array.from(document.scripts).map(s => s.textContent || '');
              return scripts.find(t =>
                t.includes('pk_meeting_info_id') ||
                t.includes('meeting_id\\\\":\\\\"') ||
                t.includes('recordings\\\\":')
              ) || '';
            })()"""
        )
        if blob:
            return blob
        time.sleep(0.25)
    return ""


def decode_subject(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        return base64.b64decode(raw).decode("utf-8").strip()
    except Exception:
        return raw


def parse_script_blob(script_blob: str) -> dict[str, Any]:
    def first(pattern: str, default: str = "") -> str:
        match = re.search(pattern, script_blob)
        return match.group(1) if match else default

    subject = decode_subject(
        first(r'origin_subject\\":\\"([^\\]+?)\\"')
        or first(r'subject\\":\\"([^\\]+?)\\"')
    )
    meeting_id = first(r'meeting_id\\":\\"(\d+)\\"')
    meeting_code = first(r'meeting_code\\":\\"([^\\]+?)\\"')
    start_time = first(r'start_time\\":\\"(\d+)\\"')
    date_text = ""
    if start_time:
        try:
            date_text = datetime.fromtimestamp(int(start_time) / 1000).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            date_text = ""

    recordings: list[ChromeRecordingMeta] = []
    seen_recordings: set[str] = set()
    record_matches = re.finditer(
        r'sharing_id\\":\\"([^\\]+?)\\"[\s\S]*?id\\":\\"(\d+)\\"[\s\S]*?name\\":\\"([^\\]+?)\\"'
        r'[\s\S]*?minutes_status\\":(\d+|null)[\s\S]*?minutes_exportable\\":(\d+|null)',
        script_blob,
    )
    for match in record_matches:
        recording_id = match.group(2)
        if recording_id in seen_recordings:
            continue
        seen_recordings.add(recording_id)
        minutes_status = None if match.group(4) == "null" else int(match.group(4))
        minutes_exportable = None if match.group(5) == "null" else int(match.group(5))
        recordings.append(
            ChromeRecordingMeta(
                sharing_id=match.group(1),
                recording_id=recording_id,
                name=match.group(3),
                minutes_status=minutes_status,
                minutes_exportable=minutes_exportable,
            )
        )

    return {
        "subject": subject,
        "meeting_id": meeting_id,
        "meeting_code": meeting_code,
        "date_text": date_text,
        "recordings": recordings,
    }


def click_transcript_tab(bridge: ChromeBridge, attempts: int = 20) -> bool:
    for _ in range(attempts):
        raw = bridge.js(
            """(function() {
              const btn = [...document.querySelectorAll('button')]
                .find(x => (x.innerText || '').trim() === '逐字稿');
              if (btn) {
                btn.click();
                return JSON.stringify({ clicked: true });
              }
              return JSON.stringify({
                clicked: false,
                body: (document.body && document.body.innerText || '').slice(0, 1000)
              });
            })()"""
        )
        state = json.loads(raw)
        if state.get("clicked"):
            time.sleep(0.8)
            return True
        time.sleep(0.4)
    return False


def extract_transcript_rows(bridge: ChromeBridge, max_steps: int = 80) -> list[str]:
    bridge.js(
        """(function() {
          const list = document.querySelector('.minutes-module-list');
          window.__codexRows = [];
          window.__codexRowSet = {};
          if (list) list.scrollTop = 0;
          return 'ok';
        })()"""
    )

    last_top = -1.0
    for _ in range(max_steps):
        state = json.loads(
            bridge.js(
                """(function() {
                  const list = document.querySelector('.minutes-module-list');
                  if (!list) return JSON.stringify({ hasList: false });
                  const rows = [...document.querySelectorAll('.minutes-module-row')]
                    .map(x => (x.innerText || '').trim())
                    .filter(Boolean);
                  window.__codexRows = window.__codexRows || [];
                  window.__codexRowSet = window.__codexRowSet || {};
                  for (const row of rows) {
                    if (!window.__codexRowSet[row]) {
                      window.__codexRowSet[row] = 1;
                      window.__codexRows.push(row);
                    }
                  }
                  const before = list.scrollTop;
                  list.scrollTop = Math.min(
                    list.scrollTop + Math.floor(list.clientHeight * 0.9),
                    list.scrollHeight
                  );
                  return JSON.stringify({
                    hasList: true,
                    before: before,
                    after: list.scrollTop,
                    seen: window.__codexRows.length
                  });
                })()"""
            )
        )
        if not state.get("hasList"):
            return []
        time.sleep(0.12)
        current_top = float(state.get("after", 0))
        if current_top == last_top:
            break
        last_top = current_top

    rows = json.loads(bridge.js("JSON.stringify(window.__codexRows || [])"))
    filtered: list[str] = []
    for row in rows:
        if ROW_TIME_RE.search(row) or row.strip() == "内容由 AI 生成，仅供参考":
            filtered.append(row)
    return filtered


def parse_row(row: str) -> dict[str, str]:
    lines = [line.strip() for line in row.splitlines() if line.strip()]
    if len(lines) >= 3 and TIME_RE.match(lines[1]):
        return {
            "speaker": lines[0],
            "time": lines[1],
            "text": "\n".join(lines[2:]).strip(),
        }
    return {
        "speaker": "",
        "time": "",
        "text": row.strip(),
    }


def export_check(
    bridge: ChromeBridge,
    meeting_id: str,
    recording: ChromeRecordingMeta,
) -> dict[str, Any]:
    params = {
        "meeting_id": meeting_id,
        "recording_id": recording.recording_id,
        "lang": "zh-CN",
        "type": "txt",
        "id": recording.sharing_id,
        "pwd": "",
        "activity_uid": "",
        "minutes_version": "1",
        "from_share": "1",
        "c_app_id": "1400143280",
        "c_os_model": "web",
        "c_os": "web",
        "c_os_version": "1",
        "c_timestamp": str(int(time.time() * 1000)),
        "c_nonce": uuid.uuid4().hex[:8],
        "c_app_version": "1",
        "c_instance_id": "5",
        "rnds": uuid.uuid4().hex[:8],
        "c_district": "0",
    }
    params_js = json.dumps(params, ensure_ascii=False)
    raw = bridge.js(
        f"""(function() {{
          const params = new URLSearchParams({params_js});
          const url = '/wemeet-cloudrecording-webapi/v1/minutes/export?' + params.toString();
          const xhr = new XMLHttpRequest();
          xhr.open('GET', url, false);
          xhr.withCredentials = true;
          try {{
            xhr.send(null);
          }} catch (e) {{
            return JSON.stringify({{ error: String(e), url }});
          }}
          return JSON.stringify({{
            status: xhr.status,
            responseText: xhr.responseText || '',
            url: url
          }});
        }})()"""
    )
    result = json.loads(raw)
    response_text = result.get("responseText") or ""
    try:
        payload = json.loads(response_text) if response_text else {}
    except Exception:
        payload = {"raw": response_text}
    return {
        "recording_name": recording.name,
        "recording_id": recording.recording_id,
        "sharing_id": recording.sharing_id,
        "minutes_status": recording.minutes_status,
        "minutes_exportable": recording.minutes_exportable,
        "http_status": result.get("status"),
        "url": result.get("url"),
        "payload": payload,
    }


def classify_chrome_status(
    body_excerpt: str,
    transcript_row_count: int,
    export_results: list[dict[str, Any]],
    meeting_id: str,
) -> tuple[str, str]:
    if transcript_row_count > 0:
        return "ok", "chrome_dom_extracted"
    if "暂无访问权限" in body_excerpt:
        return "no_access", "page shows access denied"
    if "暂未检测到文字内容" in body_excerpt:
        for export_result in export_results:
            payload = export_result.get("payload") or {}
            if payload.get("code") == 30017:
                return "disabled_by_owner", str(payload.get("message") or "owner disabled transcript access")
        return "no_text_detected", "page shows no transcript text"
    for export_result in export_results:
        payload = export_result.get("payload") or {}
        if payload.get("code") == 30017:
            return "disabled_by_owner", str(payload.get("message") or "")
        if payload.get("code") == 91001:
            return "export_failed", str(payload.get("message") or "")
    if not meeting_id:
        return "meeting_id_missing", "meeting_id not exposed in page data"
    return "unknown", "no transcript rows extracted from page"


def write_chrome_transcript_markdown(
    path: Path,
    entry: Entry,
    meta: dict[str, Any],
    rows: list[dict[str, str]],
) -> None:
    lines = [
        f"# {meta.get('subject') or entry.title or entry.short_code}",
        "",
        f"- 原始链接：{entry.url}",
        f"- 页面链接：https://meeting.tencent.com/cw/{entry.short_code}",
        f"- 会议时间：{meta.get('date_text') or entry.date_text}",
        f"- meeting_id：{meta.get('meeting_id') or ''}",
        f"- meeting_code：{meta.get('meeting_code') or ''}",
        f"- 提取方式：登录态 Chrome 页面逐字稿 DOM 抽取",
        "",
        "## 逐字稿",
        "",
    ]
    for item in rows:
        if item["speaker"] and item["time"]:
            lines.append(f"### {item['time']} {item['speaker']}")
            lines.append("")
            lines.append(item["text"])
            lines.append("")
        else:
            lines.append(item["text"])
            lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def process_via_chrome(
    bridge: ChromeBridge,
    entry: Entry,
    files_dir: Path,
) -> dict[str, Any]:
    bridge.open_url(entry.url)
    clicked = click_transcript_tab(bridge)

    info = page_info(bridge)
    script_blob = get_script_blob(bridge)
    meta = parse_script_blob(script_blob)
    rows_raw = extract_transcript_rows(bridge)
    parsed_rows = [parse_row(row) for row in rows_raw]
    export_results: list[dict[str, Any]] = []
    if meta["meeting_id"] and meta["recordings"]:
        export_results = [
            export_check(bridge, meta["meeting_id"], recording)
            for recording in meta["recordings"]
        ]
    recording_failures = chrome_recording_failures(export_results)

    status, status_detail = classify_chrome_status(
        info.get("body", ""),
        len(parsed_rows),
        export_results,
        meta.get("meeting_id", ""),
    )

    result: dict[str, Any] = {
        "clicked_transcript_tab": clicked,
        "page_url": info.get("url"),
        "page_title": info.get("title"),
        "title": meta["subject"] or entry.title or info.get("title") or entry.short_code,
        "meeting_id": meta["meeting_id"],
        "meeting_code": meta["meeting_code"],
        "date_text": meta["date_text"] or entry.date_text,
        "body_excerpt": info.get("body", ""),
        "recordings": [asdict(recording) for recording in meta["recordings"]],
        "export_results": export_results,
        "recording_failures": recording_failures,
        "transcript_row_count": len(parsed_rows),
        "status": status,
        "status_detail": status_detail,
    }

    if parsed_rows:
        base = chrome_base_name(entry, result)
        transcript_json_path = files_dir / f"{base}.json"
        transcript_md_path = files_dir / f"{base}.md"
        write_json(
            transcript_json_path,
            {
                "entry": asdict(entry),
                "meta": {
                    key: value
                    for key, value in result.items()
                    if key not in {"body_excerpt", "export_results"}
                },
                "rows": parsed_rows,
            },
        )
        write_chrome_transcript_markdown(transcript_md_path, entry, meta, parsed_rows)
        result["transcript_json_path"] = str(transcript_json_path)
        result["transcript_md_path"] = str(transcript_md_path)

    return result


def save_api_result(
    files_dir: Path,
    entry: Entry,
    target: ApiRecordingTarget,
    first_page: dict[str, Any],
    paragraphs: list[dict[str, Any]],
) -> dict[str, Any]:
    base = api_base_name(target)
    md_path = files_dir / f"{base}.md"
    json_path = files_dir / f"{base}.json"
    write_api_transcript_markdown(md_path, target, first_page, paragraphs)
    write_json(
        json_path,
        {
            "entry": asdict(entry),
            "recording": {
                "recording_index": target.recording_index,
                "share_id": target.share_id,
                "is_single": target.is_single,
                "meeting_id": target.meeting_id,
                "recording_id": target.recording_id,
                "record_name": target.record_name,
                "meeting_subject": target.meeting_subject,
                "meeting_code": target.meeting_code,
                "creator_name": target.creator_name,
                "minutes_status": target.minutes_status,
            },
            "minutes": first_page.get("minutes"),
            "more": first_page.get("more"),
        },
    )
    return {
        "index": entry.index,
        "source": entry.source,
        "date_text": target.meeting_date_text or entry.date_text,
        "title": target.meeting_subject or entry.title,
        "short_code": entry.short_code,
        "source_url": entry.url,
        "method": "api",
        "scope": f"recording_{target.recording_index}",
        "recording_index": target.recording_index,
        "meeting_id": target.meeting_id,
        "recording_id": target.recording_id,
        "share_id": target.share_id,
        "paragraph_count": len(paragraphs),
        "transcript_markdown": str(md_path),
        "transcript_json": str(json_path),
        "status": "ok",
    }


def save_chrome_result(entry: Entry, chrome_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": entry.index,
        "source": entry.source,
        "date_text": chrome_result.get("date_text") or entry.date_text,
        "title": chrome_result.get("title") or entry.title or entry.short_code,
        "short_code": entry.short_code,
        "source_url": entry.url,
        "method": "chrome_dom",
        "scope": "page_visible_transcript",
        "recording_index": None,
        "meeting_id": chrome_result.get("meeting_id") or "",
        "recording_id": "",
        "share_id": "",
        "paragraph_count": chrome_result.get("transcript_row_count") or 0,
        "transcript_markdown": chrome_result.get("transcript_md_path", ""),
        "transcript_json": chrome_result.get("transcript_json_path", ""),
        "status": "ok",
    }


def process_entry(
    entry: Entry,
    *,
    session: requests.Session,
    bridge: ChromeBridge | None,
    files_dir: Path,
    diagnostics_dir: Path,
    strategy: str,
    initial_limit: int,
    timeout: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    manifest_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    diagnostic: dict[str, Any] = {
        "entry": asdict(entry),
        "api": {"resolve_error": None, "recordings": []},
        "chrome": None,
    }

    any_success = False
    had_api_failure = False

    if strategy in {"auto", "api"}:
        try:
            targets = resolve_recordings(session, entry, timeout=timeout)
            diagnostic["api"]["resolved_recordings"] = [
                {
                    "recording_index": target.recording_index,
                    "meeting_id": target.meeting_id,
                    "recording_id": target.recording_id,
                    "share_id": target.share_id,
                    "record_name": target.record_name,
                    "minutes_status": target.minutes_status,
                }
                for target in targets
            ]
        except Exception as exc:  # noqa: BLE001
            diagnostic["api"]["resolve_error"] = str(exc)
            had_api_failure = True
            failures.append(
                build_failure_record(
                    entry,
                    method="api_resolve",
                    error=str(exc),
                    recording_index=None,
                    recording_id=None,
                )
            )
            targets = []

        for target in targets:
            try:
                time.sleep(0.2 + random.random() * 0.4)
                first_page, paragraphs = fetch_full_transcript(
                    session,
                    target,
                    initial_limit=initial_limit,
                    timeout=timeout,
                )
                row = save_api_result(files_dir, entry, target, first_page, paragraphs)
                manifest_rows.append(row)
                diagnostic["api"]["recordings"].append(
                    {
                        "recording_index": target.recording_index,
                        "recording_id": target.recording_id,
                        "status": "ok",
                        "paragraph_count": len(paragraphs),
                        "transcript_markdown": row["transcript_markdown"],
                        "transcript_json": row["transcript_json"],
                    }
                )
                any_success = True
            except Exception as exc:  # noqa: BLE001
                had_api_failure = True
                diagnostic["api"]["recordings"].append(
                    {
                        "recording_index": target.recording_index,
                        "recording_id": target.recording_id,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                failures.append(
                    build_failure_record(
                        entry,
                        method="api_minutes",
                        error=str(exc),
                        recording_index=target.recording_index,
                        recording_id=target.recording_id,
                        record_name=target.record_name,
                    )
                )

    should_try_chrome = strategy == "chrome" or (
        strategy == "auto" and (not any_success or had_api_failure)
    )

    if should_try_chrome:
        if bridge is None:
            raise DownloadError("Chrome strategy requested but Chrome bridge is not available")
        try:
            chrome_result = process_via_chrome(bridge, entry, files_dir)
            diagnostic["chrome"] = chrome_result
            if chrome_result.get("transcript_md_path"):
                manifest_rows.append(save_chrome_result(entry, chrome_result))
                any_success = True
            else:
                failures.append(
                    build_failure_record(
                        entry,
                        method="chrome",
                        error=f"{chrome_result.get('status')}: {chrome_result.get('status_detail')}",
                        recording_index=None,
                        recording_id=None,
                        extra={
                            "recording_failures": chrome_result.get("recording_failures") or [],
                        },
                    )
                )
        except Exception as exc:  # noqa: BLE001
            diagnostic["chrome"] = {
                "status": "error",
                "status_detail": str(exc),
            }
            failures.append(
                build_failure_record(
                    entry,
                    method="chrome",
                    error=str(exc),
                    recording_index=None,
                    recording_id=None,
                )
            )

    diagnostic_path = diagnostics_dir / f"{entry.short_code}.json"
    write_json(diagnostic_path, diagnostic)
    diagnostic["diagnostic_path"] = str(diagnostic_path)

    for row in manifest_rows:
        row["diagnostic"] = str(diagnostic_path)
    return manifest_rows, failures, diagnostic


def write_manifest_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "index",
        "source",
        "date_text",
        "title",
        "short_code",
        "source_url",
        "method",
        "scope",
        "recording_index",
        "meeting_id",
        "recording_id",
        "share_id",
        "paragraph_count",
        "transcript_markdown",
        "transcript_json",
        "diagnostic",
        "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    entries = load_entries(list(args.sources) + list(args.input))
    if args.codes:
        selected = set(args.codes)
        entries = [entry for entry in entries if entry.short_code in selected]
    if not entries:
        print("No valid Tencent Meeting entries found.", file=sys.stderr)
        return 1

    output_dir = args.output_dir
    files_dir = output_dir / "files"
    diagnostics_dir = output_dir / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    files_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_dir.mkdir(parents=True, exist_ok=True)

    session = build_session()
    bridge = ChromeBridge(settle_seconds=args.settle_seconds) if args.strategy in {"auto", "chrome"} else None

    manifest_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    entry_summaries: list[dict[str, Any]] = []

    print(f"Found {len(entries)} entries. Output: {output_dir}")
    for entry in entries:
        print(f"[{entry.index:03d}/{len(entries):03d}] {entry.short_code} {entry.title or entry.short_code}")
        entry_manifest, entry_failures, diagnostic = process_entry(
            entry,
            session=session,
            bridge=bridge,
            files_dir=files_dir,
            diagnostics_dir=diagnostics_dir,
            strategy=args.strategy,
            initial_limit=args.initial_limit,
            timeout=args.timeout,
        )
        manifest_rows.extend(entry_manifest)
        failures.extend(entry_failures)
        diagnostics.append(diagnostic)
        entry_summary = summarize_entry(entry, entry_manifest, entry_failures, diagnostic)
        entry_summaries.append(entry_summary)
        print(
            f"  status={entry_summary['status']} saved={len(entry_manifest)} "
            f"failures={len(entry_failures)} diag={Path(diagnostic['diagnostic_path']).name}"
        )
        print(f"  reason={entry_summary['summary']}")

    manifest_path = output_dir / "manifest.json"
    manifest_csv_path = output_dir / "manifest.csv"
    failures_path = output_dir / "failures.json"
    summary_path = output_dir / "summary.json"
    write_json(manifest_path, manifest_rows)
    write_manifest_csv(manifest_csv_path, manifest_rows)
    write_json(failures_path, failures)
    write_json(
        summary_path,
        {
            "entry_count": len(entries),
            "saved_count": len(manifest_rows),
            "failure_count": len(failures),
            "strategy": args.strategy,
            "output_dir": str(output_dir),
            "manifest": str(manifest_path),
            "manifest_csv": str(manifest_csv_path),
            "failures": str(failures_path),
            "diagnostics_dir": str(diagnostics_dir),
            "status_counts": {
                status: sum(1 for item in entry_summaries if item["status"] == status)
                for status in sorted({item["status"] for item in entry_summaries})
            },
            "entry_summaries": entry_summaries,
        },
    )

    print(
        f"Completed: {len(manifest_rows)} transcripts saved, {len(failures)} failure records. "
        f"Summary: {summary_path}"
    )
    return 0 if manifest_rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
