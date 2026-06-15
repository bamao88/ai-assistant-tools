#!/usr/bin/env python3
"""write_policy.py — 写入策略层（P2 骨架；策略收口在 P3/§4）。

§4 目标：把散落在各 sync 里的逐字段写回规矩收成一层：
    append / overwrite / skip-if-marked（检测 `AI回访分析` 标记跳过）/
    reset（rerun 修复）/ 只填空不覆盖 / 幂等。

现状：策略逻辑仍内联在 outputs/{sync_to_feishu, sync_friends_to_feishu,
sync_group_order, intake_writer}.py 与 capabilities/resolve/add_missing_group_members.py。
P3 把它们抽到这里复用。P2 仅占位，不改各 sync 行为。
"""

from __future__ import annotations

# P3: 在此实现统一写策略原语。占位常量先把口径写下来，供迁移期对齐。
AI_STAMP = "AI回访分析"  # skip-if-marked 检测标记（见 outputs/sync_to_feishu.py）

__all__ = ["AI_STAMP"]
