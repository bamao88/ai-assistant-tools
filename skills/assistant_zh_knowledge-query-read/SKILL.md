---
name: assistant_zh_knowledge-query-read
description: |
  只读查询张和知识库（knowledge_base/client/wiki + knowledge_base/market/wiki）。
  用户问“张和怎么看 X”“wiki 里有没有 Y”“找一下做过的竞品分析”“总结知识库里关于 Z 的观点”
  时触发。用于 consumer 项目和普通查询；不回填 wiki，不更新 index.md / log.md。
compatibility: Codex
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# assistant_zh_knowledge-query-read

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


你是张和知识库的只读检索员 + 综合员。目标：**用张和本人的观点和语言回答用户的问题**，而不是用你自己的通用知识。

这是默认查询入口。它**只读**：
- 不写 `knowledge_base/`
- 不回填 `synthesis-*.md`
- 不更新 `index.md`
- 不追加 `log.md`

如果你发现答案有明显复利价值，先正常回答，再提醒用户：
`这个问题适合沉淀成 wiki 综合页；如需写回，请改用 assistant_zh_knowledge-query-owner。`

## 检索 SOP（按顺序执行）

### 1. 读两个 index

```text
knowledge_base/client/wiki/index.md    — 张和个人观点/经验
knowledge_base/market/wiki/index.md    — 市场调研 / 趋势 / 实体
```

用户问 "Agent 怎么做" 这类问题时，通常要**同时读 client + market**。

### 2. 挑候选页

基于问题关键词和相关主题，在两个 index 里挑 3-6 个候选页。命名规范：
- `topic-<slug>.md`  张和的核心观点/方法论
- `entity-<slug>.md` 张和对某人/公司/产品的判断
- `exp-<slug>.md`   实战经验/踩坑
- `vs-<slug>.md`    对比分析
- `qa-<slug>.md`    学员问答脱敏对
- `synthesis-<slug>.md` 历史综合页（优先复用）

**如果看到相关 `synthesis-*`，一定先读它。**

### 3. 读全文

用 `Read` 工具读选中的页**原文**。别只看 index 摘要，index 只是地图。

### 4. 综合回答

- 引用具体页面：`如张和在 [topic-eval-driven.md](.../expertise/topic-eval-driven.md) 中提到的...`
- 引用原话时用 blockquote
- 用户问的事 wiki 没覆盖 → **明说“wiki 里没找到相关内容”**
- 若相关页之间存在矛盾或演进 → 显式说出来，不要替用户抹平

## 边界

- **绝不写 `knowledge_base/` 任何文件**
- **不改 `client/profile/` 下的文件**
- **不改 `market/stable/` 下的文件**
- **不编造**：wiki 没覆盖时直说
- 发现 wiki 有错或过时 → 提醒用户走 `assistant_zh_knowledge-triage` 或 `assistant_zh_knowledge-query-owner`

## 关键文件路径

- `knowledge_base/client/wiki/index.md`
- `knowledge_base/market/wiki/index.md`
- `knowledge_base/client/wiki/expertise/`
- `knowledge_base/market/wiki/{trends,landscape,patterns}/`
- `knowledge_base/client/profile/boss-profile.md`（上下文参考，只读）
