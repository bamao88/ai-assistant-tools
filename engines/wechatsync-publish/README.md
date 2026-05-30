# wechatsync-publish

在开源 `@wechatsync/cli` 外面包一层的封装脚本。**底层完全复用 wechatsync**，本目录不重写任何平台适配器——多平台发布的维护成本交给上游开源项目，这里只做稳定性优化。

## 为什么有这个封装

直接用 `wechatsync` 命令时踩过的坑（已定位）：

1. **僵尸进程占端口**：命令中断会留下 `node .../@wechatsync/cli/dist/index.js` 进程占住桥接端口 9527/9528，后续所有命令报「已有实例正在运行但 Chrome Extension 未连接」。该进程名不含 `wechatsync`，极难排查——这是之前反复"连不上"的真正根因。
2. **没有同步前预检**：登录态掉没掉，要等同步失败才知道。
3. **账号混淆**：有些平台登录的不是张和本人（B站=MiaoDX、百家号=利幼枫0hK），容易误发。

封装脚本解决：跑前自动清残留 + 释放端口、先做登录态预检、账号白名单只发张和本人、解析草稿链接、跑完自动清理。

**不能解决（任何方案都不行）**：登录态过期本身。掉了得去对应平台重新登录——但脚本会精确告诉你掉的是哪几个，不用再盲查。

## 前置依赖

- 全局 `wechatsync`：`npm i -g @wechatsync/cli`
- 环境变量 `WECHATSYNC_TOKEN`（扩展设置里复制）
- 浏览器装 wechatsync 扩展，设置里「CLI / MCP 连接」开关**打开**（显示"已连接"而非"等待连接"），Chrome 保持开着

> 注意：扩展的「CLI / MCP 连接」是一次性等待——CLI 实例启动时扩展才会连上去。开关开着、状态停在"等待连接…"是正常的，脚本运行时会自动建立连接。

## 用法

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/wechatsync-publish

# 登录态预检（只读，不发任何东西）
./publish.sh check

# 同步草稿：清残留→预检→自动选张和本人账号平台→同步→报告草稿链接→清理
./publish.sh sync /tmp/article.md --title "标题" --cover /tmp/cover.png
```

`sync` 选项：
- `--title "标题"`：建议显式给，否则 wechatsync 从文件首个 `#` 提取
- `--cover <图片>`：封面图本地路径或 URL
- `--platforms a,b,c`：手动指定平台，覆盖白名单自动选择
- `--all-accounts`：允许同步到非张和本人账号的平台（默认跳过）
- `--dry-run`：只预览不实际写草稿

**所有平台均为草稿，最终发布需手动点。**

## 账号白名单

脚本里 `ZHANGHE_ACCOUNTS` 关联数组定义"平台 → 期望账号名关键词"。当前登录账号名包含该关键词才视为张和本人、才会被自动选中同步。新增平台或张和换账号名时改这里即可。

## 已知平台情况（截至 2026-05-29）

| 平台 | 张和账号 | 备注 |
|---|---|---|
| zhihu 知乎 | 张和 | ✓ 可发 |
| toutiao 头条 | 张和AI产品 | ✓ 可发 |
| csdn | 张和All in AI | ✓ 可发 |
| jianshu 简书 | 张和AllinAI | ✓ 可发 |
| juejin 掘金 | 张和AllinAI | ⚠ 报 `must bind phone`，需先在掘金后台绑手机号 |
| weixin 公众号 | 张和专业讲AI | 建议走专用 `gzh-publish`，排版更好 |
| bilibili | MiaoDX | ✗ 非张和本人，默认跳过 |
| baijiahao 百家号 | 利幼枫0hK | ✗ 非张和本人，默认跳过 |
| douyin 抖音图文 | — | 需配图，默认跳过 |
