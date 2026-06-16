#!/usr/bin/env python3
"""customer-management engine — 命令分发入口。

按 §6 暴露 7 个一级命令，每个落到 recipes/ 的配方（P4 起全部接线，无 stub）。

用法:
    python3 -m customer-management <command> [args...]
    # 或从 engine 根: python3 __main__.py <command> [args...]

命令（→ 配方）:
    gather         读取侧 Facade（本地+飞书镜像+微信+付款+diff，默认只读 0-LLM）  → recipes.gather
    intake         新学员入表（gather → 判断 → 写回）                          → recipes.intake
    employment     就业回访（recognize gate → analyze 就业卡 → 写回）           → capabilities.analyze.employment
    friends-sync   好友刷新建行（sync+audit+merge 三步合一）                    → recipes.friends_sync
    group-order    群序号同步（resolve → 写回）                                → recipes.group_order
    payment        付款金额（acquire 解图 + analyze 视觉卡 → 写回）             → recipes.payment
    health-check   客户表数据体检/订正闭环（吸收死脚本，scan→plan→apply→archive） → recipes.health_check
    read-chat      读某人解码+分层聊天 + 信息地图（只读 / 0-LLM）              → recipes.read_chat
    search-chat    跨全部人按关键词/日期/方向找候选 wxid + 解码片段（只读/0-LLM） → recipes.read_chat

写回安全（红线）:
    gather / health-check 默认只读 / dry-run；employment 默认 --auto（真写），其余写回类
    （intake/friends-sync/group-order/payment 写回/health-check）均以 --apply 为授权门。
    各命令的具体 flag 见其 --help。
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

# command -> 目标模块（全部已接线到真实配方）
_DISPATCH: dict[str, str] = {
    "gather": "recipes.gather",
    "intake": "recipes.intake",
    "employment": "capabilities.analyze.employment",
    "friends-sync": "recipes.friends_sync",
    "group-order": "recipes.group_order",
    "payment": "recipes.payment",
    "health-check": "recipes.health_check",
    # 只读 / 0-LLM 的 ad-hoc 读聊天 / 找人（补回迁移丢失的 agent 入口）
    "read-chat": "recipes.read_chat",
    "search-chat": "recipes.read_chat",
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
    # 把剩余参数交给目标模块的 argparse；argv[0] 用原命令名（让共享模块按 cmd 分支 + help 更友好）。
    sys.argv = [cmd] + rest
    try:
        runpy.run_module(target, run_name="__main__", alter_sys=True)
    except SystemExit as e:
        return int(e.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
