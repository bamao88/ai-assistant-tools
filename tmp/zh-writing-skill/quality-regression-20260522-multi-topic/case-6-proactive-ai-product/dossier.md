# Zhang Viewpoint Dossier

## Topic
主动式 AI 产品（proactive AI：会主动提醒、主动推送、主动行动的 AI 形态）的真正工程难点。
边界收在"判断此刻该不该打扰用户"这一个决策点上，不展开主动式 AI 的全部产品形态，也不写"主动 vs 被动哪个更好"的泛论。

## Search Terms Used
主动 / 打扰 / 提醒 / 通知 / 打断 / interrupt / proactive / 时机 / 该不该 / 自然交互 / 影子模式 / 上下文过时 / Apple Intelligence

## Confirmed Zhang Views
- [自然交互不等于对话框——最自然的 AI UI 是按场景选最优交互方式，可能是对话、GUI 嵌入、下拉菜单] 来源：`knowledge_base/client/wiki/expertise/topic-natural-interaction-design.md`（一期第四课原文）；置信度 HIGH；证据类型：课程原文。
- [苹果 Apple Intelligence 的失败核心是"低估了场景的复杂度，高估了 3B 模型对世界的抽象理解力和任务调用能力"；主动个性化 Siri 的承诺至今未兑现] 来源：`knowledge_base/client/wiki/expertise/topic-apple-intelligence-failure.md`（二期第五课原文）；置信度 HIGH；证据类型：课程原文 + 直接引语。
- [影子模式：AI 可以在后台静默运行、不打扰用户、不需要用户主动反馈，靠影子模型与生产模型的差异自动挖掘 bad case] 来源：`knowledge_base/client/wiki/expertise/topic-shadow-mode-llm.md`（一期第六课 + 二期第七课原文）；置信度 HIGH；证据类型：课程原文 + 直接引语。
- [上下文过时检测：Agent 行动前必须用确定性 Hook 检查"我对现状的理解是否还成立"，否则会基于已被改变的旧上下文继续行动而出错——这是他自研产品 ExcelMaster 的真实架构痛点和解法] 来源：`knowledge_base/client/wiki/expertise/topic-context-staleness-pattern.md`（ExcelMaster Agent 升级会议）；置信度 HIGH；证据类型：张和自研产品演示 + 直接引语。
- [Hook 的本质是"用确定性的传统软件，去监管不确定的 AI"] 来源：同上 ExcelMaster 升级会议摘要；置信度 HIGH。
- [评测驱动：必须让评测集超前于训练集，先把问题暴露清楚，再优化；数据闭环关键不是采集而是评测驱动] 来源：`topic-shadow-mode-llm.md`；置信度 HIGH。

## Viewpoint Core
张和反复讲两件事：一是 AI 产品最容易翻车的地方是"高估了模型对真实场景复杂度的理解力"（Apple Intelligence 的死因）；二是好的 AI 交互不是默认弹对话框，而是按场景选最克制、最合适的形态，必要时用确定性代码守门、让 AI 先在后台静默判断。把这两条接到"主动式 AI"上：主动式 AI 真正难的不是"会不会提醒"，而是"判断此刻该不该打扰"——这是一个高复杂度的场景判断，正好落在模型最不可靠、最被低估的那一格。

## Boundaries
- 张和没有用过"主动式 AI 最难的是克制"这句话，也没专门写过 proactive AI 这个品类。"主动式 AI 难在克制判断"这句核心论点是**本文从他已确认观点推演出来的判断**，必须以他的思考方式写出，不能写成"我一直认为主动式 AI……"这种像是他长期挂在嘴边的原话。
- 张和没说过 Apple 新闻推送摘要出错的具体事件细节；这部分作为外部佐证，按 Ledger 处理，且保持定性、不写精确日期与数字。
- 张和没有给出"沉默正确率"这个具体评测指标的命名；这是本文把他的"评测驱动"方法论延伸到主动式 AI 上的产物，写成本文提出的判断，不归因为他原话。

## Depth Gap
现有张和材料分散在四个 topic 页里，缺一条把它们串成"主动式 AI = 克制判断"的主线；缺一个外部公认的反例事件做触发点（Apple Intelligence 主动推送翻车是最现成的）；缺对"为什么错误打扰比漏报更贵"这条非对称性的明确论证。

## Research Questions
1. Apple Intelligence 主动推送/通知摘要翻车，公开报道里能确认到什么程度（保持定性）？
2. "错误打扰 vs 漏报"的成本非对称，能不能用张和已有的"低估场景复杂度"框架解释清楚？
3. 张和的三个解法（确定性守门 / 影子模式 / 自然交互选形态）能不能直接映射成主动式 AI 的设计动作？

## Research Source Ledger
- [苹果 24 年 6 月发布 Apple Intelligence，端侧 semantic index 记忆、个性化 Siri、第三方应用被 Siri 操作全部延期] 来源：`topic-apple-intelligence-failure.md`；原文支持程度：直接支持；可否写进正文：YES。
- [苹果的新闻推送/通知摘要功能曾因生成错误摘要而被报道、最后不得不暂停该功能] 来源：作者对公开报道的一般性记忆（知识截止 2026-01），非本库素材；原文支持程度：只支持方向不支持精确日期/数字；可否写进正文：DOWNGRADE（只写定性"把新闻推送摘要写错、闹到要把功能先关掉"，不写具体时间、不写比例）。
- [特斯拉影子模式 2-3 周完成一次完整数据闭环迭代] 来源：`topic-shadow-mode-llm.md`；原文支持程度：直接支持；可否写进正文：YES（但本文只借"静默观察"思路，不强调这个数字）。

## Allowed Extensions
- "主动式 AI 最难的是判断什么时候不该打扰" —— 由 Apple 失败（低估场景复杂度）+ 自然交互按场景选形态推演，写成本文/张和此刻的判断，不写成他长期原话。
- "错误打扰的成本远高于漏报" —— 由 Apple 推送翻车 + 信任一次性损耗推演，写成本文判断。
- "把'该不该打扰'做成一个评测维度（沉默正确率）" —— 由张和评测驱动方法论延伸，写成本文提出的操作建议。

## Forbidden Moves
- 不把 Apple 新闻摘要事件写成精确日期、百分比或具体投诉方。
- 不把 ExcelMaster 的上下文过时案例补写成现场对话、用户情绪或没发生的演示细节。
- 不把"主动式 AI 难在克制"伪装成张和早就反复讲过的原话。
- 不把影子模式从"数据闭环采集"偷换成"它本来就是为主动式 AI 设计的"——要写明这是借用思路。

## Decision Before Research
WRITE-RESEARCH —— 张和观点 HIGH（四个 topic 页直接支撑），主线判断是合法推演，只需少量外部佐证保持定性。可进入 Article Brief。
