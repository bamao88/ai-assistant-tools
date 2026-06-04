# 腾讯会议（官方 MCP）

适用：查询/下载本人有权限的腾讯会议录制、逐字稿、转写搜索和 AI 智能纪要。

默认使用官方 `tencent-meeting-skill` / `tencent-meeting-mcp`，不要再把本地网页抓取脚本作为默认方案。官方包元数据：owner `WeMeeting`，latest `1.0.8`，endpoint `https://mcp.meeting.tencent.com/mcp/wemeet-open/v1`。

## 前提

1. 访问 https://meeting.tencent.com/ai-skill 获取 Token。
2. 设置环境变量：

```bash
export TENCENT_MEETING_TOKEN="<你的 token>"
```

3. 若当前 Agent 环境已暴露官方腾讯会议 MCP tools，直接调用工具；若没有 MCP tool，可以使用本仓库的轻量桥接 CLI：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py tools-list
```

## 网络 / 代理绕过

本机常开系统代理或代理环境变量时，腾讯会议 MCP 与录制下载必须绕过代理走本地网络：

- `mcp_cli.py` 默认忽略 `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` 等环境变量；只有显式加 `--use-proxy` 才会使用代理。
- 录制文件下载默认使用 `curl --noproxy '*'`，并清理子进程代理环境变量，同时沿用旧方案验证过的 `Referer: https://meeting.tencent.com/` 和 Chrome UA。
- 如果 Tailscale exit node / 全局路由仍把直连流量带到境外，先应用 host route，让腾讯会议域名走本地网关：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply \
  meeting.tencent.com mcp.meeting.tencent.com ylz.cos.meeting.tencent.com
```

只查看当前路由，不改系统：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh status \
  meeting.tencent.com mcp.meeting.tencent.com ylz.cos.meeting.tencent.com
```

## 标识符规则

- 有 `meeting_id`：直接用于 `get_records_list`、`get_meeting` 等工具。
- 有 9 位 `meeting_code`：先用 `get_meeting_by_code` 转换，或直接传给 `get_records_list --meeting-code`。
- 只有 `https://meeting.tencent.com/crm/...` / `cw/...` 分享短链：官方 MCP 不以分享短码为主键。不要硬套旧短链脚本；请让用户补会议号、会议时间范围，或用时间范围查询录制列表后按标题/时间匹配。

## 录制与转写流程

1. 需要“会议内容/总结”时优先 `get_smart_minutes`，再查 `get_transcripts_details`，最后才取录制下载地址。
2. 获取录制列表：
   - `meeting_id` / `meeting_code` 已知：按会议查。
   - 只知道大致时间：按 `start_time` + `end_time` 查，范围不超过 31 天，起始不早于 1 年前。
3. 从 `get_records_list` 结果里区分：
   - `meeting_record_id`：传给 `get_record_addresses`，拿视频/音频下载地址。
   - `record_file_id`：传给 `get_transcripts_paragraphs` / `get_transcripts_details` / `get_smart_minutes`。
4. 下载视频时先拿 `get_record_addresses`，再用 `download-addresses` / `download-url` 下载到用户指定目录；下载大文件前确认磁盘空间。
5. 每次工具返回的 `X-Tc-Trace` 或 `rpcUuid` 都要展示给用户，便于后续排障。

## 常用 MCP 桥接命令

列工具：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py tools-list
```

按会议号查录制：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py records \
  --meeting-code 904854736 \
  --output /abs/path/tencent_records.json
```

按时间范围查录制：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py records \
  --start-time "2026-06-01T00:00:00+08:00" \
  --end-time "2026-06-04T23:59:59+08:00" \
  --page-size 20 \
  --output /abs/path/tencent_records.json
```

获取录制下载地址：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py record-addresses \
  --meeting-record-id <meeting_record_id> \
  --output /abs/path/record_addresses.json
```

从 `record_addresses.json` 里提取录制 URL 并绕过代理下载：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py download-addresses \
  --input /abs/path/record_addresses.json \
  --output-dir /abs/path/meetings/files
```

如果已经拿到单个下载 URL：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py download-url \
  "https://..." \
  --dest /abs/path/meetings/files/recording.mp4
```

获取转写全文：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py transcript \
  --record-file-id <record_file_id> \
  --pid 0 \
  --output /abs/path/transcript.json
```

获取智能纪要：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py smart-minutes \
  --record-file-id <record_file_id> \
  --output /abs/path/minutes.json
```

任意工具调用：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/mcp_cli.py call get_records_list \
  --args '{"meeting_code":"904854736"}'
```

## 时间处理

- 用户用“今天、昨天、下周一”等相对时间时，先调用官方 `convert_timestamp`，不要模型心算。
- 用户明确给时区时，`convert_timestamp` 传 `timezone`；返回的 `parsed_time_unix` 已经是正确 UTC 时间戳，不要二次换算。
- 若只用桥接 CLI 且用户已经给了明确时间，优先传 ISO 8601，例如 `2026-06-04T15:00:00+08:00`。

## 旧脚本状态

`engines/tencent-meeting/scripts/cli.py`、`fetch_tencent_meeting_transcripts_stable.py`、`download_tencent_meeting_videos_stable.py`、`download_tencent_stream.py` 保留为 legacy：

- 只用于历史排障、回归对照，或用户明确要求旧的分享短链/分轨归档路径。
- 默认不自动回退到 legacy，避免继续依赖非官方网页接口。
- 分轨“说话人轨/共享屏幕轨”目前官方 MCP 未在 reference 中声明；用户明确要分轨素材时，可以说明限制后再考虑 legacy `download_tencent_stream.py`。
