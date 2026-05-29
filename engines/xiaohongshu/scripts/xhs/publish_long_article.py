"""长文发布模式，参考 cdp_publish.py 的长文工作流。"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .cdp import Page
from .errors import PublishError
from .publish import _click_publish_tab, _navigate_to_publish_page
from .selectors import (
    AUTO_FORMAT_BUTTON_TEXT,
    CONTENT_EDITOR,
    LONG_ARTICLE_TITLE,
    NEW_CREATION_BUTTON_TEXT,
    NEXT_STEP_BUTTON_TEXT,
    TEMPLATE_CARD,
    TEMPLATE_TITLE,
)

logger = logging.getLogger(__name__)

# 等待常量
_AUTO_FORMAT_WAIT = 3.0
_TEMPLATE_WAIT_ROUNDS = 15
_PAGE_LOAD_WAIT = 3.0


def publish_long_article(
    page: Page,
    title: str,
    content: str,
    image_paths: list[str] | None = None,
) -> list[str]:
    """长文发布：导航 → 点击写长文 → 新的创作 → 填写标题正文 → 一键排版。

    返回可用模板名称列表。

    Args:
        page: CDP 页面对象。
        title: 长文标题。
        content: 长文正文（段落用换行分隔）。
        image_paths: 可选的图片路径列表（插入编辑器）。

    Returns:
        可用模板名称列表。

    Raises:
        PublishError: 操作失败。
    """
    # 1. 导航到发布页
    _navigate_to_publish_page(page)

    # 2. 点击"写长文"TAB
    _click_publish_tab(page, "写长文")
    time.sleep(1)

    # 3. 点击"新的创作"
    _click_new_creation(page)

    # 4. 填写标题（textarea）
    _fill_long_title(page, title)

    # 5. 填写正文（TipTap 编辑器）
    # 一键排版需要足够内容才能生成模板，内容不足时自动填充
    if len(content) < 150:
        filler = "这是占位内容，图片将替换本文所有内容。" * 5
        padded_content = content + "\n" + filler
        logger.info("内容太短 (%d 字)，自动填充至 %d 字以触发模板生成", len(content), len(padded_content))
        content = padded_content
    _fill_long_content(page, content)

    # 6. 可选：插入图片到编辑器
    if image_paths:
        _insert_images_to_editor(page, image_paths)

    # 7. 点击"一键排版"
    _click_auto_format(page)

    # 8. 等待模板加载并返回名称列表
    loaded = _wait_for_templates(page)
    template_names = get_template_names(page)
    if loaded and template_names:
        # 自动选第一个模板，确保"下一步"按钮可用
        select_template(page, template_names[0])
        logger.info("已自动选择模板: %s", template_names[0])
    elif not loaded:
        logger.warning("模板未加载，下一步按钮可能不可用")
    logger.info("模板加载完成: %s", template_names)
    return template_names


def get_template_names(page: Page) -> list[str]:
    """获取当前可用的排版模板名称列表。

    Args:
        page: CDP 页面对象。

    Returns:
        模板名称列表。
    """
    names = page.evaluate(
        f"""
        (() => {{
            const cards = document.querySelectorAll({json.dumps(TEMPLATE_CARD)});
            const names = [];
            for (const card of cards) {{
                const title = card.querySelector({json.dumps(TEMPLATE_TITLE)});
                names.push(title ? title.textContent.trim() : 'Template ' + names.length);
            }}
            return names;
        }})()
        """
    )
    return names or []


def select_template(page: Page, template_name: str) -> bool:
    """选择指定名称的排版模板。

    Args:
        page: CDP 页面对象。
        template_name: 模板名称。

    Returns:
        是否成功选择。
    """
    clicked = page.evaluate(
        f"""
        (() => {{
            const cards = document.querySelectorAll({json.dumps(TEMPLATE_CARD)});
            for (const card of cards) {{
                const title = card.querySelector({json.dumps(TEMPLATE_TITLE)});
                if (title && title.textContent.trim() === {json.dumps(template_name)}) {{
                    card.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )

    if clicked:
        logger.info("已选择模板: %s", template_name)
        time.sleep(1)
    else:
        logger.warning("未找到模板: %s", template_name)

    return bool(clicked)


def click_next_and_fill_description(page: Page, description: str) -> None:
    """点击下一步，进入发布页并填写正文描述。

    长文发布页的描述框是 tiptap ProseMirror，等待页面跳转后直接定位。
    如果 description 超过 1000 字，截断到 800 字。
    """
    # 点击"下一步"
    _click_button_by_text(page, NEXT_STEP_BUTTON_TEXT)

    # 等待发布页描述框出现（轮询，最多 15 秒）
    desc_selector = _wait_for_description_box(page, timeout=15)
    if not desc_selector:
        logger.warning("等待描述框超时，继续尝试")
        desc_selector = _find_description_selector(page)

    # 填写发布页描述（用 CDP 逐字输入，与普通图文发布一致）
    if description and desc_selector:
        if len(description) > 1000:
            description = description[:800]
            logger.warning("描述超过1000字，已截断到800字")
        page.input_content_editable(desc_selector, description)
        time.sleep(0.5)
        # 校验实际插入内容
        actual = page.evaluate(
            f"""
            (() => {{
                const el = document.querySelector({json.dumps(desc_selector)});
                return el ? el.textContent.length : 0;
            }})()
            """
        ) or 0
        if actual < len(description) * 0.8:
            logger.warning(
                "描述填充不完整（期望 %d 字, 实际 %d 字），尝试 execCommand 重试",
                len(description), actual,
            )
            page.evaluate(
                f"""
                (() => {{
                    const el = document.querySelector({json.dumps(desc_selector)});
                    if (!el) return;
                    el.focus();
                    el.click();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                    document.execCommand('insertText', false, {json.dumps(description)});
                }})()
                """
            )
            time.sleep(0.3)
            actual = page.evaluate(
                f"""
                (() => {{
                    const el = document.querySelector({json.dumps(desc_selector)});
                    return el ? el.textContent.length : 0;
                }})()
                """
            ) or 0
        logger.info("已填写发布页描述（%d 字, 实际 %d 字）", len(description), actual)


def replace_cover_images(page: Page, image_paths: list[str]) -> None:
    """替换封面图片：先上传新图片，再删除旧图片，最终只保留新上传的。

    Args:
        page: CDP 页面对象。
        image_paths: 本地图片绝对路径列表（按顺序上传）。

    Raises:
        PublishError: 未找到图片上传入口。
    """
    if not image_paths:
        return

    # 等待封面图片区域加载，尝试多种 selector 检测已有图片
    init_count = 0
    close_selector = ".close-btn"
    _close_selectors = [
        ".close-btn",
        ".delete-btn",
        ".remove-btn",
        "[class*='close']",
        "[class*='delete']",
    ]
    for _ in range(20):
        for sel in _close_selectors:
            c = page.evaluate(
                f"document.querySelectorAll({json.dumps(sel)}).length"
            ) or 0
            if c > 0:
                init_count = c
                close_selector = sel
                break
        if init_count > 0:
            break
        time.sleep(0.5)

    # 如果按钮 selector 都没找到，用 img 标签做交叉验证
    if init_count == 0:
        img_count = page.evaluate(
            "document.querySelectorAll('.coverImg img, .cover-image img, "
            "[class*=\"cover\"] img, [class*=\"image-item\"] img').length"
        ) or 0
        if img_count > 0:
            init_count = img_count
            logger.info("通过 img 标签检测到 %d 张初始图片", img_count)
    logger.info("封面区域已加载，初始图片 %d 张（selector: %s）", init_count, close_selector)

    # 1. 先上传新图片（小红书要求至少保留1张，必须先传再删旧图）
    # 增加重试机制：最多重试3次
    max_retries = 3
    upload_success = False
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("尝试上传图片（第 %d/%d 次）...", attempt, max_retries)
            
            doc = page._send_session("DOM.getDocument", {"depth": 0})
            root_id = doc["root"]["nodeId"]
            nodes = page._send_session("DOM.querySelectorAll", {
                "nodeId": root_id,
                "selector": "input[type='file'][accept*='jpg']",
            })
            
            if not nodes.get("nodeIds"):
                if attempt < max_retries:
                    logger.warning("未找到图片上传 input，等待10秒后重试...")
                    time.sleep(10)
                    continue
                else:
                    raise PublishError("未找到图片上传 input（已重试3次）")
            
            page._send_session("DOM.setFileInputFiles", {
                "nodeId": nodes["nodeIds"][0],
                "files": list(image_paths),
            })
            logger.info("已上传 %d 张新图片", len(image_paths))
            upload_success = True
            break
            
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning("上传失败（第 %d 次）：%s，等待10秒后重试...", attempt, str(e))
                time.sleep(10)
            else:
                logger.error("上传失败（第 %d 次）：%s", attempt, str(e))
    
    if not upload_success:
        raise PublishError(f"图片上传失败（已重试3次）：{last_error}")

    # 等待所有新图片加载完成（count 稳定在 init + new 以上）
    expected = init_count + len(image_paths)
    prev = -1
    for _ in range(30):  # 最多 15 秒
        time.sleep(0.5)
        count = page.evaluate(
            f"document.querySelectorAll('{close_selector}').length"
        ) or 0
        if count >= expected and count == prev:
            break  # 稳定了
        prev = count
    logger.info("图片加载稳定，当前 %d 张（期望 %d 张）", count, expected)

    # 2. 删除旧图片（旧图在前，新图追加在末尾）
    # 即使 init_count=0，如果上传后总数 > 目标数，也尝试删除多余的前排图片
    target = len(image_paths)
    to_delete = max(init_count, count - target) if count > target else init_count
    deleted_count = 0
    for _ in range(to_delete + 5):
        if deleted_count >= to_delete:
            break
        count = page.evaluate(
            f"document.querySelectorAll('{close_selector}').length"
        ) or 0
        if count <= target:
            break
        if count <= 1:  # 平台要求至少保留 1 张
            break
        deleted = page.evaluate(
            f"""
            (() => {{
                const btn = document.querySelector('{close_selector}');
                if (!btn) return false;
                btn.style.display = 'flex';
                btn.style.visibility = 'visible';
                btn.style.opacity = '1';
                btn.style.pointerEvents = 'auto';
                btn.click();
                return true;
            }})()
            """
        )
        if not deleted:
            break
        deleted_count += 1
        time.sleep(0.6)
    logger.info("已删除 %d 张旧图片（初始 %d 张）", deleted_count, init_count)

    time.sleep(2)
    final = page.evaluate(
        f"document.querySelectorAll('{close_selector}').length"
    ) or 0
    logger.info("封面图片替换完成，最终 %d 张（目标 %d 张）", final, target)


def declare_original(page: Page) -> bool:
    """声明原创：点击原创声明开关 → 确认弹窗中的"声明原创"按钮。

    Returns:
        True 表示已开启原创声明，False 表示操作失败。
    """
    # 如果弹窗已经打开，直接处理（不需要再点开关）
    modal_open = page.evaluate("!!document.querySelector('.d-modal')")
    if not modal_open:
        # 检查开关是否已经打开
        already = page.evaluate("""
        (() => {
            const card = document.querySelector('.custom-switch-card');
            const sw = card ? card.querySelector('.d-switch') : null;
            return sw ? !!sw.querySelector('.d-switch-simulator.checked') : false;
        })()
        """)
        if already:
            logger.info("原创声明已开启")
            return True
        # 点击开关触发弹窗
        clicked = page.evaluate("""
        (() => {
            const card = document.querySelector('.custom-switch-card');
            const sw = card ? card.querySelector('.d-switch') : null;
            if (!sw) return false;
            sw.click();
            return true;
        })()
        """)
        if not clicked:
            logger.warning("未找到原创声明开关")
            return False
        time.sleep(0.8)

    # 勾选"我已阅读并同意"复选框（否则"声明原创"按钮为 disabled）
    page.evaluate("""
    (() => {
        const modal = document.querySelector('.d-modal');
        if (!modal) return;
        const cb = modal.querySelector('.d-checkbox.d-clickable');
        if (cb) cb.click();
    })()
    """)
    time.sleep(0.5)

    # 点击"声明原创"按钮
    confirmed = page.evaluate("""
    (() => {
        const btn = Array.from(document.querySelectorAll('button')).find(function(b) {
            return b.textContent.trim() === '声明原创'
                && b.getBoundingClientRect().width > 0
                && !b.classList.contains('disabled');
        });
        if (btn) { btn.click(); return true; }
        return false;
    })()
    """)

    time.sleep(0.5)
    # 验证
    is_checked = page.evaluate("""
    (() => {
        const card = document.querySelector('.custom-switch-card');
        const sw = card ? card.querySelector('.d-switch') : null;
        return sw ? !!sw.querySelector('.d-switch-simulator.checked') : false;
    })()
    """)
    if is_checked:
        logger.info("原创声明已开启")
    else:
        logger.warning("原创声明开启状态未确认（confirmed=%s）", confirmed)
    return bool(is_checked)


def add_topics(page: Page, topics: list[str]) -> None:
    """在发布页描述框末尾添加话题标签（正确 entity，颜色与正文不同）。

    每个话题通过点击"话题"按钮 → 输入关键词 → 等待搜索建议 →
    键盘导航到第一个匹配项 → Enter 确认 → 加空格分隔。

    Args:
        page: CDP 页面对象。
        topics: 话题关键词列表，如 ["大模型", "Claude", "效率工具"]。
    """
    # 在正文末尾换行，确保话题与正文之间有空行
    page.evaluate("""
    (() => {
        const el = document.querySelector('div.tiptap.ProseMirror');
        if (!el) return;
        el.focus();
        const sel = window.getSelection();
        if (sel) sel.selectAllChildren(el);
        if (sel) sel.collapseToEnd();
    })()
    """)
    time.sleep(0.2)
    page._send_session("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
    page._send_session("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
    time.sleep(0.3)

    for keyword in topics:
        _add_single_topic(page, keyword)
        time.sleep(0.5)
    logger.info("已添加 %d 个话题", len(topics))


# ========== 内部辅助函数 ==========


def _click_new_creation(page: Page) -> None:
    """点击"新的创作"按钮。"""
    _click_button_by_text(page, NEW_CREATION_BUTTON_TEXT)
    time.sleep(2)
    page.wait_dom_stable()
    logger.info("已点击'新的创作'")


def _fill_long_title(page: Page, title: str) -> None:
    """填写长文标题（textarea，需使用 native setter）。"""
    page.wait_for_element(LONG_ARTICLE_TITLE, timeout=10)

    page.evaluate(
        f"""
        (() => {{
            const el = document.querySelector({json.dumps(LONG_ARTICLE_TITLE)});
            if (!el) return false;
            const nativeSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            el.focus();
            nativeSetter.call(el, {json.dumps(title)});
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }})()
        """
    )
    logger.info("已填写长文标题: %s", title[:20])
    time.sleep(0.5)


def _fill_long_content(page: Page, content: str) -> None:
    """填写长文正文（TipTap/ProseMirror 编辑器）。

    TipTap/ProseMirror 必须通过 document.execCommand('insertText') 插入文本，
    直接操作 DOM 或 CDP key events 无效。
    """
    # 等待编辑器出现
    for sel in (".ProseMirror", ".tiptap"):
        if page.has_element(sel):
            content_selector = sel
            break
    else:
        content_selector = CONTENT_EDITOR

    # 用 execCommand 插入（TipTap 标准做法）
    inserted = page.evaluate(
        f"""
        (() => {{
            const el = document.querySelector({json.dumps(content_selector)});
            if (!el) return false;
            el.focus();
            el.click();
            // 清空已有内容
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            // 插入新内容
            document.execCommand('insertText', false, {json.dumps(content)});
            return el.textContent.length;
        }})()
        """
    )
    logger.info("已填写长文正文 (%d 字入, 实际 %s 字)", len(content), inserted)
    time.sleep(1)


def _insert_images_to_editor(page: Page, image_paths: list[str]) -> None:
    """将图片插入到编辑器中。"""
    for img_path in image_paths:
        file_uri = Path(img_path).resolve().as_uri()
        page.evaluate(
            f"""
            (() => {{
                const editor = document.querySelector({json.dumps(CONTENT_EDITOR)});
                if (!editor) return false;
                const img = document.createElement('img');
                img.src = {json.dumps(file_uri)};
                editor.appendChild(img);
                editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return true;
            }})()
            """
        )
    logger.info("已插入 %d 张图片到编辑器", len(image_paths))
    time.sleep(1)


def _click_auto_format(page: Page) -> None:
    """点击"一键排版"按钮。"""
    _click_button_by_text(page, AUTO_FORMAT_BUTTON_TEXT)
    logger.info("已点击'一键排版'，等待模板加载...")
    time.sleep(_AUTO_FORMAT_WAIT)


def _wait_for_templates(page: Page) -> bool:
    """等待模板卡片出现。"""
    for _ in range(_TEMPLATE_WAIT_ROUNDS):
        count = page.get_elements_count(TEMPLATE_CARD)
        if count and count > 0:
            logger.info("发现 %d 个模板卡片", count)
            return True
        time.sleep(1)

    logger.warning("等待模板卡片超时")
    return False


def _wait_for_description_box(page: Page, timeout: int = 15) -> str | None:
    """等待长文发布页的描述框出现，返回可用的 CSS selector。

    优先查找含 '输入正文描述' placeholder 的 textbox 父元素，
    回退到 div.tiptap.ProseMirror。
    """
    for _ in range(timeout * 2):
        sel = _find_description_selector(page)
        if sel:
            logger.info("描述框已就绪（selector: %s）", sel)
            return sel
        time.sleep(0.5)
    return None


def _find_description_selector(page: Page) -> str | None:
    """查找长文发布页描述框的实际 selector。"""
    # 方案 1：通过 placeholder 定位含 textbox role 的父元素（与 publish.py 一致）
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
                            return 'textbox';
                        }
                    }
                    // 没找到 textbox parent，返回 tiptap
                    return 'tiptap';
                }
            }
            return '';
        })()
        """
    )
    if found == "textbox":
        return "[role='textbox']"
    if found == "tiptap":
        return "div.tiptap.ProseMirror"

    # 方案 2：直接查找 tiptap 编辑器
    if page.has_element("div.tiptap.ProseMirror"):
        return "div.tiptap.ProseMirror"

    return None


def _add_single_topic(page: Page, keyword: str) -> bool:
    """添加单个话题：点话题按钮 → 输入关键词 → 键盘导航选择 → Enter + 空格。

    Returns:
        True 表示成功选择了话题 entity，False 表示未找到匹配建议。
    """
    # 点击"话题"按钮（需编辑器已 focused）
    page.evaluate(
        "(() => { const b = document.querySelector('button.contentBtn.topic-btn'); if (b) b.click(); })()"
    )
    time.sleep(1.5)

    # 逐字输入关键词
    for ch in keyword:
        page._send_session("Input.dispatchKeyEvent", {"type": "keyDown", "text": ch})
        page._send_session("Input.dispatchKeyEvent", {"type": "keyUp", "text": ch})
        time.sleep(0.12)

    # 轮询等待含关键词的建议（最多 10 秒）
    found = False
    for _ in range(20):
        time.sleep(0.5)
        items = page.evaluate(
            """(() => Array.from(document.querySelectorAll('.tippy-box [class*="item"]'))
               .filter(el => el.offsetParent !== null)
               .map(el => el.textContent.trim()))()"""
        )
        if items and any(keyword.lower() in it.lower() for it in items):
            found = True
            break

    if not found:
        logger.warning("话题 '%s' 未找到建议，跳过", keyword)
        # 退出并清除已输入内容
        _press_escape(page)
        for _ in range(len(keyword) + 1):
            page._send_session(
                "Input.dispatchKeyEvent",
                {"type": "keyDown", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8},
            )
            page._send_session(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8},
            )
        return False

    # 检查默认 is-selected 项是否已含关键词
    selected = page.evaluate(
        """(() => {
            const el = document.querySelector('.tippy-box [class*="item"].is-selected');
            return el ? el.textContent.trim() : null;
        })()"""
    )
    if not (selected and keyword.lower() in selected.lower()):
        # 用 ArrowDown 找到第一个含关键词的选项（最多 8 次）
        for _ in range(8):
            page._send_session(
                "Input.dispatchKeyEvent",
                {"type": "keyDown", "key": "ArrowDown", "code": "ArrowDown", "windowsVirtualKeyCode": 40},
            )
            page._send_session(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "key": "ArrowDown", "code": "ArrowDown", "windowsVirtualKeyCode": 40},
            )
            time.sleep(0.12)
            cur = page.evaluate(
                """(() => {
                    const el = document.querySelector('.tippy-box [class*="item"].is-selected');
                    return el ? el.textContent.trim() : null;
                })()"""
            )
            if cur and keyword.lower() in cur.lower():
                break

    # Enter 确认选择
    page._send_session(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
    )
    page._send_session(
        "Input.dispatchKeyEvent",
        {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
    )
    time.sleep(0.3)

    # 加空格分隔下一个话题
    page._send_session("Input.dispatchKeyEvent", {"type": "keyDown", "text": " "})
    page._send_session("Input.dispatchKeyEvent", {"type": "keyUp", "text": " "})
    logger.info("已添加话题: #%s", keyword)
    return True


def _press_escape(page: Page) -> None:
    page._send_session(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27},
    )
    page._send_session(
        "Input.dispatchKeyEvent",
        {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27},
    )
    time.sleep(0.1)


def _click_button_by_text(page: Page, text: str) -> None:
    """通过文本内容查找并点击按钮（通用方法）。"""
    clicked = page.evaluate(
        f"""
        (() => {{
            const elems = document.querySelectorAll(
                'button, [role="button"], span, div, a, [class*="btn"]'
            );
            for (const el of elems) {{
                if (el.textContent.trim() === {json.dumps(text)}) {{
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    el.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
    )

    if not clicked:
        raise PublishError(f"未找到'{text}'按钮，页面结构可能已变化")
