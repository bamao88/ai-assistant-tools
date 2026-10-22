---
name: assistant_zh_knowledge-query
description: |
  旧口令兼容别名。用户明确说 `assistant_zh_knowledge-query`，或要求“查询后顺手回填 wiki / 存综合页 / 记入知识库”
  时触发。行为等同 `assistant_zh_knowledge-query-owner`。
compatibility: Codex
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
---

# assistant_zh_knowledge-query

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


这是兼容旧口令的薄别名，行为等同 `assistant_zh_knowledge-query-owner`。

执行步骤：

1. 先读 `../assistant_zh_knowledge-query-owner/SKILL.md`
2. 完全按 `assistant_zh_knowledge-query-owner` 的规则执行
3. 若用户没有明确写回诉求，优先只查不写；需要沉淀时再回填 wiki
