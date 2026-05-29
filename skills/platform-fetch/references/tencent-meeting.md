# 腾讯会议（tencent-meeting）

适用：批量下载腾讯会议分享链接里的逐字稿和录制视频。

## 入口

统一入口：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py transcripts ...
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py videos ...
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py both ...
```

底层稳定脚本（一般不直接调）：

- `scripts/fetch_tencent_meeting_transcripts_stable.py`
- `scripts/download_tencent_meeting_videos_stable.py`

## 输入

- 直接传一个或多个腾讯会议分享链接
- 或传一个本地文件路径；脚本会从 Markdown/文本里提取 `https://meeting.tencent.com/crm/...` 和 `https://meeting.tencent.com/cw/...`
- 只想跑部分短链：`--codes <短码1> <短码2>`

## 工作流

1. 逐字稿默认 `transcripts --strategy auto`
2. `auto` 会先调公开 transcript API；失败后回退到已登录的可见 `Google Chrome` 会话
3. 视频下载 `videos`，走稳定下载接口，不依赖页面按钮点击
4. 批量视频前先确认目标磁盘空间，大批量优先写到外置盘
5. 每次运行后检查输出目录里的 `summary.json` / `manifest.json` / `manifest.csv` / `failures.json` / `diagnostics/`
6. `summary.json` 的 `entry_summaries` 按短链聚合 `status` 和 `summary`，不再只给模糊的 partial failure
7. `failures.json` 每条失败附 `reason`、`error_code`、`failure_type`，区分"链接不支持""创建者关闭转写""无访问权限"
8. 下载文件默认命名 `YYYYMMDD_会议主题`。同一链接下多段录制 / 多种视频流时，才加最小后缀（如 `录制2`、`主视频`、`共享屏幕`、`发言人视角`）

## 前提

- 逐字稿回退模式依赖 macOS 上可见的 `Google Chrome`，且 Chrome 已登录有权限的腾讯会议账号
- 视频下载不依赖 Chrome 登录态，但分享页本身必须能暴露下载链路
- 默认 `python3` 和 `requests`

## 输出目录

`--output-dir` 优先级：

1. 用户明确指定的路径
2. 用户没指定 → 从当前对话上下文推断项目目录，在其下新建 `tencent_output/`
3. 视频等大文件，推断出外置盘可用时优先写外置盘

## 常用命令

下载逐字稿：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py transcripts \
  --output-dir <输出目录> \
  /abs/path/links.md
```

下载视频（默认只下主视频）：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py videos \
  --output-dir <输出目录> \
  /abs/path/links.md
```

显式指定视频流：

```bash
# 主视频
--video-type video_main

# 多条流
--video-type video_stream_1 --video-type video_stream_2

# 全部流
--video-type all
```

逐字稿 + 视频一起跑：

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

视频附带音频：

```bash
--include-audio
```

## 常见失败码

| 码 | 含义 |
|-----|------|
| `30017` | 创建者关闭了转写查看和下载 |
| `91001` | 录制转写导出失败 |
| `30002` | 公开链路拿不到逐字稿 |
| `40339` | 共享未开启纪要 / 纪要不可见 |
| `暂无访问权限` | 当前登录态没有页面访问权限 |

遇到失败别只看终端，先打开本次输出目录里的 `diagnostics/*.json` 和 `failures.json`。
