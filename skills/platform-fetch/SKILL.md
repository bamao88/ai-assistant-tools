---
name: platform-fetch
description: |
  指定平台的内容抓取统一入口。覆盖 WebFetch / mcp-fetch 拿不到的封闭平台：小红书、微信公众号、视频号博主作品列表、腾讯会议（官方 MCP）、以及视频站点（YouTube/B站/抖音/小红书视频等 1000+ 站点）的字幕/封面/关键帧。
  当用户要求搜笔记、搜公众号、拉文章、看博主作品列表、下载腾讯会议逐字稿等平台原始内容，或其他任务需要这些采集步骤时，优先使用本 skill，不要先尝试 WebFetch 或 mcp-fetch。单条音视频的字幕、逐字稿、关键帧与素材研究优先 video-content；本 skill 保留视频 reference 供多平台采集或显式调用复用。完整文章由 source-longform-writing 负责，研究、选题任务仍由对应技能负责；本 skill 取材后交回原任务继续。
  本 skill 不处理：通用网页/API 抓取（用 mcp-fetch）、视频内容处理和素材整理（用 video-content）、飞书会议/妙记（用 lark-vc / lark-minutes）、NotebookLM 问答（用 notebooklm）、多源结构化研报（用 deep-research）、内容发布与多平台分发（用 Agent-Publish）、互动（用 xhs-interact）。
---

# 平台内容抓取

通用能力：账号定位、事实、素材与输出位置遵循当前项目；项目已有专属入口时优先沿其规则衔接。

你是"平台抓取路由器"。当用户需要从下面这些平台拿数据时，本 skill 是统一入口：

单条音视频的字幕、逐字稿、关键帧或研究素材直接以 `video-content` 为主入口。下表的视频分支保留供多平台采集、既有流程或用户显式调用本 Skill 时复用，不改变视频素材入口的主责。

| 平台 | 信号 | 用哪份 reference |
|------|------|------------------|
| 小红书 | xiaohongshu.com / xhslink.com URL；"小红书""xhs""搜笔记""博主主页"等 | `references/xiaohongshu.md` |
| 微信公众号 | mp.weixin.qq.com URL；"公众号""微信文章""gzh""扒一下 XXX 最近文章" | `references/gongzhonghao.md` |
| 视频号博主/作品列表 | "视频号博主""视频号作品""拉这个视频号最近内容""批量抓视频号笔记/作品" | `references/shipinhao.md` |
| 腾讯会议 | meeting.tencent.com URL；"逐字稿""会议录制""智能纪要""腾讯会议" | `references/tencent-meeting.md` |
| 视频字幕/封面/关键帧 | YouTube/B站/抖音/Twitter/视频号单条 URL/Vimeo 等 URL；"拉字幕""视频转写""抽关键帧""视频元数据" | `references/video.md` |

## 工作流程

**步骤 1 — 判断平台。**
看用户给的 URL 或表述，定位到上表的一行。如果不确定，问用户而不是猜。

**步骤 2 — 读对应的 reference。**
一次只读一个 reference。reference 里有完整的 CLI 命令、参数、子命令选择逻辑、失败兜底。**不要凭记忆拼命令** —— 路径长、参数多，照着 reference 抄。

**步骤 3 — 判断粒度：列表 vs 单条。**

| 需求 | 典型表述 | 路径 |
|------|----------|------|
| 列表 / 批量 | "拉这博主全部公开笔记""最近发了什么""一批爆款""扫一下监控列表" | 走 search / list / monitor 类命令 |
| 单条 / 详情 | "看这篇""这条详情""下载这个""抽这视频的字幕" | 走 detail / download / transcript 类命令 |

**步骤 4 — 执行并交付结构化结果。**
保留可继续深挖的 ID、xsec_token、fakeid、short_code、video_id、本地输出路径等 —— 用户下一步可能要拿这些做后续操作。
独立采集请求将结果交给用户；为写作、研究或选题任务取材时，将结果交回原任务并继续完成其目标，不能以采集结果替代最终交付。

## 多平台/多链接

用户一次给多个不同平台的链接或目标：拆成多次调用，每个平台独立路由。不要尝试用一个命令处理混合输入。

## 与其他 skill 的边界

读到 reference 前先确认 —— 如果用户的需求落在下面，**不要用本 skill**：

- **通用 URL（普通网页/API/JSON）** → `mcp-fetch`（`fetch_html` / `fetch_markdown` / `fetch_json` / `fetch_txt`）
- **单条音视频的字幕、逐字稿、关键帧或素材研究**（本地文件或 URL） → `video-content`。本 skill 的视频 reference 保留 URL 纯抓取原语（`info` / `transcript` / `keyframes`），供平台混合采集或显式调用复用。
- **根据 YouTube 等来源写完整文章/公众号长文** → `source-longform-writing` 主责；需要平台原始材料时再调用本 Skill，取材后返回写作流程。
- **账号、竞品研究或选题规划** → 对应研究或选题 Skill 主责，本 Skill 只执行其需要的平台采集步骤。
- **根据已有材料起标题、封面文案或发布正文** → `content-package-create`。
- **飞书妙记/视频会议** → `lark-minutes` / `lark-vc`（走 lark-cli）
- **NotebookLM 上你自己上传的源做问答** → `notebooklm`
- **跨多个来源做带引用的研报** → `deep-research`
- **发布 / 评论 / 点赞 / 登录** → 各平台对应的 publish/interact/auth skill

## 失败处理总则

每个 reference 里有平台特定的失败码和兜底策略。共同点：

- 看到登录态失败 → 引导用户去对应平台的 auth skill 或扫码流程，**不要自动重试无意义的请求**。
- 看到限流 → 减少并发、加 sleep，必要时切账号。
- 看到 "页面不可访问 / 私密 / 已删除" → 直接告知用户并停止，**不要绕路尝试**。
- 看到大批量任务卡住 → 检查输出目录里的 `failures.json` / `diagnostics/`，按 reference 里的失败码表给用户解释。

## 输出原则

- CLI 默认 JSON 输出，结构化转给用户时用 markdown 表格突出关键指标（阅读量、点赞、时长、发布时间等）。
- 单条详情类结果：标题、作者、发布时间、互动数据、正文/字幕、本地落盘路径，按这个顺序呈现。
- 列表类结果：表格 + ID/token 列，方便用户挑出感兴趣的让你深挖。
- 大文件下载（视频、批量逐字稿）默认提示用户输出目录占用，避免磁盘塞满。
