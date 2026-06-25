from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .core import (
    default_run_dir,
    extract_contact_items,
    extract_feed_objects,
    extract_next_marker,
    normalize_contact,
    normalize_feed_object,
    response_error,
    write_json,
    write_jsonl,
)


def _base(api_base: str) -> str:
    return api_base.rstrip("/")


def _get_json(api_base: str, path: str, params: dict[str, Any] | None = None, timeout: float = 60) -> dict[str, Any]:
    query = urlencode({k: v for k, v in (params or {}).items() if v not in ("", None)})
    url = f"{_base(api_base)}{path}"
    if query:
        url = f"{url}?{query}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except URLError as exc:
        raise RuntimeError(f"local api unavailable: {url}: {exc}") from exc
    return json.loads(body)


def _unwrap(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"raw": raw}
    code = raw.get("code")
    if code in (0, "0") and isinstance(raw.get("data"), dict):
        return raw["data"]
    return raw


def diagnose(api_base: str) -> dict[str, Any]:
    last_error = ""
    for path in ("/api/channels/status", "/api/status", "/api/v1/status"):
        try:
            raw = _get_json(api_base, path, timeout=5)
            return {
                "success": True,
                "status": "ready",
                "backend": "local_api",
                "api_base": _base(api_base),
                "raw": raw,
            }
        except Exception as exc:
            last_error = str(exc)
    return {
        "success": False,
        "status": "local_api_unavailable",
        "backend": "local_api",
        "api_base": _base(api_base),
        "message": last_error,
    }


def search_accounts(api_base: str, *, keyword: str, next_marker: str = "", search_type: int = 1) -> dict[str, Any]:
    raw = _get_json(
        api_base,
        "/api/channels/contact/search",
        {"keyword": keyword, "next_marker": next_marker, "type": search_type},
    )
    response = _unwrap(raw)
    err = response_error(response)
    contacts = [normalize_contact(item) for item in extract_contact_items(response)]
    return {
        "success": not err and raw.get("code", 0) in (0, "0"),
        "status": "ok" if not err else "api_error",
        "backend": "local_api",
        "api_base": _base(api_base),
        "message": err or raw.get("message", ""),
        "keyword": keyword,
        "next_marker": extract_next_marker(response),
        "contacts": contacts,
        "count": len(contacts),
        "raw": raw,
    }


def list_feeds(
    api_base: str,
    *,
    username: str,
    next_marker: str = "",
    max_pages: int = 1,
    limit: int = 0,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    marker = next_marker
    pages: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    error = ""

    for _page_no in range(1, max_pages + 1):
        raw = _get_json(
            api_base,
            "/api/channels/contact/feed/list",
            {"username": username, "next_marker": marker},
        )
        response = _unwrap(raw)
        pages.append(raw)
        error = response_error(response)
        if raw.get("code", 0) not in (0, "0"):
            error = str(raw.get("message") or raw.get("error") or "local api returned non-zero code")
        if error:
            break
        objects = extract_feed_objects(response)
        for obj in objects:
            normalized = normalize_feed_object(obj)
            key = normalized["object_id"] or json.dumps(obj, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            items.append(normalized)
            if limit and len(items) >= limit:
                break
        marker = extract_next_marker(response)
        if limit and len(items) >= limit:
            break
        if not marker or not objects:
            break

    output_dir = out_dir or default_run_dir(username)
    for idx, page_response in enumerate(pages, start=1):
        write_json(output_dir / "raw_pages" / f"page_{idx:03d}.json", page_response)
    write_json(output_dir / "feeds.json", items)
    write_jsonl(output_dir / "feeds.jsonl", items)
    summary = {
        "success": not error,
        "status": "ok" if not error else "api_error",
        "backend": "local_api",
        "api_base": _base(api_base),
        "message": error,
        "username": username,
        "count": len(items),
        "pages": len(pages),
        "next_marker": marker,
        "out_dir": str(output_dir),
        "feeds_json": str(output_dir / "feeds.json"),
        "feeds_jsonl": str(output_dir / "feeds.jsonl"),
        "items": items,
    }
    write_json(output_dir / "summary.json", {k: v for k, v in summary.items() if k != "items"})
    return summary


def get_feed_detail(api_base: str, *, object_id: str = "", nonce_id: str = "", url: str = "") -> dict[str, Any]:
    raw = _get_json(
        api_base,
        "/api/channels/feed/profile",
        {"object_id": object_id, "nonce_id": nonce_id, "url": url},
    )
    response = _unwrap(raw)
    err = response_error(response)
    data = response.get("data") if isinstance(response.get("data"), dict) else response
    obj = data.get("object") if isinstance(data, dict) and isinstance(data.get("object"), dict) else {}
    return {
        "success": not err and raw.get("code", 0) in (0, "0"),
        "status": "ok" if not err else "api_error",
        "backend": "local_api",
        "api_base": _base(api_base),
        "message": err or raw.get("message", ""),
        "object_id": object_id,
        "nonce_id": nonce_id,
        "item": normalize_feed_object(obj) if obj else {},
        "raw": raw,
    }


def list_comments(
    api_base: str,
    *,
    object_id: str,
    nonce_id: str = "",
    comment_id: str = "",
    next_marker: str = "",
) -> dict[str, Any]:
    raw = _get_json(
        api_base,
        "/api/channels/feed/comment/list",
        {
            "object_id": object_id,
            "nonce_id": nonce_id,
            "comment_id": comment_id,
            "next_marker": next_marker,
        },
    )
    response = _unwrap(raw)
    err = response_error(response)
    return {
        "success": not err and raw.get("code", 0) in (0, "0"),
        "status": "ok" if not err else "api_error",
        "backend": "local_api",
        "api_base": _base(api_base),
        "message": err or raw.get("message", ""),
        "object_id": object_id,
        "nonce_id": nonce_id,
        "next_marker": extract_next_marker(response),
        "raw": raw,
    }
