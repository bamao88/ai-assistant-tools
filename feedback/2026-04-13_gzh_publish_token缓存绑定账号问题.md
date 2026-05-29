---
status: fixed
fixed_in: token cache per-appId file (token_<appId>.json in wechat.ts)
date_fixed: 2026-04-13
---

# Bug: token.json 缓存未绑定 App ID，切换账号后使用旧 token

## 问题描述

`gzh-publish` 工具将 access_token 缓存在 `~/.gzh-publish/token.json`，但缓存中未记录对应的 App ID。当 `config.json` 中的凭证更新为不同的 App ID 时，工具仍会使用旧账号的缓存 token，导致图片上传到错误账号，草稿创建失败（media_id 不匹配）。

## 复现步骤

1. 工具曾经用账号 A 的凭证运行过，生成了 token 缓存
2. 将 `~/.gzh-publish/config.json` 改为账号 B 的凭证
3. 运行发布命令，工具显示"成功"但草稿出现在账号 A（或根本不存在）

## 期望行为

token 缓存应包含 App ID 字段，每次使用前校验缓存的 token 是否属于当前 config.json 中的 App ID，不匹配则丢弃并重新获取。

## 实际行为

- 工具用旧 token 上传图片，返回了属于旧账号的 media_id（`5SP5Rtq9...` 前缀）
- 用该 media_id 创建草稿时，API 报 `errcode 40007: invalid media_id`
- 工具代码中 `if (data.errcode)` 未被触发（可能是响应结构差异），工具误报"成功"

## 临时解决方案

手动删除 `~/.gzh-publish/token.json` 后重新运行即可。

## 建议修复

在 `saveTokenCache` 和 `loadTokenCache` 中加入 `app_id` 字段，`getAccessToken` 加载缓存时校验 app_id 是否一致。
