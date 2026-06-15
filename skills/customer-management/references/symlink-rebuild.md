# ⚠️ 双 host 软链重建 runbook（软链脆弱性）

本 skill 的真源在 `tools/skills/customer-management/`。两个 host 各有一条**绝对路径软链**指向它：

| host | 软链 |
|---|---|
| Claude Code | `assistant_zh/.claude/skills/customer-management` → `tools/skills/customer-management` |
| Codex | `assistant_zh/.agents/skills/customer-management` → `tools/skills/customer-management` |

**为什么用绝对路径**：assistant_zh 与 tools 是两个独立仓库（不同根），相对软链跨仓脆弱；用绝对路径
指向 tools 的稳定位置。**风险**：移动 / 重命名 tools 目录会断这两条链。

## 重建（移动 tools 目录后、或链丢失时跑）

软链建立步是**可重跑**的——直接重跑下面这条幂等命令（删旧链再建，指向同一 tools 源）：

```bash
bash /Volumes/ExtSSD2601/AI_Assistant/tools/skills/customer-management/install-symlinks.sh
```

或手动（等价）：

```bash
SRC=/Volumes/ExtSSD2601/AI_Assistant/tools/skills/customer-management
for HOST in .claude .agents; do
  D=/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/$HOST/skills
  mkdir -p "$D"
  ln -sfn "$SRC" "$D/customer-management"
done
```

## 验证

```bash
readlink -f /Volumes/ExtSSD2601/AI_Assistant/assistant_zh/.claude/skills/customer-management
readlink -f /Volumes/ExtSSD2601/AI_Assistant/assistant_zh/.agents/skills/customer-management
# 两者必须输出同一路径，且该路径下有 SKILL.md
```

## 注意

- 本 skill **不进全局 `~/.claude/skills`**（业务专属，registry 标 `scope: assistant_zh`，
  `sync-skills.py` / `check-tools.py` 跳过它）。它只在 assistant_zh 项目本地可见。
- 不要用 `sync-skills.py` 装本 skill——那是全局共享层的脚本，本 skill 走上面的项目本地软链脚本。
