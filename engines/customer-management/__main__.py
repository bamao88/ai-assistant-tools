#!/usr/bin/env python3
"""customer-management engine — 命令分发入口（P2 stub）。

按 §6 暴露 7 个一级命令；P2 仅落骨架 + 路由到已迁移模块，配方内部编排
（gather facade、health_check 吸收死脚本、analyze 合并）在 P3/P4 完成。

用法:
    python3 -m customer-management <command> [args...]
    # 或从 engine 根: python3 __main__.py <command> [args...]

命令:
    gather         读取侧 Facade（acquire+recognize+resolve 对账）— P4 新建
    intake         新学员入表（gather → 判断 → 写回）           — recipes/intake (P4)
    employment     就业回访（recognize gate → analyze → 写回）  → capabilities.analyze.employment
    friends-sync   好友刷新建行（sync+audit+merge 三步合一）     — recipes/friends_sync (P4)
    group-order    群序号同步                                   → outputs.sync_group_order
    payment        付款金额（acquire 解图 + analyze 视觉读）     → recipes.payment
    health-check   客户表数据体检/订正闭环（吸收死脚本）         — recipes/health_check (P4)

注（P2）：本 stub 把已迁移的原子命令直接转发到对应模块；尚未编排的配方
（gather / intake / friends-sync / health-check）打印 "P4 待建" 提示并退出，
不静默失败。
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

# command -> 已迁移模块（None 表示配方尚未编排，P4 建）
_DISPATCH: dict[str, str | None] = {
    "gather": None,            # P4: recipes/gather facade
    "intake": None,            # P4: recipes/intake (现有 outputs.intake_writer 是其写回器)
    "employment": "capabilities.analyze.analyze",
    "friends-sync": None,      # P4: recipes/friends_sync = sync+audit+merge 合一
    "group-order": "outputs.sync_group_order",
    "payment": "recipes.payment",
    "health-check": None,      # P4: recipes/health_check 吸收死脚本
}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2

    cmd, rest = argv[0], argv[1:]
    if cmd not in _DISPATCH:
        print(f"[customer-management] 未知命令: {cmd}\n可用: {', '.join(_DISPATCH)}", file=sys.stderr)
        return 2

    target = _DISPATCH[cmd]
    if target is None:
        print(f"[customer-management] 命令 '{cmd}' 的配方将在 P4 编排，P2 尚未实现。", file=sys.stderr)
        return 3

    # 把剩余参数交给目标模块的 argparse；以 engine 根为 sys.path 锚点跑 -m。
    sys.argv = [target] + rest
    runpy.run_module(target, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
