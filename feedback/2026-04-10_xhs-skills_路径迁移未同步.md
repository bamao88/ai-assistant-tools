---
status: fixed
fixed_date: 2026-04-10
note: 经核查，所有 xhs-* skill 文件中的路径已正确指向新位置，实际工具文件也均存在。问题已解决，无需额外修复。
---

# Bug: xhs-* skills 路径未同步到新位置

## 发现时间
2026-04-10

## 涉及 Skill
xhs-fetch-note, xhs-fetch-user, xhs-search-note, xhs-publish-article, xhs-publish-post, xhs-publish-video, xhs-comment, xhs-like, xhs-auth, xhs-ops

## 问题描述

所有 xhs-* skill 文件中硬编码的工具路径为旧路径：
```
/Volumes/ExtSSD2601/WXP_tool/xiaohongshu_skills/
```

但实际工具已迁移到：
```
/Volumes/ExtSSD2601/AI_Assistant_manage/tools/engines/xiaohongshu/
```

## 复现步骤

触发任意 xhs-* skill，执行 `list-accounts` 等命令时报错：
```
Exit code 127
(eval):1: no such file or directory: /Volumes/ExtSSD2601/WXP_tool/xiaohongshu_skills/.venv/bin/python
```

## 期望行为

Skill 文件中所有路径统一替换为新路径：
`/Volumes/ExtSSD2601/AI_Assistant_manage/tools/engines/xiaohongshu/`

## 临时补偿方案

Agent 本次通过 Bash 工具直接调用新路径完成任务，不走 skill 路径。

## 修复建议

批量替换所有 xhs-* skill 文件中的路径引用（包括 SKILL.md 和内嵌的 bash 示例）。
