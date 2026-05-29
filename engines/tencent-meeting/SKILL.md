---
name: tencent-meeting-downloader
description: |
  批量下载腾讯会议分享链接里的逐字稿和录制视频。支持直接输入分享链接，或输入包含腾讯会议链接的 Markdown/文本文件。
  逐字稿默认优先走公开 API，失败时回退到已登录且可见的 Google Chrome 页面抽取；视频走稳定的分享下载接口。
  当用户提到腾讯会议、会议纪要、逐字稿、转录、录屏、视频下载、批量导出、分享链接抓取时触发。
---

# Tencent Meeting Downloader

用这个 skill 处理腾讯会议分享链接里的逐字稿和录制视频导出。

## 入口

优先使用统一入口：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py transcripts ...
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py videos ...
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py both ...
```

底层稳定脚本在：

- `scripts/fetch_tencent_meeting_transcripts_stable.py`
- `scripts/download_tencent_meeting_videos_stable.py`

## 输入

- 直接传一个或多个腾讯会议分享链接。
- 或传一个本地文件路径；脚本会从 Markdown/文本里提取 `https://meeting.tencent.com/crm/...` 和 `https://meeting.tencent.com/cw/...` 链接。
- 若只想跑部分短链，用 `--codes` 指定短码子集。

## 工作流

1. 逐字稿默认用 `transcripts --strategy auto`。
2. `auto` 会先调用公开 transcript API；失败后再回退到已登录的可见 `Google Chrome` 会话。
3. 视频下载用 `videos`，直接走稳定下载接口，不依赖页面按钮点击。
4. 批量视频下载前先确认目标磁盘空间够用，大批量场景优先写到外置盘。
5. 每次运行后检查输出目录里的 `summary.json`、`manifest.json`、`manifest.csv`、`failures.json` 和 `diagnostics/`。
6. `summary.json` 里的 `entry_summaries` 会按短链聚合给出 `status` 和 `summary`，不再只报模糊的 partial failure。
7. `failures.json` 里的每条失败会附带 `reason`、`error_code` 和 `failure_type`，方便区分“链接不支持”“创建者关闭转写”“无访问权限”等原因。
8. 下载文件默认命名为 `YYYYMMDD_会议主题`。若同一链接下存在多段录制或同时下载多种视频流，才附加最小必要后缀，例如 `录制2`、`主视频`、`共享屏幕`、`发言人视角`。

## 前提

- 逐字稿回退模式依赖 macOS 上可见的 `Google Chrome`，并且 Chrome 里已经登录了有权限的腾讯会议账号。
- 视频下载不依赖 Chrome 登录态，但分享页本身必须能暴露下载链路。
- 默认使用 `python3` 和 `requests`。

## 输出目录约定

`--output-dir` 优先级：
1. 用户明确指定的路径
2. 用户未指定时，从当前对话上下文推断项目目录，在其下新建 `tencent_output/`
3. 视频等大文件，若推断出外置盘可用，优先写到外置盘

## 常用命令

下载逐字稿：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py transcripts \
  --output-dir <输出目录，用户未指定时从项目上下文推断> \
  /abs/path/links.md
```

下载视频：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py videos \
  --output-dir <输出目录，用户未指定时从项目上下文推断> \
  /abs/path/links.md
```

只下载主视频是默认行为，也可以显式指定：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py videos \
  --output-dir <输出目录> \
  --video-type video_main \
  /abs/path/links.md
```

下载指定视频流：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py videos \
  --output-dir <输出目录> \
  --video-type video_stream_1 \
  --video-type video_stream_2 \
  /abs/path/links.md
```

下载全部视频流：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py videos \
  --output-dir <输出目录> \
  --video-type all \
  /abs/path/links.md
```

逐字稿和视频一起跑：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py both \
  --output-dir <输出目录> \
  /abs/path/links.md
```

只跑部分短链：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py transcripts \
  --output-dir <输出目录> \
  --codes N1EWObL37a 2kOB18GP56 \
  /abs/path/links.md
```

视频额外下载音频：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py videos \
  --output-dir <输出目录> \
  --include-audio \
  /abs/path/links.md
```

## 常见失败含义

- `30017`：创建者关闭了转写查看和下载。
- `91001`：录制转写导出失败。
- `30002`：公开链路拿不到逐字稿。
- `40339`：共享未开启纪要或纪要不可见。
- `暂无访问权限`：当前登录态没有页面访问权限。

遇到失败时，不要只看终端输出；优先打开本次输出目录里的 `diagnostics/*.json` 和 `failures.json`。
