# Zhang Viewpoint Dossier

## Topic
AI PM 作品集为什么不能停留在 demo，而要证明自己能把 AI 能力变成"稳定产品系统"。
边界收在：**求职/转型场景下的作品集（求职项目）**，不是商业化产品、不是创业项目。讨论对象是"给面试官看的 AI 产品项目应该做到什么程度、怎么呈现"。

## Search Terms Used
- `作品集 / demo / Demo / 产品化 / 稳定产品 / 工程化 / 可用产品`（全库 grep）
- wiki/expertise 下定向：`前后对比 / 准确率 / 从X提升到 / 评测分 / 上线后 / baseline / 迭代到第N版 / 第三版 / 结果是`
- 精读页：`topic-demo-to-production`、`topic-ai-product-launch-difficulty`、`exp-multiagent-high-cost-demo-strategy`、`topic-project-expression-depth-methodology`、`topic-iteration-storytelling`、`exp-interview-iteration-story`、`topic-job-project-showcasing`、`topic-launch-first-threshold`、`exp-startup-ai-product-interview-packaging`、`topic-ai-pm-profile-eval-driven`

## Confirmed Zhang Views

- **[Demo 变工业级 = 复刻完整人类产研流程]** 需求分析→PRD→技术架构规划→实现→单元测试→模块测试→集成测试，每个阶段不能漏，只是每个环节换成 Cloud Code/Codex 来做。来源：`wiki/expertise/topic-demo-to-production.md`（原文 + 黑客马拉松 kickoff 答疑）；置信度 **HIGH**；证据类型：会议/课程原文引用。
- **[迭代之路 / 踩坑之路是面试必杀技]** "100% 有效""市场上所有教 AI Coding 项目的人都不懂这一条"。用 v1/v2/v3 三种架构讲清演进，且每一代都用评测驱动暴露问题再升级。来源：`topic-iteration-storytelling.md`、`exp-interview-iteration-story.md`；置信度 **HIGH**；证据类型：多次会议一致表述 + 直接引语。
- **[上线 > 本地 demo]** "只要敢上线就是牛逼""有个域名、有个官网、哪怕粗糙，就比只在本地电脑跑的 demo 强太多"。来源：`topic-launch-first-threshold.md`；置信度 **HIGH**；证据类型：Demo Day 点评原文。
- **[Demo 阶段故意贵和慢、不用优化]** "在你没有用户之前，花多少钱都是零""目前阶段不用优化，先跑 demo 上线"。来源：`exp-multiagent-high-cost-demo-strategy.md`；置信度 **HIGH**；证据类型：答疑原文。
- **[项目"平淡"的本质是缺分析框架，不是项目本身差]** 有方法论/体系/对标硅谷竞品就能找到亮点。来源：`topic-project-expression-depth-methodology.md`；置信度 **HIGH**。
- **[AI PM 核心画像 = 评测驱动方法论 + 前沿洞察 + 技术平等交流]** "把项目讲深的前提是把项目做深"。来源：`topic-ai-pm-profile-eval-driven.md`；置信度 **HIGH**。
- **[求职项目本质是"自然地炫技"]** 必须占 RAG / Agent 至少一样，关键词 agent/deep research/记忆/AIGC；只调 prompt 的项目不建议走求职赛道。来源：`topic-job-project-showcasing.md`；置信度 **HIGH**。
- **[先简单后复杂，系统越复杂越难归因]** Agent 开发先用原生模型调工具，再逐步复杂化（Excel Copilot：先 workflow，发现 Python 数据分析跑不通才上 Agent）。来源：`topic-demo-to-production.md` / `exp-multiagent-high-cost-demo-strategy.md`；置信度 **HIGH**。

## Viewpoint Core
张和的真实立场：**作品集不能停在"本地能跑的 demo"，但"不停在 demo"的关键不是把产品做到生产级稳定，而是 (1) 复刻一套完整产研流程把它推到能上线的工业级，(2) 能讲清楚一条"迭代之路 / 踩坑之路"——v1→v2→v3 架构演进，每一代用评测驱动暴露问题再升级。真正打动面试官的是这条故事线证明的"产研掌握感 + 评测驱动方法论"，而不是产品的稳定性指标。**

## Boundaries
- 张和**没有**把"稳定产品系统 / 高可用 / uptime / 生产级稳定性"作为作品集的核心衡量标准。恰恰相反，他反复说 demo 阶段不用优化、花钱是零、先上线。**不能把"稳定/工程化健壮性"包装成张和的核心主张。**
- 张和讲的"工业级"指**复刻完整产研流程（含各级测试）**，落点是"能上线、能持续迭代、有评测兜底"，不是"运行稳定无故障"。两者必须区分，否则就是观点偏移。
- 没有任何一个张和学员/团队案例在知识库里留下"评测前后对比数字 / 准确率从 X 到 Y"的完整结果记录。不能编造学员项目的量化结果。
- "demo 阶段贵和慢"与"作品集要做到工业级"在张和体系里靠**阶段**区分（先上线跑 demo → 再复刻产研流程升级 → 讲迭代之路），不是矛盾；写时必须讲清阶段，不能把它写成"一上来就要做稳定系统"。

## Depth Gap
现有张和材料缺的不是观点，而是**承载这篇方法文的"主案例脊柱"和"填好样例"**：
- 缺一个贯穿全文、五要素齐全的主案例：原始状态→**失败证据**→修改动作→**结果变化（可核查/可量化）**→产品判断。现有案例（Excel Copilot workflow→Agent、Yvonne 英语 APP v1/v2/v3、赵晨旭串行多 Agent 成本）都缺"结果变化"这一环，且多为前瞻建议而非已完成迭代。
- 缺一份**填好的样例**：例如一张"demo 级 vs 工业级作品集"对照清单，或一份真实的"评测前后对比表 / 迭代之路 roadmap 实例"。现有材料只能支撑方法框架（张和的产研复刻流程、迭代之路讲法），不能给出已填好的真实样例而不涉及编造。
- 缺一个真实 bad case 的完整展开（一个"停在 demo 被面试官问穿"或"上线后崩在某个场景"的具体故事，带细节）。

## Research Questions
（仅在补足上述张和一手缺口后才需要；外部研究只能补机制/外部案例，补不了张和学员结果）
1. demo→production 在工程界公认的断裂点有哪些（评测覆盖、长尾场景、成本/延迟、可观测性）？用于补"为什么停在 demo 危险"的机制层。
2. 有没有公开可引用的、demo 到生产掉链子的真实案例（如 Apple Intelligence 3B 蒸馏不出智能——张和已引用过）可作机制佐证？
3. 业界对"AI 产品评测体系"的标准做法，用于把"评测驱动"写得更可操作。

## Research Source Ledger
**本轮未执行外部 deep research。** 原因：阻塞这篇文章的缺口（主案例脊柱的"结果变化"环 + 填好样例 + 完整 bad case）属于**张和一手学员/团队材料**，外部研究无法补足，强行用外部案例顶替会偏离 A 路由（张和第一人称方法文）的定位。因此暂不引入任何外部数字。

下表为**正文若写将依赖的内部来源台账**（全部为张和一手，非研究延展）：

| 拟用判断/事实 | 来源路径 | 支持程度 | 可否写进正文 |
|---|---|---|---|
| Demo→工业级 = 复刻完整产研流程（含各级测试） | `wiki/expertise/topic-demo-to-production.md` | 直接支持 | YES |
| 迭代之路 100% 适用、是面试必杀技 | `topic-iteration-storytelling.md` / `exp-interview-iteration-story.md` | 直接支持 | YES |
| 上线 > 本地 demo | `topic-launch-first-threshold.md` | 直接支持 | YES |
| demo 阶段不用优化、花钱是零 | `exp-multiagent-high-cost-demo-strategy.md` | 直接支持 | YES（必须标阶段） |
| Excel Copilot：workflow→Agent（先简单后复杂） | `topic-demo-to-production.md` | 直接支持原始状态+失败+动作；**不支持结果数字** | DOWNGRADE（只能定性，不能写量化结果） |
| 赵晨旭串行多 Agent ≈5 元/次、3 分钟 | `exp-multiagent-high-cost-demo-strategy.md` | 直接支持 | YES（注意是估算口径） |
| 项目平淡=缺分析框架 | `topic-project-expression-depth-methodology.md` | 直接支持 | YES |

> 注意：外部研究中的任何精确数字一旦引入，必须新增进本台账并标注支持程度；当前台账内无外部数字。

## Allowed Extensions
- 可以由外部研究补"demo→production 为什么会断裂"的**机制解释**（评测覆盖不足、长尾场景、成本/延迟、可观测性缺失），但必须写成"行业普遍机制 / 本文推演"，不能写成张和原话。
- 可以把张和分散的判断（复刻产研流程 + 迭代之路 + 评测驱动 + 上线优先）**整合**成一个"作品集成熟度阶梯"，但要标明这是本文对张和方法的体系化归纳。

## Forbidden Moves
- 把"稳定/高可用/生产级健壮性"写成张和的核心主张（实为偏移——张和讲的是产研流程完整 + 迭代故事，且明确 demo 阶段不优化）。
- 编造任何学员项目的评测前后对比数字、准确率、用户量、上线后稳定性指标。
- 把"先上线跑 demo、花钱是零"和"要做工业级"写成自相矛盾，而不交代阶段。
- 把外部 demo→production 工程实践直接归因给张和。
- 用"我在训练营看到某学员把准确率从 X 提到 Y"这类没有来源的具体战绩。

## Decision Before Research
**SUPPLEMENT-CASE**（不进入 WRITE-RESEARCH，也不是 SUPPLEMENT-ZHANG-VIEW）。

理由：张和观点充足（多页 HIGH 置信度），**不缺立场**；但这是一篇方法文，`topic-preflight.md` 硬门槛要求 Primary Case Spine（五要素齐全、贯穿全文）和一组强证据（填好样例 / 真实前后对比）。现有材料缺"结果变化"环、缺填好样例、缺一个完整展开的真实 bad case，且这些缺口是**张和一手材料**，deep research 无法补。外部研究只能补机制，补不上案例脊柱，所以也不先做研究。结论：先补素材，不写正文。详见 `brief.md`。
