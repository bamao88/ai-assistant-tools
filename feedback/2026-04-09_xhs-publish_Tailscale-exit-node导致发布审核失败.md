# Tailscale Exit Node 导致小红书发布审核失败

## 状态

fixed-in-platform-publish（旧 `xhs-publish-*` 触发入口已废弃）

## 当前处理

本反馈里的 `xhs-publish-article` / `xhs-publish-post` / `xhs-publish-video` 是历史独立发布 skill 名称。当前仓库的正式发布入口只有 `platform-publish`；`registry.yaml: deprecated` 已把这些旧触发标为废弃，`scripts/sync-skills.py` 会从 `~/.claude/skills` 移除同名旧入口。

旧建议里的“临时关闭 Tailscale exit node”不再采用。当前方案是在 `platform-publish` 的小红书 reference 中，把发布前网络门固定为：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/route-bypass/scripts/publish-network-preflight.zsh xiaohongshu apply
```

该方案只给小红书发布域名和上传 CDN 刷新本地网关路由，不关闭全局 exit node。

## 日期
2026-04-09

## 涉及工具
xhs-publish-article / xhs-publish-post / xhs-publish-video

## 问题描述

使用 Tailscale exit node（如新加坡节点）时，Chrome 所有流量走海外 IP。小红书检测到 IP 异常，导致笔记审核不通过。

## 复现步骤

1. Tailscale 开启 exit node（如 `instance-sg-ubuntu`，出口 IP 为新加坡）
2. 通过任意 xhs-publish skill 执行 `click-publish`
3. 笔记提交后被小红书审核拦截

## 期望行为

发布时使用国内真实 IP，笔记正常通过审核。

## 建议方案

在所有 publish skill 的 `click-publish` 步骤前后，自动检测并临时关闭 Tailscale exit node：

```bash
# 发布前：检测并关闭 exit node
CURRENT_EXIT_NODE=$(tailscale status --json 2>/dev/null | python3 -c "
import sys,json
s=json.load(sys.stdin)
peers=s.get('Peer',{})
for p in peers.values():
    if p.get('ExitNode'):
        print(p['HostName'])
        break
" 2>/dev/null)

[ -n "$CURRENT_EXIT_NODE" ] && tailscale set --exit-node= && sleep 2

# 执行 click-publish ...

# 发布后：恢复 exit node
[ -n "$CURRENT_EXIT_NODE" ] && tailscale set --exit-node="$CURRENT_EXIT_NODE"
```

影响窗口 < 10 秒，仅 click-publish 步骤需要，其他步骤（fill、next-step 等）不受影响。

## 涉及 skill 文件

- `skills/xhs-publish-article/SKILL.md`（及 .claude.md / .openclaw.md）
- `skills/xhs-publish-post/SKILL.md`
- `skills/xhs-publish-video/SKILL.md`

## 参考文档

已在 `shared/platform-experience/tailscale-exit-node-publish.md` 记录了完整的问题分析和方案。

## 来源
assistant_zh（ZH 内容运营 Agent）
