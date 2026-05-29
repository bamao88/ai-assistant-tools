#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import csv
import json
import re
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
DOWNLOAD_RECORD_URL = (
    "https://meeting.tencent.com/wemeet-cloudrecording-webapi/v1/download/record"
)
SHARE_URL_RE = re.compile(r"https?://meeting\.tencent\.com/(?:crm|cw)/([A-Za-z0-9]+)")
TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<date>[^|]+?)\s*\|\s*(?P<title>[^|]+?)\s*\|\s*(?P<url>https?://meeting\.tencent\.com/(?:crm|cw)/(?P<code>[A-Za-z0-9]+))\s*\|$"
)


class DownloadError(RuntimeError):
    pass


VIDEO_TYPE_CHOICES = ("video_main", "video_stream_1", "video_stream_2", "all")
VIDEO_KIND_LABELS = {
    "video_main": "主视频",
    "video_stream_1": "共享屏幕",
    "video_stream_2": "发言人视角",
    "audio": "音频",
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
class RecordingTarget:
    entry: Entry
    recording_index: int
    total_recordings: int
    page_share_id: str
    meeting_id: str
    meeting_code: str
    meeting_subject: str
    meeting_date_text: str
    record_name: str
    recording_id: str
    recording_share_id: str
    size_bytes: int
    sharing_pwd: str
    allow_download: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Batch download Tencent Meeting recording videos from share links. "
            "Uses the public share metadata API plus the stable download endpoint."
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
        default=Path.cwd() / "tencent_meeting_videos",
        help="Directory for videos, manifests, and diagnostics.",
    )
    parser.add_argument(
        "--codes",
        nargs="*",
        help="Optional subset of short codes to process.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Resolve download URLs and write manifests without downloading media files.",
    )
    parser.add_argument(
        "--include-audio",
        action="store_true",
        help="Download audio files when the endpoint returns them.",
    )
    parser.add_argument(
        "--video-type",
        "--video-types",
        action="append",
        dest="video_types",
        choices=VIDEO_TYPE_CHOICES,
        default=None,
        help="Video variants to download. Default: video_main. Use all to include every video stream.",
    )
    args = parser.parse_args()
    if not args.video_types:
        args.video_types = ["video_main"]
    return args


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_url(url: str) -> str:
    match = SHARE_URL_RE.search(url.strip())
    if not match:
        raise DownloadError(f"Not a Tencent Meeting share URL: {url}")
    return f"https://meeting.tencent.com/crm/{match.group(1)}"


def short_code_from_url(url: str) -> str:
    return urlparse(url).path.rstrip("/").split("/")[-1]


def load_entries(raw_sources: list[str]) -> list[Entry]:
    entries: list[Entry] = []
    seen_urls: set[str] = set()

    def add_entry(source: str, batch: str, date_text: str, title: str, url: str) -> None:
        normalized = normalize_url(url)
        if normalized in seen_urls:
            return
        seen_urls.add(normalized)
        entries.append(
            Entry(
                index=len(entries) + 1,
                source=source,
                batch=batch,
                date_text=date_text,
                title=title or short_code_from_url(normalized),
                url=normalized,
                short_code=short_code_from_url(normalized),
            )
        )

    for raw_source in raw_sources:
        candidate = Path(raw_source).expanduser()
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            batch = ""
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
                    add_entry(
                        str(candidate),
                        batch,
                        date_text,
                        table_match.group("title").strip(),
                        table_match.group("url").strip(),
                    )
                    continue
                for match in SHARE_URL_RE.finditer(line):
                    add_entry(str(candidate), batch, "", "", match.group(0))
            continue

        add_entry("argv", "", "", "", raw_source)

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
    timeout: int,
    stream: bool = False,
) -> Any:
    response = session.request(method=method, url=url, params=params, timeout=timeout, stream=stream)
    response.raise_for_status()
    if stream:
        return response
    return response.json()


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


def format_datetime_from_millis(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return ""


def compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


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


def recording_suffix(target: RecordingTarget) -> str:
    if target.total_recordings <= 1:
        return ""
    return f"_录制{target.recording_index}"


def kind_suffix(kind: str) -> str:
    label = VIDEO_KIND_LABELS.get(kind, kind)
    return f"_{safe_filename_text(label, kind)}"


def parse_share_id(long_url: str) -> str:
    raw = (long_url or "").strip()
    if not raw:
        return ""
    if "?" in raw:
        raw = raw.split("?", 1)[1]
    return (parse_qs(raw, keep_blank_values=True).get("id") or [""])[0]


def resolve_entry(
    session: requests.Session,
    entry: Entry,
    *,
    timeout: int,
) -> tuple[dict[str, Any], list[RecordingTarget]]:
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
    payload = request_json(session, "GET", COMMON_INFO_URL, params=params, timeout=timeout)
    if payload.get("code") != 0:
        raise DownloadError(
            f"Resolve share failed: code={payload.get('code')} msg={payload.get('msg') or payload.get('message')}"
        )

    data = payload.get("data") or {}
    meeting_info = data.get("meeting_info") or {}
    page_share_id = parse_share_id(((data.get("short_url_info") or {}).get("long_url")) or "")
    meeting_subject = maybe_decode_subject(
        str(meeting_info.get("origin_subject") or meeting_info.get("subject") or entry.title)
    )
    meeting_date_text = format_datetime_from_millis(meeting_info.get("start_time"))
    recordings = list(data.get("recordings") or [])
    if not page_share_id:
        raise DownloadError(f"Share id missing for {entry.short_code}")

    targets: list[RecordingTarget] = []
    for idx, recording in enumerate(recordings, start=1):
        recording_id = str(recording.get("id") or "")
        if not recording_id:
            continue
        targets.append(
            RecordingTarget(
                entry=entry,
                recording_index=idx,
                total_recordings=len(recordings),
                page_share_id=page_share_id,
                meeting_id=str(meeting_info.get("meeting_id") or ""),
                meeting_code=str(meeting_info.get("meeting_code") or ""),
                meeting_subject=meeting_subject,
                meeting_date_text=meeting_date_text or entry.date_text,
                record_name=str(recording.get("name") or f"recording{idx}"),
                recording_id=recording_id,
                recording_share_id=str(recording.get("sharing_id") or ""),
                size_bytes=int(recording.get("size") or 0),
                sharing_pwd=str(data.get("pwd") or data.get("sharing_pwd") or ""),
                allow_download=bool(data.get("allow_download")),
            )
        )

    if not targets:
        raise DownloadError(f"No recordings found for {entry.short_code}")
    return data, targets


def build_download_params(target: RecordingTarget) -> dict[str, str]:
    return {
        "id": target.recording_share_id,
        "source": "shares",
        "activity_uid": "",
        "tk": "",
        "sharing_id": target.page_share_id,
        "from_share": "1",
        "need_multi_stream": "1",
        "password": target.sharing_pwd,
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


def resolve_video_payload(
    session: requests.Session,
    target: RecordingTarget,
    *,
    timeout: int,
) -> dict[str, Any]:
    payload = request_json(
        session,
        "GET",
        DOWNLOAD_RECORD_URL,
        params=build_download_params(target),
        timeout=timeout,
    )
    if payload.get("code") != 0:
        raise DownloadError(
            f"Download info failed: code={payload.get('code')} message={payload.get('message') or payload.get('msg')}"
        )
    return payload


def remote_basename(url: str, fallback: str) -> str:
    name = Path(urlparse(url).path).name
    return name or fallback


def download_file(
    session: requests.Session,
    url: str,
    destination: Path,
    *,
    timeout: int,
) -> int:
    if destination.exists() and destination.stat().st_size > 0:
        return destination.stat().st_size

    response = request_json(session, "GET", url, timeout=timeout, stream=True)
    assert isinstance(response, requests.Response)
    destination.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    with response:
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                total_bytes += len(chunk)
    return total_bytes


def build_local_name(stem: str, kind: str, url: str, *, include_kind: bool) -> str:
    remote_name = remote_basename(url, stem)
    remote_path = Path(remote_name)
    suffix = "".join(remote_path.suffixes) or ".bin"
    if include_kind:
        return f"{stem}{kind_suffix(kind)}{suffix}"
    return f"{stem}{suffix}"


def process_recording(
    session: requests.Session,
    target: RecordingTarget,
    files_dir: Path,
    *,
    timeout: int,
    metadata_only: bool,
    include_audio: bool,
    video_types: list[str],
) -> list[dict[str, Any]]:
    payload = resolve_video_payload(session, target, timeout=timeout)
    data = payload.get("data") or {}
    stem = meeting_stem(
        target.meeting_subject or target.entry.title or target.entry.short_code,
        target.meeting_date_text or target.entry.date_text,
        target.entry.short_code,
    ) + recording_suffix(target)

    requested_types = set(video_types)
    allow_all_videos = "all" in requested_types
    candidates: list[dict[str, Any]] = []

    main_url = payload.get("url") or ""
    if not main_url and isinstance(data.get("urls"), list) and data["urls"]:
        main_url = str((data["urls"][0] or {}).get("url") or "")
    if main_url:
        candidates.append(
            {
                "kind": "video_main",
                "url": main_url,
            }
        )

    for stream in data.get("multi_stream_recordings") or []:
        stream_url = str(stream.get("url") or "")
        if not stream_url:
            continue
        candidates.append(
            {
                "kind": f"video_stream_{stream.get('stream_type') or 'unknown'}",
                "url": stream_url,
            }
        )

    downloads = [
        item
        for item in candidates
        if allow_all_videos or item["kind"] in requested_types
    ]

    if include_audio:
        audio_url = payload.get("audio_url") or ""
        if not audio_url and isinstance(data.get("urls"), list) and data["urls"]:
            audio_url = str((data["urls"][0] or {}).get("audio_url") or "")
        if audio_url:
            downloads.append(
                {
                    "kind": "audio",
                    "url": audio_url,
                }
            )

    if not downloads:
        wanted = ", ".join(video_types)
        raise DownloadError(f"Download payload does not contain requested media URLs: {wanted}")

    include_kind = len(downloads) > 1 or any(item["kind"] != "video_main" for item in downloads)

    rows: list[dict[str, Any]] = []
    for item in downloads:
        filename = build_local_name(stem, item["kind"], item["url"], include_kind=include_kind)
        path = files_dir / filename
        downloaded_bytes = 0
        if not metadata_only:
            downloaded_bytes = download_file(session, item["url"], path, timeout=timeout)
        rows.append(
            {
                "index": target.entry.index,
                "source": target.entry.source,
                "date_text": target.meeting_date_text or target.entry.date_text,
                "title": target.meeting_subject or target.entry.title,
                "short_code": target.entry.short_code,
                "source_url": target.entry.url,
                "meeting_id": target.meeting_id,
                "meeting_code": target.meeting_code,
                "recording_index": target.recording_index,
                "recording_id": target.recording_id,
                "recording_name": target.record_name,
                "page_share_id": target.page_share_id,
                "method": "download_record",
                "kind": item["kind"],
                "filename": filename,
                "remote_url": item["url"],
                "local_path": "" if metadata_only else str(path),
                "downloaded_bytes": downloaded_bytes,
                "recording_size_bytes": target.size_bytes,
                "status": "resolved" if metadata_only else "ok",
            }
        )
    return rows


def write_manifest_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "index",
        "source",
        "date_text",
        "title",
        "short_code",
        "source_url",
        "meeting_id",
        "meeting_code",
        "recording_index",
        "recording_id",
        "recording_name",
        "page_share_id",
        "method",
        "kind",
        "filename",
        "remote_url",
        "local_path",
        "downloaded_bytes",
        "recording_size_bytes",
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
    manifest_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    print(f"Found {len(entries)} entries. Output: {output_dir}")
    for entry in entries:
        print(f"[{entry.index:03d}/{len(entries):03d}] {entry.short_code} {entry.title or entry.short_code}")
        diagnostic: dict[str, Any] = {"entry": asdict(entry)}
        try:
            data, targets = resolve_entry(session, entry, timeout=args.timeout)
            diagnostic["common_info"] = data
            diagnostic["targets"] = [asdict(target) for target in targets]
        except Exception as exc:  # noqa: BLE001
            diagnostic["error"] = str(exc)
            failures.append(
                {
                    "index": entry.index,
                    "date_text": entry.date_text,
                    "title": entry.title,
                    "short_code": entry.short_code,
                    "url": entry.url,
                    "recording_index": None,
                    "recording_id": None,
                    "error": str(exc),
                }
            )
            write_json(diagnostics_dir / f"{entry.short_code}.json", diagnostic)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        entry_rows = 0
        for target in targets:
            try:
                rows = process_recording(
                    session,
                    target,
                    files_dir,
                    timeout=args.timeout,
                    metadata_only=args.metadata_only,
                    include_audio=args.include_audio,
                    video_types=args.video_types,
                )
                manifest_rows.extend(rows)
                diagnostic.setdefault("downloads", []).extend(rows)
                entry_rows += len(rows)
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    {
                        "index": entry.index,
                        "date_text": entry.date_text,
                        "title": target.meeting_subject or entry.title,
                        "short_code": entry.short_code,
                        "url": entry.url,
                        "recording_index": target.recording_index,
                        "recording_id": target.recording_id,
                        "error": str(exc),
                    }
                )
                diagnostic.setdefault("recording_errors", []).append(
                    {
                        "recording_index": target.recording_index,
                        "recording_id": target.recording_id,
                        "error": str(exc),
                    }
                )

        write_json(diagnostics_dir / f"{entry.short_code}.json", diagnostic)
        print(f"  saved={entry_rows} failures={len(diagnostic.get('recording_errors', []))}")

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
            "metadata_only": args.metadata_only,
            "include_audio": args.include_audio,
            "video_types": args.video_types,
            "output_dir": str(output_dir),
            "manifest": str(manifest_path),
            "manifest_csv": str(manifest_csv_path),
            "failures": str(failures_path),
            "diagnostics_dir": str(diagnostics_dir),
            "total_downloaded_bytes": sum(int(row.get("downloaded_bytes") or 0) for row in manifest_rows),
        },
    )

    print(
        f"Completed: {len(manifest_rows)} media files processed, {len(failures)} failures. "
        f"Summary: {summary_path}"
    )
    return 0 if manifest_rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
