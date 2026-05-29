# video-research

视频素材研究工具：给 URL → 产出字幕 + 关键帧 + 元数据，供内容运营写作参考；也支持本地音视频文件批量转逐字稿。

## 架构

```
video_research/
├── pyproject.toml                   # uv 管理依赖
├── README.md                        # 用户视角文档
├── CLAUDE.md                        # 维护文档（本文件）
├── scripts/
│   ├── cli.py                       # 统一 CLI 入口（argparse 子命令）
│   └── video_research/
│       ├── info.py                  # 元数据 + 封面
│       ├── transcript.py            # URL 字幕抓取 + Whisper 兜底 + search
│       ├── local_transcribe.py      # 本地音视频转逐字稿
│       ├── keyframes.py             # ffmpeg 三种模式抽帧
│       ├── quick_research.py        # 主工作流编排
│       ├── storage.py               # data/ 路径管理
│       └── utils.py                 # 时间戳 / 站点识别
├── data/{platform}_{video_id}/      # 每个 URL 视频一个目录（不纳入 git）
├── data/local_transcripts/          # 本地转写默认输出（不纳入 git）
└── skills/video-content/SKILL.md    # 给 Claude Code 读的技能说明
```

## 依赖

- **运行时**：`yt-dlp`（视频/字幕抓取）、`faster-whisper`（本地转写兜底）、`requests`
- **系统**：`ffmpeg`（抽帧 + yt-dlp 合流）

选择 `faster-whisper` 而非 `openai-whisper`：CTranslate2 实现，CPU 下快 ~4 倍、显存占用一半，自动管理模型缓存。

## CLI 子命令

| 子命令 | 作用 | 关键入参 |
|--------|------|---------|
| `info` | 元数据 + 封面 | `--url` |
| `transcript` | URL 字幕/Whisper | `--url`, `--lang`, `--force-whisper`, `--whisper-model` |
| `transcribe-local` | 本地音视频转逐字稿 | `--input`, `--out-dir`, `--lang`, `--whisper-model`, `--glossary` |
| `keyframes` | 抽帧（三选一） | `--url` 或 `--video-id`；`--at` / `--interval` / `--scene-change` |
| `search` | 在本地字幕搜关键词 | `--video-id`, `--keyword` |
| `quick-research` | 主力一键入口 | `--url`, `--lang`, `--keyframes`, `--whisper-model` |

## 代码规范

- `from __future__ import annotations` + 完整 type hints
- 行宽上限 100
- JSON 输出 `ensure_ascii=False`
- Exit code：0 成功 / 1 前置失败（如 ffmpeg 未装）/ 2 运行错误
- 日志写 stderr，JSON 结果写 stdout
- 路径用 `pathlib.Path`，不拼字符串

## 维护 Agent 约定

- 本工具由 Manager 维护；业务 Agent 只读，Bug 通过 `/Volumes/ExtSSD2601/AI_Assistant/tools/feedback/` 反馈
- 不修改 SKILL.md 文案（除非反馈明确指出措辞有误）
- 每次修复单独 commit：`fix: video-research — 问题简述`

## 常见维护场景

### 字幕抓不到某个平台

多半是 yt-dlp 版本老旧。升级：
```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research
uv lock --upgrade-package yt-dlp
uv sync
```

### Whisper 模型首次下载失败

faster-whisper 从 HuggingFace 下载模型。网络不稳时：
```bash
# 手动预下载
.venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

### 地域限制 / 需要登录

所有子命令共用 `video_research/ydl.py` 的 `merge_ydl_opts()`，会自动读取：

1. `$VIDEO_RESEARCH_COOKIES`（环境变量指定的绝对路径）
2. `~/.config/yt-dlp/cookies.txt`（yt-dlp 约定路径）
3. `~/.config/video-research/cookies.txt`（本工具专用）

浏览器导出 cookies（推荐 Chrome 插件 `Get cookies.txt LOCALLY`）后放到以上任一路径即可。
需要临时覆盖时直接 `export VIDEO_RESEARCH_COOKIES=/tmp/my_cookies.txt`。

### YouTube 机器人检测 (Sign in to confirm you're not a bot)

`merge_ydl_opts()` 已内置三道防线：
- **curl-cffi impersonation**：TLS/JA3 指纹伪装，默认挑 Chrome target（`yt-dlp --list-impersonate-targets` 查看可用）
- **player_client fallback 链**：`mweb → web_safari → tv_embedded → android_vr`
- **请求级 sleep**：每次请求间隔 1-3 秒，降低触发频控

系统依赖（可选但强烈建议）：
```bash
# macOS
brew install deno       # YouTube 新版 player 需要 JS runtime 解密签名
```
没有 `deno` 时 yt-dlp 会降级到无 JS 分支（部分格式缺失但元数据/字幕仍可抓）。

可用环境变量：
- `VIDEO_RESEARCH_IMPERSONATE`：指定具体 target，如 `chrome-136:macos-15`
- `VIDEO_RESEARCH_COOKIES`：指定 cookies 文件路径

注意：`curl-cffi` 必须锁在 `0.10 ≤ x < 0.15`，yt-dlp 2026.03.17 不兼容 0.15+。

### 场景切换检测抽不到/抽太多

调 `--scene-threshold`：默认 0.3，值越小越敏感（更多帧）、越大越保守。
