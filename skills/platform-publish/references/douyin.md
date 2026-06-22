# 抖音视频/图文发布（reference）

把**本地视频或图文发布到抖音**。底层 = `vendor/social-auto-upload` 的 `sau douyin` 子命令（patchright 浏览器自动化 + cookie 登录态）。

> ⚠️ 这份 reference 管 **抖音视频 / 抖音图文（笔记）**。注意与 `references/wechatsync.md` 里"抖音图文同步"区分：wechatsync 走的是文章同步链路；本 reference 走的是抖音创作者中心的真实上传。优先用本 reference 发抖音视频。

## 引擎路径与前置

```bash
ENGINE=/Volumes/ExtSSD2601/AI_Assistant/tools/vendor/social-auto-upload
SAU="$ENGINE/.venv/bin/sau"
```

- 账号 cookie 存在 `tools/var/state/social-auto-upload/cookies/douyin_<account>.json`（已软链，凭证只放 var/）。
- 浏览器用 patchright Chromium（安装时已 `patchright install chromium`）。
- 账号白名单见 `vendor/wechatsync/config/project-platforms.json` 的 `assistant_zh.expectedAccounts.douyin`（当前：`张和`）。账号标识约定：`张和` = 本项目（assistant_zh，负责张和全部自媒体）名下的抖音号，cookie 落 `douyin_张和.json`。**只发这个账号**，发别的先与用户确认。

## 当前状态（2026-06-22）

抖音发布工具入口存在，已补上人工最终确认需要的填表模式；账号态还需要恢复：

- `sau douyin check --account 张和` 返回 `invalid`。
- 当前 cookies 目录没有 `douyin_张和.json`。
- 最近日志里的登录尝试停在二维码登录阶段，最终报 `Target page, context or browser has been closed`。
- `upload-video` / `upload-note` 已支持 `--fill-only`：上传素材、填写标题/正文/标签/封面/定时时间后停在发布页，不点击最终“发布”。

恢复流程：先在测试号或低风险账号上完成 `login` + `check`，再用 `--fill-only --hold-seconds <秒数>` 跑通上传、封面、标签和定时设置；复测通过前，不要把抖音作为真实账号的自动最终发布通路。

## 网络分流前置步骤（强制）

为避免 Tailscale exit node 或系统代理导致抖音发布走海外/代理出口（异地 IP 登录/发布会触发抖音风控，上传链路也会变慢或失败），任何 `douyin` 子命令（check / login / upload-video / upload-note）执行前，必须先刷新本地分流路由：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh douyin apply
```

无 TTY 遇到 `sudo: a password is required` 时，改用管理员授权窗口执行同一脚本：

```bash
osascript -e 'do shell script "/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh douyin apply" with administrator privileges'
```

如果上传时发现新的字节/CDN 域名（例如 DevTools/日志里出现未覆盖的 `douyinvod` 或 `vod` 上传域），先把解析到的域名/IP 补进 `route-bypass` 并重新 `apply`，再继续测试；不要把“动态 CDN 不好穷举”当作可以走海外出口的理由。

⚠️ **绝不要用 `tailscale set --exit-node=` 关全局出口** —— 用户本地 Claude Code / Codex 靠该 exit node 访问 LLM API，关掉会断开发任务。确需补上传字节链路时，只走 route 方案，不动 exit node。

如分流 apply 或出口验证失败，**停止发布并报告**，不要带着海外出口发（登录腿必须本地）。

## 命令

**登录（建议在本地真实终端跑，可加 `--headed` 看页面）：**
```bash
"$SAU" douyin login --account <account_name> --headed
```
- 登录过程可能生成临时二维码图片；这类图片就是给用户扫的，**优先直接把本地图片展示/发给用户**，不要只给路径。

**检查登录态（只读）：**
```bash
"$SAU" douyin check --account <account_name>
```
上传前必须先跑 `check`。如果不是有效登录态，先 `login`，不要直接上传。

**发视频：**
```bash
"$SAU" douyin upload-video --account <account_name> \
  --file /abs/path/video.mp4 \
  --title "标题" \
  --desc "简介" \
  --tags 运动,训练 \
  --thumbnail-landscape /abs/cover-4x3.png \
  --thumbnail-portrait  /abs/cover-3x4.png \
  --fill-only --hold-seconds 0 \
  --schedule "2026-06-10 21:30"     # 可选：定时发布
```
- 必填：`--account --file --title`。其余可选。
- 封面：`--thumbnail-landscape`（4:3 横版）、`--thumbnail-portrait`（3:4 竖版）；`--thumbnail` 兼容旧参数=3:4 竖版。
- 带货可选：`--product-link --product-title`。
- `--schedule` 格式 `YYYY-MM-DD HH:MM`，传了即切换为抖音定时发布。
- 默认 `manual-submit` 时必须传 `--fill-only`；`--hold-seconds 0` 表示浏览器保持打开直到终端 Ctrl-C，`--hold-seconds 60` 表示停 60 秒后关闭，便于自动化复测。

**发图文（笔记）：**
```bash
"$SAU" douyin upload-note --account <account_name> \
  --images /abs/1.png /abs/2.png \
  --title "图文标题" --note "图文内容" --tags 图文,测试 \
  --fill-only --hold-seconds 0
```
- 抖音图文最多 35 张，不支持 GIF。

## 运行时开关

- `--headed` 有头（看页面 / 人工核对）、`--headless` 无头（默认）、`--debug` 失败时留更多调试信息。
- `--fill-only` 会强制使用有头浏览器并停在最终发布前；未给 `--hold-seconds` 时默认一直等，适合人工检查。
- 抖音默认无头；要可视核对再显式 `--headed`。

## ⚠️ 安全

- 上传走真实创作者中心。发布前把 标题/简介/标签/封面/视频 与用户确认。
- 默认 `manual-submit` 场景下必须带 `--fill-only`，让页面停在最终发布前。
- 只有用户明确授权机器点击最终“发布/定时发布”（`agent-submit`）时，才允许不带 `--fill-only` 执行上传命令。
- check 失效 / 报 cookie missing or expired → 让用户重跑 `douyin login`。

## 素材准备（可选）

- 字幕/封面/关键帧 → `video-content`；剪辑 → engines/video-slicer；封面 → video-cover kit；开头优化 → `dbs-hook`。
