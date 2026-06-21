"""Video cover helpers for Xiaohongshu creator publish pages."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from .cdp import Page

MARKED_IMAGE_FILE_INPUT = 'input[type=file][data-xhs-cover-input="1"]'
COVER_THUMBNAIL_SELECTOR = ".publish-page-content-cover .cover .default.column"


def _click_text(page: Page, text: str) -> bool:
    """Click the first visible simple element whose text exactly matches."""
    return bool(
        page.evaluate(
            f"""
            (() => {{
                const want = {json.dumps(text)};
                const el = Array.from(document.querySelectorAll('div,span,button'))
                    .find(e => (e.textContent || '').trim() === want
                        && e.childElementCount <= 1
                        && e.getBoundingClientRect().width > 0
                        && e.getBoundingClientRect().height > 0);
                if (!el) return false;
                el.click();
                return true;
            }})()
            """
        )
    )


def _click_last_confirm(page: Page) -> int:
    """Click the last visible confirm button, usually the crop modal action."""
    return int(
        page.evaluate(
            """
            (() => {
                const btns = Array.from(document.querySelectorAll('button, .d-button'))
                    .filter(el => {
                        const t = (el.textContent || '').trim();
                        const r = el.getBoundingClientRect();
                        return t === '确定' && r.width > 0 && r.height > 0 && !el.disabled;
                    });
                if (!btns.length) return 0;
                btns[btns.length - 1].click();
                return btns.length;
            })()
            """
        )
        or 0
    )


def _click_cover_editor_entry(page: Page) -> bool:
    """Open the cover editor by hovering and clicking the cover thumbnail."""
    box = page.evaluate(
        f"""
        (() => {{
            const el = document.querySelector({json.dumps(COVER_THUMBNAIL_SELECTOR)})
                || document.querySelector('.publish-page-content-cover .cover');
            if (!el) return null;
            el.scrollIntoView({{block: 'center'}});
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return null;
            return {{
                x: rect.left + rect.width / 2,
                y: rect.top + rect.height / 2,
            }};
        }})()
        """
    )
    if not box:
        return _click_text(page, "修改封面") or _click_text(page, "设置封面")

    page.mouse_move(float(box["x"]), float(box["y"]))
    time.sleep(0.5)
    if _click_text(page, "修改封面"):
        return True

    page.mouse_click(float(box["x"]), float(box["y"]))
    return True


def _wait_cover_ready(page: Page, timeout: float = 90.0) -> None:
    """Wait until the platform-generated first-frame cover can be edited."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        ready = page.evaluate(
            """
            (() => {
                const txt = document.body.innerText || '';
                const canEdit = Array.from(document.querySelectorAll('div,span,button'))
                    .some(e => {
                        const text = (e.textContent || '').trim();
                        const rect = e.getBoundingClientRect();
                        return (text === '修改封面' || text === '设置封面')
                            && rect.width > 0
                            && rect.height > 0;
                    });
                if (canEdit) return true;
                if (/封面上传中|封面生成中/.test(txt)) return false;
                return false;
            })()
            """
        )
        if ready:
            return
        time.sleep(1)
    raise RuntimeError("等待自动封面生成超时（未出现可编辑封面入口）")


def _mark_latest_image_input(page: Page) -> int:
    """Mark the newest image file input and return the number of candidates."""
    return int(
        page.evaluate(
            """
            (() => {
                document.querySelectorAll('[data-xhs-cover-input="1"]')
                    .forEach(el => delete el.dataset.xhsCoverInput);
                const inputs = Array.from(document.querySelectorAll(
                    'input[type="file"][accept*="image"],'
                    + 'input[type="file"][accept*="jpg"],'
                    + 'input[type="file"][accept*="jpeg"],'
                    + 'input[type="file"][accept*="png"]'
                ));
                if (!inputs.length) return 0;
                inputs[inputs.length - 1].dataset.xhsCoverInput = '1';
                return inputs.length;
            })()
            """
        )
        or 0
    )


def _wait_image_input(page: Page, timeout: float = 15.0) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        count = _mark_latest_image_input(page)
        if count > 0 and page.has_element(MARKED_IMAGE_FILE_INPUT):
            return count
        time.sleep(0.5)
    raise RuntimeError("未找到封面图片上传输入框（封面编辑弹窗可能没打开）")


def _wait_cover_editor_closed(page: Page, timeout: float = 30.0) -> dict[str, Any]:
    """Wait until the cover editor closes after confirming the uploaded image."""
    deadline = time.monotonic() + timeout
    last_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = page.evaluate(
            """
            (() => {
                const text = document.body.innerText || '';
                const modalOpen = !!document.querySelector('.cover-modal, .d-modal');
                return {
                    modalOpen,
                    stillCropping: modalOpen || /封面比例|上传图片|图片大小/.test(text),
                    reviewPassed: /封面效果评估通过|封面预审结果评估通过|封面.*通过/.test(text),
                };
            })()
            """
        ) or {}
        last_state = state
        if not state.get("stillCropping"):
            return state
        time.sleep(0.5)
    raise RuntimeError(f"封面确认后弹窗未关闭: {last_state}")


def set_video_cover(page: Page, cover_path: str) -> dict[str, Any]:
    """Set a custom cover on an already-open video publish page.

    The page must already have a processed video preview. This function does not
    click the final publish button.
    """
    cover_path = os.path.realpath(os.path.expanduser(cover_path))
    if not os.path.exists(cover_path):
        raise FileNotFoundError(f"封面文件不存在: {cover_path}")

    _wait_cover_ready(page)

    if _mark_latest_image_input(page) == 0 and not _click_cover_editor_entry(page):
        raise RuntimeError("未找到封面编辑入口")

    input_count = _wait_image_input(page, timeout=30.0)
    page.set_file_input(MARKED_IMAGE_FILE_INPUT, [cover_path])
    time.sleep(3)

    confirm_clicks = _click_last_confirm(page)
    if confirm_clicks == 0:
        raise RuntimeError("上传后未出现「确定」按钮，封面可能未生效")
    state = _wait_cover_editor_closed(page)
    return {
        "cover": cover_path,
        "image_input_count": input_count,
        "confirm_clicks": confirm_clicks,
        **(state or {}),
    }
