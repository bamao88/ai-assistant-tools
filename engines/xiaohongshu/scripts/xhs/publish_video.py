"""视频发布，对应 Go xiaohongshu/publish_video.go。"""

from __future__ import annotations

import logging
import os
import time

from .cdp import Page
from .errors import PublishError, UploadTimeoutError
from .publish import (
    _click_publish_tab,
    _find_content_element,
    _click_submit_publish_button,
    _input_tags,
    _navigate_to_publish_page,
    _set_original,
    _set_schedule_publish,
    _set_visibility,
    _wait_for_submit_publish_button,
)
from .selectors import (
    FILE_INPUT,
    TITLE_INPUT,
    UPLOAD_INPUT,
)
from .types import PublishVideoContent
from .video_cover import set_video_cover

logger = logging.getLogger(__name__)


def publish_video_content(page: Page, content: PublishVideoContent) -> None:
    """发布视频内容（填写表单 + 点击发布）。

    Args:
        page: CDP 页面对象。
        content: 视频发布内容。

    Raises:
        PublishError: 发布失败。
        UploadTimeoutError: 上传/处理超时。
    """
    fill_publish_video_form(page, content)
    click_publish_video_button(page)


def fill_publish_video_form(page: Page, content: PublishVideoContent) -> None:
    """填写视频发布表单，不点击发布按钮。

    Args:
        page: CDP 页面对象。
        content: 视频发布内容。

    Raises:
        PublishError: 填写失败。
        UploadTimeoutError: 上传/处理超时。
    """
    if not content.video_path:
        raise PublishError("视频不能为空")

    # 导航到发布页
    _navigate_to_publish_page(page)

    # 点击"上传视频" TAB
    _click_publish_tab(page, "上传视频")
    time.sleep(1)

    # 上传视频
    _upload_video(page, content.video_path)

    # 填写表单（不点击发布）
    _fill_publish_video_form(
        page,
        content.title,
        content.content,
        content.tags,
        content.schedule_time,
        content.visibility,
        content.is_original,
    )

    if content.cover_path:
        set_video_cover(page, content.cover_path)
        logger.info("视频封面已设置: %s", content.cover_path)


def click_publish_video_button(page: Page) -> None:
    """点击视频发布按钮。

    Args:
        page: CDP 页面对象。
    """
    _wait_for_publish_button_clickable(page)
    if not _click_submit_publish_button(page):
        raise PublishError("未找到可点击的视频发布按钮")
    time.sleep(3)
    logger.info("视频发布完成")


def _upload_video(page: Page, video_path: str) -> None:
    """上传视频文件。"""
    video_path = os.path.realpath(os.path.expanduser(video_path))
    if not os.path.exists(video_path):
        raise PublishError(f"视频文件不存在: {video_path}")

    # 查找上传输入框
    selector = UPLOAD_INPUT if page.has_element(UPLOAD_INPUT) else FILE_INPUT
    page.set_file_input(selector, [video_path])

    # 等待视频处理完成（出现 video 预览且无上传进度）。
    # 注意：不能在这里等"发布按钮可点击"——发布按钮要等标题等内容填好后才会变红可点，
    # 而填写发生在本步之后，先等按钮会造成死锁（历史 bug）。
    _wait_for_video_processed(page)
    logger.info("视频上传/处理完成")


def _wait_for_video_processed(page: Page) -> None:
    """等待视频上传 + 处理完成。

    判定信号：页面出现 <video> 预览（带 blob/http 源），且不再显示上传/处理进度。
    """
    max_wait = 1800.0  # 30 分钟
    max_stalled_upload_wait = 180.0
    start = time.monotonic()
    last_upload_progress = ""
    last_upload_progress_at = start

    logger.info("开始等待视频处理完成")

    while time.monotonic() - start < max_wait:
        failure_text = page.evaluate(
            """
            (() => {
                const t = document.body.innerText || '';
                const m = t.match(/.{0,40}(上传失败|网络异常|视频上传失败).{0,60}/);
                return m ? m[0] : '';
            })()
            """
        )
        if failure_text:
            raise PublishError(f"视频上传失败: {failure_text}")

        upload_progress = page.evaluate(
            """
            (() => {
                const text = document.body.innerText || '';
                const match = text.match(/上传中\\s*\\d+%/);
                return match ? match[0].replace(/\\s+/g, ' ') : '';
            })()
            """
        )
        if upload_progress:
            now = time.monotonic()
            if upload_progress != last_upload_progress:
                logger.info("视频上传进度: %s", upload_progress)
                last_upload_progress = upload_progress
                last_upload_progress_at = now
            elif now - last_upload_progress_at > max_stalled_upload_wait:
                raise UploadTimeoutError(
                    f"视频上传进度长时间无变化: {upload_progress}。"
                    "请检查小红书上传域名是否已全部走本地网关。"
                )

        done = page.evaluate(
            """
            (() => {
                const v = document.querySelector('video');
                if (!v) return false;
                const src = v.currentSrc || v.src || '';
                if (!src) return false;
                const t = document.body.innerText || '';
                if (/上传中|视频上传中|处理中/.test(t)) return false;
                return true;
            })()
            """
        )
        if done:
            return
        time.sleep(1)

    raise UploadTimeoutError("等待视频处理完成超时(30分钟)")


def _wait_for_publish_button_clickable(page: Page) -> None:
    """等待发布按钮可点击（视频处理可能需要较长时间）。"""
    logger.info("开始等待发布按钮可点击(视频)")
    _wait_for_submit_publish_button(page, timeout=1800.0)


def _fill_publish_video_form(
    page: Page,
    title: str,
    content: str,
    tags: list[str],
    schedule_time: str | None,
    visibility: str,
    is_original: bool = False,
) -> None:
    """填写视频表单（不点击发布）。"""
    # 标题
    page.input_text(TITLE_INPUT, title)
    time.sleep(1)

    # 正文 + 标签
    content_selector = _find_content_element(page)
    page.input_content_editable(content_selector, content)

    # 回点标题
    time.sleep(1)
    page.click_element(TITLE_INPUT)

    if tags:
        _input_tags(page, content_selector, tags)
    time.sleep(1)

    # 原创声明
    if is_original:
        try:
            _set_original(page)
            logger.info("已声明原创")
        except Exception as e:  # noqa: BLE001
            logger.warning("设置原创声明失败: %s", e)

    # 定时发布
    if schedule_time:
        _set_schedule_publish(page, schedule_time)

    # 可见范围
    _set_visibility(page, visibility)

    logger.info("视频表单填写完成，等待确认发布")
