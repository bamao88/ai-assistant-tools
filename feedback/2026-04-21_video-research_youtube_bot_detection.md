---
status: fixed
tool: video-research
reported_by: user
date: 2026-04-21
fixed_date: 2026-04-21
fix_summary: 新增共享 ydl_opts 构造器，集成 curl-cffi impersonation + player_client fallback + cookies 自动读取
---

# video-research — yt-dlp 遇 YouTube 机器人检测失败

## 问题描述

通过 `video-research` 对 YouTube 视频跑 `info` / `transcript` / `quick-research` 时，
yt-dlp 返回机器人检测相关的警告或直接失败：

- `WARNING: [youtube] No supported JavaScript runtime could be found.`
- `WARNING: The extractor specified to use impersonation for this download, but no impersonate target is available.`
- 某些视频会走到 `Sign in to confirm you're not a bot` 分支直接 401/403。

## 复现

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research
.venv/bin/yt-dlp -f "best" --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

输出中可见上述两类 WARNING；目前对该视频还能 fallback 到 `android vr player API`，
但对 age-restricted / region-restricted / 热门账号视频会直接被拦。

## 根因

1. **`curl-cffi` 未安装** —— yt-dlp 的 impersonate（TLS/JA3 指纹伪装）能力依赖该库，
   没装时所有 HTTP 请求都是 Python 原生 TLS 指纹，容易被 YouTube 识别为 bot。
2. **没有 JS 运行时（deno/node）** —— YouTube 播放器签名解密现需外部 JS runtime，
   没有时大量 format（含最高画质和最稳字幕通道）会缺失。
3. **`ydl_opts` 没指定 `extractor_args.youtube.player_client`** —— 只靠 yt-dlp 默认
   client 轮询，命中率偏低；应显式把 `mweb / web_safari / tv_embedded / android_vr` 串起来。
4. **没有 cookies 兜底** —— 即使 `~/.config/yt-dlp/cookies.txt` 存在，当前 ydl_opts
   也没带 `cookiefile`，浏览器登录态没发挥作用。
5. `yt-dlp==2026.03.17`，比上游最新 `2026.04.08+` 落后一个月。

## 期望行为

- 新视频默认绕过机器人检测（只要不是需要登录的私密视频）
- 需要登录时，能自动读取 `~/.config/yt-dlp/cookies.txt`
- 三个子命令（info / transcript / keyframes / whisper）共用同一套 ydl_opts

## 修复内容

1. 新增 `scripts/video_research/ydl.py`：公共 `merge_ydl_opts()`，所有子命令复用。
2. `info.py` / `transcript.py`（字幕 + Whisper 下载音频）/ `keyframes.py`（低分辨率下载）四处 `ydl_opts` 全部改走 helper。
3. `pyproject.toml` 新增 `curl-cffi>=0.10,<0.15`（yt-dlp 2026.03.17 上游约束），同时把 `yt-dlp` 切到 `[default]` extras。
4. `CLAUDE.md` 补充"YouTube 机器人检测"章节 + 推荐 `brew install deno`。

## 验证

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-research
.venv/bin/python scripts/cli.py info --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --no-thumbnail   # OK
.venv/bin/python scripts/cli.py transcript --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --lang en  # OK, source=manual
.venv/bin/yt-dlp --list-impersonate-targets | head -5   # 显示可用 Chrome/Safari 等 target
```

不再出现 `No supported JavaScript runtime could be found` / `impersonation ... no impersonate target is available` 两条 WARNING。
