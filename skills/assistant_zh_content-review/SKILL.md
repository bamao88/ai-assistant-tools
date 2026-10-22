---
name: assistant_zh_content-review
description: |
  周复盘 skill。读取本周相关 item 的 `published.md` 和 `observation.md`，输出
  `analytics/weekly/YYYY-WW.md`。
compatibility: Codex
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
---

# assistant_zh_content-review

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


你负责横向复盘，不负责单条内容状态推进。

## 输入

- 本周 item 的 `published.md`
- 本周 item 的 `observation.md`

## 输出

- `analytics/weekly/YYYY-WW.md`

## 规则

1. 周报是 analytics 产物，不回灌单条 item。
2. 缺 observation 的内容可以列风险，但不能伪造数据。
