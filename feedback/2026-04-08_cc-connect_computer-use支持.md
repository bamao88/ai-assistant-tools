# 需求：cc-connect 环境下启用 Claude Code computer use

## 场景
内容运营 Agent 写文章时，需要实测产品功能并截图（如打开 ChatGPT 演示购物功能、截取界面图放进文章）。目前只能让用户手动截图。

## 现状
- Claude Code v2.1.85+ 已内置 `computer-use` MCP server（截屏、鼠标/键盘控制、GUI 操作）
- 但只支持**交互式会话**，不支持 `-p` 非交互模式
- cc-connect 启动 Claude Code 时用的是 `--input-format stream-json`，属于非交互模式
- 所以目前 cc-connect 环境下无法使用 computer use

## 期望
在 cc-connect 环境中也能启用 computer use，至少支持：
1. 截屏（查看当前屏幕内容）
2. 打开应用并操作（打开浏览器/ChatGPT、输入内容、截图）
3. 权限通过 bypassPermissions 或预授权方式处理

## 可能的方案
1. cc-connect 启动参数中加入 computer-use 相关配置
2. 或者通过独立的 MCP server 实现（如 SebastianBaltes/claude_code_computer_use_mcp）
3. 或者在需要 computer use 时启动一个独立的交互式 Claude Code 会话

## 优先级
中等。目前可以让用户手动截图替代，但有了这个能力后文章质量会更高（实测截图 > 官方素材）。

## 来源
assistant_zh 内容运营 Agent，2026-04-08
