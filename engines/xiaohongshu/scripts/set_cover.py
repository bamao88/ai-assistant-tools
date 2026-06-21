#!/usr/bin/env python3
"""为「已打开的视频发布页」设置自定义封面（引擎缺口外挂）。

背景：`cli.py publish-video / fill-publish-video` 只上传视频、填标题/正文/标签，
**没有任何封面步骤**——小红书视频默认拿首帧当封面。本脚本补这一步：在已经
填好表单、视频已处理完成的发布页上，把本地 `cover.png` 设为封面。

UI 流程（2026-06 creator 页实测）：
  cover-plugin「修改封面」→ 弹窗 image file input 上传 → 裁剪框「确定」（封面比例 3:4）

前置：发布页必须已打开（先跑 `fill-publish-video`，本脚本 attach 同一个 Chrome 端口的活动 tab）。
本脚本**不点发布**，只设封面。

用法：
  python3 set_cover.py --account 测试号 --cover /abs/path/cover.png
  python3 set_cover.py --port 9227 --cover /abs/path/cover.png

输出 JSON；退出码 0=成功 2=失败。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from xhs.cdp import Browser  # noqa: E402

IMAGE_FILE_INPUT = 'input[type=file][accept*="image"]'


def _click_text(page, text: str) -> bool:
    """点击第一个 textContent 恰为 text 的可见元素。"""
    return bool(
        page.evaluate(
            f"""
            (() => {{
                const want = {json.dumps(text)};
                const el = Array.from(document.querySelectorAll('div,span,button'))
                    .find(e => e.textContent.trim() === want
                        && e.getBoundingClientRect().width > 0);
                if (!el) return false;
                el.click();
                return true;
            }})()
            """
        )
    )


def _click_last_confirm(page) -> int:
    """点击 DOM 中最后一个可见「确定」按钮（裁剪弹窗的确认在最上层/最末）。返回可见确定数。"""
    return page.evaluate(
        """
        (() => {
            const btns = Array.from(document.querySelectorAll('button, .d-button')).filter(el => {
                const t = (el.textContent || '').trim();
                const r = el.getBoundingClientRect();
                return t === '确定' && r.width > 0 && r.height > 0;
            });
            if (!btns.length) return 0;
            btns[btns.length - 1].click();
            return btns.length;
        })()
        """
    )


def set_cover(page, cover_path: str) -> dict:
    if not os.path.exists(cover_path):
        raise FileNotFoundError(f"封面文件不存在: {cover_path}")

    # 1. 进入封面编辑（cover-plugin「修改封面」hover 浮层）
    if not _click_text(page, "修改封面"):
        # 兜底：有的版本入口是「设置封面」标题
        _click_text(page, "设置封面")
    time.sleep(1.2)

    # 2. 上传本地图片
    if not page.has_element(IMAGE_FILE_INPUT):
        raise RuntimeError("未找到封面图片上传输入框（封面编辑弹窗可能没打开）")
    page.set_file_input(IMAGE_FILE_INPUT, [cover_path])
    time.sleep(3)

    # 3. 裁剪框确认（cover.png 已是 3:4 时无需真裁，直接确定）
    n = _click_last_confirm(page)
    if n == 0:
        raise RuntimeError("上传后未出现「确定」按钮，封面可能未生效")
    time.sleep(2)

    # 4. 校验：封面预审 + 编辑弹窗已关闭
    state = page.evaluate(
        """
        (() => ({
            stillCropping: /封面比例/.test(document.body.innerText || ''),
            reviewPassed: /封面预审结果评估通过|封面.*通过/.test(document.body.innerText || ''),
        }))()
        """
    )
    return {"confirm_clicks": n, **state}


def main() -> int:
    ap = argparse.ArgumentParser(description="为已打开的视频发布页设置自定义封面")
    ap.add_argument("--cover", required=True, help="本地封面图片绝对路径")
    ap.add_argument("--account", help="命名账号（解析为端口）")
    ap.add_argument("--port", type=int, help="Chrome 调试端口（与 --account 二选一）")
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    port = args.port
    if port is None:
        if not args.account:
            print(json.dumps({"success": False, "error": "需提供 --account 或 --port"}, ensure_ascii=False))
            return 2
        import account_manager

        port = account_manager.get_account_port(args.account)

    browser = Browser(host=args.host, port=port)
    page = browser.get_existing_page()
    try:
        result = set_cover(page, args.cover)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        return 2

    ok = (not result.get("stillCropping")) and result.get("confirm_clicks", 0) > 0
    print(json.dumps({"success": ok, "cover": args.cover, **result}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
