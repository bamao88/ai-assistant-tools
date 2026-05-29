# video_research

视频素材研究工具：给一个视频 URL，产出字幕/转写 + 关键帧截图 + 元数据+封面，供内容运营写文章时参考引用、找配图。也支持本地音视频文件批量转逐字稿。

支持 yt-dlp 覆盖的 1000+ 站点（YouTube / Bilibili / 小红书 / 抖音 / Twitter / 视频号等）。

## 安装

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research
uv sync

# 系统依赖（必需）
which ffmpeg || brew install ffmpeg
```

首次使用 Whisper 兜底时会自动下载模型到 `~/.cache/huggingface/`（默认 `base` 模型 ~150MB）。

## 使用

所有命令 JSON 输出（`ensure_ascii=False`），exit code：`0=成功 / 1=前置失败 / 2=运行错误`。

### 一键研究（推荐）

```bash
.venv/bin/python scripts/cli.py quick-research \
  --url "https://www.youtube.com/watch?v=xxx" \
  --lang zh,en
```

输出：`data/{platform}_{video_id}/` 目录，含 `info.json` / `thumbnail.jpg` / `transcript.txt` / `transcript.srt` / `keyframes/*.png` / `RESEARCH.md`。

### 单项命令

```bash
# 元数据 + 封面
.venv/bin/python scripts/cli.py info --url <URL>

# 字幕/转写
.venv/bin/python scripts/cli.py transcript --url <URL> --lang zh,en
.venv/bin/python scripts/cli.py transcript --url <URL> --force-whisper --whisper-model small

# 本地音视频批量转逐字稿
.venv/bin/python scripts/cli.py transcribe-local \
  --input /path/to/01.mov \
  --input /path/to/02.mov \
  --lang zh \
  --out-dir "$HOME/Downloads/视频逐字稿"

# 关键帧（三种模式三选一）
.venv/bin/python scripts/cli.py keyframes --url <URL> --at "00:30,01:45,03:20"
.venv/bin/python scripts/cli.py keyframes --url <URL> --interval 60
.venv/bin/python scripts/cli.py keyframes --url <URL> --scene-change

# 在已下载的 transcript 里搜关键词
.venv/bin/python scripts/cli.py search --video-id youtube_xxx --keyword "agent"
```

## 存储

```
data/{platform}_{video_id}/
├── info.json          # 元数据
├── thumbnail.jpg      # 封面
├── transcript.txt     # 清洗后的纯文本
├── transcript.srt     # 带时间戳（供 search/keyframes 引用）
├── keyframes/
│   ├── 00-03-15.png
│   └── ...
└── RESEARCH.md        # quick-research 汇总文档

local_transcripts/{timestamp}/
├── 01.json            # 本地转写 segments
├── 01.srt             # 标准字幕
├── 01.txt             # 连贯文本
├── 01.md              # 带时间轴 Markdown
└── combined.md        # 多文件汇总
```

## 不做的事

- ❌ 下载视频原文件（用 `yt-dlp` 原生命令即可）
- ❌ 视频剪辑
- ❌ OCR 关键帧文字（后续可加）
- ❌ 云端 Whisper API（本地 faster-whisper 足够）
