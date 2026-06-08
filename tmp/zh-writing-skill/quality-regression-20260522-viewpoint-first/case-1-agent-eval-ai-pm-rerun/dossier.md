# Zhang Viewpoint Dossier

## Topic
Agent 评估为什么会成为 AI PM 的基本功。边界收在：为什么是「Agent」让评估从「上线前质检」变成「贯穿开发的基本功」，以及为什么这件事天然是产品经理的活，而不是测试岗的活。不展开通用 LLM 评测教程，不展开训练营招生。

## Search Terms Used
- knowledge_base 检索：`评估 / eval / 轨迹 / trajectory / bad case / 跑分 / 评测`
- 重点读取：`topic-eval-driven.md`、`topic-ai-eval-dimensions-core.md`、`topic-dual-eval-set-iteration.md`、`topic-open-telemetry-agent-eval.md`、`qa-eval-iteration-nature.md`、`obs-2026-05-17-评测驱动ai产品落地.md`

## Confirmed Zhang Views
- [评测驱动是 AI 产品落地第一方法论，重要性甚至超过 50%；AI 时代评测与研发权重 5:5，而非传统互联网的 2:8] 来源：`knowledge_base/client/wiki/expertise/topic-eval-driven.md`、`obs-2026-05-17-评测驱动ai产品落地.md`；置信度 HIGH；证据类型：课程原文 + 多篇文章 + observation。
- [评测集要超前于训练集，一个 case 的标注成本是训练集的两到三倍；评测集是不均匀抽样（高考命题原理），困难 case 比例要高于真实分布] 来源：`topic-eval-driven.md`；置信度 HIGH；证据类型：课程原文。
- [产品经理应该是评测的最佳负责人，硅谷共识是 PM 必须做评测；要主动抢评测和数据这块，交出去就被动] 来源：`topic-eval-driven.md`（二期第七课）；置信度 HIGH；证据类型：课程原文。
- [张和本人在小米自动驾驶数据闭环项目，因把重心放在训练集而非评测集，踩了上亿元的坑后才悟出这个道理；对标特斯拉「AI 测评负责人和数据引擎负责人是同一人，直接向马斯克汇报」] 来源：`topic-eval-driven.md`、`obs-2026-05-17-评测驱动ai产品落地.md`；置信度 HIGH（亲历）；证据类型：课程原文 + observation。
- [必须亲自看原始 case，不能只看统计图 / benchmark 分数；测 10 个 case 认知是 55 分，测 100 个 case 提升到 80 分；look at your data，看够 100~200 条真实输入输出] 来源：`topic-eval-driven.md`；置信度 HIGH；证据类型：课程原文。
- [Agent 评测核心流程：trace 记录（OpenTelemetry）→ 构建评测集 → 批量跑 → 标注对比 → 筛失败 case → 理解优化方向；trace 记录能力是前提，要能分析 router / skill / planner / memory 召回各对不对] 来源：`topic-eval-driven.md`、`topic-open-telemetry-agent-eval.md`；置信度 HIGH；证据类型：课程原文 + 答疑。
- [成熟 Agent 产品要持续迭代两套评测集：端到端场景评测集 + 模块专属评测集；千万不能只做端到端、看不到中间过程] 来源：`topic-dual-eval-set-iteration.md`；置信度 HIGH；证据类型：课程原文 + 试听课答疑。
- [评测维度其实就那几类：RAG / Agent / 代码 / LLM，真实场景跑不出这些] 来源：`topic-ai-eval-dimensions-core.md`；置信度 HIGH；证据类型：答疑原文。
- [评测集穷尽不了业务场景，它是持续进化的，每周加深一点认知] 来源：`qa-eval-iteration-nature.md`；置信度 HIGH。
- [体感评测「干了就赚了」，主观排序也行，不要被科学量化打分卡死（十组里七组会因为追求科学打分而放弃）] 来源：`topic-eval-driven.md`（kickoff 0203）；置信度 HIGH。
- [AI 产品最难的不是开发，是把成功率从 40%/50% 评测驱动优化到 95% 能上线的过程；评测能解决普通团队的问题，但解决不了苹果那种「选题本身太难」的问题] 来源：`topic-eval-driven.md`；置信度 HIGH。

## Viewpoint Core
张和的原始立场：评测驱动是 AI 产品落地的第一方法论，重要性与研发持平甚至更高；它天然是产品经理最该抢的活；而且必须靠亲自看原始 case 积累，不是看跑分。这一立场来自他在小米自动驾驶重训练集轻评测集踩上亿坑的亲历，以及训练营里反复带学员做评测的经验。

## Boundaries
- 张和没有说过任何「Agent 评估比通用 LLM 评估难 X 倍 / 输出评测比轨迹评测虚高 X 成」这类带具体倍数 / 比例的对比。这类数字不能写进正文。
- 张和讲的是「评测驱动」这个大方法论；「Agent 让评估升级成基本功」这个**升级框架**是本文在他立场上的延展表述，要写成本文推演，不能写成「张和一直这么说」。
- 张和对特斯拉组织结构的描述是他**自己的对标说法**，正文要明确归到「张和讲过一个他一直拿来对标的例子」，不能写成已被第三方独立核实的事实。
- 评测能力是给普通团队的方法论，不是万能解药（苹果选题太难的边界是张和原话）。

## Depth Gap
现有张和材料覆盖「评测驱动」非常充分，但偏「通用评测方法论」。要把题收到「Agent」这个具体对象上，缺一点机制层的外部佐证：为什么 Agent 这种长链路、多步工具调用的形态，让「只看最终输出」特别不够用——需要外部一手工程资料补这块的定性机制（不是补数字）。

## Research Questions
1. 业界做 Agent 的一线工程团队，是否也把「轨迹 / trace」而不是「最终输出」当成 Agent 评估的起点？（找定性佐证，不找数字）
2. Agent 评估在工程上是否确实区分「最终输出 / 轨迹 / 单步」不同粒度？这能否佐证张和「端到端 + 模块专属两套评测集」的判断？

## Research Source Ledger
- [Agent 的「轨迹 / trace / transcript」是一次运行的完整记录，包含最终输出、工具调用、推理过程、中间结果；评测要系统化跑真实任务、定义期望输出、跟踪成功率 / token 消耗 / 工具调用次数 / 报错并收集推理轨迹] 来源：Anthropic Engineering, "Demystifying evals for AI agents"（https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents）；原文支持程度：直接支持机制方向，**不含任何「虚高 X 成」类数字**；可否写进正文：YES（仅作定性机制佐证，不带数字，不归因给张和）。
- [Agent 评估在工程上确实分三种粒度：final response（只看最终答案，把 agent 当黑盒）/ trajectory（看工具调用序列与参数）/ single step（孤立评单步）；端到端给的信号最强，但定位问题要落到单步] 来源：LangChain Docs, "Evaluate a complex agent"（https://docs.langchain.com/langsmith/evaluate-complex-agent）+ LangChain Blog, "Evaluating Deep Agents: Our Learnings"（https://www.langchain.com/blog/evaluating-deep-agents-our-learnings/）；原文支持程度：直接支持「端到端 + 模块/单步」两层评测的方向，**不含数字**；可否写进正文：YES（定性，佐证张和「两套评测集」判断，不归因给张和）。

## Allowed Extensions
- 「Agent 让评估从『上线前质检』升级成『贯穿开发的基本功』」——允许作为本文的组织框架，但写成本文推演 + 张和评测驱动立场的自然延伸。
- 用 Anthropic / LangChain 的工程实践，**定性**佐证「只看最终输出会漏掉工具调用、检索路径、重复尝试这些隐藏失败」「业界也分端到端和单步评测」——必须写成行业一手实践，不写成张和原话，不带任何被编造的数字。

## Forbidden Moves
- 写任何「Agent 评测比普通评测难 X 倍」「只看输出会虚高两到四成 / X%」类未经来源核实的数字（这正是上一版 cold-review 否决的失败模式）。
- 把 Anthropic / LangChain 的结论改写成「张和认为 / 张和在训练营讲过」。
- 把「评估 = AI PM 上限」这种延展断言写成张和的长期原话（要写成本文判断 + 由他评测驱动立场推出）。
- 把特斯拉组织结构写成已核实事实，而非张和的对标说法。

## Decision Before Research
WRITE-RESEARCH（张和观点 HIGH，research questions 明确：只补 Agent 形态下的定性机制，不补数字。研究已完成，见 Research Source Ledger。）
