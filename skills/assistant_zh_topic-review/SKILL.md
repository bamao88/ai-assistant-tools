---
name: assistant_zh_topic-review
description: |
  Review `content/shared_candidates/*.md` 与目标 persona 的 `content/<persona>/candidates/*.md` 里的选题候选，按第一手性、知识密度、展开空间和账号匹配度做筛选，
  给出 3-5 个最值得推进的方向。**人工最终拍板**，
  你的角色是把候选展示清楚 + 给出建议 + 帮用户选出下一条值得直接进入生产的内容。
  用户说"review 候选"、"看看候选批次"、"挑选题"时触发。
compatibility: Codex
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# assistant_zh_topic-review

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


## 加载顺序

1. `knowledge_base/client/profile/boss-profile.md`
2. `knowledge_base/client/profile/account-positioning.md`
3. `knowledge_base/client/profile/topic-selection-principles.md`
4. `knowledge_base/client/profile/content-strategy.md`
5. `.agents/skill-data/assistant_zh_topic-select/memory-bank/performance-insights.md`
6. `content/candidates_index.md`，以及最近相关的共享候选和目标 persona 候选批次

## 行为

### 1. 概览候选

从 `content/candidates_index.md` 确认目标 persona 后，读取最近相关的 `content/shared_candidates/*.md` 与 `content/<persona>/candidates/*.md`，按 `candidates[]` 和正文分节整理 top-N 给用户。候选默认只读；明确刷新才交给 `assistant_zh_topic-mine`。

### 2. drill 单个候选

读取该候选对应的：

- `topic`（旧批次可能写成 `title`；这里都按“选题陈述”理解，不按“最终标题”理解）
- `source_refs`
- `selection_reason`
- `source_readiness`
- `research_followups`
- 正文里的标题方向 / 证据引文
- 关联 wiki 页 / raw meeting 引用

### 3. 套五项评估

- **第一手性**：张和是否真的有资格讲，能不能拿出一手经历、案例、拆解或判断依据
- **知识密度**：是不是有方法、约束、取舍、步骤，而不只是观点表态
- **展开空间**：这条选题有没有把对象、问题、角度、边界说清，能不能撑起一篇完整内容
- **补强空间**：如果当前材料还不够，是否能通过公开资料、互联网搜索、源码/产品文档补强成一篇完整文章
- **账号匹配度**：是否贴合张和的强项，而且和近期已发/已选内容不重复

### 4. 重复度与包装边界检查

- 看最近 3-5 条已发/已选内容，避免同角度重复
- 包装只做辅助，不得因为“更像爆款标题”就压过内容质量更高的候选
- 除非原始材料明确要求强反驳，否则不要默认改成“90% 的人都搞错了”这类标题

### 5. 推荐 + 拍板

挑出 3-5 个候选给用户，每个含：
- 五项评估理由；批次确实提供 score 时才引用，不给无 score 的手工候选编造分数
- 2-3 个工作标题（判断型 / 问题型 / 拆解型）
- 写作思路（150-250 字，含核心角度 + 张和切入点 + 具体能展开的内容）

**用户拍板后**：
1. 如果用户只是说“先看一下 / 先比较一下”，停留在会话层，给出明确推荐，不创建 durable artifact
2. 如果用户说“选这个做 / 开始写”，交回 `main` 直接进入 `生产`
3. 不要求候选层再走 formalization，也不要求先看 `spec`

## 边界

- 不动 `knowledge_base/`
- 不把 `content/topic_pool/` 当候选真源，只 review 共享候选和目标 persona 候选目录
- 不主动把候选改写成营销腔、求职焦虑腔或招生话术
