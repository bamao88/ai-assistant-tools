# 文章多平台草稿路由

把 Markdown/HTML 文章同步到多个内容平台的草稿箱。当前策略是：优先使用本地无插件直传引擎 `platform-draft-direct`；直传不可用且用户接受浏览器依赖时，才回退到 Wechatsync CLI 或人工浏览器草稿流程。

**当前默认可发集合（2026-06-10 实测）**：`zhihu,juejin,csdn,baijiahao,segmentfault`。今日头条 `toutiao` 当前可通过 Chrome 编辑器自动保存草稿，但不是无插件直传。

## 边界

- 默认使用 `platform-draft-direct`；只有回退到 Wechatsync 时才使用全局 `wechatsync` 命令，不要调用本仓库 `packages/cli/dist/index.js`。
- 当前 Wechatsync 发布只服务 `assistant_zh`。`assistant_docfit` 暂无 Wechatsync 发布白名单，后续配置前不得发布。
- 发布白名单和期望账号在 `/Volumes/ExtSSD2601/AI_Assistant/tools/vendor/wechatsync/config/project-platforms.json`。
- `weixin` 和 `xiaohongshu` 即使显示已登录，也禁止通过这个 skill 发布；它们分别走专用公众号发布 skill 和 `xiaohongshu-skills`。
- 不保存、不打印、不回显 `WECHATSYNC_TOKEN`、Cookie、账号密码或平台后台敏感信息。
- 所有同步动作都先运行 `--dry-run`。只有用户明确确认后，才运行真实同步命令。
- Wechatsync 默认同步为草稿；仍然把它视为外部发布动作，因为它会使用浏览器登录态向平台写入草稿。
- 不自动正式发布、提交审核、群发或点击平台后台的最终发布按钮。
- 如果发现 Wechatsync 工具异常，按 `/Volumes/ExtSSD2601/AI_Assistant/tools/feedback/` 规则写反馈文件，不直接改工具源码。

## Wechatsync 前置条件

只有回退到 Wechatsync CLI 或执行浏览器页面提取时，才依次检查：

```bash
command -v wechatsync
wechatsync --help
if [ -n "${WECHATSYNC_TOKEN:-}" ]; then echo "WECHATSYNC_TOKEN=set"; else echo "WECHATSYNC_TOKEN=missing"; fi
wechatsync platforms --auth
```

如果 `wechatsync` 不存在，提示用户安装：

```bash
npm install -g @wechatsync/cli
```

不要在未获用户明确同意时替用户安装全局 npm 包。

如果 token 缺失，提示用户在 Chrome 扩展设置中启用 MCP/连接能力并设置 token，然后在当前 shell 中配置：

```bash
export WECHATSYNC_TOKEN="用户自己设置的 token"
```

不要要求用户把 token 发给 Agent；只需要用户在本地 shell 环境里设置。

如果扩展未连接，提示用户确认：

- Chrome/Edge 已安装并启用 Wechatsync 扩展。
- 扩展设置中已启用连接能力。
- 扩展 token 与 `WECHATSYNC_TOKEN` 一致。
- 浏览器中已登录目标平台账号。
- 如使用远程桥接，`SYNC_WS_PORT` 和 WebSocket 地址一致。

## 平台 ID

当前允许 `assistant_zh` 通过这个 skill 使用的平台：

```text
zhihu, juejin, bilibili, baijiahao, csdn, sohu, cnblogs,
51cto, segmentfault, oschina, douyin, jianshu, toutiao
```

明确禁止通过这个 skill 发布的平台：

```text
weixin, xiaohongshu
```

用户用中文平台名时，转换为对应 ID。例如：知乎 `zhihu`，掘金 `juejin`，头条 `toutiao`。如果用户要求发布到公众号或小红书，停止 Wechatsync 流程并路由到对应专用 skill。

## 当前实测状态

这张表记录 `assistant_zh` 在 2026-06-10 的真实发布结果。它优先级高于“适配器存在”的理论能力。

| 平台 | 当前结论 | 默认动作 | 注意事项 |
|------|----------|----------|----------|
| 知乎 `zhihu` | 可成功写入草稿 | 用 `platform-draft-direct` | 图片多时使用更长超时 |
| 掘金 `juejin` | 可成功写入草稿 | 用 `platform-draft-direct` | 账号必须已绑定手机号 |
| CSDN `csdn` | 可成功写入草稿 | 用 `platform-draft-direct` | 图片多时使用更长超时 |
| 百家号 `baijiahao` | 可成功写入草稿 | 用 `platform-draft-direct` | 大尺寸长图可能触发空响应；先压缩再重试 |
| 思否 `segmentfault` | 可成功写入草稿 | 用 `platform-draft-direct` | 图片多时使用更长超时 |
| 今日头条 `toutiao` | 可通过 Chrome 编辑器自动保存草稿 | 浏览器草稿流程 | 标题限制 2-30 字；当前没有直传 adapter |
| 博客园 `cnblogs` | 当前账号不可用 | 默认跳过 | 报错为用户尚未开通博客 |
| 搜狐号 `sohu` | 当前账号不可用 | 默认跳过 | 报错为用户不通过 |
| 51CTO `51cto` | 当前直传 Cookie 未登录 | 默认跳过 | 需要重新导入有效 Cookie 后再验证 |
| 开源中国 `oschina` | 当前直传 Cookie 未登录 | 默认跳过 | 需要重新导入有效 Cookie 后再验证 |
| B站专栏 `bilibili` | 当前直传 Cookie 未登录 | 默认跳过 | 需要重新导入有效 Cookie 后再验证 |
| 简书 `jianshu` | 无直传 adapter | 默认跳过 | 只能等 Wechatsync/浏览器链路恢复后再评估 |
| 抖音图文 `douyin` | 不走文章直传 | 默认跳过 | 抖音视频/图文走 `references/douyin.md` |

默认批量草稿命令只包含：

```text
zhihu,juejin,csdn,baijiahao,segmentfault
```

如果用户明确要求其他平台，先说明当前状态，再单平台验证，不要把失败平台混入默认批量发布。

## 无插件直传

目标平台只包含当前直传可用平台时，优先走 `platform-draft-direct`：

```text
zhihu, juejin, csdn, baijiahao, segmentfault
```

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/platform-draft-direct
PLATFORMS=zhihu,juejin,csdn,baijiahao,segmentfault
node src/cli.js auth --platform "$PLATFORMS"
node src/cli.js sync /absolute/path/article.md --platform "$PLATFORMS" --title "标题" --dry-run
node src/cli.js sync /absolute/path/article.md --platform "$PLATFORMS" --title "标题"
```

图片较多或平台图床慢时，把超时调大：

```bash
PLATFORM_DRAFT_DIRECT_TIMEOUT_MS=180000 \
node src/cli.js sync /absolute/path/article.md --platform "$PLATFORMS" --title "标题"
```

适配器存在但当前不要默认批量发布的平台：`51cto,cnblogs,oschina,bilibili,sohu`。只有用户明确要求并且 `auth` 验证通过后，才单独尝试。

首次或 Cookie 过期时导入浏览器导出的 Cookie JSON；也支持原始 Cookie header 文本文件：

```bash
node src/cli.js import-cookies --platform zhihu --file /absolute/path/cookies.json
node src/cli.js import-cookies --platform baijiahao --file /absolute/path/baijiahao-cookie.txt
node src/cli.js import-cookies --platform baijiahao --file - < /absolute/path/baijiahao-cookie.txt
```

直传引擎约束：

- 只写草稿箱，不正式发布。
- Cookie 存在 `var/credentials/platform-draft-direct/<platform>.json`，不打印 Cookie。
- `auth` 会读取 `vendor/wechatsync/config/project-platforms.json` 校验 `assistant_zh` 期望账号。
- 期望账号可配置为字符串，或 `{ "username": "...", "userId": "..." }`；配置 `userId` 后优先按稳定账号 ID 校验。
- `--dry-run` 不访问平台 API；只展示文件、标题、平台和图片数量。
- 今日头条不在直传首批，当前走下面的浏览器草稿流程。
- 百家号遇到图片上传空响应时，优先检查是否为超大长图；压缩该图并生成临时 Markdown 后重试。

## 今日头条草稿流程

今日头条当前没有可维护的无插件直传 adapter。公开 Wechatsync 仓库也没有可直接复用的头条 adapter 源码，且头条 Web 接口可能依赖浏览器上下文生成的 `msToken` / `a_bogus` 等参数。

高优先级发布时使用 Chrome 编辑器：

1. 打开 `https://mp.toutiao.com/profile_v4/graphic/publish`，确认登录的是 `assistant_zh` 对应账号。
2. 今日头条标题限制 2-30 字；原始标题超过限制时，先压缩标题并告知用户。
3. 把 Markdown 转成富文本 HTML，图片用可上传/可粘贴的本地或 data URI 形式注入编辑器。
4. 粘贴到正文编辑区后等待自动保存。
5. 验证页面出现 `草稿已保存`，并保留 Chrome 标签给用户人工检查。

不要声称头条已经通过 API 直传成功；当前结果只能叫“浏览器编辑器草稿已自动保存”。

## 项目账号规则

同一个 Chrome Profile 里，每个平台通常只有一个当前登录账号。后续如果在同一 Chrome Profile 登录同平台的另一个账号，Wechatsync 看到的账号会随之切换；这不会影响其他平台，但会影响该平台的发布归属。

发布前必须用 `wechatsync platforms --auth` 实时校验账号：

- 目标项目必须是 `assistant_zh`。
- 请求平台必须在 `allowedPlatforms` 中。
- 当前登录账号必须匹配 `expectedAccounts` 中的账号名。
- 对于 `douyin` 这类暂未返回账号名的平台，只允许在用户明确确认当前浏览器账号无误后继续 dry-run。
- 任一平台账号不匹配、未登录或不在白名单内，都停止发布。

## 同步流程

1. 确认输入文件是本地 Markdown、HTML 或文本文件，优先使用绝对路径。
2. 确认当前项目是 `assistant_zh`；若是 `assistant_docfit` 或未知项目，停止并要求先配置白名单。
3. 将目标平台分组：默认直传平台、今日头条浏览器草稿、其他待验证平台。
4. 默认直传平台先运行 `platform-draft-direct auth` 和 `--dry-run`。
5. `auth` 通过后再真实写入草稿；图片多时使用 `PLATFORM_DRAFT_DIRECT_TIMEOUT_MS=180000`。
6. 今日头条按“今日头条草稿流程”单独处理。
7. 其他待验证平台不要混入批量命令；先向用户说明当前状态，再单平台验证。

只有回退到 Wechatsync 时，才执行 Wechatsync 前置检查，尤其是 `wechatsync platforms --auth`，并用 `/Volumes/ExtSSD2601/AI_Assistant/tools/vendor/wechatsync/config/project-platforms.json` 校验平台白名单和账号名。

Wechatsync dry-run 示例：

```bash
wechatsync sync /absolute/path/article.md -p zhihu,juejin --dry-run
```

向用户报告将同步的平台、文章文件、标题来源、账号校验和 dry-run 结果。用户明确确认后，再运行真实同步：

```bash
wechatsync sync /absolute/path/article.md -p zhihu,juejin
```

9. 返回每个平台的结果、草稿链接或错误信息，并提醒用户到平台后台人工检查后再正式发布。

标题和封面：

```bash
wechatsync sync /absolute/path/article.md -p juejin -t "文章标题" --dry-run
wechatsync sync /absolute/path/article.md -p juejin --cover /absolute/path/cover.png --dry-run
```

图片说明：

- Markdown/HTML 中的本地图片会由 Wechatsync 处理并上传到目标平台图床。
- 同步前确保图片路径有效，优先使用相对文章文件可解析的路径或绝对路径。
- 图片上传意味着图片内容会进入目标平台 CDN，执行前需要用户接受这一点。

## 登录状态和提取

检查平台：

```bash
wechatsync platforms
wechatsync platforms --auth
wechatsync auth zhihu
wechatsync auth --refresh
```

从当前浏览器页面提取文章：

```bash
wechatsync extract -o /absolute/path/article.md
```

提取依赖浏览器当前页面。若结果不符合预期，提示用户切换到正确页面后重试。

## 失败处理

| 情况 | 处理 |
|------|------|
| `command -v wechatsync` 为空 | 提示安装全局 `@wechatsync/cli`，不要直接调用本地 clone 的 dist |
| `WECHATSYNC_TOKEN=missing` | 提示用户在扩展里设置 token 并在 shell 环境变量中配置，不要让用户把 token 发给 Agent |
| Chrome Extension 未连接 | 提示检查扩展启用、token 一致、连接开关、端口和浏览器状态 |
| 项目不是 `assistant_zh` | 停止发布，提示先为该项目配置平台白名单 |
| 平台是 `weixin` 或 `xiaohongshu` | 停止 Wechatsync 流程，路由到专用 skill |
| 平台不在白名单 | 停止发布，不要自动扩大平台范围 |
| 目标平台未登录 | 跳过该平台，提示用户先在浏览器中登录 |
| 当前账号名不匹配 | 停止发布，提示当前账号和期望账号 |
| dry-run 失败 | 停止，不执行真实同步；报告命令、平台和错误摘要 |
| 真实同步部分失败 | 报告成功和失败平台；不要自动重试大量平台，先让用户确认 |
| 博客园提示用户尚未开通博客 | 默认跳过，除非用户先开通博客 |
| 搜狐号提示用户不通过 | 默认跳过，除非用户处理账号资质 |
| 百家号图片上传空响应 | 先压缩大图/长图，再用临时 Markdown 单平台重试 |
| 今日头条直传缺 adapter | 使用 Chrome 编辑器草稿流程，不走直传批量命令 |
| 本地 Wechatsync 源码/构建异常 | 写入 `tools/feedback/`，不改 CLI/MCP/扩展源码 |

## 输出格式

回复用户时保持结构化：

```text
检查结果：
- CLI：可用/缺失
- Token：已设置/缺失
- 扩展：已连接/未连接
- 项目：assistant_zh
- 已登录平台：...
- 账号校验：通过/失败

Dry-run：
- 文件：/absolute/path/article.md
- 平台：zhihu,juejin
- 结果：...

下一步：
- 等待用户确认后执行草稿同步；或说明需要用户先处理的登录/连接问题。
```

真实同步后：

```text
同步结果：
- zhihu：成功，草稿链接 ...
- juejin：失败，原因 ...

后续：
- 请在各平台后台人工检查排版、封面、图片和链接后再正式发布。
```

## 示例请求

- "把这篇文章同步到掘金和知乎"
- "检查一下哪些平台已登录"
- "从当前浏览器页面提取文章到 Markdown"
- "把 `/path/article.md` 发布成知乎/头条草稿"
- "先 dry-run 看看这篇文章能不能同步到 CSDN"
