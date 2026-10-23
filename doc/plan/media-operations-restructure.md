# 新媒体运营职责整合与更名计划

更新日期：2026-10-23。状态：架构与计划修订，尚未实施运行变更。固定规则见 [字段与命名合同](../media-operations-contract.md)，唯一职责树见 [统一架构](../media-operations-architecture.md)。上一版预先锁定 32 个入口的表不再作为执行目标。

本次先覆盖全部 38 个现役入口的能力，按业务对象、内部模块、专业工作流和平台执行整合。入口数量来自真实责任划分；不按动词数量或运营环节数造 Skill。仍按合并、更新、删除在前，统一重命名在后推进，不做旧名兼容。

## A. 基线和实施范围

- 源码集中基线为 `6820027549c5720e2053f4e281e34b74edca0b35`；上一轮文档为 `d57c7f26e639f23178804c195e5d5b0cb35fb17b`。本计划替代其平铺入口方案；它们都不等于完整运行环境发行包。
- 当前工作区仍有其他任务改动。实施前核对有效版本，在隔离变更分支整理；只提交本轮职责范围，不覆盖进行中的业务工作。
- 冻结现役能力、独有规则、输入输出、真实停止点、写入位置、被调用资源、许可证及真实回放样本的清单。固定的是能力覆盖和责任边界，入口数可以随证据调整。
- 合并期间沿用下表承接入口的当前名称，更新完现役调用方后删除旧入口。最后再一起改目录、调用名、显示名和项目标识。

## B. 先按职责整合

| 责任组 | 当前承接入口 | 纳入的能力与组织方式 |
|---|---|---|
| 通用内容管理 | `content-operations-ledger` | 吸收 `content-topic-planning`、`content-production-prep`；形成来源/作品登记、选题计划、作品版本、排期渠道、指标分析、复盘改进六个内部模块 |
| ZH 内容管理 | `assistant_zh_content-review` | 吸收三个 ZH 选题入口、发布记录和指标记录；只连接项目事实源与独有决策，六个模块引用通用方法 |
| ZH 知识管理 | `assistant_zh_knowledge-triage` | 吸收入库、只读查询、owner 写回和旧别名的有效规则；查询、入库、裁决、修订与沉淀变成模式；删除纯兼容别名 |
| 来源处理 | `platform-fetch` | 吸收 `video-content`；正文/列表、会议原件、音视频转录、字幕、关键帧与素材解析是同一来源工作流中的模式，复用获取器 |
| 文章工作流 | `source-longform-writing` | 吸收 `article-expression-polish`；写作、重写、润色按任务选择，保留只给 YouTube URL 也继续交付文章的链路 |
| WXP 项目制作 | `assistant_wxp_self_knowledge-cards` | 吸收口播文字和封面入口的项目规则；三个制作模式按需读取；知识卡片保留完整自洽制作，不强制加载其他制作流程 |
| ZH 项目制作 | `assistant_zh_video-cover` | 吸收 `assistant_zh_platform-adapt`；封面、角色口吻与平台内容版本按模式组织；通用平台规格引用发布物料模块 |
| 平台发布与认证 | `Agent-Publish` | 吸收 `xhs-auth` 的账号列表、状态核验、登录、切换与现有多账号维护；认证是独立可请求模式，复用账号选择与身份核对合同，按实际目标执行环境适配，不把采集工具状态冒充正式浏览器登录 |
| MiMi 领域与制作 | 各沿用现有两个入口 | 管理入口接共享内容管理六模块；制作入口保留完整节目/笔记生产工艺。共同的版本、排期和分析只归管理，独有制作不重复实现管理模块 |

账号、产品与专题调研保留独立完整报告交付，共享来源/证据方法，不把产品全貌研究降为选题找材料。Markdown 排版、配图、图解和完整视频继续作为专业工作流；它们可单独交付，也可由内容管理调度。

### 合并时需要解决的重复

1. 内容登记、版本、排期、数据分析与复盘只有一份方法，不分别在 prep、ledger、ZH、MiMi 维护副本。
2. 内容管理与知识管理通过原文/知识来源关联协作；作品入库、知识观点入库和指标导入分别使用各自数据合同。
3. 项目口播风格、封面规则与平台 persona 约束放项目模式/references；只改账号或风格不再生一个 Skill。
4. 抽帧、视频获取、转录等底层方法只保留一份；配图工作流复用来源处理/引擎的能力，不自行复制原子实现。
5. 标题、平台正文与发布包共享同一确认稿和平台规格；支持单项请求，不因合并而强制完整包。
6. 认证按本次采集或发布的目标环境核验；发布路线遵守当前本机浏览器规则，不能用旧 CLI 默认身份或一个工具的会话替代另一个执行环境。
7. 模块按需读取，不能将旧文档简单拼成每次全部加载的长提示；保留来源、许可、特有质量要求与正向交付能力。

## C. 当前能力到目标架构的完整映射

本表覆盖现役 38 项。下列 21 个候选门面是本次职责分析的结果，不是新的固定数量指标；内部模块不独立注册。后续以合并与回放证明边界，再更新唯一现役 registry。

| 层次 | 当前入口 | 目标门面 | 显示名 / 内部归属 |
|---|---|---|---|
| 初始化 | `self-media-init` | `media-project-init` | 通用｜自媒体项目初始化 |
| 业务入口 | `content-topic-planning`、`content-production-prep`、`content-operations-ledger` | `content-manage` | 通用｜内容管理；六个生命周期模块 |
| 项目业务入口 | `assistant_zh_topic-mine`、`assistant_zh_topic-select`、`assistant_zh_topic-review`、`assistant_zh_publication-record`、`assistant_zh_metrics-record`、`assistant_zh_content-review` | `assistant_zh_content-manage` | assistant_zh｜内容管理；绑定共享六模块 |
| 项目业务入口 | `MiMi_TV_Operations_content-management` | `mimi_tv_operations_content-manage` | mimi_tv_operations｜内容管理；绑定共享六模块 |
| 项目业务入口 | `assistant_zh_knowledge-ingest`、`assistant_zh_knowledge-triage`、`assistant_zh_knowledge-query-read`、`assistant_zh_knowledge-query-owner`、`assistant_zh_knowledge-query` | `assistant_zh_knowledge-manage` | assistant_zh｜知识管理；检索/入库/维护模式 |
| 项目业务入口 | `customer-management` | `assistant_zh_customer-manage` | assistant_zh｜客户管理 |
| 调研工作流 | `content-creator-research` | `creator-research` | 通用｜账号调研 |
| 调研工作流 | `product-deep-research` | `product-research` | 通用｜产品调研 |
| 项目调研工作流 | `assistant_zh_deep-research` | `assistant_zh_subject-research` | assistant_zh｜专题调研 |
| 来源工作流 | `platform-fetch`、`video-content` | `source-collect` | 通用｜来源处理；平台资料/音视频解析 |
| 制作工作流 | `source-longform-writing`、`article-expression-polish` | `article-write` | 通用｜文章写作；起草/重写/润色 |
| 制作工作流 | `video-clip` | `video-produce` | 通用｜视频制作 |
| 制作工作流 | `markdown-to-cards` | `markdown-card-render` | 通用｜markdown 卡片排版 |
| 制作工作流 | `content-visual-assets` | `visual-asset-prepare` | 通用｜配图准备 |
| 制作工作流 | `diagram-design` | `diagram-design` | 通用｜图解设计 |
| 平台物料工作流 | `content-package-create` | `publish-package-prepare` | 通用｜平台文案与发布物料；单项/整包 |
| 项目制作工作流 | `assistant_wxp_self_spoken-script-style`、`assistant_wxp_self_xhs-cover`、`assistant_wxp_self_knowledge-cards` | `assistant_wxp_xhs_content-produce` | assistant_wxp_xhs｜内容制作；口播文字/封面/知识卡片 |
| 项目制作工作流 | `assistant_zh_video-cover`、`assistant_zh_platform-adapt` | `assistant_zh_content-produce` | assistant_zh｜内容制作；封面/角色与平台内容适配 |
| 项目制作工作流 | `MiMi_TV_Operations_content-package` | `mimi_tv_operations_content-produce` | mimi_tv_operations｜内容制作 |
| 平台执行 | `Agent-Publish`、`xhs-auth` | `content-publish` | 通用｜内容发布；账号与认证/草稿/提交模式 |
| 平台执行 | `xhs-interact` | `xiaohongshu-interact` | 通用｜小红书互动 |

项目门面只保留实际独有交付。WXP 小红书、公众号日常内容管理由通用入口读取原项目事实，不为项目名称对称新增空管理 Skill。现有 WXP 卡片的全套内容分析与制作、MiMi 完整生产、ZH 不同 persona 规则均保留。

## D. 合并后验证，再更名

| 代表性输入 | 必须正向完成的结果 |
|---|---|
| 查看推荐、明确刷新候选 | 默认只读；刷新有来源、候选与取舍；不擅自创建正式作品 |
| 一批作品入库与下周排期 | 复用原内容 ID，正确关联素材与版本；排期可用但不操作平台定时 |
| 导入一份官方原表并要求分析、复盘 | 同一发布 ID/时点/口径形成快照，解释数据与缺口，产生可追踪改进动作，无第二总账 |
| 知识普通查询、原文入库、明确沉淀答案 | 查询不写；另外两项按各自请求写对 wiki/pending 与日志，保留来源 |
| 一个 YouTube URL 转文章、仅润色已有文章 | 分别交付完整来源文章、局部表达修改；不把润色变成重新研究或口播 |
| WXP 知识卡片、ZH 角色改写、MiMi 制作与复盘 | 保留各自完整质量要求，产物与唯一事实源一致，不跨账号或强制套同一风格 |
| 只检查登录、创建草稿、明确提交 | 各自停止点独立；普通认证/本地排期不产生发布副作用，回执真实可查 |

静态/合同、真实输入回放、独立 Agent 完整执行与负责人验收分别记录。回放使用副本或本地资料时说明范围；无真实平台动作时不称平台 E2E。不得用“更安全地失败”代替原任务成功。

## E. 最后一次切换所有名称

| 当前项目目录 | 最终目录名 |
|---|---|
| `assistant_wxp_self` | `assistant_wxp_xhs` |
| `assistant_wxp_ai8zu` | `assistant_wxp_gzh` |
| `MiMi_TV_Operations` | `mimi_tv_operations` |
| `assistant_zh` | `assistant_zh` |

- 吸收 `assistant_wxp_xiaohongshu_ops` 的有效规则并核对无独有内容后删除旧骨架；旧拆分计划明确归档，由本计划替代。不顺带执行其产品、学习、生活资料大迁移。
- 原生 UID/AppID、历史内容/投稿/指标 ID、认证 profile、算法参数键与凭据变量不机械改写。根目录和跨项目路径、输出路由、现役回放路径、管理归属字段按责任逐项切换。
- 同一批更新 Skill 目录、frontmatter、显示名、默认提示、正文/references、registry 的 `name/source/project/scope/project_entry/entry_kind/layer` 及 Codex 发现入口。大小写归一后检查实际目录拼写；仅大小写变化且文件系统不区分大小写时，经临时目录名完成切换，避免实际名称未改变。
- 公众号项目先改 `account.yaml` 中的项目名与工作目录，再同步其生成规则。检查 `.codex/hooks.json` 中旧工作目录、现役调度、输出路由、共享资产入口与根 `.gitignore`，防止改名后写错位置或把业务数据公开提交。
- 两个 WXP 和 MiMi 的 Codex 已保存项目标签与路径也需切换，验证已有会话指向正确工作区；通过应用支持的方式更新，不直接改数据库或臆造应用 projectId。
- 公众号项目当前事实源已明确不使用飞书，清理根表过时归属，不因新名称自动分配认证身份。
- 移除被替代的注册、旧名字入口、别名、转交 Skill、兼容软链和重定向；正常项目链接直接指向唯一新源码。历史证据和 Git 记录保留原事实。

## F. 完成条件与本次状态

完成条件是：全部现役能力有归属；六个内容管理模块的规则与状态各只有一个责任方；专业工作流能独立完成其交付；项目适配没有复制核心方法；最终入口全小写、引用一致、旧入口退出；真实业务 ID、原账、选定版本和授权边界连续；代表性正向回放通过。

本轮仅完成职责架构、字段规则和迁移计划修订。当前仍为 38 个运行入口，未执行 Skill 合并、删除、目录更名、认证或平台动作；入口数量和文档检查不能代替真实回放验收。
