# Zhang Viewpoint Dossier

## Topic
细分 Agent 产品（这里是电商客服 Agent）在立项和开发早期，要不要先用通用领先模型把 baseline 跑出来，再决定加知识库、skill、工具和人工兜底。边界收在「产品开发早期的方法判断」，不展开具体客服业务设计，也不做客服行业综述。

## Search Terms Used
baseline / 基线 / 裸跑 / 通用模型 / skill 加 / 先跑 / demo / benchmark / 细分领域 / MVP。检索范围：`knowledge_base/client/wiki/expertise/`、`profile/observations/`。

## Confirmed Zhang Views
- [开发任何 AI 产品一定要先有第一版 baseline，用领先模型把 prompt 调好作为基准；有了 baseline 再和竞品对比，知道 demo 能不能做出来、差距在哪里，再决定是否换技术栈（微调、RAG）] 来源：`knowledge_base/client/wiki/expertise/exp-product-baseline-method.md`；置信度 HIGH；证据类型：课程原文 + 多次会议。
- [验证技术可行性的标准动作是「找 10 个 case，看模型给出满意结果的比例是多少」，比例够高再产品化] 来源：同上（AI 相机案例原话）；置信度 HIGH；证据类型：课程原文。
- [做 AI 产品的正确思维顺序：先探索能不能做出好效果，再研究实现难度和风险；效果出不来，技术问题都不用讨论] 来源：同上；置信度 HIGH；证据类型：课程原文。
- [产品越小，直接对比 AI API 的封装效果就行；不能小产品对标大项目] 来源：同上（黑客松 kickoff）；置信度 HIGH。
- [细分领域比通用工具更有前途，细分领域可以把效果做到更极致] 来源：`knowledge_base/client/profile/observations/obs-2026-05-09-细分领域比通用工具更有前途.md`；置信度 MEDIUM（confidence 0.75）；证据类型：训练营答疑。
- [MVP 要切到极细人群验证核心假设，而不是做全流程] 来源：`knowledge_base/client/wiki/expertise/exp-mvp-fine-grained-validation.md`；置信度 HIGH。

## Viewpoint Core
任何 AI 产品立项，先用最强通用模型跑一版 baseline、固定一组 case 看通过比例，再决定要不要换技术栈；baseline 不是走过场，它是你判断「能不能做、差距在哪、力气该往哪使」的唯一可靠依据。

## Boundaries
- 张和没有用「14→21→24→28」这组具体数字讲过——这组数字来自用户给定的某训练营学员真实案例，必须标成学员案例，不能写成张和自己跑的。
- 张和没有专门讲过电商客服 Agent 这个垂直场景；客服只是承载这套通用方法的载体。
- 张和强调的是「先建 baseline、看增量、再换技术栈」，不能把它写成「不要用 skill / 不要做知识库」这种反工具的绝对结论。
- 「订单状态和优惠券状态混在一起」这条 bad case 的机制解读（模型缺的是同时持有两个系统真实状态的能力，不是语言能力）是本文在张和 Viewpoint Core 上做的合理推演，要写成「这条 case 说明了什么」，不能写成张和早就这么断言过。

## Depth Gap
张和材料给的是方法骨架（先 baseline、看比例、再换技术栈），缺一个贯穿全程、带真实数字的填好案例。用户给定的学员案例正好补上这个 gap：一条 14→21→24→28 的曲线，外加一个最典型的失败 case。这正是 `benchmark-corpus.md` 和 `article-quality-standard.md` 此前判定 rev80 稿停在 70 分时点名要补的素材。

## Research Questions
本轮不需要外部 deep research。素材自足：张和的方法判断（HIGH 置信度）+ 用户给定的一手学员案例（带数字、带 bad case）。唯一要做的是把曲线每一段的「增量含义」讲清楚，而不是引入新的外部实验数字。

## Research Source Ledger
- [通用模型裸跑 30 个退款/物流/优惠券 case，成功 14] 来源：用户本轮给定的训练营学员真实案例；支持程度：直接支持；可否写进正文：YES（标为学员案例）。
- [加结构化知识库说明后成功 21] 来源：同上；直接支持；YES。
- [再加 skill 后成功 24] 来源：同上；直接支持；YES。
- [上线前加订单状态工具、低置信度转人工、退款政策版本校验后成功 28] 来源：同上；直接支持；YES。
- [最典型失败 case：用户同时问订单状态和优惠券限制，模型把两个系统状态混在一起] 来源：同上；直接支持；YES。
- [张和方法论：先 baseline、找 10 个 case 看比例、再换技术栈] 来源：`exp-product-baseline-method.md`；直接支持；YES（作为张和长期判断）。
- 无任何外部第三方实验数字进入正文（不引 Google/Vercel skill 实验的具体数字，避免不可核查）。

## Allowed Extensions
- 把 14→21→24→28 拆成三段增量，并解读「每段增量在告诉你模型缺什么」——这是本文推演，写成「这条曲线说明」。
- 把「订单状态+优惠券」bad case 归因为「状态接入/编排问题，不是模型智力问题」——本文推演，写成对 case 的判断。
- 把张和「先 baseline 再换技术栈」延展到「baseline 的真正用途是把模型能力问题和产品工程问题分开」——延展判断，可由学员曲线支撑。

## Forbidden Moves
- 把学员的 14→28 写成张和自己跑的实验。
- 把数字往上夸张或编造没给的中间值。
- 写成「别做知识库 / 别用 skill」的反工具爆款。
- 引入无法核查的外部实验比例、排名。
- 把方法文写成训练营招生软文。
- 用全角破折号。

## Decision Before Research
WRITE-RESEARCH 的简化形态：张和观点 HIGH 置信度，一手案例由用户直接给定，无需外部研究即可写。直接进入 Article Brief。
