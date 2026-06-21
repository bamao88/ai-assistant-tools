"""图文发布，对应 Go xiaohongshu/publish.go（837 行）。"""

from __future__ import annotations

import json
import logging
import random
import re
import time

from .cdp import Page
from .errors import ContentTooLongError, PublishError, TitleTooLongError, UploadTimeoutError
from .selectors import (
    CONTENT_EDITOR,
    CONTENT_LENGTH_ERROR,
    CREATOR_TAB,
    DATETIME_INPUT,
    FILE_INPUT,
    IMAGE_PREVIEW,
    ORIGINAL_SWITCH,
    ORIGINAL_SWITCH_CARD,
    POPOVER,
    PUBLISH_BUTTON,
    SCHEDULE_SWITCH,
    TAG_FIRST_ITEM,
    TAG_TOPIC_CONTAINER,
    TITLE_INPUT,
    TITLE_MAX_SUFFIX,
    UPLOAD_CONTENT,
    UPLOAD_INPUT,
    VISIBILITY_DROPDOWN,
    VISIBILITY_OPTIONS,
)
from .types import PublishImageContent
from .urls import PUBLISH_URL

logger = logging.getLogger(__name__)

PUBLISH_BUTTON_NAMES = ("定时发布", "发布", "立即发布", "提交发布")
MARKED_PUBLISH_BUTTON = '[data-xhs-publish-target="1"]'


def publish_image_content(page: Page, content: PublishImageContent) -> None:
    """发布图文内容（填写表单 + 点击发布）。

    Args:
        page: CDP 页面对象。
        content: 发布内容。

    Raises:
        PublishError: 发布失败。
        UploadTimeoutError: 上传超时。
        TitleTooLongError: 标题超长。
        ContentTooLongError: 正文超长。
    """
    fill_publish_form(page, content)
    click_publish_button(page)


def fill_publish_form(page: Page, content: PublishImageContent) -> None:
    """填写图文发布表单，不点击发布按钮。

    Args:
        page: CDP 页面对象。
        content: 发布内容。

    Raises:
        PublishError: 填写失败。
        UploadTimeoutError: 上传超时。
        TitleTooLongError: 标题超长。
        ContentTooLongError: 正文超长。
    """
    if not content.image_paths:
        raise PublishError("图片不能为空")

    # 导航到发布页
    _navigate_to_publish_page(page)

    # 点击"上传图文" TAB
    _click_publish_tab(page, "上传图文")
    time.sleep(1)

    # 上传图片
    _upload_images(page, content.image_paths)

    # 标签截取
    tags = content.tags[:10] if len(content.tags) > 10 else content.tags
    if len(content.tags) > 10:
        logger.warning("标签数量超过10，截取前10个")

    logger.info(
        "发布内容: title=%s, images=%d, tags=%d, schedule=%s, original=%s, visibility=%s",
        content.title,
        len(content.image_paths),
        len(tags),
        content.schedule_time,
        content.is_original,
        content.visibility,
    )

    # 填写表单（不点击发布）
    _fill_publish_form(
        page,
        content.title,
        content.content,
        tags,
        content.schedule_time,
        content.is_original,
        content.visibility,
    )


def click_publish_button(page: Page) -> None:
    """点击发布按钮。

    Args:
        page: CDP 页面对象。

    Raises:
        PublishError: 点击失败。
    """
    _wait_for_submit_publish_button(page)
    if not _click_submit_publish_button(page):
        raise PublishError("未找到可点击的发布按钮")
    time.sleep(3)
    logger.info("发布完成")


def _wait_for_submit_publish_button(page: Page, timeout: float = 1800.0) -> None:
    """等待最终发布按钮可点击。

    小红书新版发布页把底部按钮封装成 ``xhs-publish-btn`` 自定义元素，
    旧版仍可能是普通 ``button.bg-red``。这里同时兼容两种结构。
    """
    start = time.monotonic()
    logger.info("开始等待发布按钮可点击")
    while time.monotonic() - start < timeout:
        state = _mark_dom_publish_button(page)
        if state.get("clickable"):
            return
        if _has_accessible_publish_button(page):
            return
        time.sleep(1)
    raise UploadTimeoutError("等待发布按钮可点击超时")


def _click_submit_publish_button(page: Page) -> bool:
    """点击最终发布/定时发布按钮。"""
    if _click_accessible_publish_button(page):
        return True

    state = _mark_dom_publish_button(page)
    if not state.get("clickable"):
        return False

    if state.get("kind") == "xhs-publish-btn":
        point = state.get("point") or {}
        x = float(point.get("x", 0))
        y = float(point.get("y", 0))
        if x > 0 and y > 0:
            page.mouse_move(x, y)
            time.sleep(0.05)
            page.mouse_click(x, y)
            return True

    page.click_element(MARKED_PUBLISH_BUTTON)
    return True


def _scroll_publish_page_to_bottom(page: Page) -> None:
    """滚动新版发布页内部滚动容器到底部，让 sticky 提交组件挂载/可见。"""
    page.evaluate(
        """
        (() => {
            const scroller = document.querySelector('.publish-page');
            if (scroller && scroller.scrollHeight > scroller.clientHeight) {
                scroller.scrollTo(0, scroller.scrollHeight);
            }
        })()
        """
    )


def _mark_dom_publish_button(page: Page) -> dict:
    """在 DOM 中标记一个可点击的最终发布按钮，并返回定位状态。"""
    result = page.evaluate(
        f"""
        (() => {{
            document.querySelectorAll({json.dumps(MARKED_PUBLISH_BUTTON)})
                .forEach(el => delete el.dataset.xhsPublishTarget);

            const scroller = document.querySelector('.publish-page');
            if (scroller && scroller.scrollHeight > scroller.clientHeight) {{
                scroller.scrollTo(0, scroller.scrollHeight);
            }}

            const visible = el => {{
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 0
                    && rect.height > 0
                    && style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && style.opacity !== '0';
            }};
            const disabled = el => {{
                if (el.disabled) return true;
                if (el.getAttribute('aria-disabled') === 'true') return true;
                if (/disabled|disable/.test(String(el.className || ''))) return true;
                return false;
            }};
            const mark = (el, kind, point = null) => {{
                el.dataset.xhsPublishTarget = '1';
                return {{clickable: true, kind, point}};
            }};

            const legacy = document.querySelector({json.dumps(PUBLISH_BUTTON)});
            if (legacy && visible(legacy) && !disabled(legacy)) {{
                return mark(legacy, 'legacy');
            }}

            const xhsBtn = document.querySelector('xhs-publish-btn');
            if (xhsBtn && visible(xhsBtn) && xhsBtn.getAttribute('submit-disabled') !== 'true') {{
                const rect = xhsBtn.getBoundingClientRect();
                const hasSave = xhsBtn.getAttribute('is-save-draft') === 'true'
                    && xhsBtn.getAttribute('save-disabled') !== 'true';
                const buttonWidth = Math.min(120, Math.max(80, rect.width * 0.14));
                const gap = 24;
                const x = rect.left + rect.width / 2 + (hasSave ? (buttonWidth + gap) / 2 : 0);
                const y = rect.top + rect.height / 2;
                return mark(xhsBtn, 'xhs-publish-btn', {{x, y}});
            }}

            const names = new Set({json.dumps(list(PUBLISH_BUTTON_NAMES))});
            const candidates = Array.from(document.querySelectorAll(
                'button, [role="button"], .d-button, .custom-button, [class*="button"], [class*="btn"]'
            )).filter(el => {{
                if (!visible(el) || disabled(el)) return false;
                if (el.closest('.menu-container')) return false;
                const text = (el.innerText || el.textContent || '').replace(/\\s+/g, '').trim();
                return names.has(text);
            }});
            candidates.sort((a, b) => {{
                const ar = a.getBoundingClientRect();
                const br = b.getBoundingClientRect();
                const ap = window.getComputedStyle(a).position;
                const bp = window.getComputedStyle(b).position;
                const as = (ap === 'fixed' || ap === 'sticky' ? 10000 : 0) + ar.top;
                const bs = (bp === 'fixed' || bp === 'sticky' ? 10000 : 0) + br.top;
                return bs - as;
            }});
            if (candidates.length) {{
                return mark(candidates[0], 'text-button');
            }}

            return {{clickable: false}};
        }})()
        """
    )
    return result if isinstance(result, dict) else {"clickable": False}


def _has_accessible_publish_button(page: Page) -> bool:
    """检查 AX tree 中是否存在可点击的发布按钮。"""
    return bool(_get_accessible_publish_button_rect(page))


def _click_accessible_publish_button(page: Page) -> bool:
    """通过可访问性树定位发布按钮并点击。

    ``xhs-publish-btn`` 使用闭合实现时，DOM 里只能看到宿主节点；AX tree
    仍能暴露真实 button 和它的 viewport bounds。
    """
    rect = _get_accessible_publish_button_rect(page)
    if not rect:
        return False
    x = rect["x"] + rect["width"] / 2
    y = rect["y"] + rect["height"] / 2
    page.mouse_move(x, y)
    time.sleep(0.05)
    page.mouse_click(x, y)
    return True


def _get_accessible_publish_button_rect(page: Page) -> dict | None:
    """返回 AX tree 中发布按钮的 viewport rect。"""
    try:
        _scroll_publish_page_to_bottom(page)
        page._send_session("DOM.getDocument", {"depth": -1, "pierce": True})
        page._send_session("Accessibility.enable")
        tree = page._send_session("Accessibility.getFullAXTree", {})
    except Exception:
        return None

    nodes = tree.get("nodes", [])
    for button_name in PUBLISH_BUTTON_NAMES:
        for node in nodes:
            if _ax_value(node.get("role")) != "button":
                continue
            if _ax_value(node.get("name")) != button_name:
                continue
            if _ax_node_disabled(node):
                continue
            rect = _ax_node_rect(page, node)
            if rect:
                return rect
    return None


def _ax_value(value: object) -> object:
    if isinstance(value, dict):
        return value.get("value")
    return value


def _ax_node_disabled(node: dict) -> bool:
    for prop in node.get("properties", []):
        if prop.get("name") != "disabled":
            continue
        value = _ax_value(prop.get("value"))
        if value is True or value == "true":
            return True
    return False


def _ax_node_rect(page: Page, node: dict) -> dict | None:
    backend_id = node.get("backendDOMNodeId")
    if not backend_id:
        return None
    try:
        pushed = page._send_session(
            "DOM.pushNodesByBackendIdsToFrontend",
            {"backendNodeIds": [backend_id]},
        )
        node_ids = pushed.get("nodeIds") or []
        if not node_ids:
            return None
        resolved = page._send_session("DOM.resolveNode", {"nodeId": node_ids[0]})
        object_id = resolved.get("object", {}).get("objectId")
        if not object_id:
            return None
        rect_result = page._send_session(
            "Runtime.callFunctionOn",
            {
                "objectId": object_id,
                "functionDeclaration": """
                    function() {
                        const r = this.getBoundingClientRect();
                        return {x: r.left, y: r.top, width: r.width, height: r.height};
                    }
                """,
                "returnByValue": True,
            },
        )
    except Exception:
        return None

    rect = rect_result.get("result", {}).get("value")
    if not isinstance(rect, dict):
        return None
    if rect.get("width", 0) <= 0 or rect.get("height", 0) <= 0:
        return None
    return rect


def save_as_draft(page: Page) -> None:
    """点击「暂存离开」按钮保存草稿。"""
    clicked = page.evaluate(
        """
        (() => {
            const buttons = document.querySelectorAll('button.custom-button');
            for (const btn of buttons) {
                if (btn.textContent.trim() === '暂存离开') {
                    btn.click();
                    return true;
                }
            }
            return false;
        })()
        """
    )
    if clicked:
        time.sleep(2)
        logger.info("已点击「暂存离开」，内容已保存到草稿箱")
    else:
        logger.warning("未找到「暂存离开」按钮")
        raise PublishError("未找到「暂存离开」按钮")


# ========== 页面导航 ==========


def _navigate_to_publish_page(page: Page) -> None:
    """导航到发布页面。"""
    page.navigate(PUBLISH_URL)
    page.wait_for_load(timeout=300)
    time.sleep(3)
    page.wait_dom_stable()
    time.sleep(2)


def _click_publish_tab(page: Page, tab_name: str) -> None:
    """点击发布页 TAB（上传图文/上传视频）。"""
    def _is_tab_active() -> bool:
        """检查目标 tab 是否已处于 active 状态（任意匹配元素含 active 类即算）。"""
        result = page.evaluate(
            f"""
            (() => {{
                const tabs = document.querySelectorAll('div.creator-tab');
                for (const t of tabs) {{
                    const span = t.querySelector('span.title');
                    const text = (span ? span.textContent : t.textContent).trim();
                    if (text === {json.dumps(tab_name)} && t.classList.contains('active')) {{
                        return true;
                    }}
                }}
                return false;
            }})()
            """
        )
        return bool(result)

    # 已处于目标 tab，直接返回
    if _is_tab_active():
        return

    # 策略0: CDP 原生鼠标事件，通过 data-hp-kind 定位 HP overlay（isTrusted=true）
    hp_selector = f'[data-hp-kind="creator-tab-{tab_name}"]'
    try:
        page.click_element(hp_selector)
        time.sleep(0.5)
        if _is_tab_active():
            return
    except Exception:
        pass

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        # 查找匹配的 TAB（支持多种结构）
        found = page.evaluate(
            f"""
            (() => {{
                // 策略1: 查找 div.creator-tab（过滤隐藏元素）
                let tabs = document.querySelectorAll({json.dumps(CREATOR_TAB)});
                for (const tab of tabs) {{
                    const titleSpan = tab.querySelector('span.title');
                    const tabText = titleSpan ? titleSpan.textContent.trim() : tab.textContent.trim();
                    if (tabText === {json.dumps(tab_name)}) {{
                        const rect = tab.getBoundingClientRect();
                        const style = window.getComputedStyle(tab);
                        // 跳过隐藏或被移出视口的元素
                        if (rect.width === 0 || rect.height === 0) continue;
                        if (rect.left < 0 || rect.top < 0) continue;
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        const x = rect.left + rect.width / 2;
                        const y = rect.top + rect.height / 2;
                        const target = document.elementFromPoint(x, y);
                        if (target === tab || tab.contains(target)) {{
                            tab.click();
                            return 'clicked';
                        }}
                        // HP overlay can sit above the visible tab. In that case,
                        // dispatch the click on the visible tab instead of bailing
                        // before the fallback strategies get a chance to run.
                        tab.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, cancelable: true}}));
                        tab.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true, cancelable: true}}));
                        tab.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}}));
                        if (titleSpan) {{
                            titleSpan.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}}));
                        }}
                        return 'clicked';
                    }}
                }}
                
                // 策略2: 查找任意包含目标文本的元素
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {{
                    if (el.children.length === 0 && el.textContent.trim() === {json.dumps(tab_name)}) {{
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if (rect.width === 0 || rect.height === 0) continue;
                        if (rect.left < 0 || rect.top < 0) continue;
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        el.click();
                        return 'clicked';
                    }}
                }}
                
                // 策略3: 通过 data-hp-kind 找 HP 注入的 overlay 元素并 force-click
                const hpKind = 'creator-tab-' + {json.dumps(tab_name)};
                const hpEl = document.querySelector(`[data-hp-kind="${{hpKind}}"]`);
                if (hpEl) {{
                    hpEl.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}}));
                    return 'clicked';
                }}

                // 策略4: 找到所有匹配 tab，忽略位置限制直接 force-click
                for (const tab of tabs) {{
                    const titleSpan = tab.querySelector('span.title');
                    const tabText = titleSpan ? titleSpan.textContent.trim() : tab.textContent.trim();
                    if (tabText === {json.dumps(tab_name)}) {{
                        tab.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}}));
                        return 'clicked';
                    }}
                }}

                return 'not_found';
            }})()
            """
        )

        if found == "clicked":
            return

        if found == "blocked":
            # 尝试移除弹窗
            _remove_pop_cover(page)

        time.sleep(0.2)

    # 调试：输出页面信息
    debug_info = page.evaluate("""
        (() => {
            const creatorTabs = document.querySelectorAll('div.creator-tab');
            const tabTexts = Array.from(creatorTabs).map(t => ({
                text: t.textContent.trim(),
                html: t.outerHTML.substring(0, 200)
            }));
            const url = window.location.href;
            return JSON.stringify({url, tabCount: creatorTabs.length, tabs: tabTexts});
        })()
    """)
    logger.error("调试信息: %s", debug_info)
    raise PublishError(f"没有找到发布 TAB - {tab_name}")


def _remove_pop_cover(page: Page) -> None:
    """移除弹窗遮挡。"""
    if page.has_element(POPOVER):
        page.remove_element(POPOVER)
    # 点击空位置
    x = 380 + random.randint(0, 100)
    y = 20 + random.randint(0, 60)
    page.mouse_click(float(x), float(y))


# ========== 图片上传 ==========


def _upload_images(page: Page, image_paths: list[str]) -> None:
    """逐张上传图片。"""
    import os

    valid_paths = [p for p in image_paths if os.path.exists(p)]
    if not valid_paths:
        raise PublishError("没有有效的图片文件")

    for i, path in enumerate(valid_paths):
        selector = UPLOAD_INPUT if i == 0 else FILE_INPUT
        logger.info("上传第 %d 张图片: %s", i + 1, path)

        page.set_file_input(selector, [path])
        _wait_for_upload_complete(page, i + 1)
        time.sleep(1)


def _wait_for_upload_complete(page: Page, expected_count: int) -> None:
    """等待图片上传完成。"""
    max_wait = 60.0
    start = time.monotonic()

    while time.monotonic() - start < max_wait:
        count = page.get_elements_count(IMAGE_PREVIEW)
        if count >= expected_count:
            logger.info("图片上传完成: %d", count)
            return
        time.sleep(0.5)

    raise UploadTimeoutError(f"第{expected_count}张图片上传超时(60s)")


# ========== 表单提交 ==========


def _extract_hashtags_from_content(content: str, tags: list[str]) -> tuple[str, list[str]]:
    """从正文末尾提取 hashtag 行，合并到 tags 列表。

    Returns:
        (cleaned_content, merged_tags)
    """
    lines = content.rstrip().split("\n")
    # 检查最后一行是否全是 #tag 格式
    if lines:
        last_line = lines[-1].strip()
        hashtag_pattern = re.compile(r"^(#\S+\s*)+$")
        if hashtag_pattern.match(last_line):
            # 提取 hashtag
            extracted = re.findall(r"#(\S+)", last_line)
            # 合并到 tags（去重）
            existing = {t.lstrip("#") for t in tags}
            merged = list(tags)
            for t in extracted:
                if t not in existing:
                    merged.append(t)
                    existing.add(t)
            # 去掉最后一行
            cleaned = "\n".join(lines[:-1]).rstrip()
            logger.info("从正文末尾提取 %d 个标签，合并后共 %d 个", len(extracted), len(merged))
            return cleaned, merged
    return content, list(tags)


def _fill_publish_form(
    page: Page,
    title: str,
    content: str,
    tags: list[str],
    schedule_time: str | None,
    is_original: bool,
    visibility: str,
) -> None:
    """填写表单（不点击发布）。"""
    # 从正文末尾提取 hashtag 并合并到 tags
    content, tags = _extract_hashtags_from_content(content, tags)

    # 标题——填写前先校验长度，超限直接报错（由 AI 重新生成标题）
    from title_utils import calc_title_length

    title_len = calc_title_length(title)
    if title_len > 20:
        raise TitleTooLongError(str(title_len), "20")

    page.input_text(TITLE_INPUT, title)
    time.sleep(0.5)
    _check_title_max_length(page)
    logger.info("标题长度检查通过")
    time.sleep(1)

    # 正文
    content_selector = _find_content_element(page)
    page.input_content_editable(content_selector, content)

    # 回点标题（增强稳定性）
    time.sleep(1)
    page.click_element(TITLE_INPUT)
    logger.info("已回点标题输入框")

    # 标签
    if tags:
        _input_tags(page, content_selector, tags)
    time.sleep(1)
    _check_content_max_length(page)
    logger.info("正文长度检查通过")

    # 定时发布
    if schedule_time:
        _set_schedule_publish(page, schedule_time)

    # 可见范围
    _set_visibility(page, visibility)

    # 原创声明
    if is_original:
        try:
            _set_original(page)
            logger.info("已声明原创")
        except Exception as e:
            logger.warning("设置原创声明失败: %s", e)

    logger.info("表单填写完成，等待确认发布")


def _find_content_element(page: Page) -> str:
    """查找内容输入框（兼容两种 UI）。"""
    if page.has_element(CONTENT_EDITOR):
        return CONTENT_EDITOR

    # 查找带 placeholder 的 p 元素的 textbox 父元素
    found = page.evaluate(
        """
        (() => {
            const ps = document.querySelectorAll('p');
            for (const p of ps) {
                const placeholder = p.getAttribute('data-placeholder');
                if (placeholder && placeholder.includes('输入正文描述')) {
                    let current = p;
                    for (let i = 0; i < 5; i++) {
                        current = current.parentElement;
                        if (!current) break;
                        if (current.getAttribute('role') === 'textbox') {
                            return 'found';
                        }
                    }
                }
            }
            return '';
        })()
        """
    )
    if found == "found":
        return "[role='textbox']"

    raise PublishError("没有找到内容输入框")


def _check_title_max_length(page: Page) -> None:
    """检查标题长度是否超限。"""
    text = page.get_element_text(TITLE_MAX_SUFFIX)
    if text:
        parts = text.split("/")
        if len(parts) == 2:
            raise TitleTooLongError(parts[0], parts[1])
        raise TitleTooLongError(text, "?")


def _check_content_max_length(page: Page) -> None:
    """检查正文长度是否超限。"""
    text = page.get_element_text(CONTENT_LENGTH_ERROR)
    if text:
        parts = text.split("/")
        if len(parts) == 2:
            raise ContentTooLongError(parts[0], parts[1])
        raise ContentTooLongError(text, "?")


# ========== 标签输入 ==========

MARKED_TAG_ITEM = '[data-xhs-tag-target="1"]'
TAG_SUGGESTION_WAIT_SECONDS = (10.0, 30.0, 60.0)


def _input_tags(page: Page, content_selector: str, tags: list[str]) -> None:
    """输入标签。"""
    time.sleep(1)

    # 先点击正文编辑器，确保焦点在正文而非标题
    page.click_element(content_selector)
    time.sleep(0.3)

    # 把光标移动到正文“真正末尾”。
    # 注意：不能只靠 ArrowDown —— ArrowDown 会保留水平列位置，在最后一行会停在
    # 同列的中间，导致话题被插进句子中间（历史 bug）。用 Range collapse 到末尾。
    if not page.move_caret_to_end(content_selector):
        # 兜底：极端情况下没定位到可编辑元素，退回原来的逐行下移
        for _ in range(20):
            page.press_key("ArrowDown")
            time.sleep(0.01)
    time.sleep(0.2)

    # 按两次回车换行
    page.press_key("Enter")
    page.press_key("Enter")
    time.sleep(1)

    for tag in tags:
        tag = tag.lstrip("#")
        _input_single_tag(page, content_selector, tag)


def _input_single_tag(page: Page, content_selector: str, tag: str) -> None:
    """输入单个标签。"""
    for attempt, wait_seconds in enumerate(TAG_SUGGESTION_WAIT_SECONDS, start=1):
        before_count = _count_inserted_topics(page, tag)
        _type_raw_tag(page, tag)
        selected_text = _wait_for_tag_suggestion(page, tag, wait_seconds)
        if selected_text:
            page.click_element(MARKED_TAG_ITEM)
            if _wait_for_topic_inserted(page, tag, before_count):
                logger.info("点击标签联想并确认插入: %s -> %s", tag, selected_text)
                time.sleep(1.0)
                return
            logger.warning("标签联想已点击但未生成话题，删除后重试: #%s -> %s", tag, selected_text)
        else:
            logger.warning(
                "未找到精确匹配的标签联想，删除后重试: #%s (第%d/%d轮, 等待%.0fs)",
                tag,
                attempt,
                len(TAG_SUGGESTION_WAIT_SECONDS),
                wait_seconds,
            )

        _clear_raw_tag_input(page, tag)
        time.sleep(1.0)

    raise PublishError(f"多次重试后仍未找到标签联想，停止发布: #{tag}")


def _type_raw_tag(page: Page, tag: str) -> None:
    """输入待联想的原始 #标签文本。"""
    page.type_text("#", delay_ms=0)
    time.sleep(0.3)
    for char in tag:
        page.type_text(char, delay_ms=0)
        time.sleep(random.uniform(0.05, 0.12))
    time.sleep(1.0)


def _wait_for_tag_suggestion(page: Page, tag: str, timeout: float) -> str:
    """等待标签联想项出现并标记目标项。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        selected_text = _mark_tag_suggestion(page, tag)
        if selected_text:
            return selected_text
        time.sleep(0.5)
    return ""


def _clear_raw_tag_input(page: Page, tag: str) -> None:
    """删除本轮输入的原始 #标签，准备重新触发联想。"""
    page.press_key("Escape")
    time.sleep(0.2)
    for _ in range(len(tag) + 1):
        page.press_key("Backspace")
        time.sleep(0.03)


def _count_inserted_topics(page: Page, tag: str) -> int:
    """统计编辑器里已经插入的同名话题数量。"""
    return int(
        page.evaluate(
            f"""
            (() => {{
                const want = {json.dumps(tag.lstrip("#"))};
                const normalize = text => text
                    .replace(/^#/, '')
                    .replace(/新建话题/g, '')
                    .replace(/\\[话题\\]/g, '')
                    .replace(/\\s+/g, '')
                    .trim();
                return Array.from(document.querySelectorAll('[contenteditable="true"] a.tiptap-topic'))
                    .filter(a => {{
                        const raw = a.getAttribute('data-topic') || '';
                        let name = '';
                        try {{ name = JSON.parse(raw).name || ''; }} catch (_e) {{}}
                        return name === want || normalize(a.textContent || '') === want;
                    }}).length;
            }})()
            """
        )
        or 0
    )


def _wait_for_topic_inserted(page: Page, tag: str, before_count: int) -> bool:
    """等待点击联想后，同名话题真正写入编辑器。"""
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if _count_inserted_topics(page, tag) > before_count:
            return True
        time.sleep(0.2)
    return False


def _mark_tag_suggestion(page: Page, tag: str) -> str:
    """标记一个可见标签联想项，优先选择文本精确匹配的项。"""
    return str(
        page.evaluate(
            f"""
            (() => {{
                document.querySelectorAll({json.dumps(MARKED_TAG_ITEM)})
                    .forEach(el => delete el.dataset.xhsTagTarget);
                const container = document.querySelector({json.dumps(TAG_TOPIC_CONTAINER)});
                if (!container) return '';
                const items = Array.from(container.querySelectorAll({json.dumps(TAG_FIRST_ITEM)}))
                    .filter(el => {{
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.width > 0
                            && rect.height > 0
                            && style.display !== 'none'
                            && style.visibility !== 'hidden'
                            && (el.textContent || '').trim();
                    }});
                if (!items.length) return '';

                const want = {json.dumps(tag.lstrip("#"))};
                const label = el => {{
                    const name = el.querySelector('.name');
                    return (name ? name.textContent : el.textContent) || '';
                }};
                const normalize = text => text
                    .replace(/^#/, '')
                    .replace(/新建话题/g, '')
                    .replace(/\\[话题\\]/g, '')
                    .replace(/\\s+/g, '')
                    .trim();
                const exact = items.find(el => normalize(label(el)) === want);
                if (!exact) return '';
                exact.dataset.xhsTagTarget = '1';
                return label(exact).trim();
            }})()
            """
        )
        or ""
    )


# ========== 定时发布 ==========


def _set_schedule_publish(page: Page, schedule_time: str) -> None:
    """设置定时发布。"""
    from datetime import datetime

    # 解析 ISO8601 时间
    try:
        dt = datetime.fromisoformat(schedule_time)
    except ValueError as e:
        raise PublishError(f"定时发布时间格式错误: {e}") from e

    # 点击定时发布开关
    page.click_element(SCHEDULE_SWITCH)
    time.sleep(0.8)

    # 设置日期时间
    datetime_str = dt.strftime("%Y-%m-%d %H:%M")
    page.select_all_text(DATETIME_INPUT)
    page.input_text(DATETIME_INPUT, datetime_str)
    time.sleep(0.5)

    logger.info("已设置定时发布: %s", datetime_str)


# ========== 可见范围 ==========


def _set_visibility(page: Page, visibility: str) -> None:
    """设置可见范围。"""
    if not visibility or visibility == "公开可见":
        logger.info("可见范围: 公开可见（默认）")
        return

    supported = {"仅自己可见", "仅互关好友可见"}
    if visibility not in supported:
        raise PublishError(
            f"不支持的可见范围: {visibility}，支持: 公开可见、仅自己可见、仅互关好友可见"
        )

    # 点击下拉框
    page.click_element(VISIBILITY_DROPDOWN)
    time.sleep(0.5)

    # 查找并点击目标选项
    clicked = page.evaluate(
        f"""
        (() => {{
            const opts = document.querySelectorAll({json.dumps(VISIBILITY_OPTIONS)});
            for (const opt of opts) {{
                if (opt.textContent.includes({json.dumps(visibility)})) {{
                    opt.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )

    if not clicked:
        raise PublishError(f"未找到可见范围选项: {visibility}")

    logger.info("已设置可见范围: %s", visibility)
    time.sleep(0.2)


# ========== 原创声明 ==========


def _set_original(page: Page) -> None:
    """设置原创声明。"""
    # 查找原创声明卡片并点击开关
    result = page.evaluate(
        f"""
        (() => {{
            const cards = document.querySelectorAll({json.dumps(ORIGINAL_SWITCH_CARD)});
            for (const card of cards) {{
                if (!card.textContent.includes('原创声明')) continue;
                const sw = card.querySelector({json.dumps(ORIGINAL_SWITCH)});
                if (!sw) continue;
                const input = sw.querySelector('input[type="checkbox"]');
                if (input && input.checked) return 'already_on';
                sw.click();
                return 'clicked';
            }}
            return 'not_found';
        }})()
        """
    )

    if result == "already_on":
        logger.info("原创声明已开启")
        return

    if result == "not_found":
        raise PublishError("未找到原创声明选项")

    time.sleep(0.5)

    # 处理确认弹窗
    _confirm_original_declaration(page)


def _confirm_original_declaration(page: Page) -> None:
    """处理原创声明确认弹窗。"""
    time.sleep(0.8)

    # 勾选 checkbox
    page.evaluate(
        """
        (() => {
            const footers = document.querySelectorAll('div.footer');
            for (const footer of footers) {
                if (!footer.textContent.includes('原创声明须知')) continue;
                const cb = footer.querySelector('div.d-checkbox input[type="checkbox"]');
                if (cb && !cb.checked) cb.click();
                return;
            }
        })()
        """
    )
    time.sleep(0.5)

    # 点击声明原创按钮
    result = page.evaluate(
        """
        (() => {
            const footers = document.querySelectorAll('div.footer');
            for (const footer of footers) {
                if (!footer.textContent.includes('声明原创')) continue;
                const btn = footer.querySelector('button.custom-button');
                if (btn) {
                    if (btn.classList.contains('disabled') || btn.disabled) {
                        const cb = footer.querySelector('div.d-checkbox input[type="checkbox"]');
                        if (cb && !cb.checked) cb.click();
                        return 'button_disabled';
                    }
                    btn.click();
                    return 'clicked';
                }
            }
            return 'button_not_found';
        })()
        """
    )

    if result == "button_not_found":
        raise PublishError("未找到声明原创按钮")
    if result == "button_disabled":
        raise PublishError("声明原创按钮仍处于禁用状态")

    logger.info("已成功点击声明原创按钮")
    time.sleep(0.3)
