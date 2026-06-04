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

## 网络分流前置步骤（强制）

为避免 Tailscale exit node 或系统代理导致抖音发布走海外/代理出口（**异地 IP 登录/发布会触发抖音风控**），任何 `douyin` 子命令（check / login / upload-video / upload-note）执行前，必须先刷新本地分流路由：

```bash
tailscale set --exit-node-allow-lan-access=true 2>/dev/null || true
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply
```

无 TTY 遇到 `sudo: a password is required` 时，改用管理员授权窗口执行同一脚本：

```bash
osascript -e 'do shell script "tailscale set --exit-node-allow-lan-access=true 2>/dev/null || true; /Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply" with administrator privileges'
```

⚠️ **上传腿的局限**：抖音视频上传走 `*.douyinvod.com` 等动态 CDN，host 路由穷举不到，分流脚本只能保证 creator 中心/登录/风控腿走本地。要让**整条发布都走本地**，最稳的是发布时段关掉海外 exit node：`tailscale set --exit-node=`（发完再按需恢复）。如分流或验证失败，**停止发布并报告**，不要带着海外出口发。

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

**发视频：**
```bash
"$SAU" douyin upload-video --account <account_name> \
  --file /abs/path/video.mp4 \
  --title "标题" \
  --desc "简介" \
  --tags 运动,训练 \
  --thumbnail-landscape /abs/cover-4x3.png \
  --thumbnail-portrait  /abs/cover-3x4.png \
  --schedule "2026-06-10 21:30"     # 可选：定时发布
```
- 必填：`--account --file --title`。其余可选。
- 封面：`--thumbnail-landscape`（4:3 横版）、`--thumbnail-portrait`（3:4 竖版）；`--thumbnail` 兼容旧参数=3:4 竖版。
- 带货可选：`--product-link --product-title`。
- `--schedule` 格式 `YYYY-MM-DD HH:MM`，传了即切换为抖音定时发布。

**发图文（笔记）：**
```bash
"$SAU" douyin upload-note --account <account_name> \
  --images /abs/1.png /abs/2.png \
  --title "图文标题" --note "图文内容" --tags 图文,测试
```
- 抖音图文最多 35 张，不支持 GIF。

## 运行时开关

- `--headed` 有头（看页面 / 人工核对）、`--headless` 无头（默认）、`--debug` 失败时留更多调试信息。
- 抖音默认无头；要可视核对再显式 `--headed`。

## ⚠️ 安全

- 上传走真实创作者中心。发布前把 标题/简介/标签/封面/视频 与用户确认，**用户确认后再执行**。
- 若 CLI 停在草稿/待发布页，按返回提示汇报，需要用户手动点最终发布的不替用户点。
- check 失效 / 报 cookie missing or expired → 让用户重跑 `douyin login`。

## 素材准备（可选）

- 字幕/封面/关键帧 → `video-content`；剪辑 → engines/video-slicer；封面 → video-cover kit；开头优化 → `dbs-hook`。
