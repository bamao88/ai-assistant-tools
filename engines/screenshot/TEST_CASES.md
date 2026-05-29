# screenshot 测试用例

目标：用真实内容运营需求驱动截图工具优化。测试集不只验证“能截图”，还要验证 AI 能自动定位主体、裁成合适尺寸，并输出可直接用于小红书/公众号文章的素材。

## 分层原则

| 层级 | 类型 | 用途 |
|------|------|------|
| A | 公开网页资料 | 每次开发都可跑，验证网站局部内容定位、裁剪比例、尺寸输出 |
| B | X/Twitter 单条内容 | 验证公开社交内容截图；未登录优先，登录态作为兜底 |
| C | 网页原生图片直取 | 页面本身已有图片时，优先下载原图，必要时再裁剪 |
| D | 视频时间戳截图 | 真实资料需求，但首轮只定义验收，不要求实现 |
| E | 本地真实产物 | 用现有文章/图片作为稳定回归样本，防止线上页面变化导致误判 |

## 通用验收标准

- 输出文件存在，且非空白、非错误页、非登录拦截页。
- 最终像素与目标尺寸完全一致，例如 `720x1200`、`1080x1440`、`1200x675`。
- 主体内容占画面主要区域，不能被导航栏、cookie 弹窗、登录弹窗、空白边距挤占。
- 指定 selector/text/xpath 时，目标内容必须出现在截图中。
- 对页面顶部/底部元素裁剪时，clip 不越界，不出现黑边或透明边。
- 输出 metadata 记录：URL、selector、原始 viewport、clip、最终尺寸、裁剪策略、是否关闭弹窗。
- 如果页面目标本身是图片，优先下载原图；只有无法拿到原图、需要保留页面上下文、或用户明确要求界面截图时，才使用截图。

## A 层：公开网页资料

| ID | 真实需求来源 | URL / 入口 | 截图目标 | 建议尺寸 | 关键挑战 | 验收点 |
|----|--------------|------------|----------|----------|----------|--------|
| A01 | `feedback/2026-04-13_markdown-to-cards_支持inline图片.md`：文章需要 OpenAI 定价页截图作为配图 | `https://openai.com/api/pricing/` | `text=GPT-5.4 mini` 附近的价格卡片 | 小红书 `720x1200`；公众号 `1200x675` | 官方页结构复杂、有导航和 cookie 管理入口、价格卡片不是全页主体 | 能看到模型名和 Input/Cached input/Output 价格；导航不应占据主要画面 |
| A02 | WXP 个人分享：Tailscale 全平台配置指南需要价格/套餐截图 | `https://tailscale.com/pricing` | `text=Personal` 或套餐卡片区 | 公众号 `1200x675`；小红书 `720x1200` | 定价表横向很宽，移动/桌面布局差异大 | 至少包含 Personal/Standard/Premium 三列或清晰的套餐区域 |
| A03 | MDX 公众号文章：Routines 功能介绍需要官方文档佐证 | `https://code.claude.com/docs/en/routines` | `text=Automate work with routines` 主文档区域 | 公众号 `1200x675` | 文档页左侧导航和右侧目录容易抢画面 | 主标题和正文说明可读，侧边栏不能超过画面一半 |
| A04 | MDX 公众号文章：解释 Routines 触发方式，需要截“schedule/API/GitHub trigger”区域 | `https://code.claude.com/docs/en/routines` | `text=Configure triggers` 附近 | 公众号 `1200x675` | 目标在长页面中部，需要滚动后裁剪 | 画面能看出触发方式上下文，不只截到一个小标题 |
| A05 | MDX 公众号文章：展示真实开源项目协作基底 | `https://github.com/MiaoDX/roboharness/issues` | issue 列表区域 | 公众号 `1200x675` | GitHub 顶栏、筛选栏、空列表/少量列表状态都可能出现 | 截图能表达“GitHub issue 工作台”，列表/筛选区可读 |
| A06 | MDX 公众号文章：展示 PR 自动化结果 | `https://github.com/MiaoDX/roboharness/pulls` | PR 列表区域 | 公众号 `1200x675` | GitHub 页面动态加载，登录态和未登录态布局不同 | 截图能表达“PR 列表/状态”，不被登录提示遮挡 |

## B 层：X/Twitter 单条内容

2026-05-08 实测：用无登录 Playwright 上下文打开 X 公开账号主页和 5 条真实单帖链接，单帖正文均可见且页面存在 `article`。但 X 会显示 `Don’t miss what’s happening`、`Log in`、`Sign up` 等登录/注册提示，截图工具需要优先裁剪 `article` 主体，避免把登录提示截成主画面。公开视频、敏感内容、删除/限流帖、回复串深处内容仍可能需要登录态兜底。

| ID | 真实需求来源 | URL / 入口 | 截图目标 | 建议尺寸 | 关键挑战 | 验收点 |
|----|--------------|------------|----------|----------|----------|--------|
| B01 | `assistant_zh/content/ai_daily/20260507_214157.md`：AI 日报引用 Sam Altman 单帖 | `https://x.com/sama/status/2050671161915371998` | 单条 post 的 `article` 区域 | 小红书 `1080x1440`；公众号 `1200x675` | 顶部登录提示和底部注册卡片会干扰画面 | 能看到作者、正文、时间/浏览量；登录提示不能成为主体 |
| B02 | `assistant_zh/content/ai_daily/20260507_211353.md`：AI 日报引用 Bindu Reddy 单帖 | `https://x.com/bindureddy/status/2051790195423605236` | 带外链/图片的单条 post | 小红书 `1080x1440`；公众号 `1200x675` | 单帖可能包含图片或外链卡片，截图高度不固定 | 正文和外链/图片占位至少出现其一，不能只截到顶部 banner |
| B03 | `assistant_zh/content/ai_daily/20260506_220449.md`：AI 日报引用 Ethan Mollick 单帖 | `https://x.com/emollick/status/2051530202941960551` | 带 quote post 的单条 post | 公众号 `1200x675` | quote post 会形成嵌套卡片，裁剪过紧会丢上下文 | 主帖正文和 quote 区域至少保留一部分 |
| B04 | `assistant_zh/content/ai_daily/20260507_213959.md`：AI 日报引用 Greg Brockman 单帖 | `https://x.com/gdb/status/2050194039077495089` | 技术短帖 + quote post | 公众号 `1200x675` | 短正文容易被过度放大或截成空白 | 作者、正文、quote 标题/摘要可读 |
| B05 | `assistant_zh/content/ai_daily/20260507_213959.md`：AI 日报引用 AK 转帖 | `https://x.com/_akhaliq/status/2050301770421727593` | repost/视频帖区域 | 小红书 `1080x1440` | 转帖、视频缩略图和正文布局复杂 | 能看出这是转帖/视频相关内容；视频区域不应被裁掉 |

## C 层：网页原生图片直取

当网页里目标内容本来就是图片，工具应优先提取图片 URL 并下载原图，而不是对页面区域截图。直取优先级：`img.currentSrc` / `srcset` 最大图 > `picture source` > `meta[property="og:image"]` / `twitter:image` > CSS `background-image`。下载后可按平台预设做可选裁剪/缩放，并在 metadata 里记录 `method=download`、`source_image_url`、原始像素、最终像素。

| ID | 真实需求来源 | URL / 入口 | 获取目标 | 建议尺寸 | 关键挑战 | 验收点 |
|----|--------------|------------|----------|----------|----------|--------|
| C01 | `assistant_zh/content/ai_daily/20260507_211353.md`：X 单帖里有配图，文章引用时更适合取原图 | `https://x.com/bindureddy/status/2051790195423605236` | 帖内 `pbs.twimg.com/media/...` 图片 | 原图保存；可选小红书 `1080x1440` | X 未登录页面仍能看到 `article` 和图片，但图片 URL 带尺寸参数 | 下载到原始或最大可用尺寸，不带 X 页面 UI 和登录提示 |
| C02 | WXP 个人分享：Tailscale 文章需要产品视觉素材 | `https://tailscale.com/pricing` | `og:image` 或页面内产品插图 | 公众号 `1200x675` | 页面同时有 og 图、SVG 插图、定价表；需要区分“配图素材”和“表格截图” | 当目标是配图，输出图片文件；当目标是价格表，仍走截图 |
| C03 | 内容调研：网页 hero/封面图作为文章配图 | 任一文章页 URL | `og:image` / `twitter:image` | 公众号 `1200x675`；小红书 `1080x1440` | 有些 og 图是默认站点封面，不一定代表正文内容 | metadata 标记图片来源；若图片尺寸太小或明显是 logo，提示质量不足 |
| C04 | 内容调研：页面中的图表/产品截图图片 | 任一网页 URL + `--image-alt` 或 `--image-near-text` | 与 alt 文本或附近文字匹配的图片 | 原图保存；可选裁剪 | 多张图片时需要选择正确图片 | 下载的图片应与指定 alt/附近文字匹配，而不是第一张装饰图 |

## D 层：视频时间戳截图

首轮不要求实现。这里先把真实需求和验收标准写清楚，后续可复用 `video_research/` 的下载、关键帧、时间戳能力。

| ID | 真实需求来源 | 入口 | 截图目标 | 建议尺寸 | 关键挑战 | 验收点 |
|----|--------------|------|----------|----------|----------|--------|
| D01 | 内容调研：文章需要引用视频里某一帧作为证据 | YouTube / Bilibili / X 视频 URL + `HH:MM:SS` | 指定时间戳画面 | 公众号 `1200x675`；小红书 `1080x1440` | 需要下载或播放器 seek；不同平台反爬和播放器控件差异大 | 输出帧与时间戳误差小于 1 秒；不带播放器控件 |
| D02 | 视频讲解类文章：截“演示某功能”的关键画面 | 视频 URL + 一段文字描述 | 自动定位接近描述的时间点并截图 | 公众号 `1200x675` | 需要字幕/转写辅助，不属于首轮截图工具范围 | 后续实现时必须输出时间戳和截图依据 |
| D03 | X 视频帖：截取帖内视频画面 | X post URL + 时间戳 | post 内视频某一帧 | 小红书 `1080x1440` | X 视频通常更依赖登录态和媒体 API | 暂缓实现；如果页面截图能满足，就先截播放器区域 |

## E 层：本地真实产物

| ID | 真实需求来源 | 本地路径 | 截图目标 | 建议尺寸 | 关键挑战 | 验收点 |
|----|--------------|----------|----------|----------|----------|--------|
| E01 | MDX 公众号文章已用配图 | `/Volumes/ExtSSD2601/AI_Assistant/assistant_mdx/longform_write/blog_output/images/01-routines-calendar.png` | 已有人审可用的 Routines 日历截图 | 原图基准；公众号 `1200x675` | 用作视觉基准，比较新工具裁剪是否更接近已采用素材 | 新截图主体信息密度不低于现有图片 |
| E02 | MDX 公众号文章已用配图 | `/Volumes/ExtSSD2601/AI_Assistant/assistant_mdx/longform_write/blog_output/images/07-pr-list.png` | PR 列表截图 | 原图基准；公众号 `1200x675` | GitHub 页面可能变化，用本地图固定回归 | 新截图不应比基准更空、更糊或裁掉关键列 |
| E03 | MDX 公众号文章已用配图 | `/Volumes/ExtSSD2601/AI_Assistant/assistant_mdx/longform_write/blog_output/images/09-architecture-overview.png` | 架构图 | 公众号 `1200x675` | 图片本身已经是文章素材，适合测试“已有图片裁成平台尺寸” | 不应裁掉标题、节点或连线 |

## 首轮优化必须覆盖

首轮先跑并优化这些用例：

1. `A01`：OpenAI 定价页，小红书竖图和公众号横图各一张。
2. `A03`：Claude Code Routines 文档，验证文档页主体裁剪。
3. `A05`：GitHub issue 列表，验证工具类页面裁剪。
4. `B01`：X 单条公开 post，验证未登录也能裁到 `article` 主体。
5. `B03`：X quote post，验证嵌套卡片和登录提示处理。
6. `C01`：X 单帖原生图片直取，验证“网页里已有图片时优先下载原图”。

暂不纳入首轮：小红书发布页、发布后验收、ChatGPT 交互截图、视频时间戳截图。

## 需要工具支持的能力清单

- `--preset xhs-card|xhs-portrait|xhs-square|gzh-wide|raw`
- `--target WIDTHxHEIGHT`
- `--selector`、`--text`、`--xpath`、`--nth`
- `--auto-main`：无 selector 时自动选择主内容区
- `--actions actions.json`：打开页面后的点击、输入、等待、滚动
- `--download-image`：从网页提取并下载目标图片，而不是截图页面
- `--image-alt`、`--image-near-text`、`--image-index`：图片选择条件
- `--metadata out.json`
- `--keep-raw`：保留原始截图，便于调试裁剪失败
- `--compare baseline.png`：和本地基准图做尺寸/空白/主体区域对比
