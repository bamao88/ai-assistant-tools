from __future__ import annotations

import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def tools_root() -> Path:
    return Path(__file__).resolve().parents[4]


TVP_SCRIPTS = tools_root() / "engines" / "tencent-video-publish" / "scripts"
if str(TVP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TVP_SCRIPTS))

from patchright.async_api import async_playwright  # noqa: E402
from tvp import accounts as tvp_accounts  # noqa: E402
from tvp.core import context_kwargs, harden_context, launch_kwargs  # noqa: E402


DEFAULT_BOOT_URLS = [
    "https://channels.weixin.qq.com/web/pages/feed",
    "https://channels.weixin.qq.com/web/pages/search",
    "https://channels.weixin.qq.com/platform",
]

DATA_DIR = tools_root() / "var" / "data" / "wechat-channels-fetch"
WECHAT_WINDOWS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    "MicroMessenger/3.9.12.17(0x63090c33) WindowsWechat(0x63090c33) XWEB/11931"
)

API_STATUS_JS = """() => {
  const api = window.WXU && window.WXU.API;
  const api2 = window.WXU && window.WXU.API2;
  return {
    href: location.href,
    title: document.title || "",
    has_wxu: !!window.WXU,
    has_api: !!api,
    has_api2: !!api2,
    finder_search: !!(api2 && typeof api2.finderSearch === "function"),
    finder_user_page: !!(api && typeof api.finderUserPage === "function"),
    finder_get_comment_detail: !!(api && typeof api.finderGetCommentDetail === "function"),
    finder_get_comment_list: !!(api && typeof api.finderGetCommentList === "function"),
    wx_username_present: !!window.__wx_username,
    login_url: location.href.indexOf("/login") >= 0,
    support_update_url: location.href.indexOf("support.weixin.qq.com/update") >= 0
  };
}"""

WAIT_FOR_API_JS = """() => {
  const api = window.WXU && window.WXU.API;
  const api2 = window.WXU && window.WXU.API2;
  return !!(
    (api2 && typeof api2.finderSearch === "function") ||
    (api && typeof api.finderUserPage === "function") ||
    (api && typeof api.finderGetCommentDetail === "function") ||
    (api && typeof api.finderGetCommentList === "function")
  );
}"""


class ChannelsFetchError(RuntimeError):
    def __init__(self, status: str, message: str, *, diagnostics: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.diagnostics = diagnostics or {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "success": False,
            "status": self.status,
            "message": str(self),
            "diagnostics": self.diagnostics,
        }


@dataclass(frozen=True)
class BrowserOptions:
    account: str = ""
    headless: bool = True
    timeout_ms: int = 45000
    api_timeout_ms: int = 15000
    init_url: str = ""
    user_agent: str = WECHAT_WINDOWS_UA

    @property
    def storage_state(self) -> Path:
        return tvp_accounts.account_state_path(self.account or None)

    @property
    def boot_urls(self) -> list[str]:
        if self.init_url:
            return [self.init_url]
        return DEFAULT_BOOT_URLS


def account_payload(account: str = "") -> dict[str, Any]:
    state = tvp_accounts.account_state_path(account or None)
    return {
        "slot": account or tvp_accounts.load_config().get("default") or "default",
        "storage_state": str(state),
        "auth_summary": storage_auth_summary(state),
        **tvp_accounts.storage_state_summary(state),
    }


def storage_auth_summary(state: Path) -> dict[str, Any]:
    if not state.exists():
        return {"exists": False}
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"exists": True, "valid_json": False}
    cookies = data.get("cookies") if isinstance(data, dict) else []
    origins = data.get("origins") if isinstance(data, dict) else []
    cookie_names = sorted({str(cookie.get("name") or "") for cookie in cookies if isinstance(cookie, dict)})
    local_lengths: dict[str, int] = {}
    for origin in origins if isinstance(origins, list) else []:
        if not isinstance(origin, dict):
            continue
        if origin.get("origin") != "https://channels.weixin.qq.com":
            continue
        for item in origin.get("localStorage") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            if name in {"finder_login_token", "finder_uin", "finder_username"}:
                local_lengths[name] = len(str(item.get("value") or ""))
    return {
        "exists": True,
        "valid_json": True,
        "cookie_names": cookie_names,
        "local_storage_lengths": local_lengths,
        "has_finder_login_token": bool(local_lengths.get("finder_login_token")),
        "has_finder_uin": bool(local_lengths.get("finder_uin")),
        "has_finder_username": bool(local_lengths.get("finder_username")),
    }


def ensure_storage_state(options: BrowserOptions) -> None:
    state = options.storage_state
    if not state.exists():
        raise ChannelsFetchError(
            "missing_storage_state",
            f"missing storage state: {state}",
            diagnostics={"storage_state": str(state)},
        )
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ChannelsFetchError(
            "invalid_storage_state",
            f"invalid storage state JSON: {state}",
            diagnostics={"storage_state": str(state), "error": str(exc)},
        ) from exc
    if not isinstance(data, dict):
        raise ChannelsFetchError(
            "invalid_storage_state",
            f"invalid storage state payload: {state}",
            diagnostics={"storage_state": str(state)},
        )


async def _api_status(page) -> dict[str, Any]:
    try:
        status = await page.evaluate(API_STATUS_JS)
    except Exception as exc:
        return {"evaluate_error": str(exc), "href": getattr(page, "url", "")}
    return dict(status or {})


async def _open_ready_page(context, options: BrowserOptions):
    diagnostics: list[dict[str, Any]] = []
    page = await context.new_page()
    for url in options.boot_urls:
        page_diag: dict[str, Any] = {"url": url}
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=options.timeout_ms)
            try:
                await page.wait_for_function(WAIT_FOR_API_JS, timeout=options.api_timeout_ms)
            except Exception as exc:
                page_diag["api_wait_error"] = str(exc)
            page_diag.update(await _api_status(page))
            diagnostics.append(page_diag)
            if any(
                page_diag.get(key)
                for key in (
                    "finder_search",
                    "finder_user_page",
                    "finder_get_comment_detail",
                    "finder_get_comment_list",
                )
            ):
                return page, diagnostics
        except Exception as exc:
            page_diag["error"] = str(exc)
            diagnostics.append(page_diag)
    raise ChannelsFetchError(
        "api_unavailable",
        "WeChat Channels page API is not initialized. Refresh login state or try --headed/--init-url.",
        diagnostics={"pages": diagnostics, "account": account_payload(options.account)},
    )


async def _with_page(options: BrowserOptions, action):
    ensure_storage_state(options)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**launch_kwargs(headless=options.headless))
        kwargs = context_kwargs(str(options.storage_state))
        if options.user_agent:
            kwargs["user_agent"] = options.user_agent
        context = await browser.new_context(**kwargs)
        context = await harden_context(context)
        try:
            page, diagnostics = await _open_ready_page(context, options)
            return await action(page, diagnostics)
        finally:
            await context.close()
            await browser.close()


async def diagnose(options: BrowserOptions) -> dict[str, Any]:
    async def action(page, diagnostics):
        return {
            "success": True,
            "status": "ready",
            "account": account_payload(options.account),
            "api": await _api_status(page),
            "diagnostics": {"pages": diagnostics},
        }

    try:
        return await _with_page(options, action)
    except ChannelsFetchError as exc:
        payload = exc.to_payload()
        payload["account"] = account_payload(options.account)
        return payload


SEARCH_ACCOUNTS_JS = """async ({keyword, type, nextMarker}) => {
  const safeDecode = (value) => {
    if (!value) return "";
    try { return decodeURIComponent(value); } catch (err) { return String(value); }
  };
  if (!window.WXU || !window.WXU.API2 || typeof window.WXU.API2.finderSearch !== "function") {
    throw new Error("finderSearch is not available");
  }
  const scene = Number(type) === 3 ? 19 : 13;
  const payload = {
    query: keyword,
    scene,
    requestId: String(Date.now()),
    lastBuffer: safeDecode(nextMarker),
    lastBuff: safeDecode(nextMarker)
  };
  const response = await window.WXU.API2.finderSearch(payload);
  return {...response, payload};
}"""

LIST_FEEDS_JS = """async ({username, nextMarker}) => {
  const safeDecode = (value) => {
    if (!value) return "";
    try { return decodeURIComponent(value); } catch (err) { return String(value); }
  };
  if (!window.WXU || !window.WXU.API || typeof window.WXU.API.finderUserPage !== "function") {
    throw new Error("finderUserPage is not available");
  }
  const payload = {
    username,
    finderUsername: window.__wx_username || "",
    lastBuffer: safeDecode(nextMarker),
    needFansCount: 0,
    objectId: "0"
  };
  const response = await window.WXU.API.finderUserPage(payload);
  return {...response, payload};
}"""

GET_DETAIL_JS = """async ({objectId, nonceId, url}) => {
  if (!window.WXU || !window.WXU.API || typeof window.WXU.API.finderGetCommentDetail !== "function") {
    throw new Error("finderGetCommentDetail is not available");
  }
  const rawId = objectId ? String(objectId) : "";
  const payload = {
    needObject: 1,
    lastBuffer: "",
    scene: 146,
    direction: 2,
    identityScene: 2,
    pullScene: 6,
    objectid: rawId.indexOf("_") >= 0 ? rawId.split("_")[0] : rawId,
    objectNonceId: nonceId || "",
    encrypted_objectid: ""
  };
  if (url && !rawId) {
    payload.url = url;
  }
  const response = await window.WXU.API.finderGetCommentDetail(payload);
  return {...response, payload};
}"""

LIST_COMMENTS_JS = """async ({objectId, nonceId, commentId, nextMarker}) => {
  const safeDecode = (value) => {
    if (!value) return undefined;
    try { return decodeURIComponent(value); } catch (err) { return String(value); }
  };
  if (!window.WXU || !window.WXU.API || typeof window.WXU.API.finderGetCommentList !== "function") {
    throw new Error("finderGetCommentList is not available");
  }
  const payload = commentId ? {
    direction: 2,
    identityScene: 2,
    objectId,
    rootCommentId: commentId,
    lastBuffer: safeDecode(nextMarker)
  } : {
    finderBasereq: {
      scene: 140,
      ctxInfo: {
        clientReportBuff: '{"entranceId":"1002"}'
      },
      objectBaseInfos: []
    },
    objectId,
    objectNonceId: nonceId,
    direction: 2,
    identityScene: 2,
    lastBuffer: safeDecode(nextMarker),
    enterSessionId: String(Date.now())
  };
  const response = await window.WXU.API.finderGetCommentList(payload);
  return {...response, payload};
}"""


def response_data(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    return data if isinstance(data, dict) else {}


def base_response_ret(response: dict[str, Any]) -> int | None:
    data = response_data(response)
    base = data.get("BaseResponse") or data.get("baseResponse") or response.get("BaseResponse")
    if not isinstance(base, dict):
        return None
    for key in ("Ret", "ret", "errCode", "ErrCode"):
        if key in base:
            try:
                return int(base[key])
            except (TypeError, ValueError):
                return None
    return None


def response_error(response: dict[str, Any]) -> str:
    ret = base_response_ret(response)
    if ret not in (None, 0):
        return f"WeChat API returned Ret={ret}"
    for key in ("errCode", "err_code", "code"):
        if key in response:
            try:
                code = int(response[key])
            except (TypeError, ValueError):
                continue
            if code not in (0,):
                return str(response.get("errMsg") or response.get("message") or f"API returned {key}={code}")
    return ""


def extract_next_marker(response: dict[str, Any]) -> str:
    data = response_data(response)
    for container in (data, response):
        for key in ("lastBuffer", "lastBuff", "nextMarker", "next_marker", "last_buffer"):
            value = container.get(key) if isinstance(container, dict) else None
            if value:
                return str(value)
    return ""


def extract_feed_objects(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response_data(response)
    objects = data.get("objectList") or data.get("object") or response.get("objectList") or response.get("object") or []
    if not isinstance(objects, list):
        return []
    return [item for item in objects if isinstance(item, dict)]


def extract_contact_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response_data(response)
    items = data.get("infoList") or data.get("objectList") or data.get("object") or []
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def normalize_contact(item: dict[str, Any]) -> dict[str, Any]:
    contact = item.get("contact") if isinstance(item.get("contact"), dict) else item
    return {
        "username": str(contact.get("username") or contact.get("finderUsername") or ""),
        "nickname": contact.get("nickname") or item.get("nickname") or "",
        "avatar": contact.get("headUrl") or contact.get("headImgUrl") or item.get("headUrl") or "",
        "signature": contact.get("signature") or item.get("signature") or "",
        "raw": item,
    }


def _num(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_number(*values: Any) -> int | None:
    for value in values:
        number = _num(value)
        if number is not None:
            return number
    return None


def normalize_feed_object(obj: dict[str, Any]) -> dict[str, Any]:
    desc = obj.get("objectDesc") if isinstance(obj.get("objectDesc"), dict) else {}
    contact = obj.get("contact") if isinstance(obj.get("contact"), dict) else {}
    media = desc.get("media") if isinstance(desc.get("media"), list) else []
    first_media = media[0] if media and isinstance(media[0], dict) else {}
    return {
        "object_id": str(obj.get("id") or obj.get("objectId") or ""),
        "nonce_id": str(obj.get("objectNonceId") or obj.get("objectNonceID") or ""),
        "description": desc.get("description") or obj.get("description") or "",
        "media_type": desc.get("mediaType") or obj.get("mediaType"),
        "nickname": obj.get("nickname") or contact.get("nickname") or "",
        "username": contact.get("username") or obj.get("username") or "",
        "publish_time": _first_number(
            obj.get("createtime"),
            obj.get("createTime"),
            obj.get("create_time"),
            desc.get("timestamp"),
        ),
        "like_count": _first_number(obj.get("likeCount"), obj.get("like_count"), desc.get("likeCount")),
        "fav_count": _first_number(obj.get("favCount"), obj.get("fav_count"), desc.get("favCount")),
        "comment_count": _first_number(
            obj.get("commentCount"),
            obj.get("comment_count"),
            desc.get("commentCount"),
        ),
        "forward_count": _first_number(
            obj.get("forwardCount"),
            obj.get("forward_count"),
            desc.get("forwardCount"),
        ),
        "cover_url": first_media.get("coverUrl") or first_media.get("thumbUrl") or first_media.get("url") or "",
        "media_url": first_media.get("url") or first_media.get("urlToken") or "",
        "raw": obj,
    }


def slug(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z._-]+", "_", value.strip())
    return cleaned.strip("._") or "wechat_channels"


def default_run_dir(username: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / f"{slug(username)}_{timestamp}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


async def search_accounts(
    options: BrowserOptions,
    *,
    keyword: str,
    search_type: int = 1,
    next_marker: str = "",
) -> dict[str, Any]:
    async def action(page, diagnostics):
        response = await page.evaluate(
            SEARCH_ACCOUNTS_JS,
            {"keyword": keyword, "type": search_type, "nextMarker": next_marker},
        )
        err = response_error(response)
        contacts = [normalize_contact(item) for item in extract_contact_items(response)]
        return {
            "success": not err,
            "status": "ok" if not err else "api_error",
            "message": err,
            "keyword": keyword,
            "next_marker": extract_next_marker(response),
            "contacts": contacts,
            "count": len(contacts),
            "raw": response,
            "diagnostics": {"pages": diagnostics},
        }

    return await _with_page(options, action)


async def list_feeds(
    options: BrowserOptions,
    *,
    username: str,
    next_marker: str = "",
    max_pages: int = 1,
    limit: int = 0,
    delay_seconds: float = 0.8,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    async def action(page, diagnostics):
        marker = next_marker
        pages: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        error = ""
        for page_no in range(1, max_pages + 1):
            response = await page.evaluate(LIST_FEEDS_JS, {"username": username, "nextMarker": marker})
            pages.append(response)
            error = response_error(response)
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
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        output_dir = out_dir or default_run_dir(username)
        for idx, page_response in enumerate(pages, start=1):
            write_json(output_dir / "raw_pages" / f"page_{idx:03d}.json", page_response)
        write_json(output_dir / "feeds.json", items)
        write_jsonl(output_dir / "feeds.jsonl", items)
        summary = {
            "success": not error,
            "status": "ok" if not error else "api_error",
            "message": error,
            "username": username,
            "count": len(items),
            "pages": len(pages),
            "next_marker": marker,
            "out_dir": str(output_dir),
            "feeds_json": str(output_dir / "feeds.json"),
            "feeds_jsonl": str(output_dir / "feeds.jsonl"),
            "items": items,
            "diagnostics": {"pages": diagnostics},
        }
        write_json(output_dir / "summary.json", {k: v for k, v in summary.items() if k != "items"})
        return summary

    return await _with_page(options, action)


async def get_feed_detail(
    options: BrowserOptions,
    *,
    object_id: str,
    nonce_id: str = "",
    url: str = "",
) -> dict[str, Any]:
    async def action(page, diagnostics):
        response = await page.evaluate(
            GET_DETAIL_JS,
            {"objectId": object_id, "nonceId": nonce_id, "url": url},
        )
        err = response_error(response)
        data = response_data(response)
        obj = data.get("object") if isinstance(data.get("object"), dict) else {}
        return {
            "success": not err,
            "status": "ok" if not err else "api_error",
            "message": err,
            "object_id": object_id,
            "nonce_id": nonce_id,
            "item": normalize_feed_object(obj) if obj else {},
            "raw": response,
            "diagnostics": {"pages": diagnostics},
        }

    return await _with_page(options, action)


async def list_comments(
    options: BrowserOptions,
    *,
    object_id: str,
    nonce_id: str = "",
    comment_id: str = "",
    next_marker: str = "",
) -> dict[str, Any]:
    async def action(page, diagnostics):
        response = await page.evaluate(
            LIST_COMMENTS_JS,
            {
                "objectId": object_id,
                "nonceId": nonce_id,
                "commentId": comment_id,
                "nextMarker": next_marker,
            },
        )
        err = response_error(response)
        return {
            "success": not err,
            "status": "ok" if not err else "api_error",
            "message": err,
            "object_id": object_id,
            "nonce_id": nonce_id,
            "next_marker": extract_next_marker(response),
            "raw": response,
            "diagnostics": {"pages": diagnostics},
        }

    return await _with_page(options, action)
