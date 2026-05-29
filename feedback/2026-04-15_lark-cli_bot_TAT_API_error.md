# lark-cli bot 身份发送消息失败

**status: fixed**
**处理日期: 2026-04-15**

## 根因

lark-cli keychain 存储中 `appsecret:cli_xxx` 条目丢失（仅保留 `master.key`），导致 bot 无法获取 app_access_token，Lark API 返回 `[10003] invalid param`。

与 lark-cli 版本无关（v1.0.10 / v1.0.11 均复现）。

## 修复

用 `lark-cli config init --app-secret-stdin` 重新写入所有 profile 的 appSecret 到 keychain：

```bash
echo "<app_secret>" | lark-cli config init [--name <profile>] --app-id <app_id> --app-secret-stdin --brand feishu
```

已重建 profiles：默认（zh）、zh、hj、wxp、mdx、manage。凭证来源：`~/.cc-connect/config.toml`。

## 验证

```bash
lark-cli im chats list --profile mdx --as bot  # → code: 0, 成功
lark-cli im chats list --profile zh --as bot   # → code: 0, 成功
```

**日期**：2026-04-15
**工具**：lark-cli im +messages-send（及所有 bot 操作）
**Profile**：mdx、zh（多 profile 均失败）

## 复现步骤

```bash
lark-cli im +messages-send --profile mdx --as bot --chat-id oc_934fd04e786739bbe0c55948fa26eb34 --text "test"
```

## 期望行为

消息发送成功，返回 message_id。

## 实际行为

```
Error: TAT API error: [10003] invalid param
```

所有 bot 操作均失败，包括：
- `im +messages-send`
- `im +chat-search`
- `im chats list`

## 时间线

- 2026-04-11 ~ 2026-04-13：正常工作（有成功发送记录）
- 2026-04-14：开始失败
- 2026-04-15：更新 lark-cli 至 1.0.11 后仍失败

## 补充

- user 身份操作返回 `need_user_authorization`（不同错误，非同一问题）
- 错误类型有时为 `api_error`，有时为 `network`
- dry-run 模式下请求格式正确，问题在实际 API 调用阶段
