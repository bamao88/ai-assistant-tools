# Article Brief

## Decision
WRITE

## Route
A-firsthand（业内复盘 + 反主流单点）。主体论证由张和自研产品 ExcelMaster 的工程经历 + 他讲过的 Apple Intelligence 失败复盘扛起，外部事件只做触发点和佐证。

## Benchmark Shape
反主流单点（主形态）+ 业内复盘（支撑）。
- 反主流单点：标题本身就是反转——"最难的不是提醒用户，而是判断什么时候不该打扰"，全文围绕一个尖锐判断递进。
- 80 分最低线：要有一个能被反驳的核心断言 + 一组非第一人称也成立的强证据（Apple 复盘 + ExcelMaster 架构）+ 落到可带走的产品判断。可满足：ExcelMaster 的上下文过时 Hook 是张和不可替代的一手工程证据，Apple Intelligence 是行业公认反例。

## Zhang Viewpoint Source
- 自然交互≠对话框（HIGH，`topic-natural-interaction-design.md`）
- Apple Intelligence 失败＝低估场景复杂度、高估小模型理解力（HIGH，`topic-apple-intelligence-failure.md`）
- 影子模式：AI 后台静默判断、不打扰用户也能闭环（HIGH，`topic-shadow-mode-llm.md`）
- 上下文过时检测：行动前用确定性 Hook 检查理解是否还成立（HIGH，张和自研 ExcelMaster，`topic-context-staleness-pattern.md`）

## Viewpoint Core
主动式 AI 真正的工程难点不在"提醒"这个动作，而在"判断此刻该不该打扰"——这是高复杂度的场景判断，正落在模型最不可靠、最被低估的那一格；而一次错误打扰的成本远高于一次漏报。

## Deep Research Plan
- 机制：用张和"低估场景复杂度"框架解释为什么"该不该打扰"难——它要求模型理解用户此刻的状态、注意力、意图，而这正是小模型/端侧最弱的。
- 反例触发点：Apple Intelligence 主动个性化 Siri 延期 + 新闻推送摘要出错（定性，不写精确数字）。
- 解法映射：确定性守门（ExcelMaster Hook）/ 影子模式静默判断 / 自然交互选形态——三条都来自张和已确认观点，不能写成专为主动式 AI 发明。
- 研究延展（不归因张和原话）：错误打扰成本非对称、把"沉默正确率"做成评测维度。

## Research Source Ledger
- Apple Intelligence 24.6 发布、个性化 Siri / 端侧记忆 / 第三方调用全部延期 —— `topic-apple-intelligence-failure.md`，直接支持，可写。
- 苹果新闻推送/通知摘要曾出错、被迫暂停 —— 作者一般性记忆（截止 2026-01），只支持方向不支持精确日期/比例，正文只写定性、不写数字。
- 影子模式静默观察、不需要用户反馈 —— `topic-shadow-mode-llm.md`，直接支持，可写。
- ExcelMaster 上下文过时 → 用 Hook 强制行动前检查 —— `topic-context-staleness-pattern.md`，直接支持（张和一手产品），可写。

## Viewpoint Drift Risk
MEDIUM。最可能偏移的点：(1) 把"主动式 AI 难在克制"写成张和长期原话——避免，写成此刻由几个案例推出的判断；(2) 把影子模式说成天生为主动式 AI 设计——避免，写明是借用闭环思路；(3) Apple 推送事件夸大成精确数据——避免，保持定性。

## Publication Value
1. 解决谁的问题：做主动式 AI / Agent / 助理类产品的 PM 和创业者，他们普遍把功夫花在"提醒得准不准"，忽略"不该提醒时沉不沉得住"。
2. 为什么现在写：主动式 AI（手机助理、桌面 Agent、各种"主动推送"功能）正密集上线，Apple Intelligence 的翻车是现成的行业教训。
3. 张和凭什么讲：做过手机 OS 级 AI，自研 ExcelMaster 亲手处理过"AI 基于过时理解擅自行动"的工程问题，课上系统复盘过 Apple Intelligence。
4. 核心判断是否有风险：有——"错误打扰比漏报更贵""难点在克制不在提醒"都可被反驳，是真判断不是安全句。
5. 证据能否改判断：能——ExcelMaster Hook、Apple 复盘、影子模式都是可检验的工程事实。
6. 读者能做什么：评估主动式 AI 时多看一个维度（不该打扰时它沉得住吗），并用确定性守门 + 影子静默判断两条具体设计动作。
7. 普通 LLM 能否复刻：不能——主线判断 + ExcelMaster 一手工程证据 + 张和的 Apple 复盘是不可替代组合。

## Topic
主动式 AI 产品的核心难点：不是"会不会、准不准地提醒"，而是"判断此刻该不该打扰用户"。边界收在这一个决策点。

## Why Now
主动式助理/Agent 密集上线；Apple Intelligence 的主动个性化承诺集体延期、推送摘要翻车，是行业刚发生、读者有共鸣的反例。

## Author Right
张和做过手机 OS 级 AI；自研 ExcelMaster 亲历"AI 基于过时上下文擅自行动"的真实工程问题并给出 Hook 解法；课上系统复盘过 Apple Intelligence 失败。

## Core Claim
主动式 AI 最难的不是提醒，而是判断"此刻不该打扰"——这是个被严重低估的高复杂度场景判断，而错误打扰的代价远高于漏报；谁把精力全压在"提醒得准"上，谁就押错了优化目标。

## Evidence Plan
- 一手工程证据：ExcelMaster 上下文过时 → AI 基于旧表格结构继续生成代码 → 用 Hook 强制行动前检查（张和自研产品）。
- 行业反例：Apple Intelligence 主动个性化延期 + 推送摘要出错（定性）。
- 机制框架：张和"低估场景复杂度、高估小模型理解力"。
- 解法证据：影子模式静默判断、自然交互按场景选形态。

## Case Fact Boundary
ExcelMaster 案例只用已确认事实（上下文过时问题 + Hook 解法 + "传统代码监管不确定 AI"的定性），不补写演示当天的对话、用户反应或现场情绪。Apple 事件保持定性，不写"某用户投诉""某天"。不使用"上周一个学员"这类无来源时间锚点。

## Primary Case Spine
主案例脊柱 = ExcelMaster 上下文过时问题：
- 原始状态：Agent 基于初次解析的表格结构生成 VBA 代码。
- 失败证据：用户执行后表格已变，Agent 不知道，继续基于旧结构生成 → 出错。
- 修改动作：用 Hook 在每次行动前强制调用确定性代码检查上下文是否过时，过时则刷新。
- 结果变化：把"AI 自顾自行动"变成"行动前先确认现状还成立"。
- 产品判断：主动式 AI 的每一次"主动"都是同一个赌注——赌"我现在对用户处境的理解还成立"；难的是这个判断，不是动作。

## Reader Takeaway
评估和设计主动式 AI，别只盯"提醒准不准"，要盯"不该打扰时它沉不沉得住"；具体两招：行动前加确定性守门、让 AI 先在后台静默判断攒 bad case 再决定开不开口。

## Sales Risk
LOW。全程是产品/工程判断，不靠训练营承接，文末不引流。

## Publishability Estimate
预计 84/100。发表价值高、原创判断清楚可反驳、有张和一手工程证据 + 公认反例、专家在场强、读者带走具体、转化克制。主要风险在观点对齐（防止把推演写成原话），已在 Drift Risk 标注。

## Missing Material
无明显缺口。Apple 推送事件保持定性即可，不需要补精确数据。

## Next Action
直接写。
