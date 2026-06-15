#!/usr/bin/env python3
"""write_policy.py — 写入策略层（§4）。

把原本散落在各 sync 模块里的逐字段写回规矩收成一层**命名策略**。任务卡用
名字引用这些策略（见 cards/*.md 的 front-matter `write_back`）。

命名策略（§4）
--------------
- `append`          : 在现内容末尾追加（带分隔符；现内容空则直接写）。
                      —— 出处: outputs/sync_to_feishu 的 客户画像/备注 append 分支。
- `overwrite`       : 直接覆盖（如就业的 拿到offer Checkbox）。
- `skip_if_marked`  : 现内容已含 `AI回访分析` 标记 → 跳过（幂等，保留手填）；否则 append。
                      —— 出处: outputs/sync_to_feishu（就业 sync 的核心幂等规矩）。
- `reset`           : rerun 修复——直接覆盖（清掉上次错写），如 employment 的
                      reset_latest_entry / --rerun-not-followed-up。
- `fill_only_if_empty` (只填空不覆盖): 现值空才填，非空不动（尊重已填/手填）。
                      —— 出处: resolve/fix_*（备注及其他名称 空才补）、FIELD_SPEC「所属推广员仅在为空时填」。
- `idempotent_field`: 算 patch——拟写值 == 现值则不产生改动（跑两次幂等）。
                      —— 出处: resolve/fix_* 的 skip_no_change、sync_to_feishu 的 SKIP_NO_CHANGE。

这些是**纯函数**：吃 (现值, 新值[, 分隔符]) → (是否要写, 写什么)。各 sync/flow
把自己的逐字段判断换成调这里，行为不变（P3 抽取，不改写各 sync 现行为）。
`AI_STAMP` 是 skip-if-marked 的检测标记，沿用 outputs/sync_to_feishu 口径。
"""

from __future__ import annotations

from typing import Any

# skip-if-marked 检测标记（latest stub/LLM 模板里都会有；见 outputs/sync_to_feishu.py）
AI_STAMP = "AI回访分析"

__all__ = [
    "AI_STAMP",
    "POLICIES",
    "stringify_text",
    "append",
    "overwrite",
    "skip_if_marked",
    "reset",
    "fill_only_if_empty",
    "idempotent_field",
]


def stringify_text(value: Any) -> str:
    """飞书 Text 字段可能是 str、或 list[{type,text}] 富文本片段，统一返回纯文本。
    沿用 outputs/sync_to_feishu.stringify_text 口径。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for it in value:
            if isinstance(it, dict):
                parts.append(it.get("text") or "")
            else:
                parts.append(str(it))
        return "".join(parts)
    return str(value)


def append(current: Any, new: str, *, sep: str = "\n\n") -> tuple[bool, str]:
    """末尾追加。返回 (changed, value)。new 空 → 不写。"""
    new = (new or "").strip()
    if not new:
        return False, stringify_text(current)
    cur = stringify_text(current)
    value = (cur + (sep if cur.strip() else "") + new).strip()
    return value != cur, value


def overwrite(current: Any, new: Any) -> tuple[bool, Any]:
    """直接覆盖。返回 (changed, new)。changed = 新值 != 现值。"""
    return new != current, new


def skip_if_marked(current: Any, new: str, *, marker: str = AI_STAMP,
                   sep: str = "\n\n") -> tuple[bool, str]:
    """现内容已含 marker → 跳过（幂等）；否则 append。返回 (changed, value)。

    沿用 outputs/sync_to_feishu 的 客户画像/备注 写回规矩。
    """
    new = (new or "").strip()
    cur = stringify_text(current)
    if not new:
        return False, cur
    if marker in cur:
        return False, cur  # 已 sync 过，跳过
    return append(cur, new, sep=sep)


def reset(current: Any, new: Any) -> tuple[bool, Any]:
    """rerun 修复：无条件覆盖（清掉上次错写）。语义上等价 overwrite，但表意为
    「修复重置」（employment 的 reset_latest_entry / --rerun-not-followed-up）。"""
    return True, new


def fill_only_if_empty(current: Any, new: Any) -> tuple[bool, Any]:
    """只填空不覆盖：现值空才填。返回 (changed, value)。"""
    is_empty = current in (None, "", [], {})
    if isinstance(current, str) and not current.strip():
        is_empty = True
    if is_empty and new not in (None, "", [], {}):
        return True, new
    return False, current


def idempotent_field(current: Any, new: Any) -> tuple[bool, Any]:
    """幂等：拟写值 == 现值 → 不改动（跑两次幂等）。返回 (changed, new)。"""
    return new != current, new


# 名 → 策略函数（任务卡 write_back 按名引用）
POLICIES = {
    "append": append,
    "overwrite": overwrite,
    "skip-if-marked": skip_if_marked,
    "skip_if_marked": skip_if_marked,
    "reset": reset,
    "只填空不覆盖": fill_only_if_empty,
    "fill_only_if_empty": fill_only_if_empty,
    "idempotent": idempotent_field,
    "idempotent_field": idempotent_field,
}
