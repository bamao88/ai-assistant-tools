# 腾讯会议下载受阻：Tailscale 境外出口 SNI 拦截 + 登录态/转写可用性

## 日期
2026-05-30

## 涉及工具
tencent-meeting-downloader（`tools/engines/tencent-meeting/scripts/cli.py`）

## 问题描述

下载 5 期 DAY1 公开课录播时，逐字稿和视频都失败。逐层定位到 4 个独立坑：

1. **SKILL.md 脚本路径过期**：写的是 `tools/tencent_meeting_downloader/...`，实际已迁到 `tools/engines/tencent-meeting/...`。
2. **Tailscale 境外出口 SNI 拦截（主因）**：本机 `RouteAll: true` + exit node 漂到 AWS 东京（原新加坡节点 offline）。所有流量从境外出口走，腾讯会议对境外云 IP **按 SNI 重置**——`ConnectionResetError(54)` / curl `http_code=000`，而 `www.tencent.com` 正常。对照实验：同一目标 IP，SNI=`meeting.tencent.com` 被 RST、SNI=`www.tencent.com` 返回 200。用户明确**不允许动 Tailscale**。
3. **`/crm`、`/cw` 分享需登录态**：API 链路 `Meeting id missing` / `No recordings found`；逐字稿要走 Chrome 链路（已登录 Chrome 抓 DOM），视频要借 Chrome 页面上下文调 webapi 取下载地址。
4. **转写可用性按分享链接而定**：`minutes_exportable=0`/91001。同一会议不同分享链接，有的开了转写有的没开——换链接即可。

## 解决方案（已写入 SKILL.md「前置条件」）

- 网络：用项目自带 `tools/engines/route-bypass`（小红书/视频号同款"走本地流量"）给 `meeting.tencent.com` + `ylz.cos.meeting.tencent.com` 加本地主机路由；**再 /etc/hosts pin 国内 IP**（MagicDNS 仍解析海外 POP，海外 POP 也按 SNI 拒）。验证 `curl https://meeting.tencent.com/` = 200。**不动 Tailscale。**
- 逐字稿：开 Chrome「显示 → 开发者 → 允许 Apple 事件中的 JavaScript」并**冷重启**（`pkill -9` 确认归零再 open），`transcripts --strategy chrome`。
- 视频：Chrome 页面上下文调 `wemeet-cloudrecording-webapi/v1/download/record`（`id`=录制 sharing_id、`sharing_id`=页面 share_id，来自 `common-record-info.short_url_info.long_url`），CDN 下载带 `Referer: https://meeting.tencent.com/` + 浏览器 UA（否则 403）。
- 转写导不出时换另一条分享链接重试。

## 教训
- 现象是网络拦截时**先定位是不是 Tailscale 出口路径**（对照不同 SNI / 看 exit node），不要盲目重试、不要让用户改设置、不要动 Tailscale。
- 工具代码不擅自改（见 2026-04-09 权限约定），把稳定调用的前置步骤写进 SKILL.md 这层。

## 来源
assistant_zh（ZH 内容运营 Agent）
