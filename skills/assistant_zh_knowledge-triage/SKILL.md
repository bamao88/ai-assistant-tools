---
name: assistant_zh_knowledge-triage
description: |
  处理 knowledge_base 里 Kimi pipeline 无法自动决定的 pending 条目（client/wiki/pending/decisions.json
  和 market/wiki/pending/decisions.json），以及 lint 静态报告里的问题（死链、孤儿页、stale、
  schema 违规）。用户说"处理 pending"、"wiki 里有没有待整理的"、"知识库检查一下"、"整理知识库"、
  "triage"时触发。Karpathy LLM Wiki 里的知识级 lint（矛盾、gap、缺交叉引用）也走这个 skill。
compatibility: Codex
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# assistant_zh_knowledge-triage

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


你是 knowledge_base 的维护员。工作分四层：

1. **Pending 队列**：Kimi pipeline 决策置信度低时扔进来的观点，需要人判断
2. **Profile observations（V3+）**：pipeline 自动写入 `client/profile/observations/` 的 profile-worthy 观察，等人工拍板是否"提升"到主 profile 文件
3. **Lint 问题**：机械检查发现的 schema 违规、死链、孤儿、stale
4. **知识级检查**（用户主动要求时）：矛盾、gap、缺交叉引用 — 这是 Codex 必须亲自读页才能判断的

## 1. 打开会话时的三步

```bash
# a. 看 pending
cat knowledge_base/client/wiki/pending/decisions.json 2>/dev/null
cat knowledge_base/market/wiki/pending/decisions.json 2>/dev/null

# b. 跑最新 lint
cd /Volumes/ExtSSD2601/AI_Assistant/assistant_zh
python3 -m workflow.knowledge_ingest lint

# c. 读 lint_report.json
cat knowledge_base/lint_report.json
```

开口第一句告诉用户现状：`pending X 条 + schema violations Y + orphans Z + dead links W`。

## 2. 处理 Pending 条目（逐条）

每条 pending 长这样：

```json
{
  "source": "2026-04-12_c3_理论课_test.txt",
  "viewpoint": {
    "topic_hint": "...",
    "core_view": "...",
    "details": "...",
    "page_type": "topic"
  },
  "decision": {
    "action": "merge",
    "target_page": "topic-eval-driven.md",
    "confidence": 0.55,
    "reasoning": "..."
  },
  "reason": "low_confidence_or_contradiction"
}
```

### 对用户展示

用清单形式一条条过，**不批量**（否则信号被稀释）：

> 📋 Pending #1（来源：2026-04-12...）
>
> Kimi 建议：**merge** 到 `topic-eval-driven.md`，confidence 0.55。
>
> 原观点：
> > <core_view>
>
> 我读了 `topic-eval-driven.md`，判断 [你的判断]。
>
> 你怎么选？
> - `accept`：按 Kimi 建议 merge
> - `retarget <page>`：merge 到另一页
> - `new`：独立成新页（如需标注反转某老页，指明 `contradicts: [...]`）
> - `skip`：这条观点没价值，扔掉

### 落盘

用户选定后，**你自己用 Edit/Write 操作**（别再调 pipeline），然后：

1. 从 `pending/decisions.json` 移除该条
2. 追加 `wiki/log.md`：
   ```
   ## [YYYY-MM-DD HH:MM] [TRIAGE] resolved <topic_hint> | <accept|retarget|new|skip>
   ```

### 关键决策规则（pipeline 3-action 空间）

- **merge**：新观点是目标页判断的加深 / 延展 / 补充论据
- **new**：观点独立，现有页吸收不了
  - 若这条新观点**反转**某老页的判断（不是演进），在 new 页 frontmatter 加 `contradicts: [老页.md]`；apply 层会自动在老页加 `contradicted_by: [新页.md]`
- **skip**：已被完整覆盖 / 低价值 / 非张和原话
- **拿不准就问用户** — 不要瞎猜

**矛盾 vs 演进**：A → A+ 是演进（走 merge，更新 updated_at）；A → not A 是反转（走 new + contradicts）。

## 2.5 Profile observations 审阅（V3+）

Pipeline 对 "profile_worthy" 的观点（行业判断 / 能力圈扩展 / 账号定位迭代 / 写作风格沉淀 / 核心价值观）自动写入 `client/profile/observations/obs-YYYY-MM-DD-<slug>.md`，等待人工决定是否提升到主 profile 文件。

**主 profile 文件是人工只读的**（`boss-profile.md` / `account-positioning.md` / `content-strategy.md`），pipeline 绝不直接碰；observations/ 是独立的追加区。

### 开始审阅

```bash
python3 -c "
from workflow.knowledge_ingest.core import default_paths
from workflow.knowledge_ingest.profile import list_unpromoted
for obs in list_unpromoted(default_paths()):
    print(f'{obs[\"observation_id\"]} → {obs[\"profile_section\"]}  conf={obs[\"confidence\"]}  {obs[\"title_line\"]}')
"
```

或直接 `ls knowledge_base/client/profile/observations/`。

### 逐条展示

对每条 unpromoted 观察：

> 📋 Observation #1（来源：<source>，建议归入 `<section>` § <field>，confidence 0.82）
>
> 观察：<title_line>
>
> 核心判断：
> > <core_view from obs body>
>
> 与现有 profile 的关系：
> <relation>
>
> 你怎么选？
> - `promote`：内容合理，我把它**手动合并**到 `<section>.md` 对应章节，然后在 obs 文件里标 `promoted_to_main: true`
> - `refine <修改建议>`：观察有价值但表述需要改，我按你意见调整 obs 内容后再合并
> - `discard`：观察质量低 / 误判 / 已过时，删掉 obs 文件
> - `keep pending`：先留着，之后再看

### 落盘

- **promote**：
  1. 用 `Edit` 工具在目标主 profile（`boss-profile.md` 等）的合适章节追加 1 段话（参考 obs 的 `core_view` + `relation`），**可改写以贴合主文件语气**
  2. 调 `profile.mark_promoted(obs_path)` 或手动把 obs frontmatter 的 `promoted_to_main: false` 改成 `true`（**保留 obs 文件**作为历史痕迹）
  3. `wiki/log.md` 追加 `## [YYYY-MM-DD HH:MM] [TRIAGE-PROFILE] promoted <obs_id> → <section>`

- **refine**：
  1. Edit obs 文件里的相关字段（通常是 `## 核心判断` 或 `## 与现有 profile 的关系` section）
  2. 不立即提升；保持 `promoted_to_main: false`
  3. log.md 追加 `[TRIAGE-PROFILE] refined <obs_id>`

- **discard**：直接 `rm` obs 文件 + log.md 追加 `[TRIAGE-PROFILE] discarded <obs_id> | reason`

- **keep pending**：什么都不做

### 决策原则

- **Promote 的内容要经得起三个月后重读**：不要把短期热点判断当长期观点提升
- **Refine 优先于 promote**：pipeline 产出的 obs 往往语气偏 formal，主 profile 有自己的腔调（读读原 profile 文件感受一下再合并）
- **discard 占比应该不低**：extract 为了不漏报会倾向过度标记 profile_worthy；30-50% discard 率算正常
- **profile 主文件的增长要克制**：一个月提升 1-3 条就够了；堆太多会稀释身份定义

## 3. 处理 Lint 问题

### schema_errors（hard fail）

**必须解决**。通常是 migration 漏掉的老页或人工编辑时破坏的。修 frontmatter，不够信息就问用户。

### duplicate_topic_ids

**必须解决**。两种来源：
- 迁移时失误 → 手动合并两页内容，删掉一个
- 真的是独立页重了 slug → 重命名其中一个 topic_id

### dead_links

- 链接的页被删过 → 从引用页里删掉这个链接
- 链接的页名拼错 → 修链接
- 页应该存在但没建 → 问用户：这是遗漏的 gap 还是笔误？

### orphans

读这个页的内容判断：
- 有价值但只是没交叉引用 → 在相关页加 `[[...]]` 链接 + 更新 index.md
- 已过时 / 没人会再用 → 和用户确认后删
- `synthesis-*` 页且主题已合并进别处 → 考虑删

### stale（>60 天未更新且被引用）

问用户：这个判断还有效吗？
- 还有效 → 更新 `updated_at` 到今天，保持
- 已过时但值得留痕 → 加 `> ⚠️ [YYYY-MM-DD] 此判断已部分过时：<简短原因>` 再更新 updated_at
- 彻底过时 → 加 archive 标记或删除

## 4. 知识级检查（用户主动要求时）

用户说"帮我扫一下知识库有没有矛盾"、"wiki 哪里缺了内容" 时执行：

### 抽样读（5-10 页）

用 Glob + 随机 + 新近更新的页优先。读全文找：

- **内部矛盾**：同一主题的两页得出相反结论（不是演进）
- **缺 cross-ref**：A 页讨论的东西在 B 页也应出现但没链接
- **knowledge gap**：index 里有类目但没页（例如 `## 技术判断` 下只有 2 条，但 market 里实体已经 10+）
- **建议新探索**：张和 profile 里列出了他关心的领域，但 wiki 里缺对应页

### 产出

**建议清单**给用户，不自动改：

```
[知识级扫查结果]
矛盾：topic-X 和 topic-Y 在"<具体点>"结论相反 → 建议：<action>
缺引用：topic-A 里提到 B，应链接 entity-B
gap：market/landscape 缺对 <entity> 的独立页，尽管已在周报出现 5 次
```

用户决定怎么改，你再动手。

## 5. 边界

- **不删除 profile/ 或 stable/ 下的东西** — 人写只读
- **不调 pipeline 重跑** — 那是 `assistant_zh_knowledge-ingest` 的事。triage 只做"Kimi 已经跑完但拿不准的收尾"
- **不跳过确认** — 每条 pending / 每个 lint 项都要 explicit 用户拍板（除非用户明确说"按你判断处理"）
- **落盘失败不重试** — 报错给用户看，别猜原因改文件

## 关键路径

- `knowledge_base/client/wiki/pending/decisions.json`
- `knowledge_base/market/wiki/pending/decisions.json`
- `knowledge_base/lint_report.json`（lint 命令产物）
- `knowledge_base/client/wiki/log.md` / `knowledge_base/market/wiki/log.md`（记每次 triage）
