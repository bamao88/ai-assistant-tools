# 新媒体运营 Skill 导航

由 `registry.yaml` 生成。更新命令：`python3 scripts/check-media-skills.py --write-catalog`。
项目归属决定适用范围；全局可选不表示可套用于其他账号。名称可以用 `$名称` 调用。

## 定位与运营底座

| 调用名 | 适用范围 | 用途 |
|---|---|---|
| [self-media-init](../skills/self-media-init/SKILL.md) | 通用 | 自媒体账号项目初始化与补齐：盘点已有资料、建立定位和资产台账、明确事实源与后续能力入口，交付第一轮内容验证安排；检查模式只读 |

## 调研与洞察

| 调用名 | 适用范围 | 用途 |
|---|---|---|
| [content-creator-research](../skills/content-creator-research/SKILL.md) | 通用 | 自媒体人前期对标剖析综合工作流，四大子能力（teardown 博主拆解 / benchmark 博主对比 / niche-mapping 赛道测绘 / hook-decoding 钩子解码），带 fixture 与 checklist。产出止于结构化报告，不做物料包装。 |
| [product-deep-research](../skills/product-deep-research/SKILL.md) | 通用 | 基于一手证据研究产品全貌与关键机制，形成完整报告或来源型文章 |
| [assistant_zh_deep-research](../skills/assistant_zh_deep-research/SKILL.md) | assistant_zh | 项目研究编排与报告 |

## 选题与内容规划

| 调用名 | 适用范围 | 用途 |
|---|---|---|
| [content-topic-planning](../skills/content-topic-planning/SKILL.md) | 通用 | 研究、比较、深化选题，并按需巡看平台，为后续制作明确取舍依据 |
| [assistant_zh_topic-mine](../skills/assistant_zh_topic-mine/SKILL.md) | assistant_zh | 发掘候选与来源 |
| [assistant_zh_topic-select](../skills/assistant_zh_topic-select/SKILL.md) | assistant_zh | 选择推荐与确认选题 |
| [assistant_zh_topic-review](../skills/assistant_zh_topic-review/SKILL.md) | assistant_zh | 复核选题与更新判断 |

## 素材与知识准备

| 调用名 | 适用范围 | 用途 |
|---|---|---|
| [platform-fetch](../skills/platform-fetch/SKILL.md) | 通用 | 封闭平台内容抓取统一入口（小红书 / 公众号 / 视频号博主作品列表 / 腾讯会议官方 MCP / 视频字幕封面关键帧） |
| [content-production-prep](../skills/content-production-prep/SKILL.md) | 通用 | 自媒体内容素材包制备工作流：在选题已确定后整理内容 item、锁定口径、归档素材/脚本/转录稿/成片/封面/标题/正文/标签，并在进入剪辑、设计、审核或发布前做状态与素材完整性检查；不直接发布 |
| [video-content](../skills/video-content/SKILL.md) | 通用 | 视频字幕与研究：提取本地/URL 音视频逐字稿、字幕、关键帧和研究素材；完整文章由 source-longform-writing 编排，平台标题交 content-package-create |
| [assistant_zh_knowledge-ingest](../skills/assistant_zh_knowledge-ingest/SKILL.md) | assistant_zh | 资料入库与来源归档 |
| [assistant_zh_knowledge-triage](../skills/assistant_zh_knowledge-triage/SKILL.md) | assistant_zh | 知识待处理分拣 |
| [assistant_zh_knowledge-query-read](../skills/assistant_zh_knowledge-query-read/SKILL.md) | assistant_zh | 只读检索项目知识 |
| [assistant_zh_knowledge-query-owner](../skills/assistant_zh_knowledge-query-owner/SKILL.md) | assistant_zh | 管理项目知识与修订 |
| [assistant_zh_knowledge-query](../skills/assistant_zh_knowledge-query/SKILL.md) | assistant_zh | 兼容旧知识管理调用；兼容入口，实际职责见 `assistant_zh_knowledge-query-owner` |

## 内容制作

| 调用名 | 适用范围 | 用途 |
|---|---|---|
| [video-clip](../skills/video-clip/SKILL.md) | 通用 | 口播/长视频成片统一工作流：经 video-compose 编排转录→选题脚本→人工确认→剪辑/字幕/铸造/组装；支持 PPT 风格、原视频快剪和按需叠加，统一执行输出路由与质量门 |
| [source-longform-writing](../skills/source-longform-writing/SKILL.md) | 通用 | 文章写作：把 YouTube、播客、访谈、网页、官方文档、论文或混合资料写成中文长文；只有链接也从本入口开始，衔接资料获取、方向确认、完整文章、必要配图与表达润色 |
| [markdown-to-cards](../skills/markdown-to-cards/SKILL.md) | 通用 | Markdown 转小红书风格卡片图片 |
| [content-visual-assets](../skills/content-visual-assets/SKILL.md) | 通用 | 为文章寻找合适配图，支持直接截图和登录墙场景下的网络搜索提取 |
| [diagram-design](../skills/diagram-design/SKILL.md) | 通用 | 创建技术/产品图示的独立 HTML + inline SVG；供发布包长文配图阶段调用 |
| [article-expression-polish](../skills/article-expression-polish/SKILL.md) | 通用 | 文章润色：对已有中文文章改善表达、密度与阅读节奏，减少机器腔、翻译腔与废话；保留事实、结构、引用和来源边界 |
| [assistant_wxp_self_spoken-script-style](../skills/assistant_wxp_self_spoken-script-style/SKILL.md) | assistant_wxp_self | WXP 口播脚本文字风格；仅处理实际说出口的台词、自然说话节奏和念稿感，不作为文章、笔记正文或标题封面文案的通用风格层 |
| [assistant_zh_video-cover](../skills/assistant_zh_video-cover/SKILL.md) | assistant_zh | 张和口播视频封面生成（evc 宋体渐变，3:4）：kit 驱动单张/批量，底图轮换+相邻不撞。共享底图池/渐变素材在 platform-publish/assets/video-cover/zhanghe（黑块黄字 9:16 那套仍在 Agent-Publish） |
| [assistant_wxp_self_xhs-cover](../skills/assistant_wxp_self_xhs-cover/SKILL.md) | assistant_wxp_self | 八毛小红书封面制作，使用本项目已认可的个人视觉 |
| [assistant_wxp_self_knowledge-cards](../skills/assistant_wxp_self_knowledge-cards/SKILL.md) | assistant_wxp_self | 八毛知识卡片独立制作：分析、拆分、分页、生图与验收 |
| [MiMi_TV_Operations_content-package](../skills/MiMi_TV_Operations_content-package/SKILL.md) | MiMi_TV_Operations | 猫猫电视机内容制作与本地审阅包 |

## 平台适配与发布

| 调用名 | 适用范围 | 用途 |
|---|---|---|
| [Agent-Publish](../skills/platform-publish/SKILL.md) | 通用 | 本机复用已登录Chrome，三阶段会话hook后逐平台检查、上传或按授权提交；无登录请本人在原页登录，不启用独立配置/远端/凭据直传 |
| [content-package-create](../skills/content-package-create/SKILL.md) | 通用 | 标题与平台文案：根据已确定内容制作标题、笔记正文、平台配文、封面文字和完整发布包；完整文章交 source-longform-writing，不进入平台后台 |
| [xhs-auth](../skills/xhs-auth/SKILL.md) | 通用 | 小红书登录 / 登录态检查 / 多账号管理 |
| [assistant_zh_platform-adapt](../skills/assistant_zh_platform-adapt/SKILL.md) | assistant_zh | 项目多平台内容适配 |

## 互动与用户关系

| 调用名 | 适用范围 | 用途 |
|---|---|---|
| [xhs-interact](../skills/xhs-interact/SKILL.md) | 通用 | 小红书评论 / 回复 / 点赞 / 收藏 |
| [customer-management](../skills/customer-management/SKILL.md) | assistant_zh | 客户/学员资产管理（4 能力 + 任务卡 + 配方）：学员入表 / 就业回访 / 客户资产体检订正 / 好友刷新建行 / 付款 / 客户表同步飞书 / ad-hoc 读聊天检索 |

## 数据、复盘与改进

| 调用名 | 适用范围 | 用途 |
|---|---|---|
| [content-operations-ledger](../skills/content-operations-ledger/SKILL.md) | 通用 | 维护发布排期与记录，处理官方导出和指标快照，追踪内容复盘与改进 |
| [MiMi_TV_Operations_content-management](../skills/MiMi_TV_Operations_content-management/SKILL.md) | MiMi_TV_Operations | 猫猫电视机运营台账、官方数据与复盘 |
| [assistant_zh_publication-record](../skills/assistant_zh_publication-record/SKILL.md) | assistant_zh | 记录各渠道发布事实 |
| [assistant_zh_metrics-record](../skills/assistant_zh_metrics-record/SKILL.md) | assistant_zh | 记录官方指标快照 |
| [assistant_zh_content-review](../skills/assistant_zh_content-review/SKILL.md) | assistant_zh | 项目内容复盘 |
