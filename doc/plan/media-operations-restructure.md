# 新媒体运营 skill：复用拆分、职责整合与更名计划

更新日期：2026-10-23。状态：审计与计划修订，尚未实施运行变更。固定规则见 [字段与命名合同](../media-operations-contract.md)，职责与复用两个维度见 [统一架构](../media-operations-architecture.md)，现役证据见 [复用审计](media-cross-project-reuse-audit-2026-10-23.md)。

本计划覆盖 38 个现役运营入口，替代旧的 32 入口及后续 21 门面方案。旧包不再整包定归属，先逐规则、模块和实现拆分。入口数量来自真实责任，不是验收指标。先抽取、合并、更新和删除，最后更名，不留旧名兼容。

## A. 基线与范围

- 源码集中基线为 `6820027549c5720e2053f4e281e34b74edca0b35`；上轮职责文档为 `36e5a2d34ea38a88ee7b17952b385bf3fc8da661`。集中源码不等于脱离原项目即可运行。
- 核心 38 项分工审查正文、重要 references 和关键实现；另筛查当前发现目录 98 个去重入口的元信息并检查邻接能力，不能称 98 项完整深审。Claude 专用安装不在范围。
- 工作区有其他任务改动。实施核对有效版本和原有索引，仅提交本轮责任范围，不覆盖业务工作。
- 拆分记录方法来源、唯一责任方、消费者、输入输出、写入位置、授权停止点、许可与真实样本。
- 合并阶段删除重复及无独有能力入口，承接入口暂沿当前名改调唯一方法。新增公共工艺先通过规范方法文件回放，不安装临时别名或新旧双套入口；最后仅将承接入口和新增公共工艺一次切换为最终名称、注册与发现位置，并清除承接入口旧名。

## B. 双向拆分与规则裁决

| 工作包 | 现有错位 | 承接责任与实际改动 |
|---|---|---|
| 对象与证据合同 | init、prep、ledger 重复定义对象；研究流程重复证据规则 | 多消费者合同放 tools 内共享方法区；各流程引用同源，项目映射原格式，不强制第二总账 |
| 内容生命周期 | topics/prep/ledger、ZH 六入口、MiMi 管理重复共同步骤 | 一份六模块方法和执行核心；项目只接来源、目标、字段、原账和必要钩子 |
| 完整专题研究 | ZH deep-research 的研究、证据、claims 和引用校验被项目化 | 提升公共专题研究；ZH 只留输出与文章关联。账号/产品研究保留各自完整报告，共享证据方法 |
| 完整知识卡片 | WXP 分析、连续稿、解释单元、分页、图文构想、生图和整组检查被项目化 | 提升公共完整卡片工艺；WXP 人物、风格、样例、ID/登记绑定归项目，不降为 markdown 渲染 |
| 口播与封面 | WXP、ZH 封面和口播规则混有共同工艺 | 口播文字请求在 ASR/剪辑/成片审批前分流；封面生图/kit 渲染按需适配，kit 显式绑定资源根与状态根；个人风格、人像、品牌和账本归项目 |
| 平台适配 | ZH 平台改写不能供其他账号使用；公共包混入 ZH/AI PM 规则 | 共同改写归平台物料；硬规格共享，编辑建议可配置；身份、CTA、账号主题与 kit 迁回项目 |
| 反向清理公共包 | body_video 张和身份、publish-prep 默认 ZH 根/profile、视频白板与卡片 ZH 默认 | 显式上下文绑定及中性独立模式；认证、算法、视觉 profile 分离，不借换根目录宣称通用 |
| 批量生产实现 | MiMi 来源/哈希查重、probe/decode、导出一致性、审阅 HTML/ZIP 隐藏于项目脚本 | 共用执行核心接显式映射与政策；猫节目选材、来源授权例外、固定文案及批量编排归 MiMi |
| 平台采数与对账 | MiMi 的下载落盘、BVID 关联、表内日期范围经验只在项目 | 有效方法回灌公共平台对账 adapter；当时异常和回执保留项目案例 |
| 知识方法与存储 | ZH 五入口重复检索/演进；wiki 格式和项目权限混合；market 路径分叉 | 公共知识方法＋wiki/pending adapter；ZH 保留资料集合、pipeline、profile 保护及裁决，修正单一真实路径映射 |
| 人员识别与客户 | 共用匹配/镜像方法和 ZH 学员业务、默认路径混合 | 抽共享模块，分候选检索与身份确认；保留 ZH 业务入口。无第二真实消费者时不建空通用 CRM |
| 来源处理 | fetch、video-content、配图重复获取、抽帧与转录 | 共用来源处理及已有引擎；平台/媒体差异按需加载，材料交回后原任务继续 |

共享前必须解决：研究不照搬固定来源数、倒计时和固定长章节；卡片不把“一点一页/首图钩子”与解释单元工艺分别作为硬规则；平台硬上限、建议篇幅、账号 CTA 分开；内容对象含义同源、物理格式由 adapter 映射；人员线索 OR 命中只生成候选，不能直接确认同一人。项目只可调整声明为可配置的差异，不能覆盖事实、权限和平台硬限制。

## C. 38 个现役入口的逐项去向

每个旧入口出现一次；目标允许一拆多。项目差异可为 profile/reference/config，不自动生成项目 skill。最终调用名与显示名只在 D 节汇总。

| 环节 | 当前入口 | 共享方法/目标归属 | 项目差异与旧入口处理 |
|---|---|---|---|
| 初始化 | `self-media-init` | `media-project-init`，引用共同内容对象合同 | 读取既有定位、账号和事实源，不新建平行注册 |
| 内容管理 | `content-topic-planning` | `content-manage` 选题计划模块 | 受众、优先级、候选池由项目绑定；旧入口退出 |
| 内容管理 | `content-production-prep` | `content-manage` 来源/作品/版本及交接 | 保留原目录和选定稿关系；旧入口退出 |
| 内容管理 | `content-operations-ledger` | `content-manage` 排期/渠道/指标/复盘 | 不固化具体项目账本 |
| 内容管理 | `assistant_zh_topic-mine` | 公共选题发现、来源去重方法 | client/raw、ingest report、候选池接入归 `assistant_zh_content-manage`；旧入口退出 |
| 内容管理 | `assistant_zh_topic-select` | 公共价值/准备度、shortlist 与标题分离方法 | 人设与优先级归 ZH 配置；旧入口退出 |
| 内容管理 | `assistant_zh_topic-review` | 公共证据、密度、展开/补强、重复评估 | 本人经验与数量偏好归 ZH；旧入口退出 |
| 内容管理 | `assistant_zh_publication-record` | 公共逐 destination 凭证记账 | 原字段/路径映射归 ZH 管理入口；旧入口退出 |
| 内容管理 | `assistant_zh_metrics-record` | 公共官方原表、窗口与快照方法 | 账号与台账映射归 ZH；旧入口退出 |
| 内容管理 | `assistant_zh_content-review` | 公共复盘与行动追踪 | 承接 `assistant_zh_content-manage` 的真实项目编排 |
| 内容管理 | `MiMi_TV_Operations_content-management` | 公共六模块；采数经验回灌对账方法 | `mimi_tv_operations_content-manage` 只接项目事实与差异 |
| 知识管理 | `assistant_zh_knowledge-ingest` | 入库/证据、wiki adapter 纳入 `knowledge-manage` | ZH pipeline、资料集合、候选发现钩子归项目知识入口；旧入口退出 |
| 知识管理 | `assistant_zh_knowledge-triage` | 公共 merge/new/skip、演进与索引日志 | 承接 `assistant_zh_knowledge-manage`；profile 保护、裁决权留项目 |
| 知识管理 | `assistant_zh_knowledge-query-read` | `knowledge-manage` 索引→全文→引用，只读模式 | 数据空间由绑定指定；旧入口退出 |
| 知识管理 | `assistant_zh_knowledge-query-owner` | 共用检索，明确写回为独立模式 | ZH 可写范围、沉淀政策留项目；旧入口退出 |
| 知识管理 | `assistant_zh_knowledge-query` | 无独有核心方法 | 兼容别名删除，不保留转交入口 |
| 客户管理 | `customer-management` | 候选/身份、证据、去重、镜像/回写抽共享模块 | `assistant_zh_customer-manage` 保留学员/期次/就业/线索与私有表映射 |
| 调研 | `content-creator-research` | `creator-research`，共享证据合同 | 定位及对标偏好按项目输入 |
| 调研 | `product-deep-research` | `product-research`，共享证据合同 | 保留非内容用途，不自动写入选题池 |
| 调研 | `assistant_zh_deep-research` | `subject-research`，完整研究和证据/claims 实现 | ZH 只留输出关联配置，不保留空项目研究门面 |
| 素材 | `platform-fetch` | `source-collect` 平台正文/列表/会议模式 | 账号与环境显式绑定，不抢原任务主责 |
| 素材 | `video-content` | `source-collect` 音视频转录/字幕/关键帧/解析 | 共用获取器；旧入口退出；只取字幕可单独停止 |
| 制作 | `source-longform-writing` | `article-write` 完整来源写作、重写 | 作者风格按项目绑定，不硬调个人口播 skill |
| 制作 | `article-expression-polish` | `article-write` 可独立请求的润色模式 | 事实、结构、引用边界保留；旧入口退出 |
| 制作 | `video-clip` | `video-produce` 成片及口播文字编辑模式 | 清除 ZH 默认，显式选择配方/人物/输出/参数 |
| 制作 | `assistant_wxp_self_spoken-script-style` | 可说性、朗读与表达检查归 `video-produce` | WXP 语气、经历归项目 profile；旧入口退出 |
| 制作 | `assistant_wxp_self_knowledge-cards` | `knowledge-card-produce` 完整卡片工艺 | 人物/机器人、品牌、样例、ID/登记归项目；旧入口退出 |
| 制作 | `markdown-to-cards` | `markdown-card-render` 接收现成稿渲染 | 移出账号主题默认，视觉与认证配置分开 |
| 制作 | `content-visual-assets` | `visual-asset-prepare` 截图/取帧/裁图/字幕卡 | 输出根显式传入，清除个人发现路径依赖 |
| 制作 | `diagram-design` | `diagram-design` 图型/语义/布局/输出 | 沿用 marker 直接读 profile 的并行安全模式 |
| 制作 | `assistant_wxp_self_xhs-cover` | `cover-design` brief→生图/修订→检查 | 黑粉品牌、相貌、CTA/方案偏好归 WXP；旧入口退出 |
| 制作 | `assistant_zh_video-cover` | `cover-design` 显式 kit 渲染、总览和检查 | 人像/字体/渐变等 kit 与状态根归 ZH；旧入口退出 |
| 制作 | `MiMi_TV_Operations_content-package` | 公共查重/媒体核验/导出/审阅及封面/物料方法 | `mimi_tv_operations_content-produce` 保留独有节目/笔记批量编排 |
| 平台物料 | `content-package-create` | `publish-package-prepare` 单项/整包、公共平台适配 | 移出 ZH/AI PM 身份、主题、CTA 和封面 kit |
| 平台物料 | `assistant_zh_platform-adapt` | 共同改写归 `publish-package-prepare`，分页归卡片工艺 | 本人/课代表身份、账号映射留 ZH；旧入口退出 |
| 平台执行 | `Agent-Publish` | `content-publish` 账号/草稿/上传/提交模式 | 适配实际环境，按目标账号与本次授权停止 |
| 平台执行 | `xhs-auth` | `content-publish` 可单独请求认证/切换 | 采集/发布各验实际运行环境；旧入口退出 |
| 平台执行 | `xhs-interact` | `xiaohongshu-interact` 互动及其认证环境 | 账号、目标、互动授权按本次输入 |

## D. 最终候选入口与统一显示名

名称尚未安装；实施后由唯一 registry 生成现役导航。公共知识入口须先在独立知识空间证明 adapter 可用。若实施证据改变边界，更新本表，不创建平行清单。

| 用途 | 最终实际调用名 | 显示名 |
|---|---|---|
| 账号底座 | `media-project-init` | 通用｜自媒体项目初始化 |
| 内容生命周期 | `content-manage` | 通用｜内容管理 |
| 项目内容生命周期 | `assistant_zh_content-manage` | assistant_zh｜内容管理 |
| 项目内容生命周期 | `mimi_tv_operations_content-manage` | mimi_tv_operations｜内容管理 |
| 知识生命周期 | `knowledge-manage` | 通用｜知识管理 |
| 项目知识生命周期 | `assistant_zh_knowledge-manage` | assistant_zh｜知识管理 |
| 项目客户业务 | `assistant_zh_customer-manage` | assistant_zh｜客户与学员管理 |
| 调研 | `creator-research` | 通用｜账号调研 |
| 调研 | `product-research` | 通用｜产品调研 |
| 调研 | `subject-research` | 通用｜专题调研 |
| 来源处理 | `source-collect` | 通用｜平台资料与音视频解析 |
| 制作 | `article-write` | 通用｜文章写作与润色 |
| 制作 | `video-produce` | 通用｜视频制作与口播编辑 |
| 制作 | `knowledge-card-produce` | 通用｜知识卡片制作 |
| 制作 | `markdown-card-render` | 通用｜markdown 卡片排版 |
| 制作 | `visual-asset-prepare` | 通用｜配图准备 |
| 制作 | `diagram-design` | 通用｜图解设计 |
| 制作 | `cover-design` | 通用｜封面设计 |
| 项目制作 | `mimi_tv_operations_content-produce` | mimi_tv_operations｜内容制作 |
| 平台物料 | `publish-package-prepare` | 通用｜平台文案与发布物料 |
| 平台执行 | `content-publish` | 通用｜内容发布与账号认证 |
| 平台执行 | `xiaohongshu-interact` | 通用｜小红书互动 |

WXP 人物、语气、品牌仍属项目，但不为保存这些资料而注册 `assistant_wxp_xhs_content-produce`；ZH 通用研究和平台改写也不再套项目门面。保留的项目 skill 全部使用完整小写项目名前缀。

使用时：做卡片用公共入口＋当前项目或显式输出；写文章用公共入口＋来源＋作者/读者；改口播用视频入口的文字模式，交付文字即停止；ZH/MiMi 运营从各自入口接同一管理方法和自己的原账。公共入口不要求每次复述完整配置，由当前项目解析必要绑定。

描述词保留“视频转文章、做卡片、改口播、排期、复盘”等常用触发语并说明产物边界。独立会话必须找得到公共能力，不依赖本对话记忆。

## E. 实施顺序

| 阶段 | 交付与退出条件 |
|---|---|
| 1. 记录与裁决 | 冻结 38 项覆盖、原规则/实现/许可与样本，确认公共合同、可配置差异及冲突裁决 |
| 2. 抽取与反向清理 | 完成 B 双向拆分；公共研究/卡片/封面可独立执行，公共包无项目默认；核心接显式 adapter/policy/context |
| 3. 接入、合并与删除 | 原入口改调公共方法，项目接自己的字段/身份；同步依赖与检查器，移除重复正文、实现和无独有能力入口，更新调用方 |
| 4. 业务回放 | 公共方法、第二项目/无项目任务及每个保留项目编排有正向完成证据，缺失能力继续补齐 |
| 5. 最终更名 | 一次切换项目/skill 调用名、目录、显示名、注册、发现位置和运行配置；旧名退出，业务连续性复核 |

同一方法只在责任方改一次。项目反馈先判定共用工艺、适配、项目政策或运行事实，修改对应来源并做受影响项目的最小回归，不追加另一套永久方法。

在现有 registry 增 `uses_methods` 指向真实仓库相对文件，不建另一份模块注册。它是本地依赖检查合同，不会自动替 Codex 加载；正文必须实际引用，检查器校验存在、引用一致及依赖无环。完整工作流引用其 `SKILL.md`，局部引用指向规范 reference，不能绕过完成合同。代码依赖继续 `uses_engines/uses_vendor`，绑定引用原项目事实源，源码不依赖用户家目录发现路径。

## F. 跨项目验收后，再更名

| 代表性真实输入/场景 | 必须正向完成 |
|---|---|
| WXP 小红书与公众号分别制作卡片/文章/物料 | 同一方法、正确身份/风格/路径/选定版，不复制工艺、不混账号 |
| 无项目，仅材料和输出目录的研究与卡片 | 完成交付，不读写 ZH/WXP，不要求复制其目录/profile |
| ZH 与 MiMi 各一份真实原表及原发布账 | 同一对账/复盘方法接回各自原账；发布 ID、窗口、缺值、改进行动正确 |
| 查看/刷新候选，批量登记与下周排期 | 查看只读；刷新有来源取舍；沿用原 ID；本地排期不操作平台定时 |
| 两个独立知识空间查询/入库/明确沉淀 | 同一证据/检索/写入方法，索引日志与查写边界正确；ZH 保护仅在其绑定生效 |
| YouTube URL 转文章、仅润色、仅改口播 | 分别交付文章、原范围表达修改、可说文字；中间材料不替代完成 |
| MiMi 批次与另一项目的真实媒体/审阅包 | 同一检查实现、各自政策与账本；核验实际派生媒体、HTML/ZIP 内容及导出一致性，保留 MiMi 完整生产能力 |
| 两项目并行生成图解/封面/物料 | 无全局风格覆盖、人物串用或账本混写，各自关联选定版本 |
| 独立 Agent 新会话，只给任务与项目 | 找到公共入口，真实加载规范依赖并完成任务 |
| 仅认证、建草稿、明确提交及互动 | 各自停止点独立、账号/环境正确、真实回执；只在相应授权范围操作 |

缺依赖或缺配置检查是 `logic/contract`，不能替代原输入成功。副本回放写明范围；无平台动作不称平台 E2E。分别记录 `logic/contract`、`real replay`、`E2E agent loop`、`product acceptance`，不以文件搬出或文档通过称业务完成。

## G. 最后统一名称与引用

| 当前项目目录 | 最终目录名 |
|---|---|
| `assistant_wxp_self` | `assistant_wxp_xhs` |
| `assistant_wxp_ai8zu` | `assistant_wxp_gzh` |
| `MiMi_TV_Operations` | `mimi_tv_operations` |
| `assistant_zh` | `assistant_zh` |

- 吸收 `assistant_wxp_xiaohongshu_ops` 有效规则、核对无独有内容后删除骨架，旧拆分计划归档；不顺带迁移产品/学习/生活资料。
- 原生 UID/AppID、历史内容/投稿/指标 ID、认证 profile、算法参数和凭据变量不机械改写；项目路径、输出路由、现役回放路径与归属字段逐项切换。
- 同批更新 skill 目录、frontmatter、显示名、默认提示、正文/references、registry 和 Codex 发现入口。仅大小写变化在不区分大小写文件系统经临时目录切换并核对拼写。
- 公众号先改 `account.yaml` 项目名/工作目录再同步生成规则；检查 `.codex/hooks.json`、调度、共享资产入口、输出路由、根 `.gitignore`，避免错写或意外公开业务数据。
- 同步 Codex 保存的项目标签/路径与会话工作区，通过应用支持方式更新，不直接改数据库或臆造 projectId。
- 公众号事实源已明确不使用飞书，清理根表过时归属，不据新名称分配认证；公众号映射核对真实账号，不按旧目录推断两个账号。
- 删除被替代注册、旧名入口、别名、转交 skill、兼容软链和重定向；正常发现链接直指唯一新源码，历史证据/Git 记录保留当时事实。

## H. 完成条件与本次状态

完成条件：38 项能力与许可有去向；各环节共享方法、特化、项目政策和运行事实责任清楚；其他项目和独立任务能真正使用公共能力；项目只维护差异；实现无隐藏默认、数据/权限不串用；正向回放通过；最后全小写更名、引用一致、旧入口退出。

本轮仅完成静态审计、架构/字段规则与计划修订。当前仍为 38 个运行入口，未执行合并、删除、项目更名、认证或平台动作，未完成新架构的真实输入回放或产品验收。
