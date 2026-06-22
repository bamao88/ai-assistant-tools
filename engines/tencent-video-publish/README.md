# tencent-video-publish

视频号视频发布 engine，基于 `dreammis/social-auto-upload` 的 `uploader/tencent_uploader` 思路做本地 CLI 化。

能力边界：

- 支持视频号扫码登录、登录态检查、视频上传、保存草稿、正式发表、定时发表。
- 暂不支持视频号图文；上游 `TencentNote` 相关方法仍未实现。
- 默认保存草稿；只有显式传 `--publish` 才点击“发表”。

登录态：

- 账号按 slot 隔离，凭证保存在 `var/state/tencent-video-publish/accounts/<slot>/`。
- 正式登录态只认 Playwright/patchright `storage_state.json`；历史遗留的 `chrome-profile/` 只用于列表展示和诊断，不参与登录检查、扫码登录或发布。
- 写入凭证时先写临时文件并校验 JSON，再替换正式文件。
- 替换前保留最近的 `storage_state.json.bak_*` 备份。
- `check-login` 会在凭证缺失或 JSON 损坏时自动尝试恢复最新有效备份。
- 扫码登录强制使用可见 Chromium；headless QR 登录回调不稳定。扫码成功后保存新的 `storage_state.json`；需要验证时继续运行 `check-login`。
- 手动拿到 Cookie header 时，用 `import-cookies` 先写入候选 storage state；导入命令默认打开发布页验证，只有验证已登录才会替换正式 `storage_state.json`，未登录会非零退出且正式凭证不变。
- 当前约定：`aipm` 是默认账号，也是测试号；`zhanghe` 是张和视频号真实账号。

初始化：

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-video-publish
uv sync --python 3.11
```

网络预检：

- 发布前会自动执行视频号本地网络预检。
- 视频上传阶段会访问独立 CDN：`finderassistancea/b/c/d/e.video.qq.com`、`mmec.wxqcloud.qq.com.cn`、`res.wxqcloud.qq.com.cn`。
- 这些域名必须和 `channels.weixin.qq.com` 一起走本地网络，否则上传可能卡在 0% 或明显变慢。

常用命令：

```bash
.venv/bin/python scripts/cli.py list-accounts
.venv/bin/python scripts/cli.py add-account --slot wxp --description "WXP 视频号"
.venv/bin/python scripts/cli.py set-account-roles --slot aipm --test
.venv/bin/python scripts/cli.py --account wxp login --timeout 180
.venv/bin/python scripts/cli.py --account wxp check-login
.venv/bin/python scripts/cli.py --account wxp import-cookies --cookie-file /tmp/wxp.cookies
.venv/bin/python scripts/cli.py --account wxp --headed upload-video --file /abs/video.mp4 --title "标题" --desc "简介" --tags AI 工具
.venv/bin/python scripts/cli.py --account wxp --headed upload-video --file /abs/video.mp4 --title "测试" --fill-only --hold-open -1 --upload-timeout 90 --cover-timeout 10
```

手动 Cookie 导入：

```bash
umask 077
printf '%s' "$COOKIE_HEADER" > /tmp/wxp.cookies
.venv/bin/python scripts/cli.py --account wxp import-cookies --cookie-file /tmp/wxp.cookies
rm -f /tmp/wxp.cookies
```

不要把 Cookie 值写进文档、日志或提交。导入输出只会显示 cookie 名称、数量和登录验证结果，不回显 cookie 值。

`--no-verify` 只保存候选凭证文件，不会替换正式 `storage_state.json`；只有验证通过的候选凭证才会被提升为正式凭证。

封面说明：

- 视频号会先自动生成默认封面；页面停在“生成中”时，手动上传封面的入口不可用。
- 传入 `--thumbnail` 时，CLI 默认等待 `--cover-timeout 60` 秒后再上传自定义封面。
- 如果超时仍在“生成中”，`--fill-only` 会返回 `thumbnail_warning` 并停在提交前；保存草稿/正式发表会直接失败，避免误以为封面已上传。
- 用户要求上传完成后停在页面时，使用 `--fill-only --hold-open -1`；这不会点击“保存草稿”或“发表”。

原创声明：

- 视频号原创入口需要两步：先点页面里的“声明原创”勾选项，再在“原创权益”弹窗里勾选协议并点击“声明原创”。
- 原创入口必须等视频上传处理、封面、定时等内容都填完后再处理；过早查找会出现入口未渲染或 checkbox disabled。
