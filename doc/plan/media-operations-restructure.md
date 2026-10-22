# 新媒体运营 Skill 重组与项目更名迁移计划

日期：2026-10-22。状态：计划已编制；本轮尚未执行 Skill 合并、入口删除或项目更名。固定字段及命名规则统一见 [权威规则](../media-operations-contract.md)，本文件只维护本次执行顺序、任务和验收。

目标：保留现有能力，将 38 个入口收敛为 32 个正式 Skill；项目最终使用 `assistant_wxp_xhs`、`assistant_wxp_gzh`。按用户要求先合并、更新、删除，最后一次性切换名称，不做旧名兼容。

## A. 基线与执行方式

- 已集中源码的 GitHub 基线为 `6820027549c5720e2053f4e281e34b74edca0b35`。它是 Skill 源码快照，不是完整运行环境发行包。
- 当前 tools 工作区仍有其他任务的改动。实施前核对最新有效版本，在隔离变更分支中处理；不得整仓提交或覆盖进行中的业务工作。
- 记录 38 个入口的输入、输出、独有规则、调用方和读写边界；现有 ID、选定作品版本与项目事实源保持连续。
- 合并、依赖更新和对应旧入口删除在同一组变更完成；该组仍使用下表的当前承接名称。新名称统一留到最后阶段切换。

## B. 先合并、更新和删除

| 组 | 当前承接入口，暂不改名 | 合并与删除 | 必须保留的任务 |
|---|---|---|---|
| ZH 选题 | `assistant_zh_topic-select` | 吸收 `assistant_zh_topic-mine`、`assistant_zh_topic-review` 后删除这两个入口 | 查看推荐默认只读；增量发现、候选比较与评审分别按需执行；正式内容交回制作流程 |
| ZH 知识维护 | `assistant_zh_knowledge-triage` | 吸收 `assistant_zh_knowledge-query-owner`；删除 owner 和 `assistant_zh_knowledge-query` 兼容入口 | 待裁决处理、知识修订、按要求沉淀综合页；普通查询交独立只读入口；新资料入库继续独立 |
| ZH 运营 | `assistant_zh_content-review` | 吸收 `assistant_zh_publication-record`、`assistant_zh_metrics-record` 后删除这两个入口 | 发布事实、指标窗口与周复盘有独立模式、写入位置与证据；周复盘不顺便改作品状态 |

本组减少六个正式入口，38 → 32；不删除业务能力。`knowledge-ingest`、只读检索、制作准备、发布包准备、文章写作与润色、MiMi 制作与运营、WXP 知识卡片与 Markdown 排版分别保留。

### 同步更新范围

1. 每组合并前后核对全部独有正文、references、模板、脚本、素材及许可证，已吸收的重复内容删除；不把两份正文简单拼接。
2. 更新直接调用方，尤其知识入库后的候选发现、发布后的记账、观察窗口和周复盘路由；不留旧名转交层。
3. 通用 Skill 吸收可复用方法；项目 Skill 保留项目事实源与角色约束。平台规格只维护一份，项目适配引用它。
4. 修正现役说明和提示中已失效的职责、路径、重复质量关卡与旧别名；项目资料与运行状态留在原项目。
5. 现有检查器在最终阶段补齐目录、显示名和现役旧名扫描；删除 `customer-management` 前缀例外。本阶段不为了“检查通过”跳过职责回放。

### 项目结构清理

- `assistant_wxp_self` 是当前活跃内容源。`assistant_wxp_xiaohongshu_ops` 只有旧拆分骨架及占位文件：先吸收有效规则、核对无独有业务内容，再删除骨架。新的小红书目录将在最后由活跃源更名得到。
- 旧 `migration_plan.md`、`MIGRATION_FILE_MAP.md` 中指向旧骨架的计划作废，归档并标明本计划替代；保留作为历史记录，移除现役执行引用。
- 不借项目重命名启动旧计划中的产品、学习、生活资料大迁移。现役范围不符的内容按已有项目事实源处理；历史作品的跨平台素材和证据保持作品关系。
- 根项目表关于公众号项目使用 Lark 的说明已落后于公众号项目当前事实源，应删除该过时归属；不给新公众号项目自动分配飞书身份。
- 本轮没有 `assistant_wxp_ai8zu` 专属现役 Codex Skill，不为项目名称对称性新建空 Skill。

## C. 合并后先验证任务

| 代表性任务 | 需要验证的结果 | 层级 |
|---|---|---|
| 读取已有候选并明确刷新一批 | 默认查看无写入；刷新产生可用候选、来源与明确取舍；不创建重复正式作品 | real replay；另核对只读合同 |
| 普通知识查询、待裁决维护、明确沉淀答案 | 查询可回答且不写；维护正确落盘、保留来源和日志；入库链路仍独立可用 | real replay |
| 一条已有作品的发布事实、指标与周报 | 沿用真实记录和原台账；分别写到正确位置；内容、渠道和指标不串用 | real replay，不点击平台发布 |
| 已有 YouTube 来源转文章及文章润色 | 按现有来源完成可审阅文章，保留事实引用；润色不改成口播 | real replay |
| 一项 WXP 制作与一项 MiMi 运营任务 | 项目规则正确恢复，作品或复盘产物可用，选定版本和事实源连续 | real replay |

静态注册检查、元数据与链接检查、已有必要测试先通过，再进行上述真实输入回放。独立 Agent 从自然语言请求自行选中入口并交付的任务单列 `E2E agent loop`；负责人确认任务结果单列 `product acceptance`。不能混称已完整验证。

仅在本地副本完成写入回放时说明副本范围与差异；不能把 mock、合成输入或副本合同检查说成已验证真实平台链路。

## D. 最后统一重命名

该阶段同时改项目目录、Skill 调用名、显示名、注册、发现入口和实际运行引用，不建立旧名兼容层。

### 项目切换

| 源 | 最终目标 |
|---|---|
| `assistant_wxp_self/` | `assistant_wxp_xhs/` |
| `assistant_wxp_ai8zu/` | `assistant_wxp_gzh/` |
| `assistant_wxp_xiaohongshu_ops/` | 前置清理阶段吸收后删除，不保留第二工作区 |

### 完整最终 Skill 表

| 环节 | 当前入口 | 最终调用名 | 最终显示名 |
|---|---|---|---|
| 定位 | `self-media-init` | `media-project-init` | 通用｜自媒体项目初始化 |
| 调研 | `content-creator-research` | `creator-research` | 通用｜账号调研 |
| 调研 | `product-deep-research` | `product-research` | 通用｜产品调研 |
| 调研 | `assistant_zh_deep-research` | `assistant_zh_subject-research` | assistant_zh｜专题调研 |
| 选题 | `content-topic-planning` | `topic-plan` | 通用｜选题规划 |
| 选题 | `assistant_zh_topic-mine`、`assistant_zh_topic-select`、`assistant_zh_topic-review` | `assistant_zh_topic-plan` | assistant_zh｜选题规划 |
| 素材 | `platform-fetch` | `platform-content-fetch` | 通用｜平台内容采集 |
| 素材 | `video-content` | `audio-video-analyze` | 通用｜音视频解析 |
| 素材 | `content-production-prep` | `production-prepare` | 通用｜制作准备 |
| 素材 | `assistant_zh_knowledge-ingest` | `assistant_zh_knowledge-ingest` | assistant_zh｜知识入库 |
| 素材 | `assistant_zh_knowledge-query-read` | `assistant_zh_knowledge-search` | assistant_zh｜知识检索 |
| 素材 | `assistant_zh_knowledge-triage`、`assistant_zh_knowledge-query-owner`、`assistant_zh_knowledge-query` | `assistant_zh_knowledge-manage` | assistant_zh｜知识维护 |
| 制作 | `source-longform-writing` | `article-write` | 通用｜文章写作 |
| 制作 | `article-expression-polish` | `article-polish` | 通用｜文章润色 |
| 制作 | `video-clip` | `video-produce` | 通用｜视频制作 |
| 制作 | `markdown-to-cards` | `markdown-card-render` | 通用｜Markdown 卡片排版 |
| 制作 | `content-visual-assets` | `visual-asset-prepare` | 通用｜配图准备 |
| 制作 | `diagram-design` | `diagram-design` | 通用｜图解设计 |
| 制作 | `assistant_wxp_self_spoken-script-style` | `assistant_wxp_xhs_spoken-script-polish` | assistant_wxp_xhs｜口播润色 |
| 制作 | `assistant_wxp_self_xhs-cover` | `assistant_wxp_xhs_cover-design` | assistant_wxp_xhs｜封面设计 |
| 制作 | `assistant_wxp_self_knowledge-cards` | `assistant_wxp_xhs_knowledge-card-produce` | assistant_wxp_xhs｜知识卡片制作 |
| 制作 | `assistant_zh_video-cover` | `assistant_zh_video-cover-design` | assistant_zh｜视频封面设计 |
| 制作 | `MiMi_TV_Operations_content-package` | `MiMi_TV_Operations_content-produce` | MiMi_TV_Operations｜内容制作 |
| 分发 | `content-package-create` | `publish-package-prepare` | 通用｜发布包准备 |
| 分发 | `assistant_zh_platform-adapt` | `assistant_zh_platform-content-adapt` | assistant_zh｜平台内容适配 |
| 分发 | `Agent-Publish` | `content-publish` | 通用｜内容发布 |
| 分发 | `xhs-auth` | `xiaohongshu-session-manage` | 通用｜小红书登录与切换 |
| 互动 | `xhs-interact` | `xiaohongshu-interact` | 通用｜小红书互动 |
| 用户 | `customer-management` | `assistant_zh_customer-manage` | assistant_zh｜客户资料维护 |
| 复盘 | `content-operations-ledger` | `operations-manage` | 通用｜运营记录与复盘 |
| 复盘 | `assistant_zh_publication-record`、`assistant_zh_metrics-record`、`assistant_zh_content-review` | `assistant_zh_operations-manage` | assistant_zh｜运营记录与复盘 |
| 复盘 | `MiMi_TV_Operations_content-management` | `MiMi_TV_Operations_operations-manage` | MiMi_TV_Operations｜运营记录与复盘 |

合并完成后的正式数量为 32：18 通用、14 项目专属。固定规则在权威文档；本表是一次迁移的完整清单，不作为第二份现役注册表。

### 同一批必须切换的引用

1. tools 的 Skill 目录、frontmatter、显示名、默认提示、正文、references、模板及 `registry.yaml` 的 `name/source/project/scope/project_entry`。
2. Codex 全局三个 WXP Skill 入口、原项目本地两个入口以及其他已更名入口。只安装新名，移除旧名；项目正常链接直接指向唯一源码。
3. WXP 项目的有效 AGENTS、业务规则、定位入口、现有 `project_name` 等管理归属字段与实际路径；公众号项目先修改 `account.yaml` 的 `agent.name/agent.work_dir`，再同步其生成的规则文件，不能只改编译文本。
4. 视频输出路由的项目检测、目标路径和作品定位，以及仍被使用的真实回放输入路径。既有算法 profile/preset 键按独立参数域处理。
5. 公众号项目 `.codex/hooks.json` 中写死旧目录的运行命令；现役自动化、启动脚本和工作目录配置。按已有调度机制原位更新，保持调度标识，不新增重复任务。
6. 根项目表、现役共享资产入口，以及根 `.gitignore` 对业务项目的忽略范围，防止更名后业务资料意外进入公开仓库。
7. Codex 已保存的两个项目标签与路径。通过应用支持的项目管理方式更新，并验证已有会话仍能打开正确工作区；不直接改写应用数据库或臆造应用 projectId。
8. 统一生成现役导航。旧计划和迁移记录仅作为明确历史材料保留；本轮旧名不保留 `compatibility_for`、旧注册、转交 Skill、别名或旧路径软链。`deprecated` 如保留仅用于单向卸载检查，不能成为旧名调用或重定向机制。

## E. 最终完成条件

- 32 个正式 Skill 的名称、目录、显示、注册与发现入口一致；所有项目前缀符合最终项目标识。
- 两个最终项目目录各只有一个有效工作区；旧目录、旧骨架及旧发现入口退出。
- 对现役配置、脚本、提示、自动化和有效文档扫描，本轮被替换名称无执行引用；未变名 Skill 及明确历史材料不误报。
- 官方账号身份、认证绑定、既有内容/版本/发布/指标 ID 与原数据对应，未因项目名变化串用或重建。真实配置和业务数据未进入公开源码提交。
- 最终名称下再次进行受影响的正向回放，验证读取和产物落点；独立 Agent 选用新入口的完成情况单列。平台交互和正式发布仍以对应任务授权为界。
- 分组提交与检查结果可追溯，按实际验证层级交付。没有真实回放时保持未验收状态，不以规则已落盘代替迁移完成。

## 本轮交付状态

已完成引用影响盘点、权威字段规则和本计划。未执行合并、入口删除、项目/Skill 更名、调度切换或真实业务回放；现有日常任务继续使用当前入口。
