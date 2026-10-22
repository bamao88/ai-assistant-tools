---
name: assistant_zh_metrics-record
description: |
  单条内容的 D+1 / D+3 / D+7 数据回填 skill。读取 `published.md`，写 `observation.md`
  并更新本地 stats 窗口。
compatibility: Codex
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
---

# assistant_zh_metrics-record

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


你负责发布后的数据观察。

## 输入

- `content/<persona>/items/<content_id>/published.md`
- `content/content_index.yaml` 中目标 `destinations[]` 的 `note_url` 和 `stats_windows`

## 输出

- `content/<persona>/items/<content_id>/observation.md`
- 更新对应 `destinations[].stats_windows` 的窗口状态

## 规则

1. 从目标 `destinations[].note_url` 取得真实链接；没有链接不允许假装回填成功。
2. 先写本地 observation。
3. 一条 item 的各 destination 分别观察；目标 destination 所有窗口完成后，由 `main` 把该 destination 的状态推进到 `archived`。
