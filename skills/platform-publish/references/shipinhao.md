# 视频号发布

本 reference 覆盖“微信视频号 / 视频号助手”的视频自动化发布。底层实现来自本仓库本地 engine：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py
```

## 能力边界

- 当前只支持 **视频**：`.mp4`、`.mov`、`.avi`、`.mkv`、`.m4v`、`.webm`、`.flv`、`.wmv`。
- 支持扫码登录、登录态检查、上传视频、保存草稿、正式发表、定时发表。
- 暂不支持视频号图文。`dreammis/social-auto-upload` 上游的 `TencentNote` 仍是未完成骨架，因此本 skill 不宣称图文可用。
- 默认只保存草稿；只有用户明确要求“正式发布 / 发出去 / 定时发布”并确认后，才加 `--publish`。
- 测试发布流程时使用 `--fill-only`，只填到提交前，不点击“保存草稿”或“发表”。

## 首次初始化

如果 `.venv/bin/python` 不存在，先运行：

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish
uv sync --python 3.11
```

如果 patchright 找不到本机 Chrome，提示用户安装 Google Chrome；本 engine 默认使用本机 Chrome channel，不自动下载浏览器。

## 网络分流前置步骤（强制）

为避免 Tailscale exit node 或系统代理导致视频号发布走海外/代理出口，账号选定后、任何会访问视频号网页的 CLI 前，必须先刷新本地分流路由：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh shipinhao apply
```

如果在无 TTY 环境中遇到 `sudo: a password is required`，允许改用 macOS 管理员授权窗口执行同一脚本：

```bash
osascript -e 'do shell script "/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh shipinhao apply" with administrator privileges'
```

适用范围：

- `check-login` 前必须完成。
- `login` 前必须完成。
- `upload-video` 前必须完成，包括 `--fill-only`、保存草稿、正式发表、定时发表。

`apply` 每次都会重新解析视频号相关域名的当前 IPv4，并把新 IP 钉到本地网关。平台边缘 IP 变化时，重复运行本步骤；不要手工改 hosts 或 route。

**如果直接执行和管理员授权 fallback 都失败，立即停止视频号发布流程并报告错误；不得继续打开发布页、上传视频、保存草稿或发表。**

## 账号选择

每次触发后，先运行：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  list-accounts
```

根据返回 `count`：

- **0 个命名账号**：使用默认账号，后续命令不加 `--account`。
- **1 个命名账号**：告知用户“将使用账号 X 发布”，后续命令加 `--account <slot>`。
- **多个命名账号**：询问用户选择哪个账号，后续命令固定加 `--account <slot>`。

`count: 0` 不代表没有登录态。默认账号的登录态在：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/var/state/tencent-video-publish/accounts/default/storage_state.json
```

自 2026-05-28 起，视频号账号优先使用同目录下的真实 Chrome profile：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/var/state/tencent-video-publish/accounts/default/chrome-profile/
```

`storage_state.json` 仍会导出保存，用于兼容和备份；但发布、登录检查优先走 `chrome-profile`，这样不会每次只靠稀薄 cookie 冷启动。`list-accounts` 的 `default_account.logged_state_file_exists` / `profile_dir_exists` 只表示文件或 profile 是否存在；是否真正有效仍以 `check-login` 为准。

**禁止为了“强制重新扫码”移动、删除或重命名 `storage_state.json` 或 `chrome-profile/`。** 如果 `check-login` 返回 `cookie_invalid`，直接执行 `login --timeout 180`；CLI 会在扫码成功后更新 profile 并导出新的 storage state，不需要先清理旧文件。当前 engine 会在写入前保留 `storage_state.json.bak_*`，并在 `storage_state.json` 缺失或 JSON 损坏时自动尝试恢复最新有效备份。

添加命名账号：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  add-account --slot wxp --description "WXP 视频号"
```

## 登录流程

先检查登录：

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  check-login
```

如果返回 `logged_in: false`，执行扫码登录：

执行 `login` 前，也必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  login --timeout 180
```

登录命令会先打印一行：

```text
QRCODE_PATH=/absolute/path/to/tencent_video_login_YYYYMMDD_HHMMSS.png
```

Agent 必须把这张二维码图片展示给用户扫码，不能只转述路径。用户扫码并在手机微信确认后，命令会保存 storage state。

登录命令使用账号专属 `chrome-profile/` 打开视频号登录页。页面确认已登录后会保存 profile，并导出 `storage_state.json` 作为兼容备份。登录后可再运行 `check-login` 验证；如果返回 `status: cookie_invalid`，不要手动删除 cookie 或 profile，重新运行 `login --timeout 180` 即可。

如二维码超时，命令会刷新并再次打印新的 `QRCODE_PATH`。

## 保存草稿（默认推荐）

输入需求：

- 视频绝对路径
- 标题
- 简介/正文（可选）
- 话题标签（可选，不要带 `#` 也可以）
- 封面图（可选）。**张和口播竖屏视频**的封面用 `assets/video-cover/zhanghe`（底图池轮换 + 黑块黄字 Heavy 标题）生成，调用契约见该目录 `cover-kit.json` 的 `invoke`；仅限张和本人口播 9:16，适用边界见 `usage.do_not_use_for`。视频号要把生成的封面**烧进视频首帧**或经平台取帧，不能像抖音/小红书那样单独上传。

命令：

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  upload-video \
  --file "/abs/path/video.mp4" \
  --title "视频标题" \
  --desc "视频简介" \
  --tags "AI" "工具" \
  --thumbnail "/abs/path/cover.png" \
  --cover-timeout 60
```

不传 `--publish` 时，CLI 会点击“保存草稿”。完成后报告：

- 账号 slot
- 标题
- 视频路径
- 是否保存为草稿
- 当前页面 URL

## 只填表，不提交（测试流程）

用于测试自动化发布链路，停在最终提交前：

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  --headed \
  upload-video \
  --file "/abs/path/video.mp4" \
  --title "流程测试请勿发布" \
  --desc "这是自动化流程测试内容，请勿发布。" \
  --tags "流程测试" "请勿发布" \
  --fill-only \
  --hold-open 30
```

`--fill-only` 返回 `action: filled_ready_to_submit` 和 `submitted: false`，表示没有点击任何提交按钮。

`--hold-open <seconds>` 只在 `--fill-only` 下用于保留可见浏览器窗口，方便人工观察页面状态；等待结束后浏览器会关闭。

## 封面卡在“生成中”

视频号会先自动生成默认封面；在 `vertical-cover-wrap` 显示“生成中”时，官方页面会禁用手动上传封面的入口。传入 `--thumbnail` 后，CLI 默认最多等待 `--cover-timeout 60` 秒。

- `--fill-only`：封面超时只返回 `thumbnail_warning`，不会点击保存草稿/发表，适合测试并人工观察页面。
- 保存草稿/正式发表：封面超时会失败退出，避免自定义封面没传上却继续提交。
- 需要快速验证卡点时，可传 `--cover-timeout 10`；需要等更久时调大这个值。

2026-05-28 已知修复：

- 视频号官方封面抽帧依赖 blob worker + `rhino_video.wasm`，engine 的浏览器 context 已启用 `bypass_csp=True`，避免官方 worker 被 CSP 拦截。
- `aladin.wxqcloud.qq.com` 已加入 route-bypass，用于官方封面/视频处理相关 wasm 资源走本地网络。
- 上传完成和封面可编辑不是同一状态；engine 会继续等待“取消上传 / 文件上传中，请等待完成后再编辑 / 视频处理中，请等待完成后再编辑”消失，再点击封面编辑入口。

## 正式发表

正式发表是外部公开动作，必须先让用户确认标题、简介、标签、视频、封面。确认后才运行：

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  upload-video \
  --file "/abs/path/video.mp4" \
  --title "视频标题" \
  --desc "视频简介" \
  --tags "AI" "工具" \
  --thumbnail "/abs/path/cover.png" \
  --publish
```

## 定时发表

定时发表必须同时传 `--publish` 和 `--schedule-at`：

执行本步骤前，必须先完成“网络分流前置步骤”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  upload-video \
  --file "/abs/path/video.mp4" \
  --title "视频标题" \
  --desc "视频简介" \
  --tags "AI" "工具" \
  --schedule-at "2026-05-27 21:30" \
  --publish
```

约束：

- `--schedule-at` 使用本地时间。
- 定时时间必须晚于当前时间 2 小时以上。
- 未传 `--publish` 时，CLI 会拒绝 `--schedule-at`，避免误以为已定时。

## 可选字段

```bash
--short-title "短标题"
--category "生活"
--headed
--upload-timeout 300
```

- `--short-title`：视频号短标题，不传时自动从标题截取。
- `--category`：声明原创时的"原创类型"下拉选项（如 "知识"/"生活"）。**自 2026-05-28 起，upload-video 默认就会声明原创**（勾选"视频为原创" + 同意条款 + 点声明原创按钮）；不传 `--category` 时仍会声明原创，只是不选具体类型。
- `--headed`：打开可见 Chrome 窗口，适合调试页面变化；默认 headless。
- `--upload-timeout`：等待视频上传完成的秒数；测试小视频可设为 `90`，正式视频保留默认或调大。

## 视频号发布页字段映射（重要）

视频号发布页有 3 个独立输入区，对应 CLI 的 3 个固定字段：

| CLI 字段 | 视频号发布页位置 | 内部处理函数 |
|---------|----------------|--------------|
| `--title` | 短标题 input（独立字段，视频卡片显示） | `set_short_title()` |
| `--desc` | 描述/动态 editor（feed 详情正文） | `fill_title_tags_desc()` 内填正文部分 |
| `--tags` | 描述 editor 内的 `#xxx` hashtag（视频号自动识别） | `fill_title_tags_desc()` 内填标签部分 |

描述 editor 内填入顺序：**标题 → 换行 → 正文 → 换行 → 标签**（2026-05-28 终版）。短标题 input 由 `set_short_title()` 独立填；描述 editor 保留完整标题，feed 详情页两个都呈现。

## 失败处理

| 情况 | 处理 |
|------|------|
| `.venv/bin/python` 不存在 | 运行 `uv sync --python 3.11` |
| `No module named patchright` | 在 engine 目录运行 `uv sync --python 3.11` |
| Chrome 不可用 | 提示用户安装 Google Chrome，或用 `--headed` 观察 |
| `logged_in: false` | 先确认是否错误使用了 `--account <slot>`；默认账号已登录时不要加 `--account`。确认账号无误后执行 `login` 并展示二维码 |
| `storage state does not exist` | 直接运行 `check-login`，engine 会自动尝试恢复最新有效备份；仍失败再登录 |
| `not logged in or cookie invalid` | 重新登录 |
| 上传超时或页面选择器失效 | 用 `--headed` 重试；仍失败则按工具反馈机制写入 `tools/feedback/` |
| 用户要求视频号图文 | 明确告知当前不支持，不要调用视频流程替代 |
