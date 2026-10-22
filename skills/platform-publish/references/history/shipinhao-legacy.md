> 历史归档（2026-10-22）：以下为迁移前原文，仅供追溯。旧 CLI、独立配置、Cookie 恢复和远端流程均未启用，不可照抄执行。当前执行入口为上一级同名平台 reference 与 `_local-chrome.md`。原文中的相对路径按迁移前位置理解。

# 视频号发布

本 reference 覆盖“微信视频号 / 视频号助手”的视频自动化发布。底层实现来自本仓库本地 engine：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py
```

先按 [账号、浏览器与登录恢复](_accounts-and-sessions.md) 选用本次环境。正式优先复用已登录浏览器，掉线后可用同账号Cookie恢复到选定正式profile；无合适凭据或平台要求认证时扫码。以下CLI管理其自身slot内profile，不是任意日常Chrome的接管器；登录成功不自动同步到用户指定的其它浏览器。

## 能力边界

- 当前只支持 **视频**：`.mp4`、`.mov`、`.avi`、`.mkv`、`.m4v`、`.webm`、`.flv`、`.wmv`。
- 支持扫码登录、登录态检查、上传视频、保存草稿、正式发表、定时发表。
- 暂不支持视频号图文。`dreammis/social-auto-upload` 上游的 `TencentNote` 仍是未完成骨架，因此本 skill 不宣称图文可用。
- 默认只保存草稿；只有用户明确要求“正式发布 / 发出去 / 定时发布”并确认后，才加 `--publish`。
- 如果用户要求“上传完成后停在页面 / 不保存草稿 / 不要后续动作”，必须使用 `--fill-only --hold-open -1`，只上传并填表，不点击“保存草稿”或“发表”。
- 真实账号上传时默认加 `--headed`，让用户能在前台看到 Chrome 窗口、上传进度和平台提示；只有用户明确要求后台执行时才省略。

## 首次初始化

如果 `.venv/bin/python` 不存在，先运行：

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish
uv sync --python 3.11
```

如果 patchright 找不到本机 Chrome，提示用户安装 Google Chrome；本 engine 默认使用本机 Chrome channel，不自动下载浏览器。

## 本机旧引擎网络前置（按所选环境使用）

先按总入口选择发布机。已授权独立发布机承担上传时，不修改控制机路由；以下命令只适用于确实选用本机CLI及其 `local-egress` 路径的任务，不能套用于远程既有浏览器。该CLI可能自动调整本机路由，使用前核对所在电脑：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh shipinhao apply
```

如果总入口已锁定 `current-egress`（用户明确要求“不走本地流量 / 跳过本地分流 / 直接走当前网络”），跳过本节，不运行 `publish-network-preflight`；执行 `upload-video` 或 `publish-item` 时在命令前加 `PLATFORM_PUBLISH_NETWORK_MODE=current-egress`。也可以同时传 `--skip-route-bypass`。两者都会让 engine 不再自动刷新或校验本地路由。

## 账号选择

先按本次任务和项目账号表明确目标；仅需解析该引擎slot时运行：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  list-accounts
```

将已确认目标匹配到slot/profile，不按数量自动覆盖内容归属。缺少可靠匹配才询问；命令显式带 `--account <slot>`。

历史 `aipm` / `zhanghe` 属于对应业务项目，不是全局默认。测试必须有明确测试账号、测试Cookie和独立profile；项目未登记的视频号不能拿其它项目slot补位。

`count: 0` 不代表没有登录态。默认账号的登录态在：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/var/state/tencent-video-publish/accounts/default/storage_state.json
```

视频号账号目录里可能存在历史遗留的 Chrome profile：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/var/state/tencent-video-publish/accounts/default/chrome-profile/
```

发布、登录检查和扫码登录优先使用同账号目录下的 `chrome-profile/`；`storage_state.json` 只作为备份、手动 Cookie 导入候选和旧凭证迁移回退。`list-accounts` 的 `logged_state_file_exists` / `profile_dir_exists` 只表示文件或目录是否存在；是否真正有效仍以日常 `check-login` 的 profile 结果或发布命令内置校验为准。

**禁止为了“强制重新扫码”移动、删除或重命名 `storage_state.json` 或 `chrome-profile/`。** 如果检查返回 `profile_cookie_invalid`，先排除检查器/环境问题，再按共用顺序尝试可用同账号Cookie恢复到选定正式profile；需要扫码时使用同窗口 `--login-if-needed`，或仅维护登录态时 `login --timeout 180`。这两个命令只适用于所选环境就是该slot的情况。当前 engine 会在写入前保留 `storage_state.json.bak_*`，并在 `storage_state.json` 缺失或 JSON 损坏时自动尝试恢复最新有效备份。

添加命名账号：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  add-account --slot wxp --description "WXP 视频号"
```

## 登录流程

日常已登录原页无需额外启动检查器。若本次明确选择引擎slot环境，可在 `upload-video` / `publish-item` 使用 `--login-if-needed` 保留同窗口扫码分支；现有引擎未自动编排共用Cookie恢复顺序，需在调用前选好恢复方式。不能用该命令替换用户已指定的日常Chrome。

需要单独确认登录态时，可选检查登录：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  --headed \
  check-login
```

视频号登录态以账号独立 `chrome-profile/` 为准。独立登录检查默认使用 `--headed check-login`，避免 headless 预检把仍可用的 profile 误判为失效后触发扫码；只有明确要做后台校验、且已验证当前环境 headless 可稳定复用 profile 时，才省略 `--headed`。

日常发布前**不要**给 `check-login` 加 `--storage-fallback`。这个参数只用于慢速凭证诊断或旧 `storage_state.json` 迁移；它会尝试 JSON 凭证和最近备份，可能显著变慢，也不能替代 `chrome-profile` 主登录态。`profile_cookie_invalid` 只说明这次所检查会话未通过；不是必须扫码的结论。按共用规则确认掉线，再尝试可用Cookie或人工认证。

如果只想验证“发布页能否打开”，使用发布页探针：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  --headed \
  open-publish-page \
  --screenshot-out /tmp/shipinhao-publish-page.png
```

探针只打开视频号发表入口并截图，不上传视频、不保存草稿、不发表，也不执行上传阶段的本地网络分流。

同一个视频号账号 slot 的 `check-login` / `login` / `upload-video` / `publish-item` 必须串行执行，不能并发。它们共用同一个 `chrome-profile/`，并发会触发 Chrome `SingletonLock`，表现为 `profile_check_failed`、`Target page, context or browser has been closed` 或 “正在现有的浏览器会话中打开”。遇到这种情况不要扫码，等当前浏览器命令结束后重跑。

如果只想刷新登录态而不发布，执行扫码登录：

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

登录命令使用同一账号的可见 `chrome-profile/` 打开视频号登录页；不要改成 headless，视频号 QR 登录回调在 headless 下不稳定。页面确认已登录后会保存 profile，并导出 `storage_state.json` 备份。登录后可再运行 `--headed check-login` 验证；如果下一次发布仍未登录，改用发布命令的 `--login-if-needed` 单会话扫码路径。

如二维码超时，命令会刷新并再次打印新的 `QRCODE_PATH`。

Cookie恢复候选需匹配目标视频号，不把值写进日志或文档。下列导入仅写引擎slot，只有它就是选定正式持久环境时才能用来完成正式浏览器恢复；否则需要在实际正式浏览器操作，不把此命令当作已接管。写入受保护临时文件后导入指定账号slot；导入会先写候选 storage state，并默认打开发布页验证。只有验证已登录时，候选凭证才会替换正式 `storage_state.json`，并尝试迁移到账号 `chrome-profile/`；验证失败时正式凭证和 profile 保持不变：

```bash
umask 077
printf '%s' "$COOKIE_HEADER" > /tmp/shipinhao.cookies
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  --account zhanghe \
  import-cookies --cookie-file /tmp/shipinhao.cookies
rm -f /tmp/shipinhao.cookies
```

导入命令只输出 cookie 名称、数量和登录验证结果，不回显 cookie 值。若返回 `logged_in: false` 或非零退出，需区分凭据无效与连接/验证错误；不能继续上传或声称恢复成功。失败不会将候选提升为正式凭据；确认恢复不适用时在选定正式环境扫码或按用户要求补充凭据。`--no-verify` 只保存候选凭证文件，不会提升为正式凭证，也不会写入 profile。

## 保存草稿（默认推荐）

输入需求：

- 视频绝对路径
- 标题
- 简介/正文（可选）
- 话题标签（可选，不要带 `#` 也可以）
- 封面图（可选）。**张和口播竖屏视频**的封面优先使用内容目录里的 `cover.png`。视频号 engine 已支持通过 `--thumbnail` 等官方封面生成完成后上传自定义封面；不要再要求把封面烧进视频首帧。

## 内容目录一键发布（推荐）

当内容来自 `assistant_zh/content/.../items/<content_id>/` 目录时，优先使用 `publish-item`，不要手动从 `publish_copy.md` 拼 `upload-video` 参数。

`publish-item` 会自动读取：

- `publish_<account>.md` 或 `publish_copy.md` 里带 ✅ 的标题候选。✅ 可在行首，也可在标题末尾；如果没有唯一 ✅ 标题会失败退出，避免误选。
- `## 正文` 作为视频号描述正文。
- `视频号精简（5 个）` 作为视频号标签；如果缺失，才退回中文关键词前 5 个。
- 同目录 `成片.mp4` 作为视频。
- 同目录 `cover.png` 作为封面。

定时发布示例：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  --account zhanghe \
  --headed \
  publish-item \
  --login-if-needed \
  --item-dir "/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/content/zh_main/items/ZHC20260613_evc04_001" \
  --publish \
  --schedule-at "2026-07-04 20:20" \
  --upload-timeout 360 \
  --cover-timeout 90
```

只解析不打开浏览器：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  --account zhanghe \
  publish-item \
  --item-dir "/abs/item_dir" \
  --dry-run
```

测试号填表停住：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  --account aipm \
  --headed \
  publish-item \
  --login-if-needed \
  --item-dir "/abs/item_dir" \
  --fill-only \
  --hold-open -1
```

命令：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  --headed \
  upload-video \
  --login-if-needed \
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

用于测试自动化发布链路，或按用户要求“上传完成后停在页面，不保存草稿/不发表”：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  [--account <slot>] \
  --headed \
  upload-video \
  --login-if-needed \
  --file "/abs/path/video.mp4" \
  --title "流程测试请勿发布" \
  --desc "这是自动化流程测试内容，请勿发布。" \
  --tags "流程测试" "请勿发布" \
  --fill-only \
  --hold-open -1
```

`--fill-only` 会完成上传、填标题/正文/标签、等待上传完成，然后停在发布页；返回 `action: filled_ready_to_submit` 和 `submitted: false`，表示没有点击任何提交按钮。

`--hold-open <seconds>` 只在 `--fill-only` 下用于保留可见浏览器窗口，方便人工观察页面状态；等待结束后浏览器会关闭。`--hold-open -1` 表示一直停在页面，直到用户关窗口或 Agent 中断命令。

## 封面卡在“生成中”

视频号会先自动生成默认封面；在 `vertical-cover-wrap` 显示“生成中”时，官方页面会禁用手动上传封面的入口。传入 `--thumbnail` 后，CLI 默认最多等待 `--cover-timeout 60` 秒。

- `--fill-only`：封面超时只返回 `thumbnail_warning`，不会点击保存草稿/发表，适合测试并人工观察页面。
- 保存草稿/正式发表：封面超时会失败退出，避免自定义封面没传上却继续提交。
- 需要快速验证卡点时，可传 `--cover-timeout 10`；需要等更久时调大这个值。

2026-05-28 已知修复：

- 视频号官方封面抽帧依赖 blob worker + `rhino_video.wasm`，engine 的浏览器 context 已启用 `bypass_csp=True`，避免官方 worker 被 CSP 拦截。
- 视频上传阶段会走独立上传/CDN 域名，不等同于页面域名；若上传卡在 0% 或明显变慢，优先查看 CLI 输出的上传状态和浏览器网络诊断。
- 上传完成和封面可编辑不是同一状态；engine 会继续等待“取消上传 / 文件上传中，请等待完成后再编辑 / 视频处理中，请等待完成后再编辑”消失，再点击封面编辑入口。

## 原创声明

2026-09-23：`upload-video` / `publish-item` 默认不声明原创，原创内容需显式 `--declare-original`；转载内容使用 `--no-declare-original`。历史示例未带此参数时不再自动勾选，不能把旧行为用于转载账号。

视频号原创声明是两步，不是单点 checkbox：

1. 页面表单里点击“声明原创”（旧版可能显示为“视频为原创”）。
2. 在“原创权益”弹窗里勾选“我已阅读并同意《原创声明须知》和《使用条款》”，再点击弹窗里的“声明原创”按钮。

原创入口必须放在视频上传处理、封面、定时等内容都填完之后再找。过早处理时页面可能还没渲染入口，或者 checkbox 仍是 disabled。

## 正式发表

正式发表是外部公开动作，必须先让用户确认标题、简介、标签、视频、封面。确认后才运行：

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
--login-if-needed
--skip-route-bypass
```

- `--short-title`：视频号短标题，不传时自动从标题截取。
- `--category`：声明原创时的"原创类型"下拉选项（如 "知识"/"生活"）。**2026-09-23 起，默认不声明原创**；确认素材为原创并获授权时显式加 `--declare-original`，转载使用 `--no-declare-original`。`--category` 只指定原创类型，本身不会开启声明。
- `--headed`：打开可见 Chrome 窗口。真实账号草稿上传默认使用，便于用户观察上传进度；无人值守测试才考虑省略。
- `--upload-timeout`：等待视频上传完成的秒数；测试小视频可设为 `90`，正式视频保留默认或调大。
- `--login-if-needed`：发布命令内置扫码兜底。profile 失效时在同一个发布浏览器里展示二维码，扫码成功后继续上传；真实账号日常发布默认加。
- `--skip-route-bypass`：跳过本地分流路由刷新和校验，直接使用当前网络出口；只有用户明确要求 current-egress 时才加。

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
| `profile_cookie_invalid` | 确认实际profile与创作页状态，掉线后按共用规则选Cookie原位恢复或扫码；仅当该slot是所选正式环境才用其登录命令 |
| `profile_check_failed` | Chrome/profile 校验本身失败，不要扫码；先看 `profile_error`。如果包含 `SingletonLock` / `正在现有的浏览器会话中打开`，说明同账号命令并发或上个浏览器未退出，等待结束后串行重跑 |
| `logged_in: false` | 核对slot/正式profile及实际页面，排除无头检查误报；确认掉线后按共用恢复顺序处理 |
| `storage state does not exist` | 直接运行 `check-login`，engine 会自动尝试恢复最新有效备份；仍失败再登录 |
| `not logged in or cookie invalid` | 保留现有发布页，恢复选定正式环境并核对账号/字段；不直接重跑上传命令 |
| 上传超时或页面选择器失效 | 用 `--headed` 重试；仍失败则按工具反馈机制写入 `tools/feedback/` |
| 用户要求视频号图文 | 明确告知当前不支持，不要调用视频流程替代 |

## 2026-09-23 登录与回执修复

- 页面网络错误、入口找不到、浏览器错误不再一律当成登录过期；只有实际登录页/登录控件才返回未登录并触发扫码。`profile_check_failed` 应先查错误，不能让用户反复扫码。
- 点击发表或保存草稿后未等到稿件列表回执，返回 `status: submission_result_unknown`、`submission_attempted: true`、`submitted: null`、`retry_safe: false`。先到后台查重，禁止重复点击。回到稿件列表也只证明提交流程回执，不证明到点公开。
- 本轮验证是 21 项 logic/contract（含 mock），猫猫电视机真实账号尚未绑定和 replay。历史成功发布记录仍有效；长期登录复用未验收。
- 当前每条命令的 finally 仍会关闭其浏览器；异常保留原页、跨条复用会话仍是缺口。登录独立命令不注入 shim，而发布路径仍注入轻量 shim，需真实对照检查 QR 行为，不能猜测已修复。
