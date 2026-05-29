# tencent-video-publish 登录态 storage_state 不稳定

## 复现步骤

1. 使用 `cli.py --headed login --timeout 180` 扫码登录视频号助手。
2. 随后多次使用 `cli.py check-login` 或 `cli.py --headed upload-video --fill-only ...`。
3. 观察登录态在短时间内失效，或 `check-login` 返回 `cookie_invalid`。

## 期望行为

扫码成功后，后续 skill / Claude Code 调用可以稳定复用同一账号登录态完成上传表单填写。

## 实际行为

`storage_state.json` 内主要只有 `channels.weixin.qq.com` 下的少量 cookie（如 `sessionid`、`wxuin`）和 localStorage。多次新建浏览器上下文后，登录态容易退回 `https://channels.weixin.qq.com/login.html`。

## 日志片段

```json
{
  "success": true,
  "logged_in": false,
  "status": "cookie_invalid",
  "current_url": "https://channels.weixin.qq.com/login.html"
}
```

## 处理记录

2026-05-28 已将视频号 engine 改为账号独立 `chrome-profile/` 优先，并继续导出 `storage_state.json` 作为兼容备份，减少仅靠 storage_state 冷启动导致的登录态不稳定。
