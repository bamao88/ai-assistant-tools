# platform-publish 问题进度日志

## 日期

2026-06-22

## 范围

记录当前发布相关 Skill / engine / feedback 的收敛状态。正式发布入口只有 `skills/platform-publish`；旧的独立发布触发入口不再使用。

## 当前结论

| 问题 | 状态 | 当前处理 |
|------|------|----------|
| 小红书发布是否还有旧 `xhs-publish-*` Skill | closed | 当前正式入口只有 `platform-publish`。`registry.yaml: deprecated` 已标记 `xhs-publish` / `xhs-publish-article` / `xhs-publish-post` / `xhs-publish-video` 废弃，`scripts/sync-skills.py` 会移除 stale trigger。 |
| 小红书 Tailscale exit node 导致发布审核失败 | superseded | 旧方案曾使用发布前本地路由分流；2026-07-01 已撤销发布链路的本地路由门，默认直接走当前网络。 |
| 小红书 auth 缺少 `import-cookies` / `check-creator-login` | open, not blocking publish | 这是认证工具增强项：仅在“用户直接给 Cookie 字符串要求导入账号并验证 creator 后台登录态”时需要。正常扫码登录和当前 `platform-publish` 发布流程不依赖。 |
| 抖音发布流程是否已打通 | reopened, test-account-required | 测试号曾跑通 fill-only，但真实账号 `张和` 自动定时发布暴露 cookie 校验不一致、`--headed` 未贯穿、封面 modal 阻塞、异常后无法接管当前会话等问题。结论改为：暂停真实账号自动提交，先用测试号把 headed 全链路和异常接管调通。 |
| 抖音定时发布能力 | partial, not production-ready | 测试号 fill-only 可切到“定时发布”并校验时间值；但真实账号最终定时提交链路未稳定，尤其封面 modal 会阻塞后续定时设置。不能再把“测试号 fill-only 成功”视为真实账号自动定时发布可用。 |
| 发布网络是否统一走本地网络 | closed-by-removal | 2026-07-01 已撤销：`platform-publish` 不再有发布网络模式，不再运行 `publish-network-preflight`，小红书/视频号 CLI 内置路由检查也已删除；发布默认直接走系统当前网络。 |
| Wechatsync 与小红书/公众号发布入口混淆 | fixed | `wechatsync.md` 已明确：`weixin` / `xiaohongshu` 不通过 Wechatsync 发布，继续留在 `platform-publish` 内对应 reference。 |
| engine 文档误导为可触发小红书 Skill | fixed | `engines/xiaohongshu/README.md` / `SKILL.md` / `CLAUDE.md` 已改为底层 engine 文档，明确发布走 `skills/platform-publish`。 |

## 已更新文件

- `feedback/2026-05-17_xhs-auth_cookie导入缺少标准命令.md`：补充状态和解释，明确不是当前发布流程阻塞项。
- `feedback/2026-04-09_xhs-publish_Tailscale-exit-node导致发布审核失败.md`：标记为 `fixed-in-platform-publish`，说明旧 `xhs-publish-*` 是历史名称。
- `feedback/2026-06-22_douyin-publish_登录态无效且缺少填表模式.md`：新增抖音问题记录；后续已用测试号验证 fill-only 链路。
- `feedback/2026-06-22_douyin-publish_登录态无效且缺少填表模式.md`：追加真实账号试跑反馈，状态从 `fixed` 改为 `open`；明确暂停真实账号自动提交，先用测试号调通。
- `skills/platform-publish/SKILL.md`：发布前先确定平台、账号、最终提交权限；已移除发布网络模式。
- `skills/platform-publish/SKILL.md`：新增正式账号活跃会话异常处理原则：真实账号已上传/已填表时，优先接管当前页面完成本条，发布后再修脚本；不要先关闭流程再重传。
- `skills/platform-publish/references/xiaohongshu.md`：保留小红书测试号稳定性门槛；已移除本地路由前置说明。
- `skills/platform-publish/references/douyin.md`：更新为抖音测试号 fill-only 已跑通，保留测试阶段禁止最终发布和最多 5 个话题限制。
- `skills/platform-publish/references/wechatsync.md`：去掉“小红书/公众号路由到专用 Skill”的旧表述。
- `engines/route-bypass/`：保留为转录链路与历史诊断工具，不再由 `platform-publish` 调用。
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

1. 抖音：暂停真实账号自动提交。用测试号重新跑 headed 全链路：cookie check、上传、标题/描述、话题联想、竖版/横版封面、封面 modal 关闭、自主声明、定时发布时间写入、最终按钮前停留。
2. 抖音：补“异常时当前会话保活/接管”能力。正式账号发布时如果弹窗/按钮/校验阻塞，不能立刻退出并重传；应保留 headed 窗口，输出当前 URL、弹窗文本和可操作诊断，允许在当前会话内处理。
3. 抖音：统一 cookie 管理。`check`、`login`、`upload-video`、`upload-note` 必须共用同一创作者中心发布入口校验；发布结束后刷新 storage state，避免入口层有效、上传器内部又误判失效。
4. 抖音：真实账号恢复条件必须写清楚：测试号 headed + fill-only + 定时 fill-only + 至少一次异常弹窗恢复链路通过后，才允许回到 `张和` 真实账号逐条发布。
5. 小红书 auth：如后续确实要支持“用户提供 Cookie 字符串导入账号”，再实现 `import-cookies` 和 `check-creator-login`。
6. 小红书视频：继续坚持测试号稳定门槛；在测试号未连续跑通前，不对真实账号执行自动最终发布。
7. 网络：发布链路不再维护本地路由前置门。上传慢或失败时，优先保留当前页面、检查登录态、素材路径、页面提示和浏览器上传状态；不要把补路由作为默认步骤。

## 2026-06-22 真实账号试跑补充记录

- 用户重新生成并提供了抖音 cookie，已导入 `张和` 账号 cookie 文件；反馈文件不记录 cookie 内容。
- 前 3 条真实账号定时发布曾成功提交；随后真实账号继续发布时暴露流程问题，后续 9 条没有继续完成。
- `ZHC20260613_evc15_001` 两次真实账号尝试均未成功定时提交：
  - 第一次：封面/推荐封面相关 modal 阻塞“定时发布”单选，流程退出。
  - 第二次：封面完成按钮选择器无法找到新版 modal 的可见按钮，流程退出。
  - 最后一次用户中断时：视频已上传、话题已选择，准备设置封面；页面随后关闭，没有进入定时发布和最终提交。
- 用户明确反馈：正式账号发布中遇到问题，应优先处理当前打开的发布页，把当前任务完成；发布后再修脚本。不能频繁关闭已上传/已填写的流程并重新上传，这会带来风控风险。
- 当前决策：抖音发布流程回到测试号调试阶段。真实账号不再作为调试载体，直到测试号链路稳定。
