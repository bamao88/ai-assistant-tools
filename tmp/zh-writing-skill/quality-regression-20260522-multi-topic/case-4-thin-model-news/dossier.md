# Zhang Viewpoint Dossier

## Topic
用户原话："OpenAI 刚发了一个新模型，帮我写一篇张和主账号文章。"

边界问题：请求**没有指明是哪个模型**，没有给型号名、发布时间、能力指标、定价、对比基线或任何官方链接。"OpenAI 一个新模型"在 2026-05 这个时间点既可能指某个 GPT 系列、o 系列推理模型，也可能是图像/语音/agent 方向的发布——无法锁定写作对象。

## Search Terms Used
- 在 `knowledge_base/client/wiki/expertise/` 全库 grep：`OpenAI` / `GPT` / `新模型` / `模型发布` / `发布会` / `o[0-9]` / `追热点` / `新闻`（命中 164 文件，多为泛 AI 主题）
- 精读直接相关 3 篇：`exp-hot-topic-strategy.md`、`qa-ai-hotspot-push.md`、`topic-always-prefer-new-in-ai.md`
- 旁证可调用框架（未精读，仅登记可用）：`topic-model-tier-framework.md`、`topic-ai-tech-evaluation-framework.md`、`topic-public-benchmark-limitations.md`、`topic-dev-prod-model-separation.md`、`entity-chatgpt-product-analysis.md`、`topic-domestic-vs-global-model-gap.md`

## Confirmed Zhang Views
- [AI 方向要优先选新模型，不要守旧；新模型通常又好又快又便宜，旧技术的"稳定"在 AI 里反而是劣势] 来源：`topic-always-prefer-new-in-ai.md`；置信度 HIGH；证据类型：课程原文（一期/二期第一课）。
- [蹭热点（如小龙虾）对求职者展示技术先进性、引发面试官兴趣有用] 来源：`exp-hot-topic-strategy.md`；置信度 MEDIUM；证据类型：4.5 期 kickoff 会议。**注意：这是对学员求职策略的建议，不是张和主账号自己要追新闻热点。**
- [信息聚合/热点产品技术含量一般，价值在于"做深 + 产出能获得流量的深度内容"，让产品进入有结果的状态] 来源：`qa-ai-hotspot-push.md`；置信度 MEDIUM；证据类型：训练营 AMA 答疑。
- [评估 AI 新技术有四维框架；公开 benchmark 有局限；模型分层选型（dev/prod 分离）] 来源：`topic-ai-tech-evaluation-framework.md` / `topic-public-benchmark-limitations.md` / `topic-model-tier-framework.md` / `topic-dev-prod-model-separation.md`；置信度 MEDIUM（未在本轮精读，标记为可调用框架）。

## Viewpoint Core
张和对"新模型"的稳定立场是**选型与落地视角**，不是发布会快讯视角：AI 方向永远优先用新模型，但模型好不好要用自己的评估框架和真实场景验证、别只看公开 benchmark，并区分开发态与生产态选型。他从不以"复述某次发布的参数"作为内容形态。

## Boundaries
张和**没有**对"OpenAI 这次这个（未命名）新模型"说过任何具体判断——没有实测、没有 boss_take、没有点评。
不能直接归到张和名下的：这个模型强不强、能不能用、对哪个产品意味着什么、对标谁、定价是否划算。这些都需要先确定是哪个模型 + 真实信息 + 张和（或可核查的产品视角）判断。

## Depth Gap
几乎全空：
- **缺写作对象**：不知道是哪个模型。
- **缺原始事实**：型号、发布时间、能力边界、定价、官方链接、对比基线全无。
- **缺张和对该模型的具体判断**：没有实测、没有点评、没有 boss_take。
- **缺角度**：没有"这篇要回答 PM 的什么问题"。

## Research Questions
在确定模型之前，deep research 无从下手——研究的前提是知道研究哪个对象。一旦补齐型号，才谈得上去查：能力边界、定价、对标模型、官方文档，再用张和的评估/选型框架做 PM 视角解读。

## Research Source Ledger
（空。没有任何外部数字、比例、发布时间被引用，因为尚未确定写作对象，也未做研究。本案不向正文写入任何未核查事实。）

## Allowed Extensions
在补齐"模型名 + 可核查事实 + 张和（或明确的 PM 视角）判断"之后，允许用张和已有的稳定框架（优先选新、评估四维、benchmark 局限、dev/prod 分离、模型分层）去解读这次发布。这些框架可写成"张和一贯的判断方法"，但**对这个具体模型的结论**只能是研究后的本文推演，不能写成张和原话。

## Forbidden Moves
- 编造未命名模型的参数、跑分、定价、发布时间或能力边界。
- 把"OpenAI 又发新模型"写成一篇看似内行实则只复述新闻的快讯。
- 把张和"优先选新"的泛立场，包装成他对这个具体模型的背书。
- 用"张和实测了""张和认为这个模型"等表述——素材里没有任何对应来源。

## Decision Before Research
**SUPPLEMENT-ZHANG-VIEW**（若用户意图只是追新闻发稿，则降为 KILL）。

题材本身（模型发布的 PM 视角解读）在张和账号是可成立的形态，但当前输入连"是哪个模型"都没有，更没有任何可核查事实和张和对该模型的判断。不研究、不起稿，先回到用户补料。
