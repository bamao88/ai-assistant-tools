# Zhang Viewpoint Dossier

## Topic
做 AI 产品评测集时，评测维度的设计。边界收紧到：**自建业务评测集里"该用几个维度、哪些维度"的取舍**，不是公开学术 benchmark 的设计，也不是评测驱动开发的全套方法论。核心要论证的反直觉判断：维度越多，评测越可能给出错误信号，反而拖垮迭代。

## Search Terms Used
- Grep `评测|eval|维度|打分|评估|benchmark`（限定 `knowledge_base/client/wiki/expertise/`）
- 重点读取：`topic-eval-dimension-principles`、`topic-ai-eval-dimensions-core`、`topic-eval-user-thinking-dominant`、`qa-eval-iteration-nature`、`qa-eval-team-management-lessons`、`topic-public-benchmark-limitations`、`exp-feature-eval-dual-dimension`、`topic-eval-driven`

## Confirmed Zhang Views
- [YC Mind 招聘搜索项目，学员提"有用性/正确性/引用正确性"三维度，张和直接否掉："不要三个维度，只要一个：检索正确性"，人工标注 Top5 标准答案，召回了就算成功，生成质量在此阶段不评] 来源：`knowledge_base/client/wiki/expertise/topic-eval-dimension-principles.md`（AMA 0814）；置信度 HIGH；证据类型：会议答疑。
- [背景虚化评测集，分单双人/前后排/伸手不伸手/光线，但**不区分男女老少**，因为性别年龄不影响虚化效果，是"伸手"这个姿态影响——只把真正影响效果的特征提炼进评测集，"通过实测发现哪些特征敏感，就加哪些维度"] 来源：`topic-eval-dimension-principles.md`（二期第六课）；置信度 HIGH；证据类型：理论课。
- ["评测维度要聚焦，不要追求完美主义……先看几个 case 比较常见的问题是什么，然后你再去断定你真正重要的几个维度是什么；不要预设一个完美的大而全的评价体系"] 来源：`topic-eval-driven.md`（shopify 项目答疑 1210）；置信度 HIGH；证据类型：项目答疑。
- ["一旦要求你做打分的科学性、科学量化什么的，十个小组有七个小组就会遇到困难，然后说啊好难评啊，不干了——不干了就亏大了"，体感评测主观排序也行] 来源：`topic-eval-driven.md`（黑客级调研 kickoff 0203）；置信度 HIGH；证据类型：项目答疑。
- [AI 评测维度其实就那些：RAG、Agent、代码、LLM，真实世界跑不了那么多花样，不必方方面面都兼顾] 来源：`topic-ai-eval-dimensions-core.md`（试听课 DAY1）；置信度 HIGH。
- [AI 评测 90% 是用户思维、10% 是技术；"怎么定义更准确、用什么打分"是用户思维不是纯技术] 来源：`topic-eval-user-thinking-dominant.md`；置信度 HIGH。
- [评测集不能穷尽业务场景，是持续进化的，每周加深一点认知] 来源：`qa-eval-iteration-nature.md`；置信度 HIGH。
- [小米自动驾驶把重心放在训练集而非评测集，踩了"上亿元"的大坑后才悟出评测比训练重要；后来 VP 级老板亲自参加评测会、看 case、问"数据集靠不靠谱、评测维度科不科学、相比竞品什么水平"] 来源：`topic-eval-driven.md` + `qa-eval-team-management-lessons.md`；置信度 HIGH；证据类型：本人亲历 + 试听课复述。
- [公开学术评测集方法论可学、数据和结论不可信：数据污染、刷榜、scope 过窄；benchmark 很快饱和失去区分度] 来源：`topic-public-benchmark-limitations.md`；置信度 HIGH。

## Viewpoint Core
张和的一贯立场：**评测集的价值不在维度多，而在每个维度都真正影响模型效果、且能驱动下一步优化决策。** 该用一个维度就别上三个；维度要靠先跑 case、实测哪些特征敏感来定，不能预设一个大而全的评价体系——否则不仅没用，还会让团队测不动、退回凭感觉。

## Boundaries
- 张和没有说过"维度越多越可能错"这句话本身——这是本文对他多条判断的**锐化表述**，必须呈现为本文的论点，不能写成张和原话。
- 张和并不反对多维度本身：功能评估他主张过"产品价值 + 架构复杂度"双维度（`exp-feature-eval-dual-dimension`），质量评估他列过准确性/完整性/可用性/风格多维。所以本文的命题是"无节制堆维度"，不是"维度越少越好"。必须保留这个边界，否则就是把谨慎判断写成绝对断言。
- "上亿元的坑"是张和试听课里的自述措辞，按其原话写"上亿"，不另造更精确数字。

## Depth Gap
现有张和材料其实已经够深（机制 + 两个一手案例 + 本人亲历 + 失败成本），缺的不是外部研究，而是：把散落在多次答疑/课程里的判断**收敛成一条因果链**，并补一个读者能直接照做的判断规则（一个填好的维度取舍样例 + 一句删维度的自检）。

## Research Questions
本篇**不需要外部 deep research**。张和一手材料已覆盖论点、机制、案例、反例边界。不引入任何外部精确数字、比例或实验结论，避免观点偏移和不可核查风险。

## Research Source Ledger
无外部研究条目。全文证据均来自上方 `Confirmed Zhang Views` 的知识库路径（张和本人课程/答疑/亲历），不写入任何需要外部 URL 追溯的精确数字、比例或实验结果。

## Allowed Extensions
- 可以把"维度越多越可能错"作为本文论点提出，但要明确这是本文对张和判断的提炼，并给出可被反驳的边界（多维度在某些成熟阶段是对的）。
- 可以把"7/10 小组放弃"从"打分科学性门槛"的语境，延展为"维度堆叠 → 执行崩溃 → 退回凭感觉"这条机制——这是合理推演，写成本文分析，不写成张和原话。

## Forbidden Moves
- 不把"维度越多越可能错"写成张和的原话或长期口号。
- 不补写 YC Mind 学员当时的情绪、现场对话、张和的即时神态等未提供的细节。
- 不引入外部博主/论文的精确数字来"加强"，避免无法追溯。
- 不把命题推到"评测维度越少越好""不需要多维度"的绝对结论。

## Decision Before Research
WRITE-RESEARCH —— 但研究置零：张和观点 HIGH 置信、且已远超 50% 深度，本篇直接进入 Article Brief 与写作，不做外部研究，不引入外部数字。
