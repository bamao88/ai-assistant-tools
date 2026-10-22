# 抓取线架构

> 最后更新：2026-08-31
> 适用范围：`platform-fetch` 抓取入口 + 小红书、公众号、视频号、腾讯会议、视频 URL 抓取引擎

## 一句话

抓取现在是一条线，不是很多个零散技能。`platform-fetch` 是唯一入口，负责判断用户要从哪个封闭平台拿内容，再把任务交给对应 reference 和 engine。

大白话：用户说“帮我看这条小红书 / 拉这个公众号 / 查腾讯会议逐字稿 / 抽这个视频字幕”时，Agent 不应该先拿普通网页抓取硬试，而是先到抓取总台分诊。

## 现在有哪些部件

| 部件 | 路径 | 做什么 |
|---|---|---|
| 抓取入口 | `skills/platform-fetch/SKILL.md` | 判断平台和任务粒度，只读对应一份 reference |
| 小红书 reference | `skills/platform-fetch/references/xiaohongshu.md` | 搜笔记、首页推荐、笔记详情、用户主页；默认锁测试号 |
| 公众号 reference | `skills/platform-fetch/references/gongzhonghao.md` | 搜公众号、列文章、下载单篇、监控爆款 |
| 视频号 reference | `skills/platform-fetch/references/shipinhao.md` | 搜视频号账号、拉作品列表、查作品详情和评论 |
| 腾讯会议 reference | `skills/platform-fetch/references/tencent-meeting.md` | 查录制、逐字稿、智能纪要；视频/分轨下载走现役脚本 |
| 视频 URL reference | `skills/platform-fetch/references/video.md` | 抓 URL 视频的元数据、字幕、封面和关键帧 |
| 小红书 engine | `engines/xiaohongshu/` | 实际执行小红书登录态读取、搜索、详情抓取等 CLI |
| 公众号 engine | `engines/gzh-scraper/` | 实际执行公众号搜索、文章列表、下载和监控 |
| 视频号 engine | `engines/wechat-channels-fetch/` | 实际执行视频号公开账号和作品列表抓取 |
| 腾讯会议 engine | `engines/tencent-meeting/` | 官方 MCP 桥接和录制/转写/分轨下载能力 |
| 视频抓取 engine | `engines/video-research/` | 通过 `yt-dlp`、字幕和关键帧流程抓 URL 视频素材 |

## 核心契约

1. **先分平台，再读 reference。** `SKILL.md` 只做路由；真正命令、参数、失败兜底在各平台 reference。一次任务只读相关 reference，避免把五个平台的细节混在一起。
2. **抓取线默认只读。** 它可以搜索、查看、下载有权限的内容和保存结构化结果；不能点赞、评论、关注、发布或私信。需要写操作时转到 `xhs-interact` 或 `Agent-Publish`。
3. **优先用低风险账号。** 小红书抓取默认 `--account 测试号`；视频号调研默认 `--account aipm`。这能避免调研动作污染真实运营号的推荐和操作记录。
4. **保留可追溯 ID 和输出路径。** 抓取结果要把 `feed_id`、`xsec_token`、`fakeid`、`username`、`meeting_record_id`、`record_file_id`、本地文件路径等留给用户和下游流程。
   小红书笔记详情中的配图可通过同一个 Python CLI 下载到本地，再读取图片里的文字；这是笔记图文完整读取的一部分。
5. **普通网页不走这条线。** 通用 URL、开放 API、JSON、普通博客文章不应该触发 `platform-fetch`。

## 平台怎么路由

| 用户要什么 | 走哪份 reference | 底层 engine |
|---|---|---|
| 小红书搜索、笔记详情、博主主页 | `references/xiaohongshu.md` | `engines/xiaohongshu/` |
| 微信公众号搜索、文章列表、单篇下载、监控 | `references/gongzhonghao.md` | `engines/gzh-scraper/` |
| 视频号博主搜索、作品列表、作品详情、评论 | `references/shipinhao.md` | `engines/wechat-channels-fetch/` |
| 腾讯会议录制、逐字稿、智能纪要、分轨视频 | `references/tencent-meeting.md` | `engines/tencent-meeting/` |
| YouTube/B站/抖音/小红书视频等 URL 的字幕、封面、关键帧 | `references/video.md` | `engines/video-research/` |

## 和其他 Skill 的边界

| 需求 | 应该转到哪里 | 原因 |
|---|---|---|
| 普通网页、开放 API、JSON | 通用 fetch 工具 | 这不是封闭平台抓取 |
| 本地视频转写、跨视频研究、整理视频素材包 | `video-content` | 那是内容处理，不是纯抓取 |
| 小红书点赞、评论、收藏 | `xhs-interact` | 那是写操作 |
| 多平台发布、草稿、正式提交 | `Agent-Publish` | 抓取线不发布 |
| 飞书会议/妙记 | `lark-vc` 或对应飞书 skill | 腾讯会议 reference 只管腾讯会议 |
| 多源带引用研报 | `deep-research` | 抓取线只提供原始平台材料 |

## 常见维护场景

### 新增一个抓取平台

1. 先确认它确实属于“封闭平台内容抓取”，不是普通网页。
2. 新增 `skills/platform-fetch/references/<platform>.md`，写清适用信号、CLI、账号边界、失败处理和输出。
3. 如果需要新 engine，在 `engines/<name>/` 放代码，并登记到 `registry.yaml: engines`。
4. 在 `registry.yaml` 的 `platform-fetch.uses_engines` 里登记新 engine。
5. 更新本文档的平台路由表。
6. 给 `skills/platform-fetch/evals/evals.json` 增加触发样例和反例。
7. 跑结构检查和必要的真实 replay。

### 修改已有平台命令

先改对应 reference，再改 engine。大白话：reference 是 Agent 照着执行的说明书，engine 是后厨工具；命令变了但说明书没变，Agent 下次仍会照旧命令跑错。

结构或行为变化要同步更新本文档。纯 bug fix 如果不改变入口、命令、账号边界和输出契约，可以不改本文档。

### 处理废弃入口

不要复活 `xhs-fetch`、`gzh-scraper`、`tencent-meeting-downloader`、`content-research-hub` 等旧触发入口。它们已经归到 `platform-fetch`。如果保留旧说明文件，只能写成“已废弃，去 platform-fetch”，不能继续当独立入口。

## 验证层级

| 层级 | 说明 | 可以证明什么 | 不能证明什么 |
|---|---|---|---|
| `logic/contract` | 跑 `scripts/check-tools.py`、`scripts/skill-audit.py`，或检查 eval 样例 | registry、软链、文档映射、触发样例没有明显结构漂移 | 不能证明真实平台还能抓到数据 |
| `real replay` | 用真实 URL、会议号或关键词跑某个平台 CLI | 能证明某条平台链路在当前登录态和网络下可用 | 不能证明 Agent 会在复杂任务中总是正确路由 |
| `E2E agent loop` | 给 Agent 一个真实用户请求，让它加载 skill、读 reference、执行 CLI、汇报结果 | 能证明从用户请求到输出的完整 Agent 链路可用 | 不能替代用户对内容质量的判断 |
| `product acceptance` | 用户确认结果能用于选题、调研、发布准备或素材整理 | 能证明业务目标达成 | 不能自动覆盖所有平台和异常情况 |

以后汇报时必须说清楚做到了哪一层。比如只跑 `check-tools.py` 和 `skill-audit.py`，只能说“结构检查通过”，不能说“抓取链路完整跑通”。

## 当前风险

- 平台前端和登录态经常变，尤其小红书、公众号、视频号；真实抓取能力要靠 real replay 定期抽查。
- 腾讯会议视频/分轨下载和官方 MCP 查询不是同一条能力，不能混用；说话人轨下载必须按 reference 的现役脚本走。
- 视频 URL 抓取覆盖站点很多，但不同平台的字幕、登录、地域限制差异大；失败时要结构化说明原因，不要无限重试。
- 抓取线聚合了多个平台，任何拆分、合并或新增入口前，先打开 `doc/skill-governance-architecture.md` 中的官方文档链接，按最新 Skill 最佳实践判断。
