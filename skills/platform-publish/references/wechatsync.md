# WechatSync 本地发布助手

使用全局 `wechatsync` CLI 把 Markdown/HTML 文章同步到多个内容平台。这个 skill 是本地 AI_Assistant 的发布操作层，只包装 Wechatsync CLI 的安全工作流；不要修改 Wechatsync 的 CLI、MCP Server、Chrome 扩展或平台适配器源码。

## 边界

- 默认使用全局 `wechatsync` 命令，不要调用本仓库 `packages/cli/dist/index.js`。
- 当前 Wechatsync 发布只服务 `assistant_zh`。`assistant_docfit` 暂无 Wechatsync 发布白名单，后续配置前不得发布。
- 发布白名单和期望账号在 `/Volumes/ExtSSD2601/AI_Assistant/tools/wechatsync/config/project-platforms.json`。
- `weixin` 和 `xiaohongshu` 即使显示已登录，也禁止通过这个 skill 发布；它们分别走专用公众号发布 skill 和 `xiaohongshu-skills`。
- 不保存、不打印、不回显 `WECHATSYNC_TOKEN`、Cookie、账号密码或平台后台敏感信息。
- 所有同步动作都先运行 `--dry-run`。只有用户明确确认后，才运行真实同步命令。
- Wechatsync 默认同步为草稿；仍然把它视为外部发布动作，因为它会使用浏览器登录态向平台写入草稿。
- 不自动正式发布、提交审核、群发或点击平台后台的最终发布按钮。
- 如果发现 Wechatsync 工具异常，按 `/Volumes/ExtSSD2601/AI_Assistant/tools/feedback/` 规则写反馈文件，不直接改工具源码。

## 前置条件

执行任何同步或提取前，依次检查：

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
douyin, jianshu, toutiao
```

明确禁止通过这个 skill 发布的平台：

```text
weixin, xiaohongshu
```

用户用中文平台名时，转换为对应 ID。例如：知乎 `zhihu`，掘金 `juejin`，头条 `toutiao`。如果用户要求发布到公众号或小红书，停止 Wechatsync 流程并路由到对应专用 skill。

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
3. 执行前置检查，尤其是 `wechatsync platforms --auth`。
4. 用 `/Volumes/ExtSSD2601/AI_Assistant/tools/wechatsync/config/project-platforms.json` 校验平台白名单和账号名。
5. 确认目标平台已登录；未登录的平台不要同步。
6. 先运行 dry-run：

```bash
wechatsync sync /absolute/path/article.md -p zhihu,juejin --dry-run
```

7. 向用户报告将同步的平台、文章文件、标题来源、账号校验和 dry-run 结果。
8. 用户明确确认后，再运行真实同步：

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
