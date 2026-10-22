# 视频纯抓取原语（video fetch primitives）

**重要边界：** 单条音视频的字幕、逐字稿、关键帧和素材研究以 `video-content` 为主入口。本 reference 保留 URL 视频的**纯抓取**（元数据 / 字幕 / 关键帧），供多平台采集或显式调用 `platform-fetch` 的既有流程复用；根据已有逐字稿起标题或写平台配文交给 `content-package-create`。用户要求“把这个 YouTube 视频写成文章”等完整文章时，由 `source-longform-writing` 主责，按需要调用视频取材，拿到逐字稿或研究包后返回原写作任务继续，不能只交素材就结束。

支持 yt-dlp 覆盖的 1000+ 站点（YouTube / Bilibili / 小红书 / 抖音 / Twitter / 视频号 / Vimeo 等）。

## 前置

1. `ffmpeg` 已装：`which ffmpeg || brew install ffmpeg`
2. 工具依赖：`cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research && uv sync`
3. Whisper 兜底（首次自动下模型到 `~/.cache/huggingface/`，默认 `base` 约 150MB）

## CLI 路径

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research/scripts/cli.py <子命令>
```

所有子命令输出 JSON（`ensure_ascii=False`）。Exit code：`0=成功 / 1=前置失败 / 2=运行错误`。

## 三个抓取原语

### info — 元数据 / 封面

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research/scripts/cli.py info \
  --url "<URL>"
```

### transcript — 字幕 / 转写

```bash
# 默认：先试字幕（人工 > 自动），再试 Whisper
python scripts/cli.py transcript --url "<URL>" --lang zh,en

# 字幕烂时强制 Whisper
python scripts/cli.py transcript --url "<URL>" --force-whisper --whisper-model small
```

返回字段里的 `source`：

| 值 | 含义 |
|-----|------|
| `manual` | 人工字幕（最准） |
| `auto` | 平台自动字幕（有错漏） |
| `whisper` | 本地 Whisper 转写（兜底） |
| `none` | 都失败了 |

### keyframes — 关键帧（3 种模式三选一）

```bash
# 模式 1：指定时间戳（最常用）
python scripts/cli.py keyframes --url "<URL>" --at "00:30,01:45,03:20"

# 模式 2：每 N 秒一帧
python scripts/cli.py keyframes --url "<URL>" --interval 60

# 模式 3：场景切换自动检测
python scripts/cli.py keyframes --url "<URL>" --scene-change --scene-threshold 0.3
```

时间戳格式：`SS` / `MM:SS` / `HH:MM:SS`。

## 输出布局

落盘位置 `data/{platform}_{video_id}/`：

- `info.json` — 元数据
- `thumbnail.jpg` — 封面
- `transcript.txt` / `transcript.srt` — 字幕
- `keyframes/HH-MM-SS.png` — 关键帧

## 失败处理

| 场景 | 处理 |
|------|------|
| 未装 ffmpeg | Exit 1，提示 `brew install ffmpeg` |
| 未装 faster-whisper | 字幕抓不到时降级返回 `source: none`，提示运行 `uv sync` |
| 地域限制 / 需要登录 | yt-dlp 报错，指引用户导出 cookies 到 `~/.config/yt-dlp/cookies.txt` |
| 视频超长（几小时） | Whisper 转写会很慢，建议 `--whisper-model tiny` 或不用 Whisper |
| keyframes 失败 | 低分辨率格式抓不到，回退用 `--interval` 避开 scene-change |

## 注意

- **时间戳文件名用 `-` 不用 `:`**（macOS/Windows 兼容）：`00-03-15.png`
- **不要用这个下载视频原文件**；要原文件直接 `yt-dlp <URL>`
- **长视频（>30min）优先用字幕**，Whisper CPU 跑 large 模型会很慢
- **小红书 / 抖音视频**有时需要登录态，失败时提示用户导 cookies
