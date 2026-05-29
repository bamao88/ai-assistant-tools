# 小红书博主调研（抓取部分）

目标：把一个小红书博主的公开笔记尽量拉全，供上层做画像/爆款分析。

## 唯一执行方式

只用本项目 Python CLI，不要用 MCP / Go 工具。CLI 路径每次完整写：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py <子命令>
```

## 前置：账号选择 + 网络分流

1. 先 `list-accounts`，按返回 `count` 选账号（0=默认不加 `--account`；1=告知并加 `--account`；多个=问用户后固定）。
2. 任何访问小红书网页的命令前，先刷新本地分流路由（避免 Tailscale 走海外出口）：

```bash
tailscale set --exit-node-allow-lan-access=true 2>/dev/null || true
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/xhs-route-bypass.zsh apply
```

## 抓取流程

### 1. 用户主页（拿博主基础信息 + 笔记列表）

`user_id` 和 `xsec_token` 成对使用。若只有主页 URL，先从 URL 解析 user_id 和 xsec_token；或先 `search-feeds` 搜到该博主某条笔记拿到作者 id/token。

```bash
... cli.py user-profile --user-id <USER_ID> --xsec-token <XSEC_TOKEN>
```

输出含：昵称、简介、粉丝/关注/获赞、笔记列表（每条带 `id` + `xsec_token` + 标题 + 封面 + 互动数）。

### 2. 高互动笔记取详情（拿正文/话题/评论做爆款分析）

从主页笔记列表里挑互动数据靠前的若干篇（默认 Top 5–10），逐条取详情：

```bash
... cli.py get-feed-detail --feed-id <FEED_ID> --xsec-token <XSEC_TOKEN>
```

需要看评论区共鸣点时加 `--load-all-comments --max-comment-items 50`。

### 3. 结构化落盘

把每条笔记的 标题 / 发布时间 / 赞藏评 / 话题标签 / 是否图文或视频 / 正文要点 汇总成表，供上层分析选题分布、爆款规律、发布节奏。

## 失败处理

- 未登录 → 提示走 `xhs-auth` 扫码登录，不要空转重试。
- 主页不可访问 → 博主已注销或设隐私，告知用户并停止。
- 限流 → 降低取详情并发、加 sleep，必要时切账号。
- 笔记私密/已删 → 跳过并记录，不绕路。
