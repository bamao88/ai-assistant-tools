---
title: Agent 跑不完一个入职流程，问题不在模型
theme: cards-claude
cover: assets/adk-stateless-vs-stateful.png
digest: Google ADK 团队披露了一套让 Agent "睡过去再醒过来"的方案——HR onboarding、销售跟进这种横跨几周的流程，靠的不是更强的模型，而是把 idle time 当一等公民。
published: draft
---

# Agent 跑不完一个入职流程，问题不在模型

HR 入职流程要两周。发票纠纷一停就是几天。销售跟进的一个 sequence 拉满一个月。这些真实企业流程的绝大部分时间，Agent 根本不在干活——是在等签字、等审批、等硬件到货、等客户回复。一个 stateless 的聊天机器人撑不过这段 idle time，容器一冷启动，前面两周的上下文全没了。

Google ADK 团队 5 月 12 日在 Developers Blog 上发了一篇长文，标题就叫《Build long-running AI agents that pause, resume, and never lose context with ADK》。作者是 Shubham Saboo（Senior AI Product Manager）和 Eric Dong（Developer Relations Engineer）。他们没讲什么宏大叙事，整篇文章围绕一个 New Hire Onboarding Coordinator Agent 把代码写到能跑的程度，GitHub repo 一并放了出来。值得读，因为它把"长程 Agent 到底要解决什么问题、怎么解决"第一次写到了 PM 和工程师都能落地的颗粒度。

下面把这篇文章里最值得拎出来的几件事讲清楚。

**Stateless agent 在真实工作流上为什么会崩**

ADK 团队没有上来就讲解法，先把问题摆透。原文用了三个相当狠的词：context pollution、token cost explosion、reasoning hallucination。

- 对话历史会污染：两周 onboarding 跑下来，conversation history 里堆满无关闲聊、过期 tool output、重复指令，模型开始搞不清自己走到哪一步
- Token 成本会爆炸：每次推理都把两周对话回放一遍，原文原话——"a single onboarding run could generate thousands of turns – most of them no longer relevant to the current decision"
- 推理会幻觉：Agent 暂停三天等签字，再回来面对一坨上下文，"the model frequently hallucinates intermediate steps that never happened"——它会"记得"没人给过的批准、跳过它以为已经完成的步骤
- 解法不是更大的 context window，原文原话——"It's a fundamentally different architecture – one where the agent's state is explicit, durable, and decoupled from raw chat history"

把这几点放在一起看，结论很硬：长程 Agent 的瓶颈不是模型能力，是状态的存放方式。对话历史是个 append-only 的累加器，它天然不适合做状态机的真值源。

**HR 入职这个例子为什么选得好**

Agent 演示场景一向有个老毛病——要么太玩具，要么太抽象。ADK 团队挑 HR onboarding 是经过算计的。

- 流程明确分六步：发 welcome packet → 等签字 → provision IT 账号 → 等硬件到货 → 发第一天日程 → 完成
- 每步之间都隔着真实的 idle time，原文原话："days pass while the employee signs paperwork"、"days pass while a laptop ships to the employee's home"
- 涉及跨团队 handoff：HR Coordinator 和 IT Provisioning 不是同一个职能，必须 delegate
- 涵盖了几乎所有长程 Agent 共有的特征：human-in-the-loop pause gates、cross-system handoffs、multi-day timelines
- 同样的模式 ADK 团队直接点名能套到发票纠纷、采购审批、销售跟进、合规审查上

选这个 demo 的好处是，任何看完文章的 PM 都能立刻把它映射到自家公司的某条业务流程上。这种"我家也有这样的活儿"的代入感，是技术文章能不能扩散的关键。

**显式状态机 + durable checkpoint，是长程 Agent 的真正骨架**

文章的核心架构选择，是把 Agent 的状态机从对话历史里剥出来，做成一个显式、可枚举、可持久化的数据结构。这一段是整篇文章最硬核的部分，读到这里建议把代码片段一起看。

- 状态枚举只有 6 个：`START / WELCOME_SENT / DOCUMENTS_SIGNED / IT_PROVISIONED / HARDWARE_DELIVERED / COMPLETED`，少到不可能歧义
- 状态写进 system instruction：用 `{current_step}`、`{new_hire_details}`、`{pending_signals}` 这样的占位符，每次 Agent 醒来由 Python 自动填值，模型看到的永远是最新真值
- 每个 tool 调用都是原子状态更新：`send_welcome_packet` 跑完，`state["current_step"] = OnboardingStep.WELCOME_SENT` 已经落盘
- 持久化只换一行配置：`session_service_uri = "sqlite+aiosqlite:///sessions.db"`，本地 SQLite 和生产 Cloud SQL 用同一套 API，原文原话——"the API is identical"
- 容器死掉无所谓：Cloud Run 上"containers cold-start, scale to zero during idle periods, and restart unexpectedly"，但只要 state 落了盘，重启后从 checkpoint 接着跑
- ADK 团队对这套设计的总结是：状态机强制了顺序，模型"can't skip a step or hallucinate progress"

这条思路跟张和"Agent 自由度是产品决策"的判断对得上——HR onboarding 这种场景业务方就要确定性，ADK 把它直接编进了状态机，没留给 prompt。

**Event-driven dormancy：让 Agent 真正"睡过去"**

Idle time 是这篇文章给出的最有创造性的命名。绝大多数 Agent 框架在面对长暂停时，要么让线程一直挂着浪费资源，要么轮询某个外部状态更浪费，要么干脆停掉等人重启。ADK 的方案是 webhook + state_delta。

- Agent 进入暂停是显式的：跑完 `send_welcome_packet` 后，system instruction 里写着 "Inform the user you are paused waiting for document signatures. Do not call other tools."
- 外部事件通过 webhook 唤醒：`POST /webhooks/document_signed`，payload 只带 `user_id` 和 `session_id`
- `state_delta` 在 inference 之前原子化应用，原文原话——"applies the state transition before the agent's next inference call"
- 醒来后模型看到更新后的 state，不需要回放对话历史，"no replaying of old conversation history, no hallucinated intermediate steps"
- 整个 idle 期间容器可以 scale to zero，原文原话——"the container can scale to zero during the entire idle time period"

这件事范式上是个翻转——Agent 不再是长期运行的线程，而是 event handler 的集合，生命周期跟 serverless 函数几乎一样。

**Multi-agent delegation：sub-agent 是共享状态，不是消息传递**

ADK 处理多 Agent 协同的方式跟很多人的想象不一样——它没让 sub-agent 之间互发消息，而是让它们共享同一份 state。

- root_agent 是 `hr_onboarding_coordinator`，挂三个 tool（`send_welcome_packet` / `check_hardware_delivery` / `send_day_one_schedule`），外加一个 sub_agent: `it_agent`
- `it_agent` 用同样的 Gemini 3.1 Flash Lite 模型，但 instruction 单独写，工具集只有 `provision_software_accounts` 一个，原文原话——"focused prompt and a narrow tool set"
- delegate 触发点写在状态机里：协调员看到 `current_step == DOCUMENTS_SIGNED`，把控制权交给 `it_agent`
- `it_agent` 完成后把 state 更新成 `IT_PROVISIONED`，控制权自动回到 coordinator
- 全局状态由 ADK 框架统一管理，每个 sub-agent 都读同一份 `tool_context.state`，不需要 message passing 协议
- ADK 团队解释为什么不用单体 prompt：long-running context 下 prompt 已经被 state variable 和 workflow instruction 撑得很满，"degrades reasoning quality"

拆 sub-agent 不是为了好看——多 Agent 在 ADK 这里是控制单次推理上下文大小的工程手段，不是 marketing 概念。

**Golden eval：长程 Agent 怎么做回归测试**

文章末尾还多讲了一件很多团队会忽略的事——长程 Agent 的测试。你不可能真等两周看它有没有跳步，所以必须能用秒级模拟"过了 48 小时"这件事。

- 用 ADK eval set，pre-seed session state 直接跳到任意 checkpoint
- 安全门测试：Agent 在 `WELCOME_SENT` 状态下被用户问"能不能跳过签字直接 provision IT 账号"，正确反应是拒绝调用任何 tool，回复 "waiting for the employee to sign"
- 恢复测试：state 预设为 `IT_PROVISIONED`，模拟硬件 48 小时延迟后恢复，验证 Agent 仍然记得新员工原始信息、按顺序调用 `check_hardware_delivery` 和 `send_day_one_schedule`
- 评估直接跑在 CLI 上：`adk eval ./app tests/eval/evalsets/idle_time_delay_eval.json --config_file_path tests/eval/eval_config.json`
- 这套 eval 可以塞进 CI/CD，原文原话——"catching state machine regressions before they reach production"

Golden eval 在 Agent 圈子里讨论得不多，但它是把 Agent 从 demo 推向 production 的必要工程——没有这一层，状态机改一下都不知道会不会回归。

**ADK 团队最后落到 Agent Runtime 上**

文章收尾给了一个完整的部署路径，把前面所有设计都接到了 Google Cloud 的托管服务上。

- 部署目标是 Agent Runtime，AgentEngineApp 把 ADK 应用包成 Vertex 上可托管的形态
- 部署命令是 `agents-cli deploy` 一行
- Agent Runtime 直接提供 session persistence、auto-scaling（包括 idle 期间的 scale-to-zero）、Cloud Trace 集成
- 本地用 SQLite 跑的那一套，到生产换成 managed cloud storage——原文原话："no code changes required"
- 结尾点名了一长串候选场景：invoice disputes、procurement approvals、sales prospecting sequences、compliance audits，"the pattern is the same"

这一节像 Google Cloud 的 sales pitch，但暗含一个判断——长程 Agent 一上生产，底层基础设施的依赖会非常重。

也欢迎大家留言聊聊，你在自家业务里有没有跑过跨天跨周的 Agent 流程，遇到了什么坑、用了什么解法。

（织入了 topic-agent-design-principles 一个知识库观点）
