# 新媒体运营 Skill 跨项目复用审计

审计日期：2026-10-23。本文记录当前源码的实际发现、判断依据和迁移影响，不是第二份架构、命名规则或目标入口清单。职责以 [统一架构](../media-operations-architecture.md) 为准，固定字段以 [合同](../media-operations-contract.md) 为准，实施顺序以 [迁移计划](media-operations-restructure.md) 为准。本文使用当前源码名称定位证据，不代表最终名称。

## 范围与证据层级

- 本次分工深审覆盖 38 个运营核心入口的正文、相关 references 及影响职责判断的关键实现；各组读取深度随实际耦合点而定，不表示逐行审阅所有文件或测试所有脚本。
- 另对 `~/.agents/skills` 与 `~/.codex/skills` 的 98 个 realpath 去重入口做名称、描述、来源等 metadata 筛查，再按相关性阅读 `product-idea-management`、`image-prompt-reverse`、`mimi-tv-cover-art`、`mimi-tv-naive-illustration` 等邻接能力。**98 个入口没有全部进行正文和实现深审。**
- 未将 Claude 独有安装列入迁移范围。系统与插件 Skill 是外部能力依赖，不复制进自有源码目录。
- 结论来自静态职责、调用关系和数据合同审计。本轮没有执行资料入库、客户写回、采数、生成作品、账号认证或平台动作，也没有完成跨项目真实业务回放。

## 核心判断

“通用／项目专属”应在每个业务职责中分别判定，不能仅按 Skill 所在目录或名称决定。当前同时存在两个方向的错位：通用工艺被锁在项目入口里，项目身份和策略又进入了标记为通用的工作流。

仅把源码搬进 `tools`，或者把绝对路径改成一个 root 参数，不等于完成通用化。一次可复用任务至少要明确输入、核心方法、质量标准、返回产物和回写责任；实际存储格式、执行器和项目事实通过适配衔接。项目消费别人的授权资料，与项目复用共同方法也应分别描述。

本轮修订前按现有入口归并的门面表不足以证明可复用性：ZH 专题研究和 WXP 知识卡片包含完整公共工艺，知识与客户领域也有共享方法。需要先分解职责，再决定哪些保留独立公共入口、哪些成为按需方法、哪些只是项目配置。不能为了入口数量或项目对称新增空 Skill。

## 38 个核心入口的责任审计覆盖

下表只记录当前能力中共享与项目差异的落点，不规定新名称或要求每行注册一个 Skill。

| 责任组／数量 | 本组全部当前入口 | 可复用内容 | 项目、平台或存储差异 |
|---|---|---|---|
| 项目初始化／1 | `self-media-init` | 盘点、定位假设、最小资产关系、能力接入、首轮验证 | 真实账号、品牌、目标、事实源与已有目录；初始化模板应引用共享对象合同 |
| 研究与洞察／3 | `content-creator-research`、`product-deep-research`、`assistant_zh_deep-research` | 来源身份、证据、主张验证及报告方法；账号、产品、专题各自的独立研究交付 | 研究对象、目标读者、当前问题和输出路由；ZH 专题研究主体不应继续作为专属工艺 |
| 选题／4 | `content-topic-planning`、`assistant_zh_topic-mine`、`assistant_zh_topic-select`、`assistant_zh_topic-review` | 来源信号、增量候选、价值／可信度／准备度判断、比较、选题与标题分离 | 人设与目标权重、候选池和知识输入、正式内容登记权限、现有程序接线 |
| 知识／5 | `assistant_zh_knowledge-ingest`、`assistant_zh_knowledge-triage`、`assistant_zh_knowledge-query-read`、`assistant_zh_knowledge-query-owner`、`assistant_zh_knowledge-query` | 有来源的检索、抽取、合并／新建／跳过、矛盾演进、综合沉淀、索引日志一致性 | wiki schema／存储 adapter、client／market 分类、profile 保护及裁决权限；旧兼容别名不构成独立能力 |
| 生命周期、记录与复盘／6 | `content-production-prep`、`content-operations-ledger`、`assistant_zh_publication-record`、`assistant_zh_metrics-record`、`assistant_zh_content-review`、`MiMi_TV_Operations_content-management` | 作品与来源、版本依赖、渠道发布、排期、指标快照、分析及改进动作闭环 | 项目原账和字段映射、发布目标、窗口配置、成功标准、真实状态及已认可基准 |
| 来源处理／2 | `platform-fetch`、`video-content` | 素材复用、来源与实读范围、采集／转录／字幕／帧与解析结果 | 平台、会议和音视频 adapter、当前会话、访问权限及项目输出路由 |
| 文章与口播文字／3 | `source-longform-writing`、`article-expression-polish`、`assistant_wxp_self_spoken-script-style` | 来源型成文、润色、事实保持，以及口播可说性和读稿检查 | 文章／口播的载体差异；WXP 人物经验、措辞偏好和已确认表达不成为所有账号默认 |
| 配图、图解与封面／4 | `content-visual-assets`、`diagram-design`、`assistant_zh_video-cover`、`assistant_wxp_self_xhs-cover` | 真实素材、视觉层级、裁切、可读性、批量选图、生成／编辑／渲染与验收方法 | 人物身份原图、品牌 kit、字体配色、尺寸及平台导出；项目视觉标准不应复制成另一套通用执行器 |
| 卡片／2 | `markdown-to-cards`、`assistant_wxp_self_knowledge-cards` | 已有稿件排版渲染与完整知识解释卡片工艺分别复用；不能互相降级 | 账号人物、画风样例、品牌及写回位置；分页方法冲突须先裁决 |
| 视频与项目整包制作／2 | `video-clip`、`MiMi_TV_Operations_content-package` | 通用视频处理、素材查重、媒体实测、可携带审阅包与版本证据 | MiMi 选材与使用决定、A16／文案／CTA 等制作基准、特定项目 item schema；ZH 视频 preset 只按明确项目选择 |
| 平台物料与改写／2 | `content-package-create`、`assistant_zh_platform-adapt` | 单项／整包字段制作、目标平台版本改写、事实与角色保持、公共平台规格 | persona、账号身份、项目关键词与语气；公共改写方法不能只能从 ZH 入口取得 |
| 平台执行／3 | `Agent-Publish`、`xhs-auth`、`xhs-interact` | 身份核验、停止点、回执、草稿／提交／互动的执行合同 | 平台与执行环境 adapter、授权账号和会话；项目人设不能默认注入执行器 |
| 客户／1 | `customer-management` | 人员候选检索、身份确认、增量资料、证据匹配、订正及读写分离 | ZH 学员／就业／线索业务、具体任务卡、总表与字段写回范围；先共享方法，不承诺现引擎已是通用 CRM |

合计 38 个当前入口。核心入口和邻接能力的处理优先级取决于任务及复用证据，不以本表行数作为目标入口数。

## 关键发现与迁移影响

### 1. 专题研究与完整知识卡片工艺应从项目归属中分离

证据：

- [ZH 研究主流程](../../skills/assistant_zh_deep-research/SKILL.md) 的问题界定、检索、交叉核验、提纲、综合、批评与报告流程，以及 [methodology](../../skills/assistant_zh_deep-research/reference/methodology.md)，没有依赖 ZH 人设才能成立的业务语义。项目耦合集中在输出路由、规则包装和写作关联。
- [citation_manager.py](../../skills/assistant_zh_deep-research/scripts/citation_manager.py) 的来源规范化和稳定 ID、[evidence_store.py](../../skills/assistant_zh_deep-research/scripts/evidence_store.py) 的证据记录已经接受独立目录参数；不需要复制每个项目的同类程序。
- [WXP 知识卡片](../../skills/assistant_wxp_self_knowledge-cards/SKILL.md) 第 2–6 节包含分析、连续稿、解释单元、分页、逐页图文构想、提示词、生成和整组检查。其第 1 节也明确其他目录可按指定位置保存。完整工艺并非仅能处理 WXP 材料；项目绑定主要是人物、样例偏好、ID 与选定版本回写。

影响：两者都具有明确独立交付，应公共化工艺并注入项目资料。知识卡片保留完整自洽流程，不拆成必须由用户手动串联的零散工具，也不能直接并入 Markdown 渲染。来源署名、第三方许可和真实已认可能力随迁移保留。

旧研究方法的固定来源数、每个主张多来源数量、分钟倒计时、固定章节长度，与当前公共研究按问题与证据缺口判断的做法存在冲突。不能把“原项目里存在”当作升级为全局要求的依据。

### 2. 口播、封面与平台改写混合了公共方法和项目身份

证据：

- [WXP 口播](../../skills/assistant_wxp_self_spoken-script-style/SKILL.md) 的事实锁定、可说性、读稿检查、删空转与不虚构经历可复用；个人措辞及示例属于人物风格资料。
- [WXP 封面](../../skills/assistant_wxp_self_xhs-cover/SKILL.md) 的原始身份参考、局部编辑、源图与上传图、实际视觉检查可复用；黑粉色、人物特征、构图比例和资源 CTA 是项目 kit 或已选模式。
- [ZH 封面](../../skills/assistant_zh_video-cover/SKILL.md) 的批量底图、裁切、标题渲染和重复检查可复用；本人身份、evc 视觉及底图库属于项目 kit。
- [ZH 平台改写](../../skills/assistant_zh_platform-adapt/SKILL.md) 的源稿→目标平台版本、改写与发布分离、身份一致性和独立自检可复用；`zh_main`／`zh_assistant` 定位、账号和输出字段映射属于项目差异。

影响：公共工艺读取显式风格、身份和目标平台信息；项目入口只加载 kit／persona／路径和确有不同的编排。角色特征不因工艺复用而跨账号传播，封面与口播风格也不扩张为所有文章、正文的统一风格。

分页存在具体方法冲突：[ZH 平台改写](../../skills/assistant_zh_platform-adapt/SKILL.md) 写“一页一个意思”，[WXP 卡片](../../skills/assistant_wxp_self_knowledge-cards/SKILL.md) 以解释单元组织，允许一个问题跨页、同页并置多个事实。迁移前应判断前者是特定卡型策略还是失效概括；不能将两条互相冲突的命令并列变成通用规则。开头固定秒数、钩子优先等也要区分平台事实、表达策略与项目选择。

### 3. 通用包反向携带项目默认，构成跨账号污染入口

证据：

- [body_video.md:17](../../skills/platform-publish/assets/prompts/body_video.md#L17) 直接让模型扮演 ZH 本人，后续还有该人物经历、口头禅、业务战略与语气。它位于通用发布包内部，却承担创作身份。
- [platform_rules.yaml](../../skills/platform-publish/assets/platform_rules.yaml) 混合平台规格、项目账号列表和项目封面工具选择；真实账号引擎参数虽另有事实源，项目账号映射仍不应成为通用平台规格。
- video-clip 的 [质量门](../../skills/video-clip/references/quality-gates.md) 将 `zh_business` 白板样式列为默认锁定基准，[工作流](../../skills/video-clip/references/workflows.md) 含 `--profile zh_main` 示例，须核对默认选择与引擎调用的真实传播范围。
- [markdown-to-cards](../../skills/markdown-to-cards/SKILL.md) 的默认规则直接列出 ZH 专业号及其账号风格配置。

影响：项目人物、策略、账号到制作 preset 的选择回迁项目；通用层保留参数、接口、公共规格和无项目默认的任务方法。迁移不能只检查项目目录向外抽取，也必须检查公共提示词、模板、引擎默认和生成物是否还携带原账号身份。本文仅指出错位，未修改这些文件。

### 4. 内容管理已有共享基础，MiMi 的可复用经验仍须继续提取

证据：

- [通用台账](../../skills/content-operations-ledger/SKILL.md)、[data-contract](../../skills/content-operations-ledger/references/data-contract.md) 和 [复盘方法](../../skills/content-operations-ledger/references/content-review.md) 已包含发布事实、窗口、官方原表、缺失、动作采用与效果复查。
- [MiMi 制作](../../skills/MiMi_TV_Operations_content-package/SKILL.md) 的跨已发、定时、在制与本批查重，以及 [content_package.py](../../skills/MiMi_TV_Operations_content-package/scripts/content_package.py) 的来源身份、哈希、probe、审阅页和 ZIP，在项目 schema 外仍有可复用方法与程序部分。
- [MiMi 采数经验](../../skills/MiMi_TV_Operations_content-management/references/data-collection.md) 记录下载事件超时但文件落盘、同名 CSV 的作品关联、B站范围合计／逐日、小红书原表 0 与统计未就绪的区别。这些问题不是猫猫电视机独有。

影响：查重核心、媒体检查和包交付方法应支持注入项目字段适配。采数的稳定经验进入公共平台采集与数据合同；项目保留历史事故证据、当前账号与已认可策略。真实后台界面是时变事实，不能把某次页面结构或下载表现冻结成永远有效的跨平台规则。

同时，[初始化数据合同](../../skills/self-media-init/references/data-contract.md)、台账数据合同和 [制作准备](../../skills/content-production-prep/SKILL.md) 重复定义对象、状态与文案唯一源。比如制作准备把 `publish_<account>.md` 写成唯一源，而 MiMi 使用 `item.copy`。共享合同应固定对象语义与关系，项目存储适配指定原文件和字段；初始化模板只提供实现之一，不能另立第二个强制 schema。

### 5. 选题应复用判断与增量机制，项目保留价值取舍和程序接线

证据：

- [通用选题方法](../../skills/content-topic-planning/references/ideation-framework.md) 已区分受众价值、自身贡献、内容支撑和准备度，并支持不同内容目的。
- [ZH 选择](../../skills/assistant_zh_topic-select/SKILL.md) 与 [评审](../../skills/assistant_zh_topic-review/SKILL.md) 同样维护候选／标题分离、先内容价值后包装、第一手性、展开空间、不编评分等公共判断；其中人物经验、账号口吻和决策次序是项目输入。
- ZH 实际 `content/candidate_discover.py` 的 `_load_prompt_context()` 读取固定 profile，输入与 frontmatter 直接包含 `client`，输出绑定共享候选池。其来源去重和增量发现可共享，当前 CLI 还不是换 root 就能服务任何项目的通用接口。

影响：内容管理内部的选题方法只维护一份；项目提供来源集合、定位、优先级、候选 schema 和正式登记钩子。用户查看已有推荐不应被合并入口自动改为刷新候选或创建正式作品。程序耦合需要真实 adapter 和跨项目回放验证，不能只在说明写“遵循当前项目”。

### 6. 知识管理需要分开领域方法、wiki 实现和项目权限

证据：

- [只读检索](../../skills/assistant_zh_knowledge-query-read/SKILL.md) 和 [owner 检索](../../skills/assistant_zh_knowledge-query-owner/SKILL.md) 重复维护 index→候选全文→综合引用的方法；主要差别是沉淀权限和写回合同。
- [triage](../../skills/assistant_zh_knowledge-triage/SKILL.md) 混合公共 merge／new／skip 与矛盾演进、具体 pending schema、ZH profile 人工保护和提升策略。
- 实际 `workflow/knowledge_ingest/schema.py` 的观点、实体、经验、对比、问答、综合页类型是一种可复用 wiki 实现，但 `cohort` 和课程／辅导场景具有业务差异，不能要求其他项目照搬。
- 存储路径已漂移：当前检索 Skill 仍写 `knowledge_base/market/wiki`，实际 `workflow/knowledge_ingest/core.py` 的 `_market_base` 返回项目顶层 `market/`。复制旧路径会继续传播错误。

影响：公共方法接收知识空间和来源合同；wiki 文件格式、索引、日志及 pending 由存储 adapter 处理；项目保留分类、人物观点范围、profile 保护和明确写入权限。普通查询、入库、裁决、综合沉淀仍是不同请求模式。其他项目可复用方法并绑定自己的知识空间；授权读取 ZH 知识库只是一种数据消费，不代表已经完成跨项目能力复用。路径漂移本轮尚未修复。

### 7. 客户能力具有可共享内核，但尚不能宣称通用 CRM 已成立

证据：

- [客户入口](../../skills/customer-management/SKILL.md) 已按 acquire／recognize／analyze／resolve 和任务卡组织，输入、分析与写回存在可分离内核。
- [人员匹配](../../skills/customer-management/references/person-matching.md) 含规范化、多个身份字段、候选与回查逻辑；但“任一线索命中即同一人”与后文“姓名子串只是候选”的表述不一致。
- [数据模型](../../skills/customer-management/references/data-model.md) 的微信数据湖、飞书总表、特定 7 字段回写及就业任务是当前项目业务；实际 `engines/customer-management/config.py` 仍默认 ZH 数据根，并派生特定学员和聊天路径。

影响：可提取来源与读写合同、候选检索、身份确认、增量订正和可追溯回执。候选检索与身份确认必须分开，弱姓名匹配不能自动成为并人依据。任务卡、期次／就业／线索定义和表字段属于项目。当前只有一套完整客户业务；先有共享模块及明确 adapter，另一个真实业务接入后再判断是否需要独立公共入口，不因名称对称造一个无法兑现的通用 CRM。

### 8. 邻接能力通过依赖和交接复用，不扩大成无边界运营包

metadata 筛查后的重点阅读显示：

- `product-idea-management` 管理独立产品灵感资产；只有明确转成内容时才交给选题。复用研究和素材不意味着合并两套业务主库。
- `image-prompt-reverse` 是参考图分析及提示词能力，可以作为视觉工艺依赖；人物身份、授权和品牌仍来自当前项目。
- `mimi-tv-cover-art` 负责 App 内供主人选节目的节目／频道封面，`mimi-tv-naive-illustration` 负责节目画风与运行素材；它们与社交内容封面交付不同，不并入社媒项目制作。构图、参考图分析、生成和视觉检查方法可按需共用，但节目身份、产品资产路径与验收归 App 项目。
- 文档、表格、PDF、演示、图像生成、设计及其他系统／插件能力提供文件或工具执行，不因此变成自有运营方法源码。调用依赖时读取其当前真实说明，保留供应方维护边界。

影响：运营体系应能调用邻接能力并接回产物，不把产品灵感、App 运行节目或第三方工具整包搬入运营领域；也不能因为它们不属于核心清单而忽略其中可复用的依赖。

## 对实施的直接约束与剩余验证

本审计提供的迁移输入是逐段的职责判定：能独立完成的公共专业任务、由多个任务读取的共享方法、平台／存储／执行 adapter、项目人物与事实，以及单次作品状态。多种责任常常同时存在于一个旧 Skill，不能按旧目录整包决定“保留为专属”或“直接变通用”。

实施需要证明同一公共方法能在不同项目中消费各自事实源，产物回到原项目且不串身份、不另建可写主库。至少选择有真实差异的项目资料验证公共研究、卡片／封面、内容管理和知识等已改职责；没有另一业务消费者的客户流程如实保留未验证状态。目录链接和参数校验只能证明 `logic/contract`，不能证明跨项目实际完成。

本轮仅完成静态审计与计划输入，**未合并 Skill、未删除入口、未执行项目或 Skill 更名，未完成 real replay、E2E agent loop 或本轮 product acceptance。** 源码中指出的身份默认、路径漂移和规则冲突仍待按迁移计划处理。
