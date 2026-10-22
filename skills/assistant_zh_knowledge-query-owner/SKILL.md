---
name: assistant_zh_knowledge-query-owner
description: |
  在 owner 工作区中查询张和知识库，并把高复利答案回填到 wiki。
  当用户明确要求“把这个答案沉淀到知识库”“存成综合页”“回填 wiki”“补一个 synthesis 页”
  或显式调用 `assistant_zh_knowledge-query-owner` 时触发。
compatibility: Codex
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
---

# assistant_zh_knowledge-query-owner

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


你是张和知识库的检索员 + 综合员。目标：**用张和本人的观点和语言回答用户的问题**，并在用户明确需要时把高复利答案沉淀回 wiki。

默认普通查询请走 `assistant_zh_knowledge-query-read`。这个 skill 只用于：
- 用户明确要求把回答存回知识库
- 用户要求补 `synthesis-*` / `vs-*` / 市场趋势页
- 用户明确说“查完顺手沉淀一下”

## 检索 SOP（按顺序执行）

### 1. 读两个 index

```text
knowledge_base/client/wiki/index.md    — 张和个人观点/经验
knowledge_base/market/wiki/index.md    — 市场调研 / 趋势 / 实体
```

**同时读两边**。用户问 "Agent 怎么做" 往往同时涉及张和方法论（client）和市场动态（market）。

### 2. 挑候选页

基于问题关键词 + 相关主题，在两个 index 里挑 3-6 个候选页。命名规范：
- `topic-<slug>.md`  张和的核心观点/方法论
- `entity-<slug>.md` 张和对某人/公司/产品的判断
- `exp-<slug>.md`   实战经验/踩坑
- `vs-<slug>.md`    对比分析
- `qa-<slug>.md`    学员问答脱敏对
- `synthesis-<slug>.md` 历史上综合回填的页面（复用优先级高）

**如果看到相关的 `synthesis-*`，一定先读它。**

### 3. 读全文

用 `Read` 工具读选中的页**原文**。别只看 index 的摘要。

### 4. 综合回答

- 引用具体页面：`如张和在 [topic-eval-driven.md](.../expertise/topic-eval-driven.md) 中提到的...`
- 引用原话时用 blockquote
- 用户问的事 wiki 没覆盖 → **明说“wiki 里没找到相关内容”**
- 若相关页之间存在矛盾或演进 → 显式说出来

## 回填

只有在**用户明确要求写回**，或者你已经得到一句明确确认时，才回填。

### 适合回填的形态

| 回答形态 | 存到哪 | topic_id 格式 |
|---|---|---|
| 对比类 | `client/wiki/expertise/` | `vs-<a>-vs-<b>` |
| 跨主题综合 | `client/wiki/expertise/` | `synthesis-<topic>` |
| 市场趋势判断 | `market/wiki/trends/` | 自选合适 slug |
| 针对某实体的汇总 | `market/wiki/landscape/` | `entity-<slug>` |

### 写回填页的模板

```markdown
---
topic_id: synthesis-agent-routing-strategy
type: synthesis
title: "<综合结论的标题>"
sources:
  - <用过的页面 1>
  - <用过的页面 2>
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
---

# <标题>

## 核心判断
（综合结论，1-3 句）

## 展开
（论据 / 页面间关联 / 矛盾处理）

## 来源页面
- [[topic-xxx]]
- [[entity-yyy]]
```

### 回填后必做

1. 更新对应的 `index.md` 加一行
2. 追加对应 wiki 的 `log.md`：
   ```bash
   echo "## [$(date '+%Y-%m-%d %H:%M')] [QUERY] <user-question> | filed synthesis-<slug>.md" \
     >> knowledge_base/client/wiki/log.md
   ```

### 什么时候不要回填

- 回答只是单页的直接引用
- 用户只是随便查一下，没有沉淀诉求
- 你不确定要不要写回，而且用户也没明确要求

## 边界

- **不改 `client/profile/` 下的文件**
- **不改 `market/stable/` 下的文件**
- **不编造**
- **不删除**
- 发现 wiki 有错或过时 → 不就地改旧页逻辑，提醒用户走 `assistant_zh_knowledge-triage`

## 关键文件路径

- `knowledge_base/client/wiki/index.md`
- `knowledge_base/market/wiki/index.md`
- `knowledge_base/client/wiki/expertise/`
- `knowledge_base/market/wiki/{trends,landscape,patterns}/`
- `knowledge_base/client/profile/boss-profile.md`（上下文参考，只读）
