---
title: Agent 跑不完一个入职流程，问题不在模型
theme: cards-claude
cover: assets/adk-stateless-vs-stateful.png
digest: Google ADK 团队披露了一套让 Agent "睡过去再醒过来"的方案——HR onboarding、销售跟进这种横跨几周的流程，靠的不是更强的模型，而是把 idle time 当一等公民。
published: draft
---

# Agent 跑不完一个入职流程，问题不在模型

教你写 Agent 的教程，九成都停在 stateless chatbot——用户发一条、模型回一条、把对话历史 append 进去再全量塞回模型。这套范式我前后帮人 debug 过太多次，问题永远在同一个地方：业务真正想跑的流程从来不是五分钟问答。

HR 入职要两周。发票纠纷一停就是几天。Sales prospecting 一个 sequence 拉满一个月。这些流程的真实节奏里，绝大部分时间 Agent 根本不在干活，是在等——等签字、等审批、等硬件发货、等客户回复。一个 stateless chatbot 撑不过这段 idle time，容器一重启什么都没了。

Google ADK 团队 5 月 12 日在 Developers Blog 上发了一篇长文，标题就叫《Build long-running AI agents that pause, resume, and never lose context with ADK》。作者是 Shubham Saboo 和 Eric Dong——一个是 Senior AI Product Manager，一个是 DevRel Engineer。他们没有讲什么宏大叙事，整篇文章围绕一个 New Hire Onboarding Coordinator Agent 把代码写到了能跑的程度，GitHub repo 也一并放出来了。值得读，因为它把"长程 Agent 到底要解决什么问题、怎么解决"这件事，第一次写到了 PM 和工程师都能落地的颗粒度。

下面把这篇文章里最值得拎出来的几件事讲清楚。

**Stateless agent 在真实工作流上为什么会崩**

ADK 团队没有上来就讲解法，先把问题摆透。这一段对做过 Agent 的人来说几乎是当头一棒——你以为是模型不够聪明，其实是范式根本不对。

- 对话历史会被污染：两周的 onboarding 流程下来，conversation history 里堆满了无关闲聊、过期的 tool output、重复指令，模型开始搞不清自己走到哪一步了
- Token 成本会爆炸：每次推理都把两周的对话回放一遍，"a single onboarding run could generate thousands of turns – most of them no longer relevant to the current decision"
- 推理会出现幻觉：Agent 暂停三天等签字，再回来面对一大坨上下文，"the model frequently hallucinates intermediate steps that never happened"，它会"记得"没人给过的批准、跳过它以为已经完成的步骤
- 解法不是更大的 context window：ADK 团队的原话——"It's a fundamentally different architecture – one where the agent's state is explicit, durable, and decoupled from raw chat history"

把这几点放在一起看，结论很硬：长程 Agent 的瓶颈不是模型能力，是状态的存放方式。对话历史是个 append-only 的累加器，它天然不适合做状态机的真值源。

**HR 入职这个例子为什么选得好**

Agent 演示场景一向有个老毛病，要么太玩具（写个段子讲个笑话），要么太抽象（"客户支持流程"）。ADK 团队选 HR onboarding 是经过算计的。

- 流程明确分六步：发 welcome packet → 等签字 → 拿到签字后 provision IT → 等硬件到货 → 发第一天日程 → 完成
- 每步之间都隔着真实的 idle time，"days pass while the employee signs paperwork"，"days pass while a laptop ships to the employee's home"
- 涉及跨团队 handoff：HR Coordinator 和 IT Provisioning 不是同一个职能，必须 delegate
- 涵盖了几乎所有长程 Agent 共有的特征：human-in-the-loop pause gates、cross-system handoffs、multi-day timelines
- 同样的模式可以直接套到发票纠纷、采购审批、销售跟进、合规审查——ADK 团队明确点了这一长串场景

选这个 demo 的好处是，任何看完文章的 PM 都能立刻把它映射到自己公司的某条业务流程上。这种"我家也有这样的活儿"的代入感，是技术文章能不能传播的关键。

**显式状态机 + durable checkpoint，是长程 Agent 的真正骨架**

文章的核心架构选择，是把 Agent 的状态机从对话历史里剥出来，做成一个显式、可枚举、可持久化的数据结构。这一段是整篇文章最硬核的部分，PM 读到这里应该停下来认真看代码。

- 状态枚举只有 6 个：`START / WELCOME_SENT / DOCUMENTS_SIGNED / IT_PROVISIONED / HARDWARE_DELIVERED / COMPLETED`，少到不可能歧义
- 状态写进 system instruction：用 `{current_step}`、`{new_hire_details}`、`{pending_signals}` 这样的占位符，每次 Agent 醒来由 Python 自动填值，模型看到的永远是最新真值
- 每个 tool 调用都是原子状态更新：`send_welcome_packet` 跑完，`state["current_step"] = OnboardingStep.WELCOME_SENT` 已经落盘
- 持久化只换一行配置：`session_service_uri = "sqlite+aiosqlite:///sessions.db"`，本地 SQLite 和生产 Cloud SQL 用同一套 API，"the API is identical"
- 容器死掉无所谓：Cloud Run 上"containers cold-start, scale to zero during idle periods, and restart unexpectedly"，但只要 state 落了盘，重启后从 checkpoint 接着跑

ADK 团队用了一句话总结这种设计：状态机强制了顺序，所以模型"can't skip a step or hallucinate progress"。这件事很关键——不是靠 prompt 求着模型别跳步，是靠数据结构让它根本没法跳步。文章里还点了一个容易被忽略的细节：模型不需要"读懂"对话历史来理解自己在哪一步，它读的是 system instruction 顶部由 Python 自动填值的几个状态变量。这意味着模型每次推理的认知负担都是恒定的，跟流程已经跑了几天没关系。

这条思路其实跟张和反复强调的"Agent 自由度是产品决策不是技术决策"是一脉相承的。HR onboarding 这种场景天然属于"用户要确定性"的一端，业务方根本不想要 Agent 自由发挥——它只能按这六步走、按这个顺序走、每一步走完都得有 audit trail。ADK 在工程上把这个产品意图变成了一个状态机硬约束，是把"低自由度"的设计意图编进了代码而不是留在 prompt 里。从这个角度看，状态机不只是工程实现，它是一种产品契约——你向业务方承诺的"这个 Agent 会按这六步走、不会乱来"，需要有一个能被审计的数据结构作为兑现凭证，而不是一段可能被模型理解错的自然语言指令。

**Event-driven dormancy：让 Agent 真正"睡过去"**

Idle time 是这篇文章给出的最有创造性的命名。绝大多数 Agent 框架在面对长暂停的时候，要么让线程一直挂着（浪费资源），要么轮询某个外部状态（更浪费），要么干脆把任务停掉等人重启（不可靠）。ADK 的方案是 webhook + state_delta。

- Agent 进入暂停状态是显式的：执行完 `send_welcome_packet` 后 system instruction 里写着"Inform the user you are paused waiting for document signatures. Do not call other tools."
- 外部事件通过 webhook 唤醒：`POST /webhooks/document_signed`，payload 只带 `user_id` 和 `session_id`
- `state_delta` 在 inference 之前原子化应用："applies the state transition before the agent's next inference call"
- 醒来后模型看到的是更新过的 state，不需要回放对话历史，"no replaying of old conversation history, no hallucinated intermediate steps"
- 整个 idle 期间容器可以 scale to zero，"the container can scale to zero during the entire idle time period"，省钱程度不是一个量级

这件事读起来朴素，但它在范式上是个翻转——以前我们把 Agent 当成一个长期运行的线程，现在 ADK 把它当成一个 event handler 的集合。每个事件来了，hydrate session、apply state_delta、跑一次 inference、再睡过去。这跟 serverless 函数对 HTTP 请求的处理逻辑几乎一模一样。差别只在于 handler 内部跑的是一次 LLM 推理而不是一段普通业务代码，但生命周期模型完全可以复用云原生那一套。

放到更大的图景里看，这一步是 Agent 工程范式跟云原生工程范式的合流。过去十年云原生教会我们的事——别让长任务占着进程、用事件驱动、状态外置、容器随时可死——Agent 框架终于也开始这么做了。这也意味着评估一个 Agent 框架成熟度的标准要更新：能不能 scale to zero、能不能水平扩展、能不能跟现有的消息队列和事件总线对接，这些后端工程师习以为常的能力，正在变成 Agent 框架的硬指标。

**Multi-agent delegation：sub-agent 是状态共享的，不是消息传递的**

ADK 处理多 Agent 协同的方式跟很多人想象的不一样。它没有让 sub-agent 之间互发消息，而是让它们共享同一份 state。

- root_agent 是 hr_onboarding_coordinator，挂了三个 tool（send_welcome_packet / check_hardware_delivery / send_day_one_schedule），同时挂了一个 sub_agent: it_agent
- it_agent 用的是同样的 Gemini 3.1 Flash Lite 模型，但 instruction 单独写，工具集只有 `provision_software_accounts` 一个，"focused prompt and a narrow tool set"
- delegate 的触发点写在状态机里：协调员看到 `current_step == DOCUMENTS_SIGNED`，把控制权交给 it_agent
- it_agent 完成后把 state 更新成 `IT_PROVISIONED`，控制权自动回到 coordinator
- 全局状态由 ADK 框架统一管理，每个 sub-agent 都读同一份 `tool_context.state`，不需要 message passing 协议

ADK 团队解释为什么不用单体 prompt：long-running context 下 prompt 已经被 state variable 和 workflow instruction 撑得很满，"degrades reasoning quality"。拆 sub-agent 不是为了好看，是为了让每个推理 step 面对的上下文都小而干净。

这件事跟张和之前讲的"Agent 记忆是当前最大短板"形成了一个有趣的对照。如果 Memory 模块本身就脆弱，那解决办法之一就是别让任何单个 Agent 背太重的上下文——拆成多个、每个只看自己该看的状态切片，反而把脆弱的 memory 变得可管理了。ADK 这套设计不能解决"Agent 不会主动总结记忆"的根本问题，但它通过状态外置和 sub-agent 划分，绕开了"上下文一长模型就糊"的硬伤。

**Golden eval：长程 Agent 怎么做回归测试**

写到这里，文章其实还多讲了一件很多团队会忽略的事——长程 Agent 的测试。你不可能真的等两周看它有没有跳步，所以必须能用秒级的方式模拟"过了 48 小时"这件事。

- 用 ADK 的 eval set，pre-seed session state 直接跳到任意 checkpoint
- 给一个安全门测试：Agent 在 `WELCOME_SENT` 状态下被用户问"能不能跳过签字直接 provision IT 账号"，正确反应是拒绝调用任何 tool，回复"waiting for the employee to sign"
- 给一个恢复测试：state 预设为 `IT_PROVISIONED`，模拟硬件 48 小时延迟后恢复，验证 Agent 仍然记得新员工原始信息、按顺序调用 `check_hardware_delivery` 和 `send_day_one_schedule`
- 评估直接跑在 CLI 上：`adk eval ./app tests/eval/evalsets/idle_time_delay_eval.json --config_file_path tests/eval/eval_config.json`
- 这套 eval 可以塞进 CI/CD，"catching state machine regressions before they reach production"

Golden eval 在 Agent 圈子里被讨论得不多，但它其实是把 Agent 从"demo 阶段"推向"production 阶段"的必要工程。没有这一层，状态机改一下都不知道会不会回归——三周后某个用户撞到 bug，你连复现都做不到。

**PM 可以直接拿走的三个评估问题**

ADK 这篇文章对 PM 群体最大的价值，不是教你怎么用 ADK，而是给了一组评估任意长程 Agent 方案的标准。我把它压成三个问题，下次评估 Agent 选型直接照着问。

- 它能等多久不丢上下文：状态有没有显式 schema、能不能跨周跨月、对话历史是不是真值源（如果是就直接 pass）
- 重启后能不能恢复：session 存哪、本地开发和生产是不是同一套 API、容器死掉后能不能从最近 checkpoint 接着跑
- 多 Agent 协作时状态会不会乱：sub-agent 之间是共享 state 还是消息传递、谁负责全局一致性、有没有可枚举的状态机
- bonus：能不能 scale to zero——idle 期间还在烧机器的 Agent，企业用不起
- bonus：能不能写 golden eval——不能在秒级模拟长程的方案，工程上根本无法运维

这三个加两个 bonus 不是 ADK 独有的能力，它是判断"production-ready 长程 Agent"的通用标准。GPT 升到几代、模型推理能力翻多少倍，都不会让这五个问题变得不重要。

**我的思考：长程 Agent 是 Agent 工程范式的真正分水岭**

读完这篇文章我有一个很强的判断：2026 年 Agent 圈子的下一次分化，不在模型层，在工程范式层。

过去两年大家比的是模型多聪明、工具调用多准、推理链多长。这些都很重要，但它们解决的都是"单次任务做得多好"。ADK 这篇文章其实在告诉行业另一件事——真实企业场景里，"做得多好"的权重在下降，"能不能稳定地跑完"的权重在上升。一个能跑完两周入职流程的 60 分 Agent，比一个推理拉满但活不过容器重启的 95 分 Agent 有用得多。

这件事对 PM 选型的影响是结构性的。以前 PM 看 demo，关注的是"它能不能完成这个任务"。以后 PM 看 demo 应该问"如果中间停 48 小时，它还能不能接着跑、协同的 sub-agent 状态对不对、容器死了一次能不能自动恢复"。这三个问题里只要有一个答不上来，这个方案就跑不进真实业务。

对开发者的影响更直接。长程 Agent 把后端工程师过去十年云原生时代积累的东西——event-driven、stateless service + external state、idempotent operation、scale-to-zero、observability——一次性变成了 Agent 工程的必修课。这意味着 Agent 工程师的能力门槛要补一大块后端工程的硬功，光会写 prompt 已经不够了。

LangChain 几乎同期发的 DeltaChannel 也是这条主线上的——它解决的是同一类问题的另一面（checkpoint 存储怎么不爆），跟 ADK 是互补关系。一个管"状态在业务语义上怎么定义"，一个管"状态在工程实现上怎么省"。两个加起来才是完整的长程 Agent 基础设施。这说明业界的注意力已经在往同一个方向收敛——再过半年看，长程能力大概率会成为 Agent 框架的标配，而不是某家的差异化。

也欢迎大家留言讨论你的看法，特别是如果你在自家业务里已经在跑跨天跨周的 Agent 流程，遇到了什么坑、用了什么解法，都欢迎拎出来聊。

---

*本文织入了 topic-agent-design-principles（自由度作为产品决策）和 topic-agent-memory-weakness（多 Agent 拆分作为对记忆脆弱的工程应对）两个知识库观点。*
