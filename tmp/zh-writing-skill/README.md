# zh-writing-skill

> 张和账号"以输入素材类型路由"的写作 skill。当前已迁入 `.claude/skills/zh-writing-skill/`，作为正式写作入口，替代旧 `content-writing-guide`。

---

## 这个 skill 是什么

针对一个长期问题：**写作前没有显式回答“张和已经怎么看、我手里有什么素材、应该走哪种写法”**。

`content-writing-guide` 现有的 4 个 styles（观点解读 / 人物事件解读 / 体系整理 / 教程操作）按"输出形状"分类，回答的是"我想写一篇什么形状的文章"。但实际上张和这个账号的差异化主要在素材这一端——大厂 8 年经历、亲历事件、实测产品，这些素材决定走哪种写法。

现在的 `zh-writing-skill` 先按"张和观点"定原点，再按"输入素材类型"路由。大选题必须先输出 `Zhang Viewpoint Dossier`，明确张和原观点、置信度、可研究加深的方向和禁止偏移的边界。

**zh-writing-skill 按"观点原点 + 输入素材类型"路由**：

| 我手里的素材是… | 加载 |
|---|---|
| 张和亲历事件 / 个人判断 / 踩坑 / 大厂内部经历 / 长期实测产品 | A-firsthand |
| 一个技术概念 + ≥3 海外信源 + 给 PM 体系化讲透 | B-knowledge-system |
| 一篇海外博客 / 论文 / 访谈 | C-single-source |
| 都不强匹配 | 兜底 → A-firsthand 反主流单点子模板 |

详见 `SKILL.md` 路由决策树。

> **注**：D-product-feel 已删除（暂未启用），长期实测产品并入路由 A 处理。
> A/B/C 是普通 markdown 路由文件，不带 frontmatter，硬隔离不会被 Claude 当独立 skill 触发。

---

## 战略价值（3 个子路由的差异化）

研究报告（`knowledge_base/market/raw/competitor/research-report.md`）发现：

- **形态 6（业内深度复盘）**= A-firsthand 的"业内复盘"子模板 — **国内 4 个竞品博主全部缺席**，因为这种形态需要"在大厂内部真正推过这件事"的身份才能写。张和小米 8 年是不可复制的资产
- **形态 7（PM 视角技术教材）**= B-knowledge-system — **国内空白**，海外 Eugene/Lilian/Hamel/Ethan 都在做。张和已写过 3 篇同形态文章，已经在领跑
- 形态 1/2/4/5/8 — 国内有竞品在做，但 ZH 可以做得更好（结合海外信源 + 张和视角）

**A-firsthand 的"业内复盘"和 B-knowledge-system 是 ZH 账号的两块差异化阵地**，本 skill 的核心战略目标是把这两块能力沉淀下来。

---

## 目录结构

```
.claude/skills/zh-writing-skill/
│
├── README.md                  本文件 — 设计说明 + 迁移路径（人看的，不被 AI 加载）
├── SKILL.md                   ★ 唯一触发入口 — 预检 + 路由 + 审稿闭环
├── zhang-viewpoint-first.md    写前观点定位 — Zhang Viewpoint Dossier / deep research 边界 / 观点偏移防线
├── topic-preflight.md         写前选题预检 — Article Brief / 预计80分线 / WRITE-SUPPLEMENT-DOWNGRADE-KILL
├── article-quality-standard.md 发表价值标准 — 7 问 / Toulmin 论证 / 100 分表
├── benchmark-corpus.md        好文章基准库 — 5 种 80 分主形态 / 标杆样本 / 最低线
├── quality-anchors.md         正反样本校准 — 一篇正样本锚点 + 14 篇差稿反样本
├── zh-editor-review.md        写后独立审稿 — 30分rubric / 80分线 / PASS-REVISE-SUPPLEMENT-KILL
│
├── A-firsthand.md             一手经历型路由文件（含 3 子模板：反主流单点 / 踩坑指南 / 业内复盘 ★）
├── B-knowledge-system.md      知识体系型路由文件（PM 教材）★
├── C-single-source.md         单源解读型路由文件（含 3 档作者在场度）
│
├── C-single-source/           C 路由文件依赖的内部资源
│   ├── references/            深思圈样本 + style-guide + example-articles
│   └── evals/                 C 历史 eval 数据（多轮迭代记录）
│
├── corpus-paths.md            素材路径地图（张和原作 / 国内竞品 / 海外博主 / extra-samples）
│
└── evals/
    ├── routing-evals.json       顶层路由准确性测试用例（9 个）
    └── quality-loop-evals.json  预检 / 审稿 / 正反样本回归用例
```

AI 加载路径：顶层 SKILL.md（成功指标 + 总流程）→ `zhang-viewpoint-first.md`（张和观点原点 + deep research 边界）→ `topic-preflight.md`（Article Brief + 预计分）→ `article-quality-standard.md`（发表价值硬门槛）→ `benchmark-corpus.md`（选择主基准形态）→ 选中的 `X.md`（写法）→ `zh-editor-review.md`（独立审稿 + 80分线）→ 必要时 `quality-anchors.md` 校准正反样本。

A/B/C 路由文件是普通 markdown，没有 frontmatter，不会被 Claude skill 发现机制扫到。

---

## 与 content-writing-guide 的关系

**新 skill 是 content-writing-guide 的替代者，当前已作为正式入口使用**。

### A-firsthand.md 起步内容来自 content-writing-guide/SKILL.md

现有 `content-writing-guide/SKILL.md` 的 6 步流水线 + 防三种坏写法（研究综述化 / 贴标签 / 人设化）+ 引语硬规则 + 第一人称观察硬规则——本质上是为"亲历型写作"设计的方法论。

直接搬到根目录 `A-firsthand.md` 作为起步内容，**保留全部防御机制不改写**。底部加 3 个子模板（反主流单点 / 踩坑指南 / 业内复盘）的差异化指引。

### B/C 子路由各自的方法论

B-knowledge-system / C-single-source **不强求 A 的 6 步流水线**——A 的流水线为亲历型论证设计，B/C 各自需要不同的写作流程：

- B 的核心创新是"自创分类法"，对应的是 A-Step 2 的"抽象成机制卡"
- C 的核心变量是"作者在场度"，对应 A 没有

详见各子路由文件。

---

## 取代 content-writing-guide 的迁移路径

```
✅ 阶段 1（已完成）：
   建沙箱 tmp/zh-writing-skills/
   写 SKILL.md 路由 + A/B/C 三个完整路由文件 + corpus-paths
   content-writing-guide 不动

✅ 阶段 2（已完成）：
   A/B/C 三份路由文件分别经多轮 evals 调过到效果满意
   架构扁平化（去 SKILL.md frontmatter，硬隔离独立触发）

✅ 阶段 3：迁出沙箱
   tmp/zh-writing-skills/ → .claude/skills/zh-writing-skill/
   content-writing-guide 已移到 backup / 归档，不再作为正式入口

⏳ 阶段 4：路由层评测
   - 跑 evals/routing-evals.json 验证路由准确性
   - 跑同一组写作 case 对照 zh-writing-skill 和 content-writing-guide
   - 评测过关标准：路由准确 + 写作质量等量或更好
```

**当前阶段 1-3 已完成**。阶段 4 单独决策、单独执行。

---

## 本轮已完成

- ✅ 目录结构扁平化（顶层 SKILL.md + A/B/C 平级 .md 路由文件 + C 子目录承载内部资源）
- ✅ SKILL.md 完整路由决策树（3 路径 + 兜底）+ 通用规则 + 7 关基础验收
- ✅ A-firsthand.md 完整内容（多轮 evals 调过；含 3 子模板：业内复盘 ★ / 踩坑指南 / 反主流单点）
- ✅ B-knowledge-system.md 完整内容（多轮 evals 调过；自创分类法方法论）
- ✅ C-single-source.md 完整内容（多轮 evals 调过；3 档作者在场度）
- ✅ A/B/C 改为普通 markdown，无 frontmatter — Claude skill 发现机制扫不到，硬隔离
- ✅ corpus-paths.md 完整路径地图（张和原作 + 国内竞品 + 海外样本 + extra-samples）
- ✅ D-product-feel.md 移除（暂未启用，长期实测产品并入 A）
- ✅ 孤儿样本目录清理（`references/samples/` 各子目录无 body 引用，删除）
- ✅ `evals/routing-evals.json` 9 个路由测试用例（待用干净 subagent 跑）
- ✅ 增加写前 `topic-preflight.md`，新文章先 brief，不直接起稿
- ✅ 增加 `article-quality-standard.md`，用发表价值、Toulmin 论证和 100 分表替代单纯风格评分
- ✅ 增加 `benchmark-corpus.md`，先判断文章属于哪种高质量形态，再判断能否到 80 分
- ✅ 增加 `quality-anchors.md`，一篇认可稿只做质量锚点，14 篇差稿做反样本
- ✅ 增加 `zh-editor-review.md`，写后独立给 `PASS / REVISE / SUPPLEMENT / KILL`
- ✅ 明确 30 分 rubric 与 80 分交稿线，缺素材时走 `SUPPLEMENT` 而不是继续改文风
- ✅ A/B/C 从“唯一权威”降级为写法路由，预检和审稿可否决文章
- ✅ 增加两轮返修上限，防止继续堆风格禁令
- ✅ 增加 `quality-loop-evals.json` 覆盖差稿识别、正样本使用、素材不足拒写，以及“流程完整但文章不到 80 不能 PASS”
- ✅ 增加 `zhang-viewpoint-first.md`，大选题先定位张和观点，再做 deep research；研究可以做深，但不能替换或伪归因张和观点

---

## 本轮未做（留待后续）

- ⏳ 用干净 subagent 跑 `evals/routing-evals.json` 验证路由准确性
- ⏳ docx 客户作品（`2026-04_AI产品落地架构*.docx`、`*RAGFlow*.docx`）转 md
- ⏳ D 重启决策（如确实需要长期产品体感独立路径，再重建子模板）

---

## 验证方式

读完 SKILL.md 应能在 1 分钟内对以下场景做正确路由判断：

1. "我刚发现字节做出了我两年前在小米推的方向" → A-firsthand / 业内复盘子模板 ★
2. "我想把 Anthropic Eval 博客 + Hamel Eval + 张和实践串成 PM 教材" → B-knowledge-system ★
3. "我看完 Karpathy 最新一篇博客想写解读" → C-single-source（高在场度档）
4. "我用了 ColaOS 三周，体验完整地写下来" → A-firsthand（产品体感属一手亲历，按业内复盘 / 反主流单点写）
5. "我刚踩了 Claude Code 封号的坑想写指南" → A-firsthand / 踩坑指南子模板
6. "我想写 Anthropic 最新发布的鲜明判断"（无张和经历无多源整合） → C-single-source（高在场度）
7. "想写一篇关于 Agent 评估的文章"（大选题） → 先 `Zhang Viewpoint Dossier`；如果张和观点不足，先 `SUPPLEMENT-ZHANG-VIEW`，不能直接起稿

7 个场景全 match 正确 = 架构通过。

---

## 工作目录

绝对路径 | `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/.claude/skills/zh-writing-skill/`

旧沙箱路径 | `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/tmp/zh-writing-skills/`

文档生成日期 | 2026-05-08
