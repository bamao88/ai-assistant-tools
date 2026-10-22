---
name: video-content
description: |
  视频内容处理技能。把本地或 URL 视频转成逐字稿、字幕、关键帧和素材研究报告。发布标题与封面文案交给 content-package-create。
  当用户说"本地视频转逐字稿"、"提取这几个视频的逐字稿"、"视频讲了什么"、"研究这个视频"、"整理视频素材"、"视频里讲 XX 那段"时触发。
  支持本地音视频文件，以及 yt-dlp 覆盖的 1000+ 站点（YouTube / Bilibili / 小红书 / 抖音 / Twitter / 视频号 / Vimeo 等）。
  完整文章写作（含 YouTube 视频转文章）由 source-longform-writing 负责；本 skill 提供所需素材后，返回原写作任务继续完成文章。
  本 skill 不处理：视频发布（→ Agent-Publish）、平台内容纯列表抓取（→ platform-fetch）、视频本体下载（→ yt-dlp 原生命令）。
---

# video-content — 视频内容处理

通用能力：账号定位、事实、素材与输出位置遵循当前项目；项目已有专属入口时优先沿其规则衔接。

本 skill 负责把视频内容素材化：从本地文件或 URL 产出可复用的逐字稿、字幕、关键帧、素材研究报告。

## 能力边界

| 需求 | 使用方式 |
|------|----------|
| 本地视频/音频转逐字稿 | `transcribe-local` |
| URL 视频字幕/Whisper 转写 | `transcript` |
| URL 视频关键帧 | `keyframes` |
| 视频素材研究包 | `quick-research` |
| 在已下载逐字稿里搜片段 | `search` |
| 根据已有逐字稿起平台标题 | 直接交给 `content-package-create`，不重复转录 |

如果用户只要平台列表、笔记详情、公众号文章、会议录制等非视频内容抓取，走 `platform-fetch`。如果用户要发布视频或图文，走 `Agent-Publish`。

## 前置条件

1. `ffmpeg` 已安装：`which ffmpeg || brew install ffmpeg`
2. 工具依赖已装：`cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research && uv sync`
3. Whisper 模型会缓存到 `~/.cache/huggingface/`；本地长视频建议使用 `base`/`small`，短视频且追求质量可用已缓存的 large/turbo 模型。

## CLI 路径

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research/scripts/cli.py <子命令>
```

所有子命令输出 JSON（`ensure_ascii=False`）。Exit code：`0=成功 / 1=前置失败 / 2=运行错误`。

## 本地视频转逐字稿

适用场景：用户给出本地 `.mov` / `.mp4` / `.m4a` / `.mp3` 等路径，要求“提取逐字稿”“转成文字”“放到下载目录”。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research/scripts/cli.py \
  transcribe-local \
  --input "/path/to/01.mov" \
  --input "/path/to/02.mov" \
  --lang zh \
  --out-dir "$HOME/Downloads/视频逐字稿" \
  --glossary "AI Coding,Claude Code,Codex,Agentic Engineering"
```

常用参数：

- `--input`：本地音视频路径，可重复传多个
- `--out-dir`：输出目录；不传时写入 `engines/video-research/data/local_transcripts/<时间戳>/`
- `--lang zh`：指定中文；传 `auto` 自动识别
- `--whisper-model base`：faster-whisper 模型名或 HuggingFace repo
- `--glossary`：术语提示，逗号分隔，可重复
- `--replace FROM=TO`：确定性术语替换，可重复；只用于明显误识别词

输出：

- `<stem>.json`：原始分段，含 `start` / `end` / `text`
- `<stem>.srt`：标准字幕
- `<stem>.txt`：连贯文本
- `<stem>.md`：带时间轴 + 连贯文本
- `combined.md`：多文件汇总

## URL 视频字幕/转写

```bash
# 默认：先试人工字幕/自动字幕，再用 Whisper 兜底
python scripts/cli.py transcript --url "<URL>" --lang zh,en

# 字幕质量差时强制 Whisper
python scripts/cli.py transcript --url "<URL>" --force-whisper --whisper-model small
```

返回字段里的 `source`：

| 值 | 含义 |
|-----|------|
| `manual` | 人工字幕 |
| `auto` | 平台自动字幕 |
| `whisper` | 本地 Whisper 转写 |
| `none` | 都失败了 |

## 一键视频素材研究

适用场景：用户说“研究这个视频”“帮我看看这视频讲啥”“整理成可写文章的素材”。

```bash
python scripts/cli.py quick-research --url "<视频URL>" --lang zh,en
```

输出目录 `data/{platform}_{video_id}/` 包含：

- `info.json` — 元数据
- `thumbnail.jpg` — 封面
- `transcript.txt` — 纯文本转写
- `transcript.srt` — 带时间戳
- `keyframes/HH-MM-SS.png` — 关键帧
- `RESEARCH.md` — 汇总文档

## 关键帧和检索

```bash
# 指定时间戳抽图
python scripts/cli.py keyframes --url "<URL>" --at "00:30,01:45,03:20"

# 每 60 秒一帧
python scripts/cli.py keyframes --url "<URL>" --interval 60

# 搜已落盘字幕
python scripts/cli.py search --video-id youtube_abcDEF --keyword "agent"
```

## 写作与平台文案交接

用户要求“把视频写成文章”“根据 YouTube 视频写公众号长文”等完整文章时，主责是 `source-longform-writing`。本 Skill 只补齐写作需要的逐字稿、字幕、关键帧或素材研究包，附来源 URL、作者与时间戳等已有信息，再返回原写作任务继续成稿；交出 `RESEARCH.md` 或字幕不代表文章任务完成。已有可用逐字稿时直接交接，不重复转录。

用户只要标题、封面文案或平台配文时，直接由 content-package-create 读取已有逐字稿和已确认观点；不要求先运行视频处理或制作完整内容包。需要先理解尚未转录的视频时，本 Skill 完成对应素材研究，再把实际逐字稿/关键帧交给内容包入口。视频官方原标题仍可作为来源元数据保存，不当作拟发布文案。

## 失败处理

| 场景 | 处理 |
|------|------|
| 未装 ffmpeg | Exit 1，提示 `brew install ffmpeg` |
| 未装 faster-whisper | 提示运行 `uv sync` |
| 本地文件不存在 | 直接返回 missing 列表 |
| URL 地域限制/需要登录 | 指引用户导出 cookies 到 `~/.config/yt-dlp/cookies.txt` |
| 视频超长 | 建议 `--whisper-model tiny/base`，或优先使用平台字幕 |

## 注意事项

- 本地视频转写默认不修改原视频文件，只写输出目录。
- `data/` 不纳入 git；下载目录或用户指定目录由用户自行管理。
- 术语校正只做确定性替换；不确定的专有名词应提醒用户人工听校。
- 旧 skill 名 `video-research` 已被 `video-content` 替代。
