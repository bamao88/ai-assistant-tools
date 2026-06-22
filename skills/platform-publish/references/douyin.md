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

抖音发布工具入口已恢复，支持人工最终确认需要的填表模式：

- 测试号 `测试号_抖音` 已通过真实 fill-only 复测：上传测试视频、填写标题/简介/话题、上传横版和竖版封面、选择自主声明，最终停在发布页，未点击“发布”。
- `upload-video` / `upload-note` 支持 `--fill-only`：上传素材、填写标题/正文/标签/封面/定时时间后停在发布页，不点击最终“发布”。
- 当前测试阶段只允许 `--fill-only`；禁止点击最终“发布/定时发布”。即使命令支持自动提交，也必须等用户之后重新明确授权。
- 新版创作者中心必须先点左侧“高清发布”菜单里的“发布视频/发布图文”；底层 CLI 已内置该入口，不再直接等旧的 `div[class^='container'] input`。
- 视频发布页表单渲染可能在文件解析后才出现，当前 CLI 最长等待 120s；不要把这段等待误判为卡死。

真实账号使用前仍必须按总入口契约确认账号和最终提交权限。若 `张和` 等真实账号 cookie 失效，先完成 `login` + `check`，再执行上传。

## 网络分流前置步骤（强制）

为避免 Tailscale exit node 或系统代理导致抖音发布走海外/代理出口（异地 IP 登录/发布会触发抖音风控，上传链路也会变慢或失败），任何 `douyin` 子命令（check / login / upload-video / upload-note）执行前，必须先刷新本地分流路由：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh douyin apply
```

无 TTY 时脚本会自动使用 macOS 管理员授权窗口。若用户取消授权或 `apply` 后 `status` 仍显示 `destination=default` / `interface=utun*`，停止发布，重新处理网络前置门。

抖音 DNS 会快速轮换边缘 IP，preflight 已配置常见 `/24` 网段兜底。若上传时仍发现新的字节/CDN 域名或新网段（例如 DevTools/日志里出现未覆盖的 `douyinvod` 或 `vod` 上传域），先把解析到的域名/IP/网段补进 `route-bypass` 并重新 `apply`，再继续测试；不要把“动态 CDN 不好穷举”当作可以走海外出口的理由。

⚠️ **绝不要用 `tailscale set --exit-node=` 关全局出口** —— 用户本地 Claude Code / Codex 靠该 exit node 访问 LLM API，关掉会断开发任务。确需补上传字节链路时，只走 route 方案，不动 exit node。

如分流 apply 或出口验证失败，**停止发布并报告**，不要带着海外出口发（登录腿必须本地）。

快速校验：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh douyin status \
  | awk '/route decisions for route target IPv4:/{flag=1;next} flag && /destination=default|interface=utun|gateway=-/{print}'
```

期望无输出；有输出表示仍有目标 IP 没走本地网络。

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
- 只有用户明确授权机器点击最终“发布/定时发布”（`agent-submit`）时，才允许不带 `--fill-only` 执行上传命令；底层 CLI 还要求同一条命令显式设置 `SAU_DOUYIN_ALLOW_SUBMIT=1`。
- 测试阶段、测试号 `测试号_抖音`、或用户说“不要点击发布”时，绝不设置 `SAU_DOUYIN_ALLOW_SUBMIT=1`。
- check 失效 / 报 cookie missing or expired → 让用户重跑 `douyin login`。

## 素材准备（可选）

- 字幕/封面/关键帧 → `video-content`；剪辑 → engines/video-slicer；封面 → video-cover kit；开头优化 → `dbs-hook`。
