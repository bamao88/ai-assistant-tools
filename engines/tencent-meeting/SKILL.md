---
name: tencent-meeting-downloader
description: |
  Deprecated legacy Tencent Meeting downloader. Do not trigger this skill.
  Use platform-fetch references/tencent-meeting.md or the official tencent-meeting-mcp path instead.
---

# Tencent Meeting MCP Bridge

腾讯会议默认走官方 MCP，不再把本地网页/API 下载脚本作为常规方案。

正确入口：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-fetch/references/tencent-meeting.md
```

官方 MCP 桥接 CLI：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py tools-list
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py records --meeting-code 904854736
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py smart-minutes --record-file-id <record_file_id>
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py record-addresses --meeting-record-id <meeting_record_id>
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py download-addresses --input /abs/path/record_addresses.json --output-dir /abs/path/meetings/files
```

内部分享链接分轨下载（不走 MCP，默认 no-proxy + 并发分段）：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/download_tencent_stream.py download \
  "https://meeting.tencent.com/crm/<short_code>" \
  --stream speaker \
  --slug "<会议主题>"
```

前提：访问 https://meeting.tencent.com/ai-skill 获取 Token，并设置：

```bash
export TENCENT_MEETING_TOKEN="<你的 token>"
```

默认会绕过代理环境变量；如果 Tailscale exit node 仍接管直连流量，先运行：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply \
  meeting.tencent.com mcp.meeting.tencent.com ylz.cos.meeting.tencent.com
```

## Legacy Scripts

以下脚本保留为历史排障、回归对照、或用户明确要求旧的分享短链/分轨归档路径时使用：

- `scripts/cli.py`
- `scripts/fetch_tencent_meeting_transcripts_stable.py`
- `scripts/download_tencent_meeting_videos_stable.py`
- `scripts/fetch_tencent_video_via_chrome.py`
- `scripts/download_tencent_stream.py`

默认不要自动回退到 legacy，避免继续依赖非官方网页接口。
