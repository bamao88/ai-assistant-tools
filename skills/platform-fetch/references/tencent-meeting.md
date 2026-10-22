# 腾讯会议（官方 MCP）

适用：查询/下载本人有权限的腾讯会议录制、逐字稿、转写搜索和 AI 智能纪要。

**按交付物分两条路，别混用（2026-06-04 固化）：**

| 你要的 | 用哪条 | 为什么 |
|---|---|---|
| 会议信息 / 录制列表 / 逐字稿 / 转写搜索 / AI 智能纪要 | 官方 MCP（默认） | 鉴权独立、稳定，下面「录制与转写流程」 |
| 下载视频，尤其是**分轨**（说话人/共享屏幕/合成） | `download_tencent_stream.py download --stream speaker`（见文末「视频与分轨下载」） | **官方 MCP 的 `get_record_addresses` 只返回单个合成/观看 `view_address`，拿不到分轨**；切口播片必须用纯摄像头「说话人」轨（合成/屏幕轨会录进共享内容 = 泄密） |

官方包元数据：owner `WeMeeting`，latest `1.0.8`，endpoint `https://mcp.meeting.tencent.com/mcp/wemeet-open/v1`。

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
- 只有 `https://meeting.tencent.com/crm/...` / `cw/...` 分享短链：官方 MCP 不以分享短码为主键。先用已知时间范围/标题匹配，或在现有授权 Chrome 会话中按 [分享链接浏览器读取](tencent-meeting-browser-share.md) 获取资料；无法匹配且没有可访问会话时再补会议号或时间范围。

## 录制与转写流程

1. 需要“会议内容/总结”时优先 `get_smart_minutes`，再查 `get_transcripts_details`，最后才取录制下载地址。
2. 获取录制列表：
   - `meeting_id` / `meeting_code` 已知：按会议查。
   - 只知道大致时间：按 `start_time` + `end_time` 查，范围不超过 31 天，起始不早于 1 年前。
3. 从 `get_records_list` 结果里区分：
   - `meeting_record_id`：传给 `get_record_addresses`，拿视频/音频下载地址。
   - `record_file_id`：传给 `get_transcripts_paragraphs` / `get_transcripts_details` / `get_smart_minutes`。
4. 下载视频时先拿 `get_record_addresses`，再用 `download-addresses` / `download-url` 下载到用户指定目录；下载大文件前确认磁盘空间。⚠️ **`get_record_addresses` 只给单个合成/观看轨，拿不到分轨**——要说话人/共享屏幕分轨，走文末「视频与分轨下载」的 `download_tencent_stream.py`。
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

## 视频与分轨下载（现役正路，不是 legacy）

`engines/tencent-meeting/scripts/download_tencent_stream.py` 是下载视频/分轨的**现役默认入口**（2026-06-04 实测跑通完整 8313s 说话人轨）。它默认走**直连分享接口 + no-proxy + 并发分段 Range 下载**，不依赖 Chrome、不碰被限流的取址通道；direct 失败才回退登录态 Chrome 同源 XHR。

下载只有人物/说话人轨（切口播片用这条）：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/download_tencent_stream.py download \
  "https://meeting.tencent.com/crm/<short_code>" \
  --stream speaker \
  --slug "<会议主题>"
```

列出三路轨道（不下载，只看有哪几路）：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/download_tencent_stream.py list-streams \
  "https://meeting.tencent.com/crm/<short_code>"
```

可选轨道：

- `--stream speaker`：只有人物/说话人（**首选**，纯摄像头满屏、零屏幕泄露、与逐字稿时间轴一致）
- `--stream screen`：只有共享屏幕
- `--stream main`：人 + 屏幕合成（会录进共享内容，发布前自查泄密）
- `--stream all`：三路都下载

**避坑（都已实测）：**
- **别用网页下载按钮 / Chrome AppleScript / 官方 MCP 取分轨**：前者把 `download/record` 取址打到 `code=4049` 限流（server 端，越重试越久，别轮询硬刚）；MCP 根本不返回分轨。
- **单流 curl 会在 ~75% 处被 cos 轮换 IP 的 SNI reset 截断**；本脚本的并发分段天然抗截断（每段独立 Range，断了只重 该段）。所以下完务必 `ffprobe ... packet=pts_time | tail -1` 核末帧 pts ≈ 总时长，别只看文件存在。
- **输出落点**：脚本归档到 `media/tencent/<slug>/video/<slug>-<轨名>.mp4`（如 `...-说话人.mp4`），**不是** `video/files/<short_code>_speaker.mp4`。下游脚本若硬编码读 `files/...`，下完要先 `cp` 覆盖到位。
- 4049 真被限流且急需时，用 `download_tencent_stream.py ingest`（认领网页下载菜单已下好的分轨文件归档），不依赖 API、永远可用。
- 直连前先 `curl -sI --noproxy '*' https://meeting.tencent.com/` 探活，**返回 200 就别动网络/Tailscale**；只有 `000`/RST 才按「网络/代理绕过」分流。

## 旧脚本状态（legacy，别再当默认）

`engines/tencent-meeting/scripts/cli.py`、`fetch_tencent_meeting_transcripts_stable.py`、`download_tencent_meeting_videos_stable.py` 保留为 legacy：查询/逐字稿/纪要走官方 MCP，视频/分轨走上面的 `download_tencent_stream.py`，这三个一般不用直接调。
