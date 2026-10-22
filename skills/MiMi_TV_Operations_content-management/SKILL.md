---
name: MiMi_TV_Operations_content-management
description: 猫猫电视机内容数据与复盘的统一项目入口。更新三平台排期／官方导出、复盘本周、诊断单篇、按复盘优化下一批笔记或复查上轮调整时使用；直接连接项目现有数据、报告、优化简报和制作规则，复用共享方法，不另建台账，不上传或发布。
---

# 猫猫电视机内容管理与复盘

本项目的数据维护、内容复盘和后续优化统一调用本Skill。人工请求与独立定时任务使用同一入口；Agent按需读取下方共享资源，不需要用户再选择另一个通用复盘Skill。

## 跨流程经验如何使用与维护

涉及返工、规则冲突或复查历史执行时，读取 [本轮完整对话复盘](/Volumes/ExtSSD2601/MiMi_TV_Operations/reviews/2026-10-21-conversation-retrospective/README.md)：覆盖物料版本、发布与中断恢复、官方导出、分析归因、实际采用和人工／定时入口，并指向各自现行规则。它是经验依据，不是第二套操作手册。日常任务按下表及流程直接读相应真源。

收到局部反馈时，回看同一目标的前后指令、相关产物和执行证据，检查上下游是否存在同因问题；区分已确认原因与未查明现象。可复用经验改共享方法，本项目事实与认可口径改项目规则，具体结果留运行记录；同时清理冲突旧说明，不为每次纠错再建Skill。仅补文档不能报告为业务流程已重新验证。

## 现有资料：从这里直接读

| 需要知道什么 | 当前文件／依据 | 使用方式 |
| --- | --- | --- |
| 排期、发布、数据缺口及执行决定 | [CONTENT_MANAGEMENT.md](/Volumes/ExtSSD2601/MiMi_TV_Operations/CONTENT_MANAGEMENT.md) | 日常主入口；生成区不手改，手写决定保留 |
| 表现、可能原因、反例和下批取舍 | [CONTENT_REVIEW.md](/Volumes/ExtSSD2601/MiMi_TV_Operations/CONTENT_REVIEW.md) | 当前结论，先看数据截止与仍待验证的判断 |
| 上轮建议是否采用、下批如何改 | [优化简报](/Volumes/ExtSSD2601/MiMi_TV_Operations/planning/CONTENT_ITERATION_BRIEF.md) | 沿action／review ID跟踪实际版本、发布与观测 |
| 分平台已发／定时事实 | [publications.csv](/Volumes/ExtSSD2601/MiMi_TV_Operations/content/publications.csv) | 每个平台独立记录，不能由计划到期猜已公开 |
| 各时点指标与来源 | [metrics.csv](/Volumes/ExtSSD2601/MiMi_TV_Operations/reviews/metrics.csv) | 保留平台、窗口、真实采集时点、统计截止和质量标记 |
| 已有观察、假设与报告索引 | [reviews/index.csv](/Volumes/ExtSSD2601/MiMi_TV_Operations/reviews/index.csv) | 同一经验沿原ID修订，保留反例 |
| 已制作作品及当前物料 | [作品索引](/Volumes/ExtSSD2601/MiMi_TV_Operations/content/index.csv) | 由artifact_path进入实际item；当前物料不自动等于已发布版本 |
| 待补采／待复查事项 | [maintenance.csv](/Volumes/ExtSSD2601/MiMi_TV_Operations/reviews/maintenance.csv)、[后台核对](/Volumes/ExtSSD2601/MiMi_TV_Operations/reviews/platform-checks.csv) | 先处理实际到期队列，不重传或改排期来核账 |
| 已取得的官方原表与核对证据 | [10月20日采集记录](/Volumes/ExtSSD2601/MiMi_TV_Operations/reviews/2026-10-20-live-reconciliation/README.md)、[首轮分析依据](/Volumes/ExtSSD2601/MiMi_TV_Operations/reviews/2026-10-20-performance-review/README.md) | 这是已登记历史依据；新轮次从metrics.source及新运行目录读取，不能把旧日期当最新采数 |
| 身份、定位及数据规则 | [account.yaml](/Volumes/ExtSSD2601/MiMi_TV_Operations/account.yaml)、[定位](/Volumes/ExtSSD2601/MiMi_TV_Operations/profile/positioning.md)、[DATA.md](/Volumes/ExtSSD2601/MiMi_TV_Operations/DATA.md) | 身份和项目边界的真源；不从历史文案推断当前权限 |
| 项目路径、平台映射和调度 | [项目配置](/Volumes/ExtSSD2601/MiMi_TV_Operations/config/content-operations-ledger.json) | 路径映射与运行状态唯一配置；变化时同步，不另建同义配置。新环境可参考本包 `ledger.config.example.json`，不覆盖现有项目配置 |
| 封面、标题、正文和实际制作 | [项目制作规则](../MiMi_TV_Operations_content-package/SKILL.md) | 优化进入具体制作时内部衔接，不要求用户重新调用另一个入口 |

真实平台账号映射、浏览器归属、授权环境及运行记录保留在项目 `account.yaml` 和 `config/content-operations-ledger.json`；平台身份每次实际核验。公开 Skill 仅提供方法与配置模板，不保存真实账号和调度状态。

## 采数前必读：已纠正的错误方法

进入平台获取表现数据前，必须读取 [官方表格采集经验](references/data-collection.md)：包含先抓页面数字的流程偏差、小红书下载事件超时但文件已落盘、B站嵌入分析页／逐稿导出及同名CSV匹配的实际修正和原始依据。再按其中链接的共享流程执行。不能只读“采用官方导出”的原则就跳过下载确认与原表核对。

## 人工与定时：同一个调用流程

人工可直接说“复盘本周”“复盘这条笔记”“根据复盘优化下一批”，或显式调用：

```text
$MiMi_TV_Operations_content-management 复盘本周三平台内容，更新报告并给出下一批调整。
$MiMi_TV_Operations_content-management 根据已有复盘优化下一批笔记，并追踪实际采用。
```

不等待定时任务。独立定时任务同样只调用本Skill，从项目文件重建上下文；频率、时间及启停状态以项目配置和应用记录为准，配置成功不代表真实采数E2E成功。

先判断任务范围，然后在本流程内完成：

1. **读现状。** 默认先读总表、当前报告、优化简报及DATA.md；单篇诊断只深入对应pub、指标和实际作品。明确本轮问题、数据截止、已认可基准、上轮动作是否实际采用；不要把所有任务强制扩大成全量采数。
2. **按需补事实。** 运行`--queue`查看到期事项。新数据会影响判断时，先读 [采集经验与修正](references/data-collection.md)，按共享流程点击官方导出、确认本次新文件完整落盘并核对后处理；原件、范围、真实时间及哈希保存在新的reviews运行目录。后台卡片只核身份、状态、可见性、排期与总量，不替代表格成绩。下载事件超时先核文件，不直接重导或改抓页面数字。认证问题按Agent-Publish的会话规则处理，不绕过验证。
3. **分析与复查。** 读取共享 [复盘执行方法](/Users/xpw/.agents/skills/content-operations-ledger/references/content-review.md) 及其分析参考。先查上轮action是否采用，再按同平台、类型、可比窗口评价规模、进入、留存和看后反馈。核实际封面／开头／正文与历史版本，分开事实、原因假设和反例；不同片长、投流、版本和稿龄不推单因素因果。
4. **回写结论和制作输入。** 修订前归档上版报告／简报及本轮依据；更新CONTENT_REVIEW.md，沿原reviews/index.csv经验ID；把下一批具体要改什么、保持什么、主要变量、适用范围和指标窗口写入优化简报。无新数据不假刷新截止，没有实施不评价动作成败。
5. **需要改笔记就实际落地。** 用户要求优化具体本地未发布物料或开始下一批制作时，在本任务内沿项目制作规则改item、成片／封面／文案、导出和验收；记录iteration的brief_version、action_ids、review_ids、applied_at、change_summary，并在简报登记真实采用版本。没有素材或仅请求分析时交付待执行制作输入，不假报改包。平台发布需对应授权，已有／已定时稿不自动修改。
6. **收尾和下次验证。** 实际发布后关联pub，按公开后约24h／72h／7天回收，回报告复验。更新队列和总表，运行刷新及`--check`。人工与定时共用一套文件；入库用既有锁，报告编辑前检查并发变化，重读合并，不覆盖他人决定。报告实际完成层级和仍缺的证据。

## 数据命令与共享资源

在项目根目录执行：

```bash
python3 scripts/content_management.py --queue
python3 scripts/content_management.py --import-snapshot reviews/<本轮>/snapshot.json
python3 scripts/content_management.py
python3 scripts/content_management.py --check
```

导出解析及入库格式读 [通用数据合同](/Users/xpw/.agents/skills/content-operations-ledger/references/data-contract.md)，平台核对细节读 [平台采集参考](/Users/xpw/.agents/skills/content-operations-ledger/references/platform-reconciliation.md)。通用 [报告模板](/Users/xpw/.agents/skills/content-operations-ledger/assets/CONTENT_REVIEW.md)、[简报模板](/Users/xpw/.agents/skills/content-operations-ledger/assets/CONTENT_ITERATION_BRIEF.md) 和引擎只维护一份，不复制项目事实。其它项目可以复用这些资源，建立自己的项目入口、数据链接和约束。

## 本项目保持的边界

- 项目只管理运营，不修改产品运行代码；来源／授权、制作审核与平台公开分别记录。发布不自动把作品review改ready。
- 外部素材与账号历史分开；不因本次复盘放开产品／QA素材，不改变原作者授权状态，不虚构item关联。
- 暂缓、备用及已排稿件的当前状态查项目事实台账；已有稿件按原证据保留，禁止为核账重传或改定时。
- A16、标题前缀、正文类型和CTA继续以项目制作规则为准。探索假设不自动覆盖认可基准；有重复证据或负责人明确决定时，在真正负责该行为的规则中修正并记录依据。
- 缺失不补零，统计截止不当采集时间；不倒填旧D+N，不混投流算自然贡献，不以赞藏粉推游玩、下载或ROI。
