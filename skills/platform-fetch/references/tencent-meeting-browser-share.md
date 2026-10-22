# 腾讯会议分享链接：已有浏览器会话取资料

当用户给的是 crm/cw 分享短链、官方 MCP 无法把它匹配到会议，而当前已有获授权且可访问该链接的 Chrome 会话时，用本分支复用既有读取能力。没有身份或权限时保留现场并恢复正常认证；不因旧网络故障记录自动修改 Tailscale、系统路由或 hosts。

先按当前项目确认资料输出目录与会议来源；已有逐字稿和录制优先复用。以下工具只在其真实前提满足时执行，先读各工具帮助核对当前参数。取回文件后核对内容/视频轨与会议身份，保存来源和实际范围。

逐字稿（已登录且已加载的 Chrome 会议页）：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/cli.py \
  transcripts --strategy chrome --settle-seconds 12 \
  --output-dir /abs/out/transcripts "<url或short_code>"
```

合成录制下载：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/scripts/fetch_tencent_video_via_chrome.py \
  "<url或short_code>" --output-dir /abs/out/videos
```

逐字稿导出和录制各有访问权限，不从一个成功推断另一个可用。用户需要说话人/共享屏幕等分轨时，回 [腾讯会议主参考](tencent-meeting.md) 的视频与分轨下载部分，不能把合成录制当作纯摄像头轨。

原项目下载 Skill 已退出发现，历史问题记录保留在项目 .skill-archive/2026-10-21；引擎未删除。这次入口整理未重跑真实会议输入。
