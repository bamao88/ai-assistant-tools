#!/usr/bin/env python3
"""group_order.py — 群序号同步配方：resolve → 写回（§5）。

把 analytics/group_member_order/by_wxid.json 的 3 列群序号同步到飞书客户管理表
（按 wxid 对齐，3 个 number 字段按当前 by_wxid.json 覆盖）。

这是 outputs.sync_group_order 的薄配方包装（保持配方层命名一致：每个一级命令都
落到一个 recipes/ 模块）。默认 dry-run，--apply 才真写（授权门）。

用法：
  python3 -m recipes.group_order             # dry-run
  python3 -m recipes.group_order --apply     # 授权门：真写
  python3 -m recipes.group_order --wxid <id>
  python3 -m recipes.group_order --limit 5
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

# engine 根（recipes/ → up 1）入 sys.path。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


def main() -> int:
    """转发到 outputs.sync_group_order（沿用其 argparse：--apply/--wxid/--limit，默认 dry-run）。"""
    sys.argv = ["outputs.sync_group_order"] + sys.argv[1:]
    try:
        runpy.run_module("outputs.sync_group_order", run_name="__main__", alter_sys=True)
    except SystemExit as e:
        return int(e.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
