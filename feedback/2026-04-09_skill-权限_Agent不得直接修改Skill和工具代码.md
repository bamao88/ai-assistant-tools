# Agent 不得直接修改 Skill 和工具代码

## 日期
2026-04-09

## 问题描述

assistant_zh 在处理「Tailscale exit node 导致发布审核失败」问题时，直接修改了以下 skill 文件：

- `~/.claude/skills/xhs-publish-article/skill.md`
- `WXP_tool/xiaohongshu_skills/skills/xhs-publish-post/SKILL.md`
- `WXP_tool/xiaohongshu_skills/skills/xhs-publish-video/SKILL.md`

这是越权行为，已被用户纠正并还原。

## 规则明确

**所有 Agent 均无权直接修改以下内容：**

1. **Skill 文件**（`~/.claude/skills/` 下的所有文件、`WXP_tool/*/skills/` 下的所有文件）
2. **工具源代码**（`WXP_tool/` 下的 `.py`、`.sh` 等可执行文件）
3. **其他 Agent 的 CLAUDE.md 或配置文件**

## 正确做法

遇到 Skill 或工具的 Bug、功能缺失、改进建议时：

1. 在 `/Volumes/ExtSSD2601/WXP_tool/feedback/` 下新建反馈文件
2. 文件命名：`YYYY-MM-DD_工具名_问题简述.md`
3. 内容包含：复现步骤、期望行为、实际行为、建议方案
4. **不要自行修改工具或 Skill 代码**

在等待 Skill 更新期间，Agent 可以在自己的执行流程中**手动补偿**（如在调用 click-publish 前后自行执行 Tailscale 开关），但不能改 Skill 文件本身。

## 请所有 Agent 注意

此规则适用于所有 Agent（assistant_zh、assistant_hj、assistant_wxp_ai8zu、assistant_wxp_self、assistant_mdx）。
