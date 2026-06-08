# Zhang Viewpoint Dossier

## Topic
基于 Google DeepMind 的 "Closing the knowledge gap with agent skills"（Gemini API developer skill 实验，2026-03-25）这一篇官方博客，写一篇张和主账号文章，重点讲它对**细分 Agent 产品 baseline** 的意义。边界收在：不写 skill 的实现教程，不做 Google vs Vercel 的技术评测复述，只回答一个产品判断问题——当"通用模型 + 一个轻量 skill"能把任务成功率从 28% 拉到 96%，细分 Agent 产品要对标的 baseline 被抬到哪里、还值不值得做。

## Search Terms Used
`baseline`、`基线`、`skill`、`Skill`、`Agent 产品`、`细分`，命中后精读 `exp-product-baseline-method`、`topic-agent-cc-plus-skill-benchmark`、`topic-skill-over-mcp`、`topic-eval-baseline-open-source`。

## Confirmed Zhang Views
- [开发任何 AI 产品先用领先模型建第一版 baseline，把 prompt 调好作为基准，再和竞品对比，知道差距在哪、再决定是否换技术栈] 来源：`knowledge_base/client/wiki/expertise/exp-product-baseline-method.md`（一期第二/三课、黑客松 kickoff）；置信度 **HIGH**；证据类型：课程 + 会议原文。
- [陪伴类产品（学员小妖）：直接用 Claude 3.5 半天跑一个 baseline，用 system prompt 模拟竞品行为，再和竞品比差距] 来源：同上；置信度 **HIGH**；证据类型：课程辅导原文。
- [AI 相机：先用 GPT-4o 高级语音 / Gemini 2.0 Flash 实测 10 个场景，看有几个建议真正贴合，6-7 个达标才说明技术可行] 来源：同上；置信度 **HIGH**；证据类型：课程辅导原文。
- [产品越大对标越大，小产品别对标大项目；简单 AI 封装就直接对比 AI API 效果] 来源：同上（黑客松 kickoff）；置信度 **HIGH**。
- [细分 Agent 如果干不过 Claude Code + 通用 Skill，说明你的产品架构、Agent 理念和核心算法框架可能已经过时] 来源：`topic-agent-cc-plus-skill-benchmark.md`（张和评估自研 Excel AI coding agent 时提出）；置信度 **HIGH**；证据类型：会议原文。
- [做产品评测要有"正确答案"才能判断架构好坏，可以用开源产品（Open Deep Research）做 baseline；干不过通用架构就说明你的架构有问题] 来源：`topic-eval-baseline-open-source.md`（黑客松 demo day 现场点评）；置信度 **HIGH**。
- [MCP 是连接器、Skill 是能力；Skill 是"结构化 Prompt + 文件系统 + 工具调用"的设计模式，不是 Anthropic 专有；只做 skill 形不成壁垒，要往产品/APP 走才能收费（Larry 股票分析 skill 用户用不起来）；可为底座 CC 封装更稳的工具，例如 Excel Master 的 Execute VBA] 来源：`topic-skill-over-mcp.md`；置信度 **HIGH**。

## Viewpoint Core
张和长期、反复主张：做任何细分 AI 产品，第一步不是写代码、不是搭架构，而是先用当下最强的通用方案跑一条 baseline；细分 Agent 的产品价值，必须先证明能跑赢这条 baseline，跑不赢就说明架构过时、没有壁垒，应该重做或放弃。

## Boundaries
- 张和没有评论过 Google 这篇博客本身，也没有提过 Gemini API developer skill、28.2%→96.6% 这些数字。这些只能作为外部事实出现，归到 Google，不能写成"张和早看出来"。
- 张和没说过"skill 会取代细分 Agent"这种话，相反他认为 skill 形不成壁垒、要往产品走；不能把本文写成"通用 skill 赢了，细分产品没戏"。
- "baseline 被抬高"这个具体推论（从裸模型抬到"通用模型+skill"）是本文基于 Google 实验做的延展判断，不是张和原话，要标清楚。

## Depth Gap
张和的 baseline 方法论是 HIGH 置信度的稳定判断，但散在多次课程和答疑里，缺一个 2026 年最新、可量化的外部事件把它重新激活；也缺一张把他几个真实 case 合并起来的"填好的" baseline 对比表。Google 这篇正好补上"通用方案这一年又强了多少"的硬数据。

## Research Questions
1. Google 的 skill 实验具体把成功率从多少拉到多少？baseline（不带 skill）有多低？（用于量化"baseline 被抬高"）
2. 这个提升靠的是什么——skill 内容形态、还是模型推理能力？（决定细分产品该对标"模型+skill"还是只对标 skill）
3. skill 本身有什么已知短板？（用于给细分产品留出真实的差异化空间，不把话说死）

## Research Source Ledger
- [Gemini API developer skill 让 gemini-3.1-pro-preview 的任务成功率从 28.2% 升到 96.6%] 来源：https://developers.googleblog.com/en/closing-the-knowledge-gap-with-agent-skills/ ；原文直接支持；可否写进正文：**YES**。
- [不带 skill 的 baseline 很低：3.0 Pro 和 Flash 均为 6.8%，3.1 Pro 为 28%] 来源：同上；直接支持；**YES**。
- [2.5 系列旧模型也受益，但远不如新模型，说明强推理能力是 skill 见效的前提] 来源：同上；直接支持；**YES**。
- [评测用 117 条 Python/TypeScript 生成 prompt，用到旧 SDK 即判失败；skill 提供 feature set / 现役模型 SDK / 示例代码 / 文档入口（source of truth），配 activate_skill 与 fetch_url 两个工具] 来源：同上；直接支持；**YES**。
- [SDK Usage 类别通过率最低，约 95%] 来源：同上；直接支持；**YES（写成"约 95%"）**。
- [Google 自己提到 Vercel 的工作显示 AGENTS.md 直接指令可能比 skill 更有效；且 skill 没有好的更新机制，过期 skill 可能帮倒忙] 来源：同上 + https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals ；方向直接支持；**YES（写成定性，不编造 Vercel 的具体数字）**。
- 作者与日期：Philipp Schmid、Mark McDonald（Google DeepMind / DevRel），2026-03-25。来源：同上；直接支持；**YES**。

## Allowed Extensions
- 把 Google 的实验结论延展成"细分 Agent 产品要对标的 baseline，已经从裸模型抬高到'通用模型 + 一个轻量 skill'"——这是本文推演，不是张和原话。
- 把张和的几个真实 baseline case（小妖陪伴、AI 相机、Open Deep Research、Excel agent）合并成一张填好的对比表——属于对已有素材的结构化整理，可写。

## Forbidden Moves
- 不把 Google/Vercel 的实验结论写成"张和一直这么测""我早就跑过 Gemini 的 skill"。
- 不把 28%→96% 这类数字写成张和实测得出的。
- 不为了爆点把张和"干不过就重做"的判断写成"细分 Agent 没机会了"。
- 不把 SDK Usage 95% 写成精确小数，不给 Vercel 编数字。

## Decision Before Research
**WRITE-RESEARCH** — 张和观点 HIGH 置信度且有清晰 research questions；外部研究只用于补量化事实和激活时效，核心判断仍从 Viewpoint Core 生长。
