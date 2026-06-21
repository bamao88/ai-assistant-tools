#!/usr/bin/env python3
"""为「已打开的视频发布页」设置自定义封面（兼容入口）。

正常发布请直接使用 `cli.py publish-video --cover ...` 或
`cli.py fill-publish-video --cover ...`。本脚本只保留给已经打开的发布页做
封面补救。

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

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from xhs.cdp import Browser  # noqa: E402
from xhs.video_cover import set_video_cover  # noqa: E402


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
        result = set_video_cover(page, args.cover)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        return 2

    ok = (not result.get("stillCropping")) and result.get("confirm_clicks", 0) > 0
    print(json.dumps({"success": ok, "cover": args.cover, **result}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
