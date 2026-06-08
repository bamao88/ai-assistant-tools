# Article Brief

## Decision
WRITE

## Route
A-firsthand

## Benchmark Shape
业内人士深度复盘（主）+ 反主流单点（辅）。匹配理由：张和有小米自动驾驶重训练集轻评测集踩上亿坑的一手经历，加训练营里反复带学员做 Agent 评测的实战，足以撑起「业内复盘」这种国内竞品普遍缺席的形态；同时文章有一个能被反驳的反主流断言（Agent 评估是 PM 的活、是上限，不是测试岗的活）。80 分最低线要求：有贯穿全文的真实主案例 + 非第一人称证据 + 可被反驳的核心判断——均满足。

## Zhang Viewpoint Source
见 `dossier.md`。张和原观点：评测驱动是 AI 产品落地第一方法论，重要性 5:5；PM 是评测最佳负责人；必须亲自看原始 case 不能看跑分；Agent 评测靠 trace + 两套评测集。来源为 `knowledge_base/client/wiki/expertise/topic-eval-driven.md` 等多个 wiki 页 + observation，置信度 HIGH。

## Viewpoint Core
评测驱动是 AI 产品落地第一方法论，天然是产品经理最该抢的活，必须靠亲自看原始 case 积累——这个立场不能被研究带偏，也不能被稀释成「要重视 eval」。

## Deep Research Plan
只补「Agent 形态下，为什么只看最终输出不够」的定性机制，以及「业界也分端到端 / 单步评测」的佐证。属于研究延展、不能归因给张和的：Anthropic、LangChain 的工程实践描述。研究已完成。

## Research Source Ledger
- [Agent 轨迹 = 完整运行记录（输出 + 工具调用 + 推理 + 中间结果）；只看最终输出会漏掉这些隐藏失败] 来源：Anthropic, "Demystifying evals for AI agents"（https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents）；只支持方向、不支持任何数字 → 正文只写定性机制。
- [Agent 评估分 final response / trajectory / single step 三种粒度，端到端信号最强但定位问题要到单步] 来源：LangChain Docs "Evaluate a complex agent" + Blog "Evaluating Deep Agents"（https://docs.langchain.com/langsmith/evaluate-complex-agent ；https://www.langchain.com/blog/evaluating-deep-agents-our-learnings/）；直接支持「两套评测集」方向、不含数字 → 正文只写定性。
- 正文所有数字（5:5 vs 2:8、标注成本 2~3 倍、困难 case 比例、10 个 case=55 分 / 100 个=80 分、40%/50%→95%、看 200 条日志、上亿坑）**全部来自张和本人原话**，写成「他的判断 / 他的经历」，不是外部研究数字。

## Viewpoint Drift Risk
MEDIUM。最易偏移处：把「评估 = AI PM 上限」写成张和原话（实为本文延展）；把 Anthropic/LangChain 结论混进张和口中。规避：延展断言用「这两年我越来越觉得」「我的判断是」这类本文口吻，外部实践明确写成行业一手资料。

## Publication Value
- 解决谁的问题：想转 / 在做 AI PM、但还把评测当测试岗杂活的人。
- 为什么现在写：2025-2026 大家都在堆 Agent / 多 Agent，链路变长、黑盒变深，评估缺位的代价被放大。
- 张和凭什么讲：小米自动驾驶上亿坑的亲历 + 训练营带学员做 Agent 评测的实战。
- 核心判断是否有风险：有，可被反驳（「评估难道不该测试岗做？」「PM 哪有时间看 case？」）。
- 证据能否改变判断：能，主案例 + 行业实践都可被检验。
- 读者能做什么：明确给出从 trace 到两套评测集、看 200 条 case 的可执行路径。
- 普通 LLM 能否复刻：不能，上亿坑、特斯拉对标、训练营 case 是不可复制一手素材。

## Topic
为什么 Agent 让「评估」从上线前质检升级成 AI PM 的基本功，以及它为什么是 PM 的活。

## Why Now
行业在 2025-2026 普遍上 Agent / 多 Agent，链路变长、工具调用变多、黑盒更深，「只看最终输出对不对」的老测试习惯失效；训练营里学员反复在「成功率上不去又不知道哪崩」上卡壳。

## Author Right
亲历（小米自动驾驶重训练集轻评测集踩上亿坑）+ 训练营真实学员案例（快递下单助手 50%→95%、deep research 多 Agent 项目看 planner/reporter/coordinator）+ 长期判断（评测驱动方法论）。

## Core Claim
在 Agent 时代，一个 AI PM 的水平上限，基本等于他建评测体系的水平——评估不是测试岗交差的质检，而是 PM 理解这个 Agent 到底在哪崩、为什么崩的唯一手段；谁掌握了 Agent 的评估，谁就掌握了这个 Agent。

## Evidence Plan
- 主案例：小米自动驾驶把重心押训练集、踩上亿坑 → 对标特斯拉评测/数据引擎合一。
- 学员案例：快递下单助手默认成功率 40%/50%，评测驱动到 95% 才上线。
- 多 Agent 案例：deep research 项目里，没有竞品对照就不知道该怪 planner 还是 reporter；看够 200 条日志再改 prompt。
- 机制证据（非第一人称）：Anthropic 把轨迹/trace 当 agent 评估起点；LangChain 区分 final response / trajectory / single step。
- 可执行样例：trace → 两套评测集（端到端 + 模块专属）→ 困难 case 比例放大 → 亲自看 100~200 条原始 case。

## Primary Case Spine
小米自动驾驶数据闭环：原始状态——团队把上亿预算和几百人精力压在训练集；失败证据——效果上不去，方向错了；修改动作——对标特斯拉，把评测/数据引擎提到核心、让评测超前于训练；结果变化——评测成为牵引研发的第一动力；产品判断——评测驱动是普通团队做出靠谱 AI 产品的第一方法论，到 Agent 时代更是 PM 躲不掉的基本功。

## Reader Takeaway
读者能带走：①Agent 评估不是测试岗的活，是 PM 该抢的活；②先 trace 再评测，不要一上来改 prompt；③做端到端 + 模块专属两套评测集；④亲自看 100~200 条原始 case，别信跑分；⑤困难 case 比例要放大；⑥评估解决普通团队的问题，但不替你解决「选题太难」。

## Sales Risk
LOW。主体是方法论复盘，训练营只在结尾轻转化，不承接转型焦虑。

## Publishability Estimate
预计 84/100。强项：专家在场（亲历 + 一手案例）、核心判断可反驳、证据密度。风险项：观点漂移（延展断言与张和原话边界）需要在写作时守住，事实可靠性需把所有数字锁死在张和原话、外部研究保持定性。

## Missing Material
无明显缺口。需注意的是「评估 = AI PM 上限」是延展断言，须以本文口吻表达。

## Next Action
直接写。
