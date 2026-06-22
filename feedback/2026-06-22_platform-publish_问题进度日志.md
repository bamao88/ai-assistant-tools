# platform-publish 问题进度日志

## 日期

2026-06-22

## 范围

记录当前发布相关 Skill / engine / feedback 的收敛状态。正式发布入口只有 `skills/platform-publish`；旧的独立发布触发入口不再使用。

## 当前结论

| 问题 | 状态 | 当前处理 |
|------|------|----------|
| 小红书发布是否还有旧 `xhs-publish-*` Skill | closed | 当前正式入口只有 `platform-publish`。`registry.yaml: deprecated` 已标记 `xhs-publish` / `xhs-publish-article` / `xhs-publish-post` / `xhs-publish-video` 废弃，`scripts/sync-skills.py` 会移除 stale trigger。 |
| 小红书 Tailscale exit node 导致发布审核失败 | fixed-in-platform-publish | 不再临时关闭全局 exit node；发布前由 `publish-network-preflight.zsh xiaohongshu apply` 刷新小红书发布域名和上传 CDN 的本地路由。 |
| 小红书 auth 缺少 `import-cookies` / `check-creator-login` | open, not blocking publish | 这是认证工具增强项：仅在“用户直接给 Cookie 字符串要求导入账号并验证 creator 后台登录态”时需要。正常扫码登录和当前 `platform-publish` 发布流程不依赖。 |
| 抖音发布流程是否已打通 | open | 入口存在，但 `sau douyin check --account 张和` 返回 `invalid`，当前缺 `douyin_张和.json`，且 `upload-video` / `upload-note` 会直接点击“发布”，没有 fill-only / manual-submit 模式。不能用于真实账号一键发布。 |
| 发布网络是否统一走本地网络 | in-progress | `platform-publish` 已把网络前置门上移：选定平台/账号/最终提交权限后，执行平台 reference 前先跑 `publish-network-preflight`。小红书、视频号、B站、抖音、公众号、文章草稿平台均已写入 reference。动态上传 CDN 未覆盖时必须先补路由再继续。 |
| Wechatsync 与小红书/公众号发布入口混淆 | fixed | `wechatsync.md` 已明确：`weixin` / `xiaohongshu` 不通过 Wechatsync 发布，继续留在 `platform-publish` 内对应 reference。 |
| engine 文档误导为可触发小红书 Skill | fixed | `engines/xiaohongshu/README.md` / `SKILL.md` / `CLAUDE.md` 已改为底层 engine 文档，明确发布走 `skills/platform-publish`。 |

## 已更新文件

- `feedback/2026-05-17_xhs-auth_cookie导入缺少标准命令.md`：补充状态和解释，明确不是当前发布流程阻塞项。
- `feedback/2026-04-09_xhs-publish_Tailscale-exit-node导致发布审核失败.md`：标记为 `fixed-in-platform-publish`，说明旧 `xhs-publish-*` 是历史名称。
- `feedback/2026-06-22_douyin-publish_登录态无效且缺少填表模式.md`：新增抖音未打通问题记录。
- `skills/platform-publish/SKILL.md`：发布前先确定平台、账号、最终提交权限，并固定网络前置门。
- `skills/platform-publish/references/xiaohongshu.md`：小红书发布网络、本地上传 CDN、测试号稳定性门槛。
- `skills/platform-publish/references/douyin.md`：标明当前抖音未打通，且无 fill-only / manual-submit 模式。
- `skills/platform-publish/references/wechatsync.md`：去掉“小红书/公众号路由到专用 Skill”的旧表述。
- `engines/route-bypass/scripts/publish-network-preflight.zsh`：发布平台统一网络前置入口。
- `engines/route-bypass/domains.txt`：发布平台域名清单，含小红书上传 CDN、抖音/视频号/B站/公众号/文章草稿平台。
- `engines/xiaohongshu/README.md` / `SKILL.md` / `CLAUDE.md`：改成底层 engine 说明，不再作为可触发发布 Skill。
- `skills/xhs-interact/SKILL.md`：把详情来源引用从旧 `xhs-fetch` 改为 `platform-fetch`。

## 验证记录

```bash
python3 scripts/check-tools.py
# 56 ok, 0 warnings, 0 errors

git diff --check
# pass

python3 scripts/sync-skills.py --dry-run
# platform-publish / platform-fetch / xhs-auth / xhs-interact 等入口正常；没有要移除的 stale trigger

ls ~/.claude/skills | rg '^xhs-publish|^xhs-fetch|^gzh-publish$|^wechatsync$|^shipinhao-publish$' || true
# no output
```

## 后续待办

1. 抖音：补 `--fill-only` / `--draft`，先用测试号跑通登录、上传、封面、标签、定时/人工停留页，再允许真实账号。
2. 小红书 auth：如后续确实要支持“用户提供 Cookie 字符串导入账号”，再实现 `import-cookies` 和 `check-creator-login`。
3. 小红书视频：继续坚持测试号稳定门槛；在测试号未连续跑通前，不对真实账号执行自动最终发布。
4. 网络：任何平台上传阶段发现新动态 CDN 域名/IP，先补 `route-bypass` 并重新 `publish-network-preflight apply`，不要关闭全局 exit node。
