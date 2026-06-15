---
name: leads
flow: leads
gate: deterministic_screen
write_back:
  添加微信标签: append
  客户标签: overwrite
---

# 线索分层 — 任务卡（三要素，⚠️ 从产物倒推重建）

> **⚠️ 重建声明（§3「从产物倒推重建」）**：本卡**无原始代码**——线索分层只在
> 2026-05-26 一次性跑过，产物落在 `assistant_zh/analytics/zh2_lead_screening/`。
> 本卡是从那批产物（`initial_screen.json` / `leads_high.json` / `leads_report.md` /
> `tag_plan_final.json` / `tag_runs/*/result.json`）**倒推重建**的口径，未经原始脚本核对。
> 重新执行前需人工复核阈值与关键词词典。
>
> 这是一张**确定性分层卡**（gate=deterministic_screen，**0-LLM**）：它不调 LLM，
> 而是用规则（双向沟通量 + 活跃度 + 关键词命中 + 排除已成交）给张和2号好友打分分层。
> 列在 cards/ 是因为它和 analyze 的 profile/employment 共享「读聊天窗口 + staff 判定」机器核，
> 且产出同样要写回飞书客户管理表 `tblfCYoeornDw0XF`。

## 怎么读（① 数据源 + 筛选）

读取范围 = **张和2号真好友**（`getContactFriendFlags == true`，约 1012 人），
逐人读其与张和2号的 1v1 聊天（`messages_user_*.json`，经 analyze 机器核规范化 + staff 判定）。

初筛（→ `initial_screen.json`，632 人）：
- 双向沟通 ≥ 3 条（`my ≥ 1` 且 `peer ≥ 1`，`total ≥ 3`）
- 最近 12 个月内活跃（`last_date` 在窗口内）

## 要什么（② 结果字段）

逐人产出（见 `leads_high.json` 每条 schema）：

```
{
  "wxid": "<wxid>",
  "alias": "<微信号>",
  "display": "<昵称/备注>",
  "total": <双向总条数>, "my": <张和2号发>, "peer": <对方发>,
  "first_date": "YYYY-MM-DD", "last_date": "YYYY-MM-DD",
  "intent_hits": {
    "课程意向": <int>, "AI 圈背景": <int>, "咨询互动": <int>, "提及张和或助理": <int>
  },
  "intent_score": <int 加权总分>
}
```

**意向关键词 4 类**（命中计数，词典需重建前人工复核）：
- `课程意向`：课程 / 报名 / 学费 / 训练营 / 多少钱 / 怎么报 …
- `AI 圈背景`：AI / 产品经理 / PM / 转型 / 大模型 …
- `咨询互动`：咨询 / 请教 / 方案 / 怎么做 / 能不能 …
- `提及张和或助理`：张和 / 八毛 / 助理 / babamao …

初筛分桶（按关键词命中数）：HIGH（≥3 类命中，150 人）/ MID（178）/ LOW（304）。

## 写回规矩（③ 分层 + 落飞书）

分层规则（→ `tag_plan_final.json` 的 `rules`，最终 318 人打标，分布见
`tag_runs/*/result.json`：学员推荐 5 / 高潜客户 73 / 潜在客户 100 / 沉睡客户 140）：

| 标签 | 规则 |
|---|---|
| 学员推荐 | 渠道含 学员推荐/推荐 或 备注含 推荐/介绍/内推 |
| 高潜客户 | 关键词 ≥3 命中 + 双向 + 近 180 天活跃 + 未成交 |
| 潜在客户 | 关键词 1-2 命中 + 双向 + 近 180 天活跃 + 未成交 |
| 沉睡客户 | 曾双向沟通 + >180 天没动 + 关键词 ≥1 命中 + 未成交 |
| 跳过 | 已有客户标签 / 已成交学员（备注含已付费）/ 已是学员（几期学员字段非空）/ 数据不足 |

排除已成交（→ `closed.json`，9 人）：备注含「已付费/已报名」+ 团队号。

写回飞书：客户标签字段=overwrite（写入分层标签）；添加微信标签=append（保留历史）。
重新执行属一次性运营动作，须人工 review `plan` 后再 `--apply`（沿用 resolve 配方的
dry-run → 确认 → 幂等回写 → 归档 run 闭环）。
