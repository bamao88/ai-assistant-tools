# Zhang Viewpoint Dossier

## Topic
大选题：Agent 评估为什么会变成 AI PM 的基本功。
边界收在：**Agent 产品（多步、调工具、有轨迹）** 这个具体形态下，评估对 AI PM 的角色，从"加分技能/上线前质检"变成"入场门槛"。不写泛泛的"AI 很重要要做 eval"，也不写转型焦虑、招生。

## Search Terms Used
- knowledge_base/client/wiki/expertise 全量 grep：`eval / 评估 / 评测 / 跑分 / Agent / 质量`
- 精读：topic-eval-driven、topic-dual-eval-set-iteration、topic-ai-eval-dimensions-core、exp-eval-driven-at-scale、qa-eval-iteration-nature、qa-eval-team-management-lessons、topic-ai-pm-agent-core-line
- 外部 deep research：agent evaluation vs LLM eval、trajectory vs output、compounding error、tool-call eval

## Confirmed Zhang Views
- [评测驱动是 AI 产品落地第一方法论，AI 时代评测/研发权重 5:5（传统互联网是 2:8）] 来源：`knowledge_base/client/wiki/expertise/topic-eval-driven.md`；置信度 HIGH；证据类型：课程+试听课原文（多处一致）。
- [产品经理是评测的最佳负责人；硅谷共识"PM 不做评测以后就别干了"；评测集这块算法工程师认知不足，是 PM 为团队做最大贡献的地方] 来源：同上 + `topic-eval-driven.md`（二期第七课）；置信度 HIGH；证据类型：课程原文。
- [小米自动驾驶把重心放训练集而非评测集，踩了上亿元大坑；特斯拉测评负责人=数据引擎负责人，直接向马斯克汇报] 来源：`topic-eval-driven.md` / `qa-eval-team-management-lessons.md`；置信度 HIGH；证据类型：张和亲历转述。
- [AI 评测必须亲眼看原始 case 和中间产物，不能只看统计图/benchmark 分数；测 10 个 case 认知 55 分、100 个 80 分、1000 个还升] 来源：`topic-eval-driven.md`；置信度 HIGH。
- [Agent 评测要养两套评测集：端到端 + 模块专属；只做端到端看不到中间过程不行] 来源：`topic-dual-eval-set-iteration.md`；置信度 HIGH。
- [deerflow 项目：先别改 prompt，先人工标 200 条日志，定位是 planner / reporter / coordinator 哪个环节出问题；有竞品对标才定位得了是哪个 Agent 差] 来源：`topic-eval-driven.md`（deerflow 段）；置信度 HIGH。
- [快递下单助手默认成功率 40-50%，用评测驱动逐步优化架构/异常/API 到 95% 上线，这个过程比做 fancy 新功能更体现 AI PM 能力] 来源：`topic-eval-driven.md`（20250723）；置信度 HIGH。
- [AI 产品功能会逐渐拉齐，但效果差异持久存在，所以对比/benchmark 关键] 来源：`topic-eval-driven.md`；置信度 HIGH。
- [体感评测先"干了就赚了"，要求科学量化打分时十组有七组会放弃；评测集不可能穷尽，是每周加深认知的持续迭代] 来源：`topic-eval-driven.md` / `qa-eval-iteration-nature.md`；置信度 HIGH。
- [评测要绑真实业务数据、用自己懂的领域测，假 case（"帮我找最贵的胡萝卜"）测不出真问题] 来源：`topic-eval-driven.md`（shopify 段）；置信度 HIGH。
- [当前 80% AI PM 岗以 Agent 为能力主线] 来源：`topic-ai-pm-agent-core-line.md`；置信度 HIGH。

## Viewpoint Core
张和的原始立场（HIGH）：评测驱动是 AI 产品落地的第一方法论，产品经理是评测的最佳负责人、必须亲手抢评测，"PM 不做评测就别干了"；评测的关键是看原始 case、看中间过程、用两套评测集、持续迭代。

## Boundaries
- 张和没有用"复合误差 0.95^20=36%""轨迹评测 vs 输出评测虚高 20-40%"这种数学/统计表述。这些是本文用来解释"为什么 Agent 把门槛抬高"的研究延展，**不能写成张和原话**。
- 张和讲的是"评测是 AI PM 核心技能"这个一般命题；"在 Agent 形态下从加分项升级为入场券"是本文在他立场上的收窄/推进，要写成本文判断，不是凭空归到张和早就这么说。
- 不把"快递助手 40→95%""deerflow 200 条日志"以外的具体数字、bad case 细节编出来。

## Depth Gap
张和材料已经很深（HIGH，覆盖机制、亲历、训练营 bad case、可执行动作），约 80% 深度。唯一缺口是**"为什么偏偏是 Agent"**的机制桥：张和讲了"看中间过程/两套评测集"，但没显式讲清 Agent 的多步轨迹如何在数学上放大不确定性、以及只看输出为什么会系统性假阳性。这正是标题"Agent"二字的承重点，需要外部研究补上 Warrant。

## Research Questions
1. Agent 评估比单轮 LLM 评估难在哪里（机制层面）？
2. 多步轨迹的复合误差有没有可量化的直觉（每步可靠性 × 步数）？
3. 只看最终输出 vs 看完整轨迹，漏判差多少？
4. 有没有权威一手来源（Anthropic / LangChain）能锚定这个机制？

## Allowed Extensions
- 复合误差直觉：0.95^20 ≈ 36%（数学事实，任何人可验证，写成"做个乘法就知道"，不归张和）。
- 输出-only 评测比轨迹评测通过率虚高 20-40%（来自 Anthropic/LangChain 工程博客，写成"业界反复出现的观察"，不归张和）。
- 工具调用假阳性、非确定性路径（机制解释，服务张和"必须看中间过程"的原始判断）。

## Forbidden Moves
- 把 36% / 20-40% 写成"张和算过 / 张和一直这么说"。
- 用外部研究把文章主张换成"Agent 评测工具选型指南"，偏离张和"PM 抢评测"立场。
- 把张和谨慎的"先干了就赚了"写成"必须一上来搞科学量化打分"。
- 暴露调研痕迹（"我查到""我看到一篇博客"）。

## Decision Before Research
WRITE-RESEARCH（张和观点 HIGH，research questions 明确且只补 Agent-specific 的机制桥，不换立场）。
