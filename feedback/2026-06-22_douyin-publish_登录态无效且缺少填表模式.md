# douyin-publish 登录态无效且缺少填表模式

## 状态

open

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
- `sau douyin check --account 张和` 返回 `invalid`。
- `tools/var/state/social-auto-upload/cookies/` 当前没有 `douyin_张和.json`。
- 最近 `vendor/social-auto-upload/logs/douyin.log` 里的登录尝试停在二维码登录阶段，最终报 `Target page, context or browser has been closed`。
- `upload-video` / `upload-note` 在流程尾部直接点击“发布”，没有 fill-only / draft / manual-submit 模式。

## 期望行为

- 发布 skill 默认 `manual-submit` 时，抖音流程只能完成登录校验、素材上传、标题/正文/标签/封面填表，并停在人工最终确认页。
- 只有用户明确授权 `agent-submit` 时，工具才允许点击最终“发布/定时发布”。
- 抖音测试号先完成 `login` + `check` + 一次低风险完整复测，再把 reference 标为可用于真实账号。

## 建议修复

1. 给 `sau douyin upload-video` / `upload-note` 增加 `--fill-only` 或 `--draft` 参数，默认不点击最终发布。
2. 给 CLI 输出明确的账号态检查结果，缺 cookie / cookie 失效 / creator 登录态失效要分开返回。
3. 用测试号跑通视频上传、封面、标签、定时发布或人工停留页，再更新 `skills/platform-publish/references/douyin.md` 的当前状态。
