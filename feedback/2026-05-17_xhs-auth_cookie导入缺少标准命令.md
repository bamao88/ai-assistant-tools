# xhs-auth cookie 导入缺少标准命令

## 状态

open（认证工具增强项，不是 `platform-publish` 当前发布流程的阻塞项）

## 当前解释

这条反馈说的是：如果用户直接给一串小红书 Cookie header，希望 Agent 把它导入某个命名账号，目前没有标准 CLI 子命令，只能临时用 CDP/浏览器脚本写入 Chrome profile；同时现有 `check-login` 主要检查常规登录态，不能清楚区分 `www.xiaohongshu.com` 登录态和 `creator.xiaohongshu.com` 发布后台登录态。

正常扫码登录、已登录账号发布、`platform-publish` 的小红书发布流程不依赖这个能力。只有“新增账号时用户给 Cookie 字符串、要求直接导入并验证 creator 后台登录态”时才会遇到。

## 复现步骤

1. 用户提供新账号名称和一组小红书 creator 端 Cookie 字符串，要求加入小红书发布 skill 的多账号列表。
2. 使用 `scripts/cli.py add-account --name MiaoDX --description MiaoDX` 可以成功创建账号配置。
3. 现有 CLI 没有 `import-cookies` / `set-cookies` 子命令，只能通过临时 CDP 脚本把 Cookie 写入该账号 Chrome profile。
4. 写入后执行：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account MiaoDX check-login
```

## 期望行为

- xhs-auth 提供标准命令从 Cookie header 字符串导入指定账号，例如：

```bash
cli.py --account <name> import-cookies --cookie-file <path>
```

- 导入后能明确验证发布域名 `creator.xiaohongshu.com` 的登录态，或者在输出中区分：
  - www 端未登录
  - creator 发布端已登录
  - Cookie 无效或缺少必要字段

## 实际行为

- 账号配置可以创建，但 Cookie 导入没有标准入口。
- 使用 CDP 成功写入 15 个 `xiaohongshu.com` Cookie 后，`check-login` 仍返回 `logged_in: false`，并生成二维码。
- 这组 Cookie 主要是 creator 端字段，可能不足以通过 `www.xiaohongshu.com/explore` 的登录检测；当前工具输出没有区分这一点。

## 日志片段

```text
添加账号: MiaoDX (port=9226)
parsed_cookie_count: 15
stored_xhs_cookie_count: 15
check-login: logged_in=false, login_method=qrcode
```

## 建议

- 增加 `import-cookies` 子命令，避免 Agent 临时写 CDP 脚本处理敏感 Cookie。
- 增加 `check-creator-login` 或让发布流程在访问发布页前验证 creator 域名登录态。
- 反馈和日志中必须屏蔽 Cookie 值，只输出 Cookie 名称和计数。
