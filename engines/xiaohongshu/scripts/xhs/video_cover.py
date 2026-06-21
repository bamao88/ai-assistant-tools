"""Video cover helpers for Xiaohongshu creator publish pages."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from .cdp import Page

IMAGE_FILE_INPUT = 'input[type=file][accept*="image"]'
MARKED_IMAGE_FILE_INPUT = 'input[type=file][data-xhs-cover-input="1"]'


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


def _wait_cover_ready(page: Page, timeout: float = 90.0) -> None:
    """Wait until the platform-generated first-frame cover can be edited."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        ready = page.evaluate(
            """
            (() => {
                const txt = document.body.innerText || '';
                if (/封面上传中|封面生成中/.test(txt)) return false;
                return Array.from(document.querySelectorAll('div,span'))
                    .some(e => (e.textContent || '').trim() === '修改封面'
                        && e.getBoundingClientRect().width > 0
                        && e.getBoundingClientRect().height > 0);
            })()
            """
        )
        if ready:
            return
        time.sleep(1)
    raise RuntimeError("等待自动封面生成超时（封面上传中一直不消失）")


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


def set_video_cover(page: Page, cover_path: str) -> dict[str, Any]:
    """Set a custom cover on an already-open video publish page.

    The page must already have a processed video preview. This function does not
    click the final publish button.
    """
    cover_path = os.path.realpath(os.path.expanduser(cover_path))
    if not os.path.exists(cover_path):
        raise FileNotFoundError(f"封面文件不存在: {cover_path}")

    _wait_cover_ready(page)

    if not _click_text(page, "修改封面"):
        _click_text(page, "设置封面")

    input_count = _wait_image_input(page)
    page.set_file_input(MARKED_IMAGE_FILE_INPUT, [cover_path])
    time.sleep(3)

    confirm_clicks = _click_last_confirm(page)
    if confirm_clicks == 0:
        raise RuntimeError("上传后未出现「确定」按钮，封面可能未生效")
    time.sleep(2)

    state = page.evaluate(
        """
        (() => ({
            stillCropping: /封面比例/.test(document.body.innerText || ''),
            reviewPassed: /封面预审结果评估通过|封面.*通过/.test(document.body.innerText || ''),
        }))()
        """
    )
    return {
        "cover": cover_path,
        "image_input_count": input_count,
        "confirm_clicks": confirm_clicks,
        **(state or {}),
    }
