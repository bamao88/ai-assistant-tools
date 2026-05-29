---
status: fixed
fixed_in: token cache per-appId + --profile flag (wechat.ts, index.ts)
date_fixed: 2026-04-13
---

# gzh-publish 需要多账号支持

- **日期**：2026-04-09
- **来源**：assistant_mdx
- **工具**：gzh_pubulish

## 问题

`~/.gzh-publish/config.json` 只支持一组凭证。多个 Agent 管理不同公众号时，会互相覆盖 config，导致文章发到错误的公众号。

## 实际案例

- config 里原来是 `wxc068...`（另一个公众号），assistant_mdx 用它上传了草稿，结果发到了错误的公众号
- 手动替换为 `wxe6e6...`（直觉机器漫谈）后才正确

## 建议

支持 `--profile` 参数，类似 lark-cli 的多 profile 机制：
```bash
npx tsx index.ts article.md --profile mdx   # 用 mdx 的凭证
npx tsx index.ts article.md --profile wxp   # 用 wxp 的凭证
```

config 结构改为：
```json
{
  "profiles": {
    "mdx": { "WECHAT_APP_ID": "...", "WECHAT_APP_SECRET": "..." },
    "wxp": { "WECHAT_APP_ID": "...", "WECHAT_APP_SECRET": "..." }
  },
  "default": "mdx"
}
```
