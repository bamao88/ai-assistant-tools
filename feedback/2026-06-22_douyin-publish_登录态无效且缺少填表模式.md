# douyin-publish 登录态无效且缺少填表模式

## 状态

open

## 处理进展

2026-06-22：已给 `sau douyin upload-video` / `upload-note` 增加 `--fill-only` 和 `--hold-seconds`。`--fill-only` 会强制有头浏览器，上传并填写内容后停在最终发布按钮前，不点击“发布”。已补单元测试覆盖 fill-only 分支不会调用最终发布 callback。

2026-06-22：测试号 `测试号_抖音` 已通过真实 fill-only 复测：视频上传进入 `post/video`，标题/简介/话题填入，横版/竖版封面上传，自主声明选择完成，最终停在发布页并输出 `Douyin video filled, ready for manual submit`，未点击发布。

2026-06-22：修复新版创作者中心入口：先打开左侧“高清发布”菜单并选择“发布视频/发布图文”，再等待对应 `input[type=file]`；同时将发布页表单等待延长到 120s，并改用新版标题/简介 selector。

2026-07-01：发布链路已撤销本地网络 preflight 要求，默认直接走系统当前网络；后续上传慢/失败按页面状态、登录态、素材路径和浏览器上传诊断处理，不再把补路由作为默认修复动作。

2026-06-22：测试号完成定时发布 fill-only 复测：`--schedule "2026-06-23 20:30"` 已成功切到“定时发布”，并读取页面输入值校验为 `2026-06-23 20:30`；流程停在最终发布页，未点击发布。

2026-06-22 追加：真实账号 `张和` 用新 cookie 跑正式定时发布时暴露出多处未覆盖问题。当前结论改为：**抖音真实账号自动定时发布流程未成熟，暂停继续真实账号自动提交；必须先用测试号把完整链路调通后再恢复。**

## 本轮新增问题（真实账号暴露）

### 1. Cookie 校验策略仍不够接近小红书

- 小红书发布流程稳定的关键之一是使用持久 Chrome profile / storage state，并在每次发布结束后刷新登录态；抖音原流程虽然部分位置也会 `context.storage_state(path=account_file)`，但登录态校验不够严格。
- 修复前的抖音 `cookie_auth()` 主要看 URL 和少量登录文案，无法可靠识别新版创作者中心的“创作者登录 / 高清发布 / 发布视频 / 发布图文”状态。
- 用户重新提供新 cookie 后，导入成功，但 CLI `check` 与上传路径中的二次校验表现不一致：入口层可以判定有效，上传器内部紧接着又误判 `cookie文件已失效`。
- 需要统一所有入口的 cookie 判定：以真实进入创作者中心发布入口为准，并在发布完成后刷新 cookie/storage state；不要让 `check`、`login`、`upload-video` 各自维护不同标准。

### 2. `--headed` 没有贯穿全链路

- 用户明确要求正式账号发布不要用 headless，窗口要前台显示。
- 修复前，上传命令即使传了 `--headed`，部分 cookie 校验仍固定用 headless 浏览器。
- 后续要求：正式账号发布默认使用 `--headed`，且登录态校验、上传、封面、定时、最终提交全部同一可见模式；测试号也应先覆盖 headed 模式。

### 3. 真实账号活跃会话异常处理方式错误

- 本次遇到弹窗/遮挡时，第一反应变成“退出流程、修脚本、重新上传”，这不适合正式账号。
- 用户反馈的正确原则：只要真实账号发布会话已经打开、素材已上传或表单已填写，遇到弹窗/校验/按钮阻挡，应优先接管当前窗口把这一条发布完成；发布完成后再修脚本。
- 频繁关闭已上传/已填写的真实账号流程，会提高平台风控和误操作风险。
- 该原则已写入 `skills/platform-publish/SKILL.md` 和 `assistant_zh/workflow/publishing-ops.md`，但抖音 engine 还缺少“异常时保持当前会话可接管”的实现。

### 4. 封面弹窗处理不稳，阻塞定时发布

- 真实账号发布 `ZHC20260613_evc15_001` 时，视频上传和话题选择已完成，进入封面步骤后抖音弹出新版封面/双封面相关 modal。
- 日志出现 `获取推荐封面超时`，并且 `verticalSupoortDualCoverModal-*` / `dy-creator-content-modal-*` 弹窗拦截后续点击。
- 原逻辑点击“完成”后只等 `div.extractFooter` 消失，不可靠；后续改成等 `[role="dialog"][aria-modal="true"]` 关闭，但实际 DOM 中旧选择器找不到 `button:visible:has-text("完成")`，仍失败。
- 最后一次被用户中断时，日志停在“视频已经传完啦 / 小人正在设置视频封面”，随后页面关闭；没有进入定时发布和最终提交。
- 需要用测试号复现并稳定覆盖：竖版封面上传、横/竖双封面、推荐封面超时 toast、封面 modal 按钮、封面 modal 关闭确认。

### 5. 失败时缺少可接管控制通道

- `sau` 当前在异常后容易让脚本退出，或者留下不可控的临时 Chrome 窗口；Agent 无法可靠接管当前页面继续完成发布。
- 后续应该支持正式账号发布的“保活/可接管”模式：
  - headed 窗口必须保持可见；
  - 异常时不要立刻关闭 page/context/browser；
  - 输出当前步骤、页面 URL、可见弹窗文本、建议人工/Agent 操作；
  - 最好固定 user data dir 或 remote debugging port，让 Agent 可以接管当前会话；
  - 未确认当前会话不可恢复前，不自动重新上传同一视频。

### 6. 批量真实发布策略过激

- 原计划把 9 条剩余真实账号内容按循环连续提交。虽然不是并发，但在链路未稳定时仍会放大风险。
- 后续真实账号只能在测试号完整链路跑通后逐条发布；每条成功并记录后再下一条。
- 真实账号批量/无人值守自动提交应暂缓。

## 发现日期

2026-06-22

## 复现/检查

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/vendor/social-auto-upload
.venv/bin/sau douyin --help
.venv/bin/sau douyin check --account 张和
```

## 当前行为

- `sau douyin` 有 `login` / `check` / `upload-video` / `upload-note` 入口。
- 修复前：`upload-video` / `upload-note` 在流程尾部直接点击“发布”，没有 fill-only / draft / manual-submit 模式。
- 修复后：已支持 `--fill-only`，测试号真实上传填表链路曾通过；但真实账号自动定时发布仍暴露 cookie 判定、headed 贯穿、封面弹窗、异常接管等问题，不能视为可稳定自动提交。

## 期望行为

- 发布 skill 默认 `manual-submit` 时，抖音流程只能完成登录校验、素材上传、标题/正文/标签/封面填表，并停在人工最终确认页。
- 只有用户明确授权 `agent-submit` 时，工具才允许点击最终“发布/定时发布”。
- 抖音测试号先完成 `login` + `check` + 一次低风险完整复测，再把 reference 标为可用于真实账号。
- 测试号必须覆盖 `--headed`、封面弹窗、定时发布时间写入、最终按钮前停留、异常时当前会话保活/接管。
- 真实账号发布过程中出现问题时，优先处理当前窗口完成本条，不先退出重开。

## 建议修复

1. ~~给 `sau douyin upload-video` / `upload-note` 增加 `--fill-only` 或 `--draft` 参数，默认不点击最终发布。~~
2. ~~用测试号跑通视频上传、封面、标签、人工停留页，再更新 `skills/platform-publish/references/douyin.md` 的当前状态。~~
3. 重新把抖音真实账号发布标为未成熟：先用测试号做 headed 全链路回归，不再直接用 `张和` 真实账号调试。
4. 统一 cookie 管理策略：导入 cookie 后做真实创作者中心发布入口校验；发布成功后刷新 storage state；`check`、`upload-video`、`upload-note` 共用同一校验逻辑。
5. 增加异常接管能力：headed 发布异常时保持当前窗口和浏览器上下文，输出可操作诊断，不自动退出并重传。
6. 用测试号补封面 modal 自动化：兼容新版双封面 modal、推荐封面超时 toast、按钮文案/DOM 变化。
7. 继续细化 CLI 账号态错误分类：缺 cookie / cookie 失效 / creator 登录态失效 / 发布入口不可用 / 平台弹窗阻挡分开返回。
