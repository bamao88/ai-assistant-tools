# 视频号博主与作品列表抓取

本 reference 覆盖微信视频号公开账号搜索、博主作品列表批量抓取、单条作品详情和评论列表。底层 engine：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py
```

## 能力边界

- 支持搜索视频号账号、按 `username` 翻页拉取公开作品列表、获取作品详情、获取评论列表。
- 默认复用视频号发布 engine 的账号 slot 和 `storage_state.json`，不复制 cookie，不改发布账号配置。
- 当前固定账号约定沿用视频号发布：`aipm` 是默认账号和测试号；`zhanghe` 是真实账号。抓取/调研默认用 `--account aipm`。
- 只读取公开可访问数据；私密、删除、登录失效、页面 API 不可用、限流都直接结构化报错。
- 单条 URL 的字幕、封面、关键帧仍走 `references/video.md`。这里处理“视频号博主/账号作品列表”。

## 重要实现说明

参考仓库 `nobiyou/wx_channel` 的能力不是公开 HTTP API，而是通过已打开的视频号页面调用页面内 `WXU` API：

- 搜索账号：`WXU.API2.finderSearch`
- 账号作品列表：`WXU.API.finderUserPage`
- 作品详情：`WXU.API.finderGetCommentDetail`
- 评论列表：`WXU.API.finderGetCommentList`

本 engine 有两个后端：

- 默认 Playwright 后端：用本仓库现有 `storage_state.json` 打开页面，在页面上下文调用 `WXU`。
- `--api-base` 后端：如果本机另有 `wx_channel` 兼容 HTTP 服务在跑，例如 `http://127.0.0.1:2026`，直接调用它的 `/api/channels/...` 接口。

## 账号与登录态

先看账号：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py \
  accounts
```

默认使用测试号：

```bash
--account aipm
```

如果 `diagnose` 显示平台页跳到 `login_url=true`，说明视频号助手登录态不可用；`auth_summary.has_finder_login_token=false` / `has_finder_uin=false` 只是辅助信号，不要单独当成最终判断。需要先走视频号发布 reference 里的扫码登录：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/scripts/cli.py \
  --account aipm login --timeout 180
```

扫码后再运行下面的 `diagnose`。不要手工打印、复制或提交 cookie/token。

## 诊断

默认页面后端：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm \
  diagnose
```

如果要使用参考仓库兼容的本地 HTTP 服务：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py \
  --api-base http://127.0.0.1:2026 \
  diagnose
```

常见状态：

- `status=ready`：可以继续抓取。
- `status=api_unavailable` 且 `login_url=true`：storage state 被视频号判为未登录。
- `status=api_unavailable` 且 `support_update_url=true`：页面被判定为浏览器不兼容；默认 engine 已使用 Windows 微信 UA，若仍出现需要检查平台前端变化。
- `status=local_api_unavailable`：`--api-base` 指向的本地服务没启动或端口不对。

## 搜索账号

必须先搜索出 `username`，不要用昵称直接拉作品列表：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm \
  search-accounts \
  --keyword "账号昵称或关键词"
```

返回里重点保留：

- `contacts[].username`
- `contacts[].nickname`
- `contacts[].avatar`

## 批量拉取作品列表

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm \
  list-feeds \
  --username "<contacts[].username>" \
  --max-pages 3 \
  --delay 0.8
```

输出目录默认：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/var/data/wechat-channels-fetch/<username>_<timestamp>/
```

关键文件：

- `feeds.json`：标准化作品数组。
- `feeds.jsonl`：一行一条，便于后续分析。
- `raw_pages/page_*.json`：原始响应。
- `summary.json`：运行摘要。

标准化字段包括：

- `object_id`
- `nonce_id`
- `description`
- `media_type`
- `nickname`
- `publish_time`
- `like_count`
- `fav_count`
- `comment_count`
- `forward_count`
- `cover_url`
- `media_url`

如果用户只要最近 N 条，加 `--limit N`。如果用户要求全量，逐步增加 `--max-pages`，每页间隔保留 `--delay 0.8` 或更高。

## 作品详情

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm \
  get-feed-detail \
  --object-id "<object_id>" \
  --nonce-id "<nonce_id>"
```

## 评论列表

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm \
  list-comments \
  --object-id "<object_id>" \
  --nonce-id "<nonce_id>"
```

## 本地 HTTP API 后端

当本机已经启动 `wx_channel` 兼容服务时，所有命令都可以加：

```bash
--api-base http://127.0.0.1:2026
```

示例：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechat-channels-fetch/scripts/cli.py \
  --api-base http://127.0.0.1:2026 \
  list-feeds \
  --username "<contacts[].username>" \
  --max-pages 3
```

这个模式依赖外部服务已经完成页面注入和 WebSocket 连接；本 CLI 只负责调用 HTTP API、标准化结果和落盘。
