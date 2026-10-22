# Agent-Publish 历史触发迁移说明

2026-10-22当前执行要求：本机已有Chrome与会话hook。下文只解释旧触发的迁移历史，不能据此恢复远程、独立profile或跳过会话检查；当前任务不执行回滚。

`Agent-Publish` 整合并取代了三个独立的发布触发入口。其操作正文已迁入 `references/`：

| 旧触发 skill | 旧来源（重构后位置） | 现位置 |
|--------------|----------------------|--------|
| `xhs-publish` | `engines/xiaohongshu/skills/xhs-publish/SKILL.md` | `references/xiaohongshu.md` |
| `gzh-publish` | `engines/gzh-publish/skills/gzh-publish/SKILL.md` | `references/gongzhonghao.md` |
| `wechatsync` | `vendor/wechatsync/skills/wechatsync/SKILL.md` | `references/wechatsync.md` |

底层 CLI 未改动，仍在 `engines/xiaohongshu`、`engines/gzh-publish`、`vendor/wechatsync`。
`~/.claude/skills/` 下 `xhs-publish` / `gzh-publish` / `wechatsync` 的触发入口已被 `sync-skills.py` 移除，避免与 `Agent-Publish` 触发竞争。

## 如何回滚到独立触发

1. 恢复旧 SKILL 文件（从本 reference 反向还原，或 `git checkout <pre-restructure-commit> -- <旧路径>`）。
2. 在 `registry.yaml` 的 `skills:` 重新登记 `xhs-publish` / `gzh-publish` / `wechatsync`。
3. 运行 `python3 scripts/sync-skills.py` 重新创建 `~/.claude/skills/` 软链。
4. 删除或停用 `skills/platform-publish/`。

> 注意：恢复独立触发会重新引入触发竞争（记忆 `feedback_skill_consolidation_pattern`：改描述无效，只能靠"super-skill + 删下层入口"根治）。除非确有需要，不建议回滚。
