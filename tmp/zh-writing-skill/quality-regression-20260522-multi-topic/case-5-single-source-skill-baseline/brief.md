# Article Brief

## Decision
WRITE

## Route
C-single-source（高在场度档）。Google 这篇官方博客是唯一原始信源，但论证主体是张和的 baseline 方法论；原文只做弹药。

## Benchmark Shape
**高在场度单源解读**为主，混合 **PM 视角技术判断**。匹配理由：原文有可量化实验（28%→96%、117 题、6.8% 低基线），正好转成读者能带走的产品判断工具——一张填好的 baseline 对比表 + 一条"先过 baseline 再谈架构"的决策规则。80 分最低线（单源解读不能没有张和视角、节标题不能改成"原文第一点第二点"）能满足：全文节标题都是张和的机制断言，原文只在第二段和数据处出现。

## Zhang Viewpoint Source
见 Dossier。核心来自 `exp-product-baseline-method.md`（HIGH，先建 baseline 再对比）、`topic-agent-cc-plus-skill-benchmark.md`（HIGH，干不过 CC+Skill 即架构过时）、`topic-eval-baseline-open-source.md`（HIGH，用开源做 baseline）、`topic-skill-over-mcp.md`（HIGH，skill 形不成壁垒要往产品走）。

## Viewpoint Core
做细分 Agent 产品，第一步是用当下最强的通用方案跑 baseline；产品价值必须先证明跑得赢这条 baseline，跑不赢就是架构过时、没有壁垒。Google 的实验把这条 baseline 又抬高了一截。

## Deep Research Plan
外部研究补三件事：Google skill 实验的量化数据（成功率提升、低基线、推理依赖）、skill 的形态（活文档 + SDK 指引 + 文档入口）、skill 的已知短板（更新机制弱、Vercel 的 AGENTS.md 对照）。这些都属于研究延展，归 Google/Vercel，不归张和。张和提供的是判断框架和真实 case，不是这些数字。

## Research Source Ledger
（继承 Dossier 的 Ledger，全部直接支持）
- 28.2%→96.6%（gemini-3.1-pro-preview）；3.0 Pro/Flash 低基线 6.8%、3.1 Pro 28%；2.5 系列受益少→依赖推理；117 题 Python/TS、用旧 SDK 判失败；SDK Usage 约 95%；Vercel AGENTS.md 方向性更优 + skill 更新机制弱。来源：Google Developers Blog（2026-03-25）+ Vercel blog。Vercel 只写定性，不编数字。

## Viewpoint Drift Risk
LOW。最易偏移处：(1) 把"baseline 抬高"写成张和原话——已在 Dossier 标为本文推演；(2) 把 Google 数字写成张和实测——正文严格归因 Google；(3) 把判断写成"细分产品没机会"——用张和"干不过就重做、跑得赢才有壁垒"原意收口。

## Publication Value
- 解决谁的问题：正在做或准备做细分 Agent 产品的 AI PM / 独立开发者 / 团队负责人，在"该不该自研架构、产品壁垒在哪"这个决策时刻，常误判为"做了细分就有壁垒"。
- 为什么现在写：Google 2026-03-25 用硬数据证明通用方案这一年又强了一大截，baseline 的位置变了。
- 张和凭什么讲：自研 Excel AI coding agent、给一期到四点五期学员逐个产品做过 baseline 诊断（小妖陪伴、AI 相机、deep research 自建数据库、Larry 股票 skill）。
- 核心判断有风险：可被反驳（"细分领域有私有数据/工作流，baseline 比不出来"），文中要正面处理。
- 证据能改判断：让读者看到"通用 baseline 已是模型+skill，不是裸模型"这个被忽略的变量。
- 读者能做什么：带走一张填好的 baseline 对比表 + 一条上线前自查规则。
- 普通 LLM 能否复刻：不能。去掉张和的真实 case 和"干不过即过时"判断，文章就垮成 Google 博客翻译。

## Topic
当通用模型 + 一个轻量 skill 就能把任务成功率拉到 96%，细分 Agent 产品要对标的 baseline 已经被抬高；先过 baseline，再谈架构和壁垒。

## Why Now
Google DeepMind 2026-03-25 公布 Gemini API skill 实验：28%→96%。这是"通用方案 baseline 又涨了一截"的最新硬证据。

## Author Right
自研 Excel AI coding agent 并提出"干不过 CC+Skill 即架构过时"；多期训练营里给真实学员产品逐个做过 baseline 诊断。非履历标签，是反复出现的方法论 + 真实 case。

## Core Claim
你的细分 Agent 现在要赢的 baseline，已经不是裸模型，而是"通用模型 + 一个几百行的通用 skill"；过不了这条线，你做的不是产品，是把通用能力包了层壳。

## Evidence Plan
- 原始来源：Google Developers Blog（28%→96%、6.8% 低基线、117 题、SDK Usage 约 95%、推理依赖），Vercel 对照（定性）。
- 一手 case：小妖陪伴产品 Claude 3.5 半天 baseline；AI 相机 10 场景 6-7 达标判据；hackathon 自建数据库 vs Open Deep Research；Excel agent vs CC+Skill；Larry 股票 skill 用户用不起来。
- 填好的样例：一张五行 baseline 对比表（对象 / baseline 用什么 / 怎么搭 / 达标判据 / 张和结论）。

## Case Fact Boundary
- 已给事实：上述 case 的对象、用的模型/方法、张和的判据和结论，均来自 wiki 原文。
- 合理产品判断：把这些 case 抽象成"先过 baseline"的统一规则，可写。
- 不可写：学员当时的情绪、现场原话之外的对话、张和的即时表情反应、具体到"上周/某天"的时间锚点。case 用代表性措辞（"在训练营里给学员做产品诊断时，我反复遇到"），不伪装成某个具体最近事件。

## Primary Case Spine
主案例脊柱 = 张和的 baseline 诊断方法本身，贯穿全文：原始状态（学员/自己想直接搭细分架构）→ 失败证据（不跑 baseline 就不知道差距，自建数据库/纯 skill 跑不赢通用方案）→ 修改动作（先用领先模型+通用方案建 baseline，10 场景看达标比例）→ 结果变化（达标比例、能否跑赢通用架构）→ 产品判断（跑不赢即架构过时、没壁垒）。Google 实验是这条脊柱在 2026 年的外部放大器。

## Reader Takeaway
一条决策规则：动手做细分 Agent 前，先花半天用"领先模型 + 通用 skill"搭 baseline，定 10 个场景的达标判据，跑不赢就别急着写架构；加一张可直接套用的 baseline 对比表。

## Sales Risk
LOW。训练营只在文末一句轻带，正文价值闭环不依赖报名。

## Publishability Estimate
预计 84/100。发表价值、原创判断、专家在场、读者带走都强；唯一风险是单源解读容易滑成 Google 复述，靠"张和 case 当主体 + 填好的表"压住。

## Missing Material
无明显缺口。Google 数据已核到原文，张和 case 已是 HIGH 置信度。

## Next Action
直接写。
