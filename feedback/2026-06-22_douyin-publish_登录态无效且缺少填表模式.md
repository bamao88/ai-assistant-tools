# douyin-publish 登录态无效且缺少填表模式

## 状态

fixed

## 处理进展

2026-06-22：已给 `sau douyin upload-video` / `upload-note` 增加 `--fill-only` 和 `--hold-seconds`。`--fill-only` 会强制有头浏览器，上传并填写内容后停在最终发布按钮前，不点击“发布”。已补单元测试覆盖 fill-only 分支不会调用最终发布 callback。

2026-06-22：测试号 `测试号_抖音` 已通过真实 fill-only 复测：本地网络 preflight 后，视频上传进入 `post/video`，标题/简介/话题填入，横版/竖版封面上传，自主声明选择完成，最终停在发布页并输出 `Douyin video filled, ready for manual submit`，未点击发布。

2026-06-22：修复新版创作者中心入口：先打开左侧“高清发布”菜单并选择“发布视频/发布图文”，再等待对应 `input[type=file]`；同时将发布页表单等待延长到 120s，并改用新版标题/简介 selector。

2026-06-22：修复网络 preflight：无 TTY 时使用 macOS 管理员授权窗口，抖音新增静态 `/24` 网段兜底，避免 DNS 换边缘 IP 后又落回 Tailscale/proxy。

2026-06-22：追加网络反馈：这次视频上传慢/失败不是 Skill 完全没写本地网络要求，而是抖音上传阶段出现了新动态 CDN 网段，且浏览器已建立的旧 TCP 连接不会因为后面补路由自动切换出口。后续应把 `publish-network-preflight` 下沉到 CLI/engine 的自动强制门，并在上传期审计浏览器 NetworkService 的远端 IP；发现平台相关连接仍从 Tailscale/代理出口出去时，应自动失败并提示补路由、重启上传会话。

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
- 修复后：已支持 `--fill-only`，测试号真实上传填表链路已通过；真实账号发布仍需先确认账号和最终提交权限。

## 期望行为

- 发布 skill 默认 `manual-submit` 时，抖音流程只能完成登录校验、素材上传、标题/正文/标签/封面填表，并停在人工最终确认页。
- 只有用户明确授权 `agent-submit` 时，工具才允许点击最终“发布/定时发布”。
- 抖音测试号先完成 `login` + `check` + 一次低风险完整复测，再把 reference 标为可用于真实账号。

## 建议修复

1. ~~给 `sau douyin upload-video` / `upload-note` 增加 `--fill-only` 或 `--draft` 参数，默认不点击最终发布。~~
2. ~~用测试号跑通视频上传、封面、标签、人工停留页，再更新 `skills/platform-publish/references/douyin.md` 的当前状态。~~
3. 后续可继续细化 CLI 账号态错误分类：缺 cookie / cookie 失效 / creator 登录态失效分开返回。
