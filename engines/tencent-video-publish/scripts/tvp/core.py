from __future__ import annotations

import asyncio
import base64
from http.cookies import CookieError, SimpleCookie
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from patchright.async_api import Page, async_playwright

from tvp import accounts


LOGIN_URL = "https://channels.weixin.qq.com"
UPLOAD_URL = "https://channels.weixin.qq.com/platform/post/create"
MANAGE_URL = "https://channels.weixin.qq.com/platform/post/list"

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".flv", ".wmv"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MIN_SCHEDULE_LEAD_TIME = timedelta(hours=2)
MAX_PAGE_DIAG_ITEMS = 80
PAGE_DIAG_RELEVANT_HOSTS = (
    "channels.weixin.qq.com",
    "finderpre.video.qq.com",
    "finder.video.qq.com",
    "wxapp.tc.qq.com",
    "store.mp.video.tencent-cloud.com",
    "res.wx.qq.com",
    "wxqcloud.qq.com",
)
PAGE_DIAG_RELEVANT_TOKENS = (
    "upload",
    "video",
    "finder",
    "qcloud",
    "tencent",
    "cos",
    "vod",
    "weixin",
    "wxqcloud",
)
COOKIE_ATTRIBUTE_NAMES = {
    "domain",
    "expires",
    "httponly",
    "max-age",
    "path",
    "samesite",
    "secure",
}
STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-component-update",
    "--disable-sync",
    "--window-size=1280,900",
]
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
"""


@dataclass
class UploadVideoRequest:
    storage_state: Path
    file_path: Path
    title: str
    desc: str = ""
    tags: list[str] | None = None
    publish: bool = False
    schedule_at: datetime | None = None
    thumbnail_path: Path | None = None
    short_title: str | None = None
    category: str | None = None
    fill_only: bool = False
    hold_open_seconds: int = 0
    upload_timeout: int = 300
    cover_timeout: int = 60
    headless: bool = True


def launch_kwargs(headless: bool) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"headless": headless, "args": STEALTH_ARGS}
    chrome_path = ""
    if chrome_path:
        kwargs["executable_path"] = chrome_path
    else:
        kwargs["channel"] = "chrome"
    return kwargs


def context_kwargs(storage_state: str | None = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "viewport": {"width": 1280, "height": 900},
        "bypass_csp": True,
    }
    if storage_state:
        kwargs["storage_state"] = storage_state
    return kwargs


def profile_dir_for_storage_state(storage_state: Path) -> Path:
    return storage_state.parent / "chrome-profile"


def credential_metadata(storage_state: Path, credential_source: str = "") -> dict[str, Any]:
    return {
        "storage_state": str(storage_state),
        "profile_dir": str(profile_dir_for_storage_state(storage_state)),
        "profile_ignored": False,
        "auth_primary": "chrome_profile",
        "storage_state_role": "backup",
        "credential_source": credential_source,
    }


async def launch_profile_context(playwright, storage_state: Path, *, headless: bool):
    profile_dir = profile_dir_for_storage_state(storage_state)
    profile_dir.mkdir(parents=True, exist_ok=True)
    kwargs = {
        **launch_kwargs(headless=headless),
        **context_kwargs(),
    }
    return await playwright.chromium.launch_persistent_context(str(profile_dir), **kwargs)


async def harden_context(context):
    # Keep this small. A broader stealth shim breaks WeChat's login iframe.
    await context.add_init_script(STEALTH_JS)
    return context


def append_limited(items: list[dict], item: dict, limit: int = MAX_PAGE_DIAG_ITEMS) -> None:
    items.append(item)
    if len(items) > limit:
        del items[: len(items) - limit]


def relevant_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        haystack = f"{parsed.netloc}{parsed.path}".lower()
    except Exception:
        haystack = url.lower()
    return any(host in url for host in PAGE_DIAG_RELEVANT_HOSTS) or any(
        token in haystack for token in PAGE_DIAG_RELEVANT_TOKENS
    )


def tail_text(text: str, max_chars: int = 2000) -> str:
    text = text.strip()
    return text[-max_chars:] if len(text) > max_chars else text


def attach_page_diagnostics(page: Page) -> dict[str, list[dict]]:
    diag: dict[str, list[dict]] = {
        "console": [],
        "page_errors": [],
        "request_failed": [],
        "http_errors": [],
        "requests": [],
        "hosts": [],
    }

    def record_host(url: str) -> None:
        try:
            host = urlparse(url).netloc
        except Exception:
            host = ""
        if host and host not in diag["hosts"]:
            append_limited(diag["hosts"], host, limit=200)

    def on_console(msg) -> None:
        try:
            text = str(getattr(msg, "text", ""))[:1200]
            msg_type = str(getattr(msg, "type", ""))
            location = getattr(msg, "location", None)
            if msg_type in {"error", "warning"} or any(token in text for token in ("cover", "Cover", "封面", "KeyFrame", "Frame", "upload", "Upload")):
                append_limited(diag["console"], {"type": msg_type, "text": text, "location": location})
        except Exception as exc:
            append_limited(diag["console"], {"error": str(exc)})

    def on_page_error(exc) -> None:
        append_limited(diag["page_errors"], {"error": str(exc)[:2000]})

    def on_request_failed(request) -> None:
        try:
            url = str(getattr(request, "url", ""))
            if not relevant_url(url):
                return
            record_host(url)
            failure = getattr(request, "failure", "")
            if callable(failure):
                failure = failure()
            append_limited(
                diag["request_failed"],
                {"method": str(getattr(request, "method", "")), "url": url[:1000], "failure": str(failure)[:1000]},
            )
        except Exception as exc:
            append_limited(diag["request_failed"], {"error": str(exc)})

    def on_response(response) -> None:
        try:
            status = int(getattr(response, "status", 0) or 0)
            url = str(getattr(response, "url", ""))
            if relevant_url(url):
                record_host(url)
            if status >= 400 and relevant_url(url):
                append_limited(diag["http_errors"], {"status": status, "url": url[:1000]})
        except Exception as exc:
            append_limited(diag["http_errors"], {"error": str(exc)})

    def on_request(request) -> None:
        try:
            url = str(getattr(request, "url", ""))
            if not relevant_url(url):
                return
            record_host(url)
            append_limited(
                diag["requests"],
                {"method": str(getattr(request, "method", "")), "url": url[:1000]},
                limit=120,
            )
        except Exception as exc:
            append_limited(diag["requests"], {"error": str(exc)})

    page.on("request", on_request)
    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)
    page.on("response", on_response)
    return diag


def storage_state_json_is_valid(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and isinstance(data.get("cookies", []), list)


def parse_cookie_string(cookie_string: str) -> list[dict[str, Any]]:
    cookie_string = cookie_string.strip()
    if not cookie_string:
        raise ValueError("cookie string is empty")

    parsed = SimpleCookie()
    try:
        parsed.load(cookie_string)
    except CookieError as exc:
        raise ValueError(f"invalid cookie string: {exc}") from exc

    cookies: list[dict[str, Any]] = []
    for name, morsel in parsed.items():
        if name.lower() in COOKIE_ATTRIBUTE_NAMES:
            continue
        value = morsel.value
        if not name or value is None:
            continue
        cookies.append(
            {
                "name": name,
                "value": value,
                "url": LOGIN_URL,
                "secure": True,
                "httpOnly": name.lower() == "sessionid",
                "sameSite": "Lax",
            }
        )

    if not cookies:
        raise ValueError("no cookies parsed from cookie string")
    return cookies


def restore_backup_if_needed(storage_state: Path) -> Path | None:
    if storage_state_json_is_valid(storage_state):
        return None
    for backup in reversed(accounts.storage_state_backups(storage_state)):
        if not storage_state_json_is_valid(backup):
            continue
        storage_state.parent.mkdir(parents=True, exist_ok=True)
        storage_state.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        return backup
    return None


async def save_storage_state(context, storage_state: Path) -> dict:
    storage_state.parent.mkdir(parents=True, exist_ok=True)
    state = await context.storage_state()
    encoded = json.dumps(state, ensure_ascii=False, indent=2)

    if storage_state.exists():
        try:
            if storage_state.read_text(encoding="utf-8") == encoded:
                return {"saved": False, "backup": "", "reason": "unchanged"}
        except OSError:
            pass

    backup = accounts.backup_storage_state(storage_state)
    tmp_path = storage_state.with_name(f"{storage_state.name}.tmp")
    tmp_path.write_text(encoded, encoding="utf-8")
    if not storage_state_json_is_valid(tmp_path):
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"refusing to write invalid storage state: {storage_state}")
    tmp_path.replace(storage_state)
    return {"saved": True, "backup": str(backup) if backup else "", "reason": "updated"}


async def best_effort_save_storage_state(context, storage_state: Path) -> dict:
    try:
        return await save_storage_state(context, storage_state)
    except Exception as exc:
        return {"saved": False, "backup": "", "reason": "best_effort_failed", "error": str(exc)}


def read_storage_state_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


async def seed_context_from_storage_state(context, storage_state: Path) -> None:
    state = read_storage_state_json(storage_state)
    cookies = state.get("cookies") or []
    if cookies:
        await context.add_cookies(cookies)

    for origin_state in state.get("origins") or []:
        origin = str(origin_state.get("origin") or "")
        local_storage = origin_state.get("localStorage") or []
        if not origin.startswith(("http://", "https://")) or not local_storage:
            continue
        page = await context.new_page()
        try:
            try:
                await page.goto(origin, wait_until="domcontentloaded", timeout=30000)
            except Exception as exc:
                if "Timeout" not in str(exc):
                    raise
            await page.evaluate(
                """items => {
                    for (const item of items) {
                        if (item && typeof item.name === "string") {
                            localStorage.setItem(item.name, String(item.value ?? ""));
                        }
                    }
                }""",
                local_storage,
            )
        finally:
            await page.close()


async def probe_login_context(
    context,
    storage_state: Path,
    *,
    save_on_success: bool,
    timeout_ms: int,
) -> tuple[bool, str, dict | None]:
    page = await context.new_page()
    try:
        await goto_upload_page_for_probe(page)
        logged_in = await wait_for_login_completed(page, timeout_ms=timeout_ms)
        save_result = await save_storage_state(context, storage_state) if logged_in and save_on_success else None
        return logged_in, page.url, save_result
    finally:
        await page.close()


async def probe_storage_state_file(
    playwright,
    storage_state: Path,
    *,
    headless: bool,
    save_target: Path,
    save_on_success: bool,
    timeout_ms: int,
) -> tuple[bool, str, dict | None]:
    browser = await playwright.chromium.launch(**launch_kwargs(headless=headless))
    try:
        context = await browser.new_context(**context_kwargs(str(storage_state)))
        context = await harden_context(context)
        try:
            return await probe_login_context(
                context,
                save_target,
                save_on_success=save_on_success,
                timeout_ms=timeout_ms,
            )
        finally:
            await context.close()
    finally:
        await browser.close()


async def seed_profile_from_storage_state(
    playwright,
    storage_state: Path,
    *,
    headless: bool,
    save_on_success: bool,
    timeout_ms: int = 15000,
) -> dict[str, Any]:
    if not storage_state_json_is_valid(storage_state):
        return {"seeded": False, "logged_in": False, "error": "invalid_storage_state"}

    context = await launch_profile_context(playwright, storage_state, headless=headless)
    context = await harden_context(context)
    try:
        await seed_context_from_storage_state(context, storage_state)
        logged_in, current_url, save_result = await probe_login_context(
            context,
            storage_state,
            save_on_success=save_on_success,
            timeout_ms=timeout_ms,
        )
        return {
            "seeded": True,
            "logged_in": logged_in,
            "current_url": current_url,
            "storage_state_saved": bool(save_result and save_result.get("saved")),
            "storage_state_backup": save_result.get("backup", "") if save_result else "",
        }
    except Exception as exc:
        return {"seeded": False, "logged_in": False, "error": str(exc)}
    finally:
        await context.close()


async def open_authenticated_context(
    playwright,
    storage_state: Path,
    *,
    headless: bool,
    credential_source: str,
) -> tuple[Any, Any | None, str]:
    if credential_source.startswith("chrome_profile"):
        context = await launch_profile_context(playwright, storage_state, headless=headless)
        context = await harden_context(context)
        return context, None, "chrome_profile"

    browser = await playwright.chromium.launch(**launch_kwargs(headless=headless))
    context = await browser.new_context(**context_kwargs(str(storage_state)))
    context = await harden_context(context)
    return context, browser, "storage_state"


def candidate_storage_state_path(storage_state: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return storage_state.with_name(f"{storage_state.name}.candidate_{timestamp}")


def promote_storage_state_candidate(candidate: Path, storage_state: Path) -> dict:
    if candidate == storage_state:
        raise RuntimeError("candidate storage state must not be the formal storage state")
    if not storage_state_json_is_valid(candidate):
        raise RuntimeError(f"refusing to promote invalid candidate storage state: {candidate}")

    storage_state.parent.mkdir(parents=True, exist_ok=True)
    backup = accounts.backup_storage_state(storage_state)
    tmp_path = storage_state.with_name(f"{storage_state.name}.promote_tmp")
    tmp_path.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
    if not storage_state_json_is_valid(tmp_path):
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"refusing to write invalid storage state: {storage_state}")
    tmp_path.replace(storage_state)
    candidate.unlink(missing_ok=True)
    return {
        "promoted": True,
        "backup": str(backup) if backup else "",
        "candidate_removed": True,
    }


async def save_manual_cookie_candidate_state(
    playwright,
    candidate_path: Path,
    cookies: list[dict[str, Any]],
    *,
    headless: bool,
) -> dict:
    browser = await playwright.chromium.launch(**launch_kwargs(headless=headless))
    try:
        context = await browser.new_context(**context_kwargs())
        context = await harden_context(context)
        try:
            await context.add_cookies(cookies)
            return await save_storage_state(context, candidate_path)
        finally:
            await context.close()
    finally:
        await browser.close()


async def goto_upload_page_for_probe(page: Page) -> str:
    try:
        await page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=60000)
        return ""
    except Exception as exc:
        if "Timeout" not in str(exc):
            raise
        await page.wait_for_timeout(3000)
        return str(exc)


async def import_cookies(
    storage_state: Path,
    cookie_string: str,
    *,
    headless: bool = True,
    verify: bool = True,
    clear_existing: bool = True,
) -> dict:
    parsed_cookies = parse_cookie_string(cookie_string)
    storage_state.parent.mkdir(parents=True, exist_ok=True)
    profile_dir = profile_dir_for_storage_state(storage_state)
    candidate_path = candidate_storage_state_path(storage_state)

    async with async_playwright() as playwright:
        save_result = await save_manual_cookie_candidate_state(
            playwright,
            candidate_path,
            parsed_cookies,
            headless=headless,
        )

    if not verify:
        return {
            "success": True,
            "imported": False,
            "promoted": False,
            "logged_in": None,
            "status": "cookie_candidate_saved_unverified",
            "cookie_count": len(parsed_cookies),
            "cookie_names": [cookie["name"] for cookie in parsed_cookies],
            "storage_state": str(storage_state),
            "candidate_state": str(candidate_path),
            "profile_dir": str(profile_dir),
            "profile_ignored": False,
            "auth_primary": "chrome_profile",
            "storage_state_role": "backup",
            "credential_source": "manual_cookie_candidate",
            "cleared_existing": False,
            "clear_existing_requested": clear_existing,
            "storage_state_saved": False,
            "candidate_state_saved": save_result.get("saved", False),
            "storage_state_backup": "",
            "current_url": "",
            "verify_error": "",
        }

    async with async_playwright() as playwright:
        try:
            logged_in, verify_url, _ = await probe_storage_state_file(
                playwright,
                candidate_path,
                headless=headless,
                save_target=candidate_path,
                save_on_success=False,
                timeout_ms=15000,
            )
            verify_error = ""
        except Exception as exc:
            logged_in = False
            verify_url = ""
            verify_error = str(exc)

        if not logged_in:
            return {
                "success": True,
                "imported": False,
                "promoted": False,
                "logged_in": False,
                "status": "cookie_candidate_invalid",
                "cookie_count": len(parsed_cookies),
                "cookie_names": [cookie["name"] for cookie in parsed_cookies],
                "storage_state": str(storage_state),
                "candidate_state": str(candidate_path),
                "profile_dir": str(profile_dir),
                "profile_ignored": False,
                "auth_primary": "chrome_profile",
                "storage_state_role": "backup",
                "credential_source": "manual_cookie_candidate",
                "cleared_existing": False,
                "clear_existing_requested": clear_existing,
                "storage_state_saved": False,
                "candidate_state_saved": save_result.get("saved", False),
                "storage_state_backup": "",
                "current_url": verify_url,
                "verify_error": verify_error or "cookie_candidate_invalid",
                "verify_status": "cookie_candidate_invalid",
            }

        promote_result = promote_storage_state_candidate(candidate_path, storage_state)
        seed_result = await seed_profile_from_storage_state(
            playwright,
            storage_state,
            headless=headless,
            save_on_success=True,
        )
    return {
        "success": True,
        "imported": True,
        "promoted": True,
        "logged_in": True,
        "status": "logged_in",
        "cookie_count": len(parsed_cookies),
        "cookie_names": [cookie["name"] for cookie in parsed_cookies],
        "storage_state": str(storage_state),
        "candidate_state": str(candidate_path),
        "profile_dir": str(profile_dir),
        "profile_ignored": False,
        "auth_primary": "chrome_profile",
        "storage_state_role": "backup",
        "credential_source": "chrome_profile" if seed_result.get("logged_in") else "manual_cookie_import",
        "cleared_existing": False,
        "clear_existing_requested": clear_existing,
        "storage_state_saved": True,
        "candidate_state_saved": save_result.get("saved", False),
        "storage_state_backup": promote_result.get("backup", ""),
        "profile_seeded": bool(seed_result.get("seeded")),
        "profile_logged_in": bool(seed_result.get("logged_in")),
        "profile_seed_error": seed_result.get("error", ""),
        "current_url": seed_result.get("current_url") or verify_url,
        "verify_error": "",
        "verify_status": "logged_in",
    }


def validate_video_file(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"video file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"video path is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(f"unsupported video extension: {path.suffix}")
    return path


def validate_image_file(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"image file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"image path is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(f"unsupported image extension: {path.suffix}")
    return path


def validate_schedule(schedule_at: datetime | None) -> datetime | None:
    if schedule_at is None:
        return None
    now = datetime.now(tz=schedule_at.tzinfo) if schedule_at.tzinfo else datetime.now()
    if schedule_at <= now:
        raise ValueError("schedule_at must be in the future")
    if schedule_at <= now + MIN_SCHEDULE_LEAD_TIME:
        raise ValueError("schedule_at must be more than 2 hours from now")
    return schedule_at


def format_short_title(title: str) -> str:
    allowed_special_chars = "《》“”:+?%°"
    filtered = [char if char.isalnum() or char in allowed_special_chars else " " if char == "," else "" for char in title]
    formatted = "".join(filtered)
    if len(formatted) > 16:
        return formatted[:16]
    if len(formatted) < 6:
        return formatted + " " * (6 - len(formatted))
    return formatted


def save_data_url_image(data_url: str, output_path: Path) -> Path:
    if not data_url.startswith("data:image/"):
        raise ValueError("qrcode src is not a data:image URL")
    header, encoded = data_url.split(",", 1)
    if ";base64" not in header:
        raise ValueError("qrcode image is not base64 encoded")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(encoded))
    return output_path


async def extract_qrcode_src(page: Page) -> str:
    try:
        iframe_locator = page.frame_locator('[src*="login-for-iframe"]')
        qr_code_img = iframe_locator.locator("div#app img.qrcode").first
        await qr_code_img.wait_for(state="visible", timeout=30000)
        src = await qr_code_img.get_attribute("src")
        if src and src.startswith("data:image/"):
            return src
    except Exception:
        pass

    for selector in (
        "div.login-qrcode-wrap img.qrcode",
        "div.qrcode-wrap img.qrcode",
        "img.qrcode",
        'img[src^="data:image/"]',
    ):
        qr_code_img = page.locator(selector).first
        try:
            if await qr_code_img.count() and await qr_code_img.is_visible():
                src = await qr_code_img.get_attribute("src")
                if src and src.startswith("data:image/"):
                    return src
        except Exception:
            continue
    raise RuntimeError("login qrcode not found")


async def has_publish_marker(page: Page) -> bool:
    markers = (
        page.locator('div:has-text("发表视频")').first,
        page.locator('button:has-text("发表")').first,
        page.locator('button:has-text("保存草稿")').first,
    )
    for marker in markers:
        try:
            if await marker.count() and await marker.is_visible():
                return True
        except Exception:
            continue
    return False


async def has_login_marker(page: Page) -> bool:
    markers = (
        page.locator("div.login-qrcode-wrap").first,
        page.locator("div.qrcode-wrap").first,
        page.locator("img.qrcode").first,
        page.locator('span:has-text("微信扫码登录 视频号助手")').first,
    )
    for marker in markers:
        try:
            if await marker.count() and await marker.is_visible():
                return True
        except Exception:
            continue
    return False


async def is_login_completed(page: Page) -> bool:
    if await has_publish_marker(page):
        return True
    if await has_login_marker(page):
        return False
    if page.url.startswith(UPLOAD_URL):
        return await has_upload_form_marker(page)
    return page.url.startswith(MANAGE_URL)


async def wait_for_login_completed(page: Page, timeout_ms: int = 15000) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    stable_candidate_since: float | None = None
    while asyncio.get_event_loop().time() < deadline:
        if await has_publish_marker(page):
            return True
        if await has_login_marker(page):
            return False
        if page.url.startswith(UPLOAD_URL):
            if await has_upload_form_marker(page):
                return True
            stable_candidate_since = None
        elif page.url.startswith(MANAGE_URL):
            now = asyncio.get_event_loop().time()
            if stable_candidate_since is None:
                stable_candidate_since = now
            elif now - stable_candidate_since >= 3:
                return True
        else:
            stable_candidate_since = None
        await page.wait_for_timeout(500)
    return await is_login_completed(page)


async def verify_login_session(page: Page, timeout_ms: int = 15000) -> bool:
    """Validate QR login on a page that requires an authenticated session."""
    try:
        await page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=60000)
    except Exception as exc:
        if "Timeout" not in str(exc):
            raise
        await page.wait_for_timeout(3000)
    await page.wait_for_timeout(1000)
    return await wait_for_login_completed(page, timeout_ms=timeout_ms)


async def is_qrcode_expired(page: Page) -> bool:
    for selector in (
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ):
        tip = page.locator(selector).first
        try:
            if await tip.count() and await tip.is_visible():
                return True
        except Exception:
            continue
    return False


async def refresh_qrcode(page: Page) -> None:
    for selector in (
        "div.login-qrcode-wrap div.mask.show div.refresh-wrap",
        "div.login-qrcode-wrap div.mask.show .refresh-wrap",
        "div.login-qrcode-wrap div.refresh-wrap",
    ):
        refresh = page.locator(selector).first
        try:
            if await refresh.count() and await refresh.is_visible():
                await refresh.click()
                return
        except Exception:
            continue
    raise RuntimeError("qrcode refresh control not found")


async def check_login(storage_state: Path, headless: bool = True, *, save_on_success: bool = True) -> dict:
    recovered_from_backup = restore_backup_if_needed(storage_state)
    profile_error = ""
    profile_url = ""

    async with async_playwright() as playwright:
        try:
            profile_context = await launch_profile_context(playwright, storage_state, headless=headless)
            profile_context = await harden_context(profile_context)
            try:
                logged_in, profile_url, save_result = await probe_login_context(
                    profile_context,
                    storage_state,
                    save_on_success=save_on_success,
                    timeout_ms=15000,
                )
            finally:
                await profile_context.close()
            if logged_in:
                return {
                    "success": True,
                    "logged_in": True,
                    "status": "logged_in",
                    **credential_metadata(storage_state, "chrome_profile"),
                    "recovered_from_backup": str(recovered_from_backup) if recovered_from_backup else "",
                    "storage_state_saved": bool(save_result and save_result.get("saved")),
                    "storage_state_backup": save_result.get("backup", "") if save_result else "",
                    "current_url": profile_url,
                }
        except Exception as exc:
            profile_error = str(exc)

        if not storage_state.exists():
            return {
                "success": True,
                "logged_in": False,
                "status": "missing_storage_state",
                **credential_metadata(storage_state),
                "profile_error": profile_error,
                "profile_current_url": profile_url,
                "latest_backup": str(accounts.latest_storage_state_backup(storage_state) or ""),
            }
        if not storage_state_json_is_valid(storage_state):
            return {
                "success": True,
                "logged_in": False,
                "status": "invalid_storage_state",
                **credential_metadata(storage_state),
                "profile_error": profile_error,
                "profile_current_url": profile_url,
                "recovered_from_backup": str(recovered_from_backup) if recovered_from_backup else "",
                "latest_backup": str(accounts.latest_storage_state_backup(storage_state) or ""),
            }

        try:
            logged_in, current_url, save_result = await probe_storage_state_file(
                playwright,
                storage_state,
                headless=headless,
                save_target=storage_state,
                save_on_success=save_on_success,
                timeout_ms=15000,
            )
            storage_error = ""
        except Exception as exc:
            logged_in = False
            current_url = ""
            save_result = None
            storage_error = str(exc)

        if logged_in:
            seed_result: dict[str, Any] = {}
            if save_on_success:
                seed_result = await seed_profile_from_storage_state(
                    playwright,
                    storage_state,
                    headless=headless,
                    save_on_success=True,
                )
            if seed_result.get("logged_in"):
                return {
                    "success": True,
                    "logged_in": True,
                    "status": "logged_in",
                    **credential_metadata(storage_state, "chrome_profile_seeded_from_storage_state"),
                    "recovered_from_backup": str(recovered_from_backup) if recovered_from_backup else "",
                    "storage_state_saved": bool(seed_result.get("storage_state_saved")),
                    "storage_state_backup": seed_result.get("storage_state_backup", ""),
                    "current_url": seed_result.get("current_url", current_url),
                    "profile_seeded": True,
                }
            return {
                "success": True,
                "logged_in": True,
                "status": "logged_in",
                **credential_metadata(storage_state, "storage_state_fallback"),
                "recovered_from_backup": str(recovered_from_backup) if recovered_from_backup else "",
                "storage_state_saved": bool(save_result and save_result.get("saved")),
                "storage_state_backup": save_result.get("backup", "") if save_result else "",
                "profile_seeded": bool(seed_result.get("seeded")),
                "profile_seed_error": seed_result.get("error", ""),
                "current_url": current_url,
            }

        for backup in reversed(accounts.storage_state_backups(storage_state)[-3:]):
            if recovered_from_backup and backup == recovered_from_backup:
                continue
            if not storage_state_json_is_valid(backup):
                continue
            try:
                backup_logged_in, backup_url, _ = await probe_storage_state_file(
                    playwright,
                    backup,
                    headless=headless,
                    save_target=storage_state,
                    save_on_success=False,
                    timeout_ms=6000,
                )
            except Exception:
                continue
            if backup_logged_in:
                backup_result = accounts.backup_storage_state(storage_state)
                storage_state.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
                seed_result = {}
                if save_on_success:
                    seed_result = await seed_profile_from_storage_state(
                        playwright,
                        storage_state,
                        headless=headless,
                        save_on_success=True,
                    )
                if seed_result.get("logged_in"):
                    return {
                        "success": True,
                        "logged_in": True,
                        "status": "logged_in",
                        **credential_metadata(storage_state, "chrome_profile_seeded_from_backup_storage_state"),
                        "recovered_from_backup": str(backup),
                        "storage_state_saved": bool(seed_result.get("storage_state_saved")),
                        "storage_state_backup": seed_result.get("storage_state_backup", ""),
                        "current_url": seed_result.get("current_url", backup_url),
                        "profile_seeded": True,
                    }
                return {
                    "success": True,
                    "logged_in": True,
                    "status": "logged_in",
                    **credential_metadata(storage_state, "backup_storage_state_fallback"),
                    "recovered_from_backup": str(backup),
                    "storage_state_saved": False,
                    "storage_state_backup": str(backup_result) if backup_result else "",
                    "profile_seeded": bool(seed_result.get("seeded")),
                    "profile_seed_error": seed_result.get("error", ""),
                    "current_url": backup_url,
                }

        return {
            "success": True,
            "logged_in": False,
            "status": "cookie_invalid",
            **credential_metadata(storage_state),
            "recovered_from_backup": str(recovered_from_backup) if recovered_from_backup else "",
            "profile_error": profile_error,
            "profile_current_url": profile_url,
            "storage_error": storage_error,
            "storage_state_saved": False,
            "storage_state_backup": "",
            "current_url": current_url or profile_url,
        }


async def login(storage_state: Path, qrcode_dir: Path, timeout: int = 180, headless: bool = True) -> dict:
    storage_state.parent.mkdir(parents=True, exist_ok=True)
    qrcode_dir.mkdir(parents=True, exist_ok=True)
    login_headless = False

    async with async_playwright() as playwright:
        context = await launch_profile_context(playwright, storage_state, headless=login_headless)
        # Do not inject init scripts on the login page. Even the light webdriver
        # shim can prevent WeChat's QR iframe from rendering in Patchright.
        page = await context.new_page()
        qrcode_path: Path | None = None
        try:
            try:
                await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:
                if "Timeout" not in str(exc):
                    raise
                await page.wait_for_timeout(3000)
            await page.wait_for_timeout(1500)
            if await is_login_completed(page) and await verify_login_session(page):
                save_result = await save_storage_state(context, storage_state)
                return {
                    "success": True,
                    "logged_in": True,
                    "status": "success",
                    "message": "already logged in",
                    **credential_metadata(storage_state, "chrome_profile"),
                    "headless_requested": headless,
                    "headless_used": login_headless,
                    "storage_state_saved": save_result.get("saved", False),
                    "storage_state_backup": save_result.get("backup", ""),
                    "qrcode_path": "",
                    "current_url": page.url,
                }

            src = await extract_qrcode_src(page)
            qrcode_path = save_data_url_image(src, qrcode_dir / f"tencent_video_login_{datetime.now():%Y%m%d_%H%M%S}.png")
            print(f"QRCODE_PATH={qrcode_path}", flush=True)

            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                if await is_login_completed(page):
                    await asyncio.sleep(2)
                    if not await verify_login_session(page):
                        return {
                            "success": False,
                            "logged_in": False,
                            "status": "login_verification_failed",
                            "message": "QR login appeared complete, but authenticated page verification failed",
                            **credential_metadata(storage_state, "chrome_profile"),
                            "headless_requested": headless,
                            "headless_used": login_headless,
                            "storage_state_saved": False,
                            "storage_state_backup": "",
                            "qrcode_path": str(qrcode_path) if qrcode_path else "",
                            "current_url": page.url,
                        }
                    save_result = await save_storage_state(context, storage_state)
                    return {
                        "success": True,
                        "logged_in": True,
                        "status": "success",
                        "message": "login completed",
                        **credential_metadata(storage_state, "chrome_profile"),
                        "headless_requested": headless,
                        "headless_used": login_headless,
                        "storage_state_saved": save_result.get("saved", False),
                        "storage_state_backup": save_result.get("backup", ""),
                        "qrcode_path": str(qrcode_path),
                        "current_url": page.url,
                    }
                if await is_qrcode_expired(page):
                    await refresh_qrcode(page)
                    await asyncio.sleep(1)
                    src = await extract_qrcode_src(page)
                    qrcode_path = save_data_url_image(
                        src,
                        qrcode_dir / f"tencent_video_login_{datetime.now():%Y%m%d_%H%M%S}.png",
                    )
                    print(f"QRCODE_PATH={qrcode_path}", flush=True)
                await asyncio.sleep(3)

            return {
                "success": False,
                "logged_in": False,
                "status": "timeout",
                "message": "waiting for login timed out",
                **credential_metadata(storage_state, "chrome_profile"),
                "headless_requested": headless,
                "headless_used": login_headless,
                "qrcode_path": str(qrcode_path) if qrcode_path else "",
                "current_url": page.url,
            }
        finally:
            await context.close()


async def open_upload_page(page: Page) -> None:
    await page.goto(UPLOAD_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(1500)
    if await has_upload_form_marker(page):
        return

    # 2026-06: 视频号新版后台会把 /platform/post/create 重定向回
    # /platform，发布入口挂在 wujie-app 的 shadow DOM 里。旧直达 URL
    # 失败时，从首页点击“发表视频”进入同一个发布表单。
    deadline = asyncio.get_event_loop().time() + 30
    while asyncio.get_event_loop().time() < deadline:
        if await has_upload_form_marker(page):
            return
        if await click_shadow_button_by_exact_text(page, "发表视频"):
            await wait_for_upload_form_marker(page)
            return
        await page.wait_for_timeout(500)
    raise RuntimeError(f"publish entry not found after redirect; url={page.url}")


async def has_upload_form_marker(page: Page) -> bool:
    markers = (
        page.locator('input[type="file"]').first,
        page.locator('div.post-create-wrap').first,
        page.get_by_text("视频管理/发表动态", exact=False).first,
        page.get_by_text("上传时长8小时内", exact=False).first,
    )
    for marker in markers:
        try:
            if await marker.count():
                return True
        except Exception:
            continue
    try:
        return bool(
            await page.evaluate(
                """() => {
                    const seen = new Set();
                    function walk(root) {
                        for (const el of Array.from(root.querySelectorAll("*"))) {
                            if (seen.has(el)) continue;
                            seen.add(el);
                            if (el.matches && el.matches('input[type="file"]')) return true;
                            const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                            if (text.includes("视频管理/发表动态") || text.includes("上传时长8小时内")) return true;
                            if (el.shadowRoot && walk(el.shadowRoot)) return true;
                        }
                        return false;
                    }
                    return walk(document);
                }"""
            )
        )
    except Exception:
        return False


async def wait_for_upload_form_marker(page: Page, timeout_ms: int = 30000) -> None:
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        if await has_upload_form_marker(page):
            return
        await page.wait_for_timeout(500)
    raise RuntimeError(f"upload form did not open within {timeout_ms}ms; url={page.url}")


async def click_shadow_button_by_exact_text(page: Page, text: str) -> bool:
    try:
        clicked = await page.evaluate(
            """targetText => {
                const seen = new Set();
                function normalized(el) {
                    return (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                }
                function walk(root) {
                    for (const el of Array.from(root.querySelectorAll("*"))) {
                        if (seen.has(el)) continue;
                        seen.add(el);
                        if (el.tagName === "BUTTON" && normalized(el) === targetText) {
                            el.click();
                            return true;
                        }
                        if (el.shadowRoot && walk(el.shadowRoot)) return true;
                    }
                    return false;
                }
                return walk(document);
            }""",
            text,
        )
        if clicked:
            return True
    except Exception:
        pass

    button = page.locator(f'button:has-text("{text}")').first
    try:
        if await button.count():
            await button.click()
            return True
    except Exception:
        pass
    return False


async def click_text_locator(page: Page, text: str, *, exact: bool = False, tag_names: list[str] | None = None) -> bool:
    roots = [page, *page.frames]
    for root in roots:
        try:
            if tag_names:
                selector = ",".join(tag.lower() for tag in tag_names)
                locators = [root.locator(selector).filter(has_text=text)]
            else:
                # For checkboxes, the wrapping label is the most reliable click target.
                locators = [
                    root.locator("label").filter(has_text=text),
                    root.get_by_text(text, exact=exact),
                ]
            for locator in locators:
                count = await locator.count()
                for idx in range(min(count, 20)):
                    item = locator.nth(idx)
                    try:
                        if not await item.is_visible():
                            continue
                        class_name = (await item.get_attribute("class")) or ""
                        aria_disabled = (await item.get_attribute("aria-disabled")) or ""
                        disabled_attr = await item.get_attribute("disabled")
                        if (
                            disabled_attr is not None
                            or aria_disabled.lower() == "true"
                            or "disabled" in class_name
                            or "_disabled" in class_name
                        ):
                            continue
                        await item.scroll_into_view_if_needed(timeout=3000)
                        await item.click(timeout=5000)
                        return True
                    except Exception:
                        continue
        except Exception:
            continue
    return False


async def click_shadow_text(page: Page, text: str, *, exact: bool = False, tag_names: list[str] | None = None) -> bool:
    if await click_text_locator(page, text, exact=exact, tag_names=tag_names):
        return True

    try:
        for frame in page.frames:
            clicked = await frame.evaluate(
                """({ targetText, exact, tagNames }) => {
                    const seen = new Set();
                    const candidates = [];
                    function normalized(el) {
                        return (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                    }
                    function visible(el) {
                        const rect = el.getBoundingClientRect();
                        return !!(rect.width || rect.height || el.getClientRects().length);
                    }
                    function disabled(el) {
                        const cls = (el.className || "").toString();
                        return el.disabled || cls.includes("disabled") || cls.includes("_disabled");
                    }
                    function addCandidate(el) {
                        const text = normalized(el);
                        if (!text) return;
                        const matched = exact ? text === targetText : text.includes(targetText);
                        if (!matched || !visible(el)) return;
                        if (tagNames && tagNames.length && !tagNames.includes(el.tagName)) return;
                        let target = el;
                        const label = el.closest && el.closest("label");
                        if (label) target = label;
                        if (disabled(target)) return;
                        const rect = target.getBoundingClientRect();
                        candidates.push({
                            el: target,
                            area: Math.max(1, rect.width * rect.height),
                            textLen: normalized(target).length || text.length,
                        });
                    }
                    function walk(root) {
                        for (const el of Array.from(root.querySelectorAll("*"))) {
                            if (seen.has(el)) continue;
                            seen.add(el);
                            addCandidate(el);
                            if (el.shadowRoot) walk(el.shadowRoot);
                        }
                    }
                    walk(document);
                    candidates.sort((a, b) => a.textLen - b.textLen || a.area - b.area);
                    if (!candidates.length) return false;
                    candidates[0].el.click();
                    return true;
                }""",
                {"targetText": text, "exact": exact, "tagNames": tag_names},
            )
            if clicked:
                return True
    except Exception:
        pass
    return False


async def shadow_checkbox_checked(page: Page, text: str) -> bool:
    for root in [page, *page.frames]:
        try:
            labels = root.locator("label").filter(has_text=text)
            count = await labels.count()
            for idx in range(min(count, 20)):
                label = labels.nth(idx)
                try:
                    checkbox = label.locator('input[type="checkbox"]').first
                    if await checkbox.count() and await checkbox.is_checked():
                        return True
                    checked_marker = label.locator(
                        ".ant-checkbox-checked, .weui-desktop-form__checkbox_checked, [class*='checked']"
                    ).first
                    if await checked_marker.count():
                        return True
                except Exception:
                    continue
        except Exception:
            continue

    try:
        for frame in page.frames:
            checked = await frame.evaluate(
                """targetText => {
                    const seen = new Set();
                    const candidates = [];
                    function normalized(el) {
                        return (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                    }
                    function walk(root) {
                        for (const el of Array.from(root.querySelectorAll("*"))) {
                            if (seen.has(el)) continue;
                            seen.add(el);
                            const text = normalized(el);
                            if (text === targetText || text.includes(targetText)) {
                                const label = el.closest && el.closest("label");
                                const input = (label || el).querySelector && (label || el).querySelector('input[type="checkbox"]');
                                if (input) candidates.push(input);
                            }
                            if (el.shadowRoot) walk(el.shadowRoot);
                        }
                    }
                    walk(document);
                    return candidates.some(input => input.checked);
                }""",
                text,
            )
            if checked:
                return True
    except Exception:
        pass
    return False


async def original_statement_checked(page: Page) -> bool:
    for text in ("声明原创", "视频为原创"):
        if await shadow_checkbox_checked(page, text):
            return True
    return False


async def click_original_statement_entry(page: Page) -> bool:
    # 视频号新版发布页的入口文案是"声明原创"，旧版曾是"视频为原创"。
    # 入口通常不是一个普通 button，而是表单行里的 checkbox + label。
    for frame in page.frames:
        try:
            clicked = await frame.evaluate(
                """() => {
                    const seen = new Set();
                    const labels = ["声明原创", "视频为原创"];
                    function textOf(el) {
                        return (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                    }
                    function visible(el) {
                        const rect = el.getBoundingClientRect();
                        return !!(rect.width || rect.height || el.getClientRects().length);
                    }
                    function disabled(el) {
                        const cls = (el.className || "").toString();
                        return !!el.disabled || cls.includes("disabled") || cls.includes("_disabled");
                    }
                    function closestCandidate(el) {
                        let node = el;
                        for (let i = 0; node && i < 7; i += 1, node = node.parentElement) {
                            const text = textOf(node);
                            if (!text) continue;
                            if (
                                labels.some(label => text.includes(label)) &&
                                (text.includes("作品将展示原创标记") ||
                                 text.includes("广告收入") ||
                                 text.includes("原创标记") ||
                                 node.querySelector('input[type="checkbox"]'))
                            ) {
                                return node;
                            }
                        }
                        return el;
                    }
                    function tryClick(root) {
                        const nodes = Array.from(root.querySelectorAll("*"));
                        for (const el of nodes) {
                            if (seen.has(el)) continue;
                            seen.add(el);
                            if (el.shadowRoot && tryClick(el.shadowRoot)) return true;
                            if (!visible(el)) continue;
                            const text = textOf(el);
                            if (!labels.some(label => text === label || text.includes(label))) continue;
                            if (text.includes("原创保护记录")) continue;
                            const row = closestCandidate(el);
                            const checkbox = row.querySelector && row.querySelector('input[type="checkbox"]');
                            if (checkbox && visible(checkbox) && !disabled(checkbox)) {
                                checkbox.click();
                                return true;
                            }
                            if (!disabled(row)) {
                                row.click();
                                return true;
                            }
                        }
                        return false;
                    }
                    return tryClick(document);
                }"""
            )
            if clicked:
                return True
        except Exception:
            continue
    return False


async def original_rights_dialog_state(page: Page) -> dict[str, Any]:
    for frame in page.frames:
        try:
            state = await frame.evaluate(
                """() => {
                    function textOf(el) {
                        return (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                    }
                    function visible(el) {
                        const rect = el.getBoundingClientRect();
                        return !!(rect.width || rect.height || el.getClientRects().length);
                    }
                    function disabled(el) {
                        const cls = (el.className || "").toString();
                        return !!el.disabled ||
                            el.getAttribute("aria-disabled") === "true" ||
                            cls.includes("disabled") ||
                            cls.includes("_disabled");
                    }
                    const dialogs = Array.from(document.querySelectorAll(".declare-original-dialog, [role='dialog'], .mp-dialog, .weui-desktop-dialog, div"))
                        .filter(el => {
                            if (!visible(el)) return false;
                            const text = textOf(el);
                            return text.includes("原创权益") &&
                                text.includes("获得原创标记") &&
                                text.includes("声明原创");
                        })
                        .sort((a, b) => textOf(a).length - textOf(b).length);
                    const dialog = dialogs[0];
                    if (!dialog) return { visible: false };

                    const protocolCheckbox = Array.from(dialog.querySelectorAll('input[type="checkbox"]'))
                        .find(el => visible(el) && !disabled(el));
                    const protocolChecked = protocolCheckbox ? !!protocolCheckbox.checked : false;
                    const buttons = Array.from(dialog.querySelectorAll("button"))
                        .filter(el => visible(el) && textOf(el).trim() === "声明原创");
                    const confirmButton = buttons.find(el => !disabled(el)) || null;
                    const disabledConfirmButton = buttons.find(el => disabled(el)) || null;
                    return {
                        visible: true,
                        protocol_found: !!protocolCheckbox,
                        protocol_checked: protocolChecked,
                        confirm_enabled: !!confirmButton,
                        confirm_disabled: !!disabledConfirmButton && !confirmButton,
                    };
                }"""
            )
            if state.get("visible"):
                return state
        except Exception:
            continue
    return {"visible": False}


async def confirm_original_rights_dialog(page: Page) -> bool:
    # The "声明原创" entry opens a second-step modal named "原创权益".
    # The flow must accept the protocol checkbox and then click the modal's
    # orange "声明原创" button. Clicking only the page-level checkbox is not enough.
    deadline = asyncio.get_running_loop().time() + 30
    while asyncio.get_running_loop().time() < deadline:
        clicked = False
        for frame in page.frames:
            try:
                clicked = await frame.evaluate(
                    """() => {
                        function textOf(el) {
                            return (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                        }
                        function visible(el) {
                            const rect = el.getBoundingClientRect();
                            return !!(rect.width || rect.height || el.getClientRects().length);
                        }
                        function disabled(el) {
                            const cls = (el.className || "").toString();
                            return !!el.disabled ||
                                el.getAttribute("aria-disabled") === "true" ||
                                cls.includes("disabled") ||
                                cls.includes("_disabled");
                        }
                        const dialogs = Array.from(document.querySelectorAll(".declare-original-dialog, [role='dialog'], .mp-dialog, .weui-desktop-dialog, div"))
                            .filter(el => {
                                if (!visible(el)) return false;
                                const text = textOf(el);
                                return text.includes("原创权益") &&
                                    text.includes("获得原创标记") &&
                                    text.includes("声明原创");
                            })
                            .sort((a, b) => textOf(a).length - textOf(b).length);
                        const dialog = dialogs[0];
                        if (!dialog) return false;

                        const protocolCheckbox = Array.from(dialog.querySelectorAll('input[type="checkbox"]'))
                            .find(el => visible(el) && !disabled(el));
                        if (protocolCheckbox && !protocolCheckbox.checked) {
                            protocolCheckbox.click();
                            return true;
                        }

                        const confirmButton = Array.from(dialog.querySelectorAll("button"))
                            .find(el => visible(el) && textOf(el).trim() === "声明原创" && !disabled(el));
                        if (confirmButton) {
                            confirmButton.click();
                            return true;
                        }
                        return false;
                    }"""
                )
            except Exception:
                clicked = False
            if clicked:
                await page.wait_for_timeout(1000)
                state = await original_rights_dialog_state(page)
                if not state.get("visible"):
                    return True
                if state.get("confirm_enabled"):
                    continue
        state = await original_rights_dialog_state(page)
        if not state.get("visible"):
            return False
        await page.wait_for_timeout(500)
    return False


async def dump_original_debug(page: Page, page_diag: dict[str, list[dict]] | None, reason: str) -> str:
    dump_dir = Path("/tmp/tencent_video_debug")
    dump_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot = dump_dir / f"{reason}_{ts}.png"
    data_path = dump_dir / f"{reason}_{ts}.json"
    try:
        await page.screenshot(path=str(screenshot), full_page=True)
    except Exception:
        pass

    frame_diag = []
    for idx, frame in enumerate(page.frames):
        try:
            diag = await frame.evaluate(
                """() => {
                    const matches = [];
                    const clickable = [];
                    const textRe = /.{0,80}(原创|声明|授权|视频为原创|我已阅读).{0,140}/g;
                    for (const el of Array.from(document.querySelectorAll("*"))) {
                        const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                        if (!text) continue;
                        let match;
                        while ((match = textRe.exec(text)) && matches.length < 40) {
                            matches.push(match[0]);
                        }
                        if (/原创|声明|授权/.test(text) && clickable.length < 80) {
                            const rect = el.getBoundingClientRect();
                            const cls = (el.className || "").toString();
                            clickable.push({
                                tag: el.tagName,
                                className: cls.slice(0, 180),
                                text: text.slice(0, 240),
                                visible: !!(rect.width || rect.height || el.getClientRects().length),
                                disabled: !!el.disabled || cls.includes("disabled") || cls.includes("_disabled"),
                            });
                        }
                    }
                    return { url: location.href, matches, clickable };
                }"""
            )
            diag["frame_idx"] = idx
            diag["frame_url"] = frame.url
            frame_diag.append(diag)
        except Exception as exc:
            frame_diag.append({"frame_idx": idx, "frame_url": frame.url, "error": str(exc)})

    locator_diag: dict[str, Any] = {}
    for name, selector in {
        "original_label": "label:has-text('视频为原创')",
        "original_text": "text=视频为原创",
        "declare_entry_label": "label:has-text('声明原创')",
        "declare_entry_text": "text=声明原创",
        "original_rights_dialog": "text=原创权益",
        "agree_text": "text=我已阅读并同意",
        "declare_button": "button:has-text('声明原创')",
        "checkboxes": "input[type='checkbox']",
    }.items():
        locator = page.locator(selector)
        item = locator.first
        try:
            count = await locator.count()
            if count:
                locator_diag[name] = {
                    "selector": selector,
                    "count": count,
                    "visible": await item.is_visible(),
                    "text": (await item.text_content() or "")[:1000],
                    "outer_html": (await item.evaluate("e => e.outerHTML"))[:4000],
                }
            else:
                locator_diag[name] = {"selector": selector, "count": 0}
        except Exception as exc:
            locator_diag[name] = {"selector": selector, "error": str(exc)}

    data = {
        "reason": reason,
        "url": page.url,
        "locator_diag": locator_diag,
        "frame_diag": frame_diag,
        "page_events": page_diag or {},
    }
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"{data_path} {screenshot}"


async def upload_video_file(page: Page, file_path: Path) -> None:
    file_input = page.locator('input[type="file"]').first
    await file_input.wait_for(state="attached", timeout=30000)
    await file_input.set_input_files(str(file_path))


async def focus_editor_end(editor) -> None:
    await editor.click()
    await editor.evaluate(
        """el => {
            el.focus();
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(el);
            range.collapse(false);
            selection.removeAllRanges();
            selection.addRange(range);
        }"""
    )


async def fill_title_tags_desc(page: Page, title: str, tags: list[str], desc: str) -> None:
    # 视频号发布页有两个独立文案区，本函数填的是"视频描述"editor，需要完整呈现：
    #   - 短标题 input（独立字段）→ set_short_title() 单独 fill，简短版本（卡片显示）
    #   - 描述/动态 editor（本函数）→ 标题 + 正文 + 标签的完整版（feed 详情显示）
    # 用户明确要求描述 editor 顺序：标题 → 换行 → 正文 → 换行 → 标签。
    editor = page.locator("div.input-editor").first
    await editor.wait_for(state="visible", timeout=30000)
    await focus_editor_end(editor)
    if title:
        await page.keyboard.insert_text(title)
        await page.keyboard.press("Enter")
    desc = desc.strip()
    if desc:
        await page.keyboard.insert_text(desc)
    if tags:
        await focus_editor_end(editor)
        await page.keyboard.press("Enter")
    for tag in tags:
        tag = tag.strip().lstrip("#")
        if not tag:
            continue
        # 标签必须逐个输入并等待平台识别；不要把标签和正文一次性粘贴。
        await focus_editor_end(editor)
        await page.keyboard.type("#", delay=30)
        await page.keyboard.type(tag, delay=30)
        await page.wait_for_timeout(500)
        await page.keyboard.press("Space")
        await page.wait_for_timeout(900)


async def apply_original_statement(
    page: Page,
    category: str | None,
    page_diag: dict[str, list[dict]] | None = None,
) -> None:
    # 默认声明原创（即使没传 --category）。
    # category 只用于在弹出的"原创类型"下拉里选择具体类型（如 "知识"）；不传时跳过类型选择，但仍走声明流程。
    #
    # 视频号原创入口文案会变：旧版是"视频为原创"，新版是表单行"声明原创"。
    # 必须等视频上传、文案、封面、定时等内容都进入可编辑状态后再找，否则入口不会出现或
    # checkbox disabled，点击会静默失败。
    try:
        await page.keyboard.press("End")
        await page.wait_for_timeout(500)
    except Exception:
        pass
    if not await original_statement_checked(page):
        clicked_original = False
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 60
        while loop.time() < deadline:
            clicked_original = await click_original_statement_entry(page)
            if not clicked_original:
                clicked_original = await click_shadow_text(page, "声明原创", exact=True)
            if not clicked_original:
                clicked_original = await click_shadow_text(page, "视频为原创", exact=False)
            if clicked_original:
                await page.wait_for_timeout(1000)
                await confirm_original_rights_dialog(page)
                break
            await asyncio.sleep(1)
        if not clicked_original:
            debug = await dump_original_debug(page, page_diag, "original_entry_missing")
            raise RuntimeError(f"未找到可点击的原创声明入口; debug={debug}")

    dialog_state = await original_rights_dialog_state(page)
    if dialog_state.get("visible"):
        confirmed = await confirm_original_rights_dialog(page)
        dialog_state = await original_rights_dialog_state(page)
        if not confirmed and dialog_state.get("visible"):
            debug = await dump_original_debug(page, page_diag, "original_dialog_unconfirmed")
            raise RuntimeError(f"未能完成原创权益弹窗确认; debug={debug}")

    await click_shadow_text(page, "我已阅读并同意", exact=False)

    if category:
        original_type_form = page.locator('div.original-type-form > div.form-label:has-text("原创类型"):visible')
        if await original_type_form.count():
            await page.locator("div.form-content:visible").click()
            await page.locator(
                "div.form-content:visible "
                "ul.weui-desktop-dropdown__list "
                f'li.weui-desktop-dropdown__list-ele:has-text("{category}")'
            ).first.click()
            await page.wait_for_timeout(1000)

    await page.wait_for_timeout(1000)
    dialog_state = await original_rights_dialog_state(page)
    if dialog_state.get("visible"):
        confirmed = await confirm_original_rights_dialog(page)
        dialog_state = await original_rights_dialog_state(page)
        if not confirmed and dialog_state.get("visible"):
            debug = await dump_original_debug(page, page_diag, "original_dialog_unconfirmed")
            raise RuntimeError(f"未能完成原创权益弹窗确认; debug={debug}")

    clicked_declare = await click_shadow_text(page, "声明原创", exact=True, tag_names=["BUTTON"])
    if not clicked_declare:
        clicked_declare = await click_shadow_text(page, "声明原创", exact=False, tag_names=["BUTTON"])
    if not clicked_declare:
        if await original_statement_checked(page):
            return
        debug = await dump_original_debug(page, page_diag, "original_declare_missing")
        raise RuntimeError(f"未能点击“声明原创”按钮; debug={debug}")


async def upload_edit_blocking_status(page: Page) -> tuple[bool, str]:
    blockers = (
        'button:has-text("取消上传")',
        'div.weui-desktop-popover__desc:has-text("请等待完成后再编辑")',
        'text=文件上传中，请等待完成后再编辑',
        'text=视频处理中，请等待完成后再编辑',
    )
    for selector in blockers:
        loc = page.locator(selector).first
        try:
            if await loc.count() and await loc.is_visible():
                text = (await loc.text_content() or "").strip()
                return True, " ".join(text.split())[:200] or selector
        except Exception:
            continue
    return False, ""


async def collect_upload_status_text(page: Page) -> str:
    texts: list[str] = []
    status_candidates = (
        page.locator("div.status-msg").first,
        page.locator("div.media-status-content").first,
        page.locator("div.upload-progress").first,
        page.locator('text=/上传|处理|失败|%/').first,
    )
    for status in status_candidates:
        try:
            if await status.count() and await status.is_visible():
                text = (await status.inner_text()).strip()
                if text:
                    texts.append(" ".join(text.split())[:300])
        except Exception:
            continue

    try:
        shadow_text = await page.evaluate(
            """() => {
                const seen = new Set();
                const chunks = [];
                const re = /.{0,30}(上传|处理|失败|网络异常|\\d+\\s*%).{0,80}/g;
                function visible(el) {
                    const rect = el.getBoundingClientRect();
                    return !!(rect.width || rect.height || el.getClientRects().length);
                }
                function walk(root) {
                    for (const el of Array.from(root.querySelectorAll("*"))) {
                        if (seen.has(el)) continue;
                        seen.add(el);
                        if (visible(el)) {
                            const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
                            let match;
                            while ((match = re.exec(text)) && chunks.length < 20) {
                                chunks.push(match[0]);
                            }
                        }
                        if (el.shadowRoot) walk(el.shadowRoot);
                    }
                }
                walk(document);
                return chunks.join(" | ");
            }"""
        )
        if shadow_text:
            texts.append(shadow_text[:500])
    except Exception:
        pass
    return " | ".join(dict.fromkeys(texts))[:1000]


async def dump_upload_debug(page: Page, page_diag: dict[str, list[dict]] | None, reason: str) -> str:
    dump_dir = Path("/tmp/tencent_video_debug")
    dump_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot = dump_dir / f"{reason}_{ts}.png"
    data_path = dump_dir / f"{reason}_{ts}.json"
    try:
        await page.screenshot(path=str(screenshot), full_page=True)
    except Exception:
        pass
    data = {
        "reason": reason,
        "url": page.url,
        "status_text": await collect_upload_status_text(page),
        "network_diag": page_diag or {},
    }
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"{data_path} {screenshot}"


async def wait_for_upload_complete(
    page: Page,
    timeout_seconds: int = 300,
    page_diag: dict[str, list[dict]] | None = None,
) -> None:
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    last_status = ""
    last_status_at = asyncio.get_event_loop().time()
    stalled_wait_seconds = min(180, max(60, timeout_seconds // 3))
    while asyncio.get_event_loop().time() < deadline:
        publish_button = page.get_by_role("button", name="发表").first
        try:
            if await publish_button.count():
                button_class = await publish_button.get_attribute("class")
                if button_class and "weui-desktop-btn_disabled" not in button_class:
                    blocked, blocker_status = await upload_edit_blocking_status(page)
                    if not blocked:
                        return
                    last_status = blocker_status
        except Exception:
            pass

        status_text = await collect_upload_status_text(page)
        if status_text:
            now = asyncio.get_event_loop().time()
            if status_text != last_status:
                last_status = status_text
                last_status_at = now
            elif ("%" in status_text or "上传" in status_text) and now - last_status_at > stalled_wait_seconds:
                dump = await dump_upload_debug(page, page_diag, "upload_stalled")
                raise RuntimeError(
                    f"video upload status stalled for {stalled_wait_seconds}s: {last_status}; "
                    f"debug={dump}; hosts={(page_diag or {}).get('hosts', [])}"
                )

        upload_failed = await page.locator("div.status-msg.error").count()
        delete_button = await page.locator('div.media-status-content div.tag-inner:has-text("删除")').count()
        if upload_failed and delete_button:
            dump = await dump_upload_debug(page, page_diag, "upload_failed")
            raise RuntimeError(f"video upload failed on page: {last_status}; debug={dump}")
        await asyncio.sleep(2)
    dump = await dump_upload_debug(page, page_diag, "upload_timeout")
    raise RuntimeError(
        f"video upload did not complete within {timeout_seconds}s; "
        f"last_status={last_status}; url={page.url}; debug={dump}; hosts={(page_diag or {}).get('hosts', [])}"
    )


async def cover_generation_loading(page: Page) -> tuple[bool, str]:
    loading = page.locator('div.vertical-cover-wrap div.loading-wrap').first
    try:
        if not await loading.count() or not await loading.is_visible():
            return False, ""
        cover_wrap = page.locator("div.vertical-cover-wrap").first
        status = (await cover_wrap.text_content() or "").strip() if await cover_wrap.count() else ""
        return True, " ".join(status.split())[:200] or "生成中"
    except Exception:
        return False, ""


async def collect_cover_runtime_diag(page: Page) -> dict:
    diag: dict[str, Any] = {}
    selectors = {
        "cover_wrap": ".vertical-cover-wrap",
        "cover_loading": "div.vertical-cover-wrap div.loading-wrap",
        "cover_img": "div.vertical-cover-wrap img",
        "video": "video",
        "upload_status": "div.media-status-content",
        "status_msg": "div.status-msg",
        "cancel_upload": 'button:has-text("取消上传")',
        "edit_blocker": 'div.weui-desktop-popover__desc:has-text("请等待完成后再编辑")',
        "publish_button": 'div.form-btns button:has-text("发表")',
    }
    for name, selector in selectors.items():
        loc = page.locator(selector).first
        try:
            count = await loc.count()
            if not count:
                diag[name] = {"selector": selector, "found": False}
                continue
            entry = {
                "selector": selector,
                "found": True,
                "visible": await loc.is_visible(),
                "text": (await loc.text_content() or "")[:1000],
                "outer_html": (await loc.evaluate("e => e.outerHTML"))[:4000],
            }
            if name == "video":
                entry["media_state"] = await loc.evaluate(
                    """v => ({
                        currentSrc: v.currentSrc || v.src || "",
                        readyState: v.readyState,
                        networkState: v.networkState,
                        error: v.error ? { code: v.error.code, message: v.error.message } : null,
                        duration: v.duration,
                        videoWidth: v.videoWidth,
                        videoHeight: v.videoHeight,
                        paused: v.paused,
                    })"""
                )
            diag[name] = entry
        except Exception as exc:
            diag[name] = {"selector": selector, "error": str(exc)}
    return diag


async def first_visible(locator):
    try:
        count = await locator.count()
    except Exception:
        return None
    for idx in range(min(count, 20)):
        item = locator.nth(idx)
        try:
            if await item.is_visible():
                return item
        except Exception:
            continue
    return None


async def find_cover_dialog(page: Page):
    candidates = (
        page.locator("div.weui-desktop-dialog").filter(has_text="编辑个人主页卡片"),
        page.locator("div.weui-desktop-dialog").filter(has_text="编辑个人主页和分享卡片"),
        page.locator("div.weui-desktop-dialog").filter(has_text="个人主页和分享卡片"),
        page.locator("div.weui-desktop-dialog").filter(has_text="封面"),
        page.locator("div.weui-desktop-dialog").filter(has=page.locator('input[type="file"]')),
    )
    for candidate in candidates:
        visible = await first_visible(candidate)
        if visible:
            return visible
    return None


async def set_thumbnail(page: Page, thumbnail_path: Path | None, cover_timeout_seconds: int = 60) -> None:
    # 失败时报错而不是静默跳过。封面是发布元数据的核心，必须确认实际传上。
    if not thumbnail_path:
        return

    # 视频号必须先结束官方默认封面生成，手动封面入口才可点击；生成中时点击 cover-wrap
    # 不会弹出上传窗口。这里使用短、可配置的等待，避免后端卡住时把整条发布链路挂死。
    loop = asyncio.get_running_loop()
    deadline = loop.time() + max(0, cover_timeout_seconds)
    while True:
        is_loading, status = await cover_generation_loading(page)
        if not is_loading:
            break
        if loop.time() >= deadline:
            status_note = f" current_status={status!r};" if status else ""
            timeout_note = (
                f" after {cover_timeout_seconds}s"
                if cover_timeout_seconds > 0
                else " because --cover-timeout is 0"
            )
            raise RuntimeError(
                "official video cover generation is still stuck"
                f"{timeout_note};{status_note} WeChat keeps manual cover upload disabled while this state is visible. "
                "Cover was not uploaded and no save/publish click was performed. "
                "Retry with a longer --cover-timeout, or use --fill-only --hold-open and upload the cover manually after it clears."
            )
        await asyncio.sleep(min(3, max(0.5, deadline - loop.time())))

    is_loading, status = await cover_generation_loading(page)
    if is_loading:
        raise RuntimeError(
            f"official video cover generation is still stuck; current_status={status!r}; "
            "manual cover upload remains disabled"
        )

    # 注意：不要用 `div:has-text("修改封面")` 这种宽 selector，会匹配到包含该文本的整页容器。
    # 真正的入口必须是 cover-wrap / edit-btn 类专用容器。视频处理完成和官方封面生成完成
    # 不是同一件事；如果页面提示"请等待完成后再编辑"，就继续等待而不是直接判定 DOM 变化。
    entry_selectors = (
        'div.vertical-cover-wrap .edit-btn:has-text("编辑")',
        'div.vertical-cover-wrap:has-text("个人主页和分享卡片")',
        'div.vertical-cover-wrap:has-text("3:4")',
        'div.vertical-cover-wrap:has-text("个人主页卡片")',
        'div.cover-wrap:visible',
        'div.cover-section:visible',
    )
    cover_dialog = None
    last_click_status = ""
    while loop.time() < deadline:
        blocked, blocker_status = await upload_edit_blocking_status(page)
        if blocked:
            last_click_status = blocker_status
            await asyncio.sleep(2)
            continue

        entry_clicked = False
        for selector in entry_selectors:
            cover_entry = page.locator(selector).first
            try:
                if await cover_entry.count():
                    await cover_entry.wait_for(state="visible", timeout=3000)
                    await cover_entry.click()
                    await page.wait_for_timeout(1000)
                    entry_clicked = True
                    break
            except Exception:
                continue
        if not entry_clicked:
            raise RuntimeError(
                f"cover upload entry not found on publish page (DOM may have changed); "
                f"thumbnail={thumbnail_path}"
            )

        cover_dialog = await find_cover_dialog(page)
        if cover_dialog:
            break

        blocked, blocker_status = await upload_edit_blocking_status(page)
        last_click_status = blocker_status or "cover dialog did not open after clicking edit"
        await asyncio.sleep(2)

    if not cover_dialog:
        raise RuntimeError(
            "cover upload dialog did not open before timeout; "
            f"last_status={last_click_status!r}; thumbnail={thumbnail_path}"
        )

    file_input = cover_dialog.locator(
        '.single-cover-uploader-wrap input[type="file"], input[type="file"]'
    ).first
    await file_input.wait_for(state="attached", timeout=10000)
    await file_input.set_input_files(str(thumbnail_path))
    await page.wait_for_timeout(1000)

    crop_dialog = page.locator("div.weui-desktop-dialog").filter(has_text="裁剪封面图").first
    if await crop_dialog.count():
        try:
            await crop_dialog.wait_for(state="visible", timeout=10000)
            crop_confirm = crop_dialog.locator(
                'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确定")'
            ).first
            if await crop_confirm.count():
                await crop_confirm.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

    confirm = cover_dialog.locator('div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确认")').first
    await confirm.wait_for(state="visible", timeout=10000)
    await confirm.click()


async def set_schedule_time(page: Page, publish_date: datetime) -> None:
    label = page.locator("label").filter(has_text="定时").nth(1)
    await label.click()
    await page.click('input[placeholder="请选择发表时间"]')

    current_month = publish_date.strftime("%m月")
    try:
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')
        if page_month != current_month:
            await page.click("button.weui-desktop-btn__icon__right")
    except Exception:
        pass

    elements = await page.query_selector_all("table.weui-desktop-picker__table a")
    for element in elements:
        class_name = await element.evaluate("el => el.className")
        if "weui-desktop-picker__disabled" in class_name:
            continue
        text = await element.inner_text()
        if text.strip() == str(publish_date.day):
            await element.click()
            break

    await page.click('input[placeholder="请选择时间"]')
    modifier = "Meta" if sys.platform == "darwin" else "Control"
    await page.keyboard.press(f"{modifier}+KeyA")
    await page.keyboard.type(publish_date.strftime("%H"))
    await page.locator("div.input-editor").click()


async def set_short_title(page: Page, title: str, short_title: str | None = None) -> None:
    short_title_element = (
        page.get_by_text("短标题", exact=True)
        .locator("xpath=..")
        .locator("xpath=following-sibling::div")
        .locator('span input[type="text"]')
        .first
    )
    if await short_title_element.count():
        await short_title_element.fill(short_title or format_short_title(title))


async def submit(page: Page, publish: bool) -> str:
    if publish:
        button = page.locator('div.form-btns button:has-text("发表")').first
        action = "published"
    else:
        button = page.locator('div.form-btns button:has-text("保存草稿")').first
        action = "draft_saved"

    await button.wait_for(state="visible", timeout=30000)
    await button.click()
    try:
        await page.wait_for_url("**/post/list**", timeout=10000)
    except Exception:
        pass
    return action


async def upload_video(request: UploadVideoRequest) -> dict:
    request.file_path = validate_video_file(request.file_path)
    request.thumbnail_path = validate_image_file(request.thumbnail_path) if request.thumbnail_path else None
    request.schedule_at = validate_schedule(request.schedule_at)
    if request.cover_timeout < 0:
        raise ValueError("--cover-timeout must be >= 0")
    if request.schedule_at and not request.publish:
        raise ValueError("--schedule-at requires --publish")
    if not request.title.strip():
        raise ValueError("title is required")

    login_check = await check_login(request.storage_state, headless=request.headless)
    if not login_check.get("logged_in"):
        raise RuntimeError(
            f"login state invalid ({login_check.get('status')}), login first: {request.storage_state}"
        )
    credential_source = str(login_check.get("credential_source") or "chrome_profile")

    async with async_playwright() as playwright:
        context = None
        browser = None
        try:
            context, browser, runtime_auth = await open_authenticated_context(
                playwright,
                request.storage_state,
                headless=request.headless,
                credential_source=credential_source,
            )
            page = await context.new_page()
            page_diag = attach_page_diagnostics(page)
            await open_upload_page(page)
            if not await wait_for_login_completed(page):
                raise RuntimeError(f"not logged in or cookie invalid: {request.storage_state}")

            await upload_video_file(page, request.file_path)
            await fill_title_tags_desc(page, request.title, request.tags or [], request.desc)
            await set_short_title(page, request.title, request.short_title)
            # 等视频上传 + 后端处理完成后，再填封面、定时、原创等后续项。
            # 这些入口在视频处理完成前是"未就绪"状态，过早调用会静默失败。
            await wait_for_upload_complete(page, timeout_seconds=request.upload_timeout, page_diag=page_diag)
            original_warning: str | None = None
            # 封面失败时：fill-only 模式下只 log warning 不阻断（方便人工在浏览器里诊断 DOM）；
            # 非 fill-only 模式仍然 raise，避免静默以为传上了。
            thumbnail_warning: str | None = None
            try:
                await set_thumbnail(page, request.thumbnail_path, cover_timeout_seconds=request.cover_timeout)
            except RuntimeError as exc:
                if request.fill_only:
                    thumbnail_warning = str(exc)
                    # 诊断 dump：页面 HTML + 全屏截图 + evaluate 抓 input-editor 实际内容和封面区域 DOM
                    try:
                        dump_dir = Path("/tmp/tencent_video_debug")
                        dump_dir.mkdir(exist_ok=True)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        await page.screenshot(path=str(dump_dir / f"page_{ts}.png"), full_page=True)
                        # 用 patchright locator API (piercing shadow DOM + wujie iframe) dump 状态
                        loc_diag: dict = {}
                        for name, sel in [
                            ("editor", ".input-editor"),
                            ("cover_wrap", ".vertical-cover-wrap"),
                            ("original_label", "label:has-text('视频为原创')"),
                            ("original_checkbox", "input[type='checkbox']"),
                        ]:
                            try:
                                loc = page.locator(sel).first
                                cnt = await loc.count()
                                if cnt:
                                    loc_diag[name] = {
                                        "selector": sel,
                                        "found": True,
                                        "visible": await loc.is_visible(),
                                        "text": (await loc.text_content() or "")[:600],
                                        "outer_html": (await loc.evaluate("e => e.outerHTML"))[:3000],
                                    }
                                else:
                                    loc_diag[name] = {"selector": sel, "found": False, "count": cnt}
                            except Exception as le:
                                loc_diag[name] = {"selector": sel, "error": str(le)}
                        (dump_dir / f"locator_diag_{ts}.json").write_text(
                            json.dumps(loc_diag, ensure_ascii=False, indent=2), encoding="utf-8"
                        )
                        thumbnail_warning += f" | locator_diag: /tmp/tencent_video_debug/locator_diag_{ts}.json + page_{ts}.png"
                        runtime_diag = {
                            "cover_runtime": await collect_cover_runtime_diag(page),
                            "page_events": page_diag,
                        }
                        (dump_dir / f"runtime_diag_{ts}.json").write_text(
                            json.dumps(runtime_diag, ensure_ascii=False, indent=2), encoding="utf-8"
                        )
                        thumbnail_warning += f" | runtime_diag: /tmp/tencent_video_debug/runtime_diag_{ts}.json"
                        # 跳过旧的 frame-based evaluate dump（已知 wujie 下 evaluate 找不到）
                        diag_js = """
                            () => {
                                const editor = document.querySelector('div.input-editor');
                                const coverArea = document.querySelector('div.vertical-cover-wrap')
                                    || document.querySelector('[class*="cover"]');
                                let origArea = null;
                                for (const el of document.querySelectorAll('label, div, span')) {
                                    if ((el.innerText || '').includes('视频为原创')) { origArea = el; break; }
                                }
                                // 找封面区域附近的所有可点击元素
                                const coverContext = [];
                                if (coverArea) {
                                    const ancestors = coverArea.querySelectorAll('*');
                                    for (const el of ancestors) {
                                        const txt = (el.textContent || '').trim();
                                        if (/修改|编辑|上传/.test(txt) && txt.length < 20) {
                                            coverContext.push({
                                                tag: el.tagName,
                                                cls: (el.className || '').toString().slice(0, 100),
                                                text: txt.slice(0, 30),
                                            });
                                        }
                                    }
                                }
                                return {
                                    found_here: !!(editor || coverArea || origArea),
                                    editor_innerText: editor ? editor.innerText.slice(0, 3000) : null,
                                    editor_innerHTML: editor ? editor.innerHTML.slice(0, 3000) : null,
                                    cover_outerHTML: coverArea ? coverArea.outerHTML.slice(0, 5000) : null,
                                    cover_clickable: coverContext.slice(0, 20),
                                    orig_outerHTML: origArea ? origArea.outerHTML.slice(0, 3000) : null,
                                };
                            }
                        """
                        all_diag = []
                        for idx, frame in enumerate(page.frames):
                            try:
                                d = await frame.evaluate(diag_js)
                                d["frame_idx"] = idx
                                d["frame_url"] = frame.url
                                d["frame_name"] = frame.name
                                if d.get("found_here"):
                                    all_diag.append(d)
                                # 顺便 dump 该 frame 的 HTML
                                try:
                                    fhtml = await frame.content()
                                    (dump_dir / f"frame{idx}_{ts}.html").write_text(fhtml, encoding="utf-8")
                                except Exception:
                                    pass
                            except Exception as fe:
                                all_diag.append({"frame_idx": idx, "frame_url": frame.url, "error": str(fe)})
                        (dump_dir / f"diag_{ts}.json").write_text(json.dumps(all_diag, ensure_ascii=False, indent=2), encoding="utf-8")
                        thumbnail_warning += f" | dumped: /tmp/tencent_video_debug/diag_{ts}.json + frame*_{ts}.html + page_{ts}.png"
                    except Exception as dump_exc:
                        thumbnail_warning += f" | dump failed: {dump_exc}"
                else:
                    raise
            if request.schedule_at:
                await set_schedule_time(page, request.schedule_at)
            await set_short_title(page, request.title, request.short_title)
            try:
                await apply_original_statement(page, request.category, page_diag=page_diag)
            except RuntimeError as exc:
                if request.fill_only and ("原创" in str(exc)):
                    original_warning = str(exc)
                else:
                    raise
            if request.fill_only:
                if request.hold_open_seconds < 0:
                    if original_warning:
                        print(f"ORIGINAL_WARNING={original_warning}", flush=True)
                    if thumbnail_warning:
                        print(f"THUMBNAIL_WARNING={thumbnail_warning}", flush=True)
                    print(f"FILL_ONLY_READY={page.url}", flush=True)
                    await asyncio.Event().wait()
                if request.hold_open_seconds > 0:
                    await asyncio.sleep(request.hold_open_seconds)
                save_result = await save_storage_state(context, request.storage_state)
                return {
                    "success": True,
                    "action": "filled_ready_to_submit",
                    "platform": "tencent_video",
                    "title": request.title,
                    "file": str(request.file_path),
                    **credential_metadata(request.storage_state, credential_source),
                    "runtime_auth": runtime_auth,
                    "storage_state_saved": save_result.get("saved", False),
                    "storage_state_backup": save_result.get("backup", ""),
                    "current_url": page.url,
                    "scheduled_at": request.schedule_at.isoformat() if request.schedule_at else None,
                    "submitted": False,
                    "original_warning": original_warning,
                    "thumbnail_warning": thumbnail_warning,
                }
            action = await submit(page, request.publish)
            save_result = await save_storage_state(context, request.storage_state)
            return {
                "success": True,
                "action": action,
                "platform": "tencent_video",
                "title": request.title,
                "file": str(request.file_path),
                **credential_metadata(request.storage_state, credential_source),
                "runtime_auth": runtime_auth,
                "storage_state_saved": save_result.get("saved", False),
                "storage_state_backup": save_result.get("backup", ""),
                "current_url": page.url,
                "scheduled_at": request.schedule_at.isoformat() if request.schedule_at else None,
                "submitted": True,
            }
        finally:
            # Manual fill-only flows keep the page open for user-side review and
            # publishing. Persist any cookies/tokens refreshed during that
            # session before an interrupt closes the browser.
            if context:
                await best_effort_save_storage_state(context, request.storage_state)
                await context.close()
            if browser:
                await browser.close()
