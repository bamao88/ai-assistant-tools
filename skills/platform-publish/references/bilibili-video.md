# B站视频投稿（reference）

把**本地视频文件投稿到哔哩哔哩**。底层 = `vendor/social-auto-upload` 的 `sau bilibili` 子命令，它再封装开源 `biliup`（B站投稿事实标准，自动下载二进制）。

> ⚠️ 这份 reference 只管 **B站视频投稿**。B站**专栏文章**走 `references/wechatsync.md`（完全不同的 API）。

## 引擎路径与前置

```bash
ENGINE=/Volumes/ExtSSD2601/AI_Assistant/tools/vendor/social-auto-upload
SAU="$ENGINE/.venv/bin/sau"      # CLI 入口；等价于 .venv/bin/python -m sau_cli
```

- 账号凭证存在 `tools/var/state/social-auto-upload/cookies/bilibili_<account>.json`（已软链，凭证只放 var/）。
- 首次执行会自动从 GitHub Release 下载 `biliup` 二进制到 `~/.social-auto-upload/tools/biliup/`（需联网 + 能访问 github）。
- 账号白名单见 `vendor/wechatsync/config/project-platforms.json` 的 `assistant_zh.expectedAccounts.bilibili`（当前：`张和`）。**只发这个账号**，发别的先与用户确认。
- 账号标识约定：`张和` = 本项目（assistant_zh，负责张和全部自媒体）名下的 B站 号，cookie 落 `bilibili_张和.json`。其 B站 真实昵称 **和哥专业讲AI**（UID `36184382`）。注意：不要与小红书里的 `缪东旭_个人`(MiaoDX) 混淆——那是另一个人，旧白名单曾误填 `MiaoDX`，已纠正。

## 命令

**登录（必须在真实交互终端里跑——agent 不能代扫码）：**
```bash
"$SAU" bilibili login --account 张和
```
- biliup 会在终端显示二维码；若终端显示不全，打开当前目录的 `qrcode.png` 扫码。
- 非交互环境（agent 自动跑）会直接返回提示让用户自己在本地终端执行。**遇到未登录时，让用户手动跑这一行**，不要尝试自动化扫码。

**检查登录态（只读）：**
```bash
"$SAU" bilibili check --account 张和     # 底层 biliup renew；返回有效/失效
```

**投稿视频：**
```bash
"$SAU" bilibili upload-video --account 张和 \
  --file /abs/path/video.mp4 \
  --title "标题" \
  --desc "简介" \
  --tid 122 \
  --tags AI,工具 \
  --schedule "2026-06-10 21:30"     # 可选：定时发布
```
- 必填：`--account --file --title --desc --tid`。
- `--tid` = B站分区 id（必填）。`--tags` 逗号分隔。`--schedule` 格式 `YYYY-MM-DD HH:MM`，映射到 biliup `--dtime` 定时发布。
- 参数映射：`biliup -u <cookie> upload <file> --title --desc --tid [--tag a,b] [--dtime <epoch>]`。

## ⚠️ 安全：B站没有"纯草稿"中间态

- biliup `upload` **执行即投稿**（进审核队列），不像视频号能停在草稿。
- 因此 **upload-video 是对外发布动作**：必须先把 标题/简介/分区/标签/视频文件 与用户逐项确认，**用户明确说"投"再执行**。
- 想留缓冲就用 `--schedule` 设一个未来时间（定时投稿），给用户留撤回/改动窗口。
- 投稿成功后把 biliup 返回里的稿件信息/链接（aid/bvid）原样汇报给用户。

## 分区 tid 速查（务必与用户确认，勿臆测）

常用（科技/知识向，贴合 AI 内容）：
- `122` 科技 → 野生技术协会
- `201` 知识 → 科学科普
- `188` 数码 → 手机平板 / 科技数码
- `21`  生活 → 日常

完整分区以 B站投稿页或 `bilibili-API-collect` 的分区表为准。拿不准就问用户内容属于哪个分区，不要随便填一个 tid。

## 失败兜底

- 报 `account file is missing` / check 返回失效 → 登录态掉了，让用户重跑 `bilibili login`。
- biliup 下载失败（github 限流/断网）→ 重试；已下载过会复用本地版本。
- 投稿被风控/分区不符 → 把 biliup 的 stderr 原文给用户，按提示改 tid 或内容。

## 素材准备（可选，发布前）

- 字幕/封面/关键帧 → `video-content`（engines/video-research）
- 剪辑切片 → engines/video-slicer
- 封面图 → video-cover kit
- 开头优化 → `dbs-hook`
