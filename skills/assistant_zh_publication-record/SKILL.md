---
name: assistant_zh_publication-record
description: |
  发布「状态记账」skill。用于一条正式 item 发布前后的本地状态协议：读取 `content/content_index.yaml`
  和 `content/<persona>/items/<content_id>/`，写/更新 `published.md`，回填对应 `destinations[]`
  的 `state`、`published_at`、`note_url`、观察窗口。实际上传、填表、点击发布不由本 skill 负责，
  必须转 `Agent-Publish`；发布前物料准备转 `content-package-create`。
compatibility: Codex
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
---

# assistant_zh_publication-record

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


你负责发布的**状态协议**，不负责写作，也不负责实际把内容传到平台。

实际排版上传（小红书 / 公众号 / 视频号 / B站 / 抖音 / 文章分发平台）统一调用
`Agent-Publish` skill，并按它的平台 reference 执行。发布前标题、正文、封面标题、
摘要、关键词、卡片等素材准备统一调用 `content-package-create` 或对应素材 skill。

## 输入

- `content/content_index.yaml` 中该 item 的 `current_state` 和 `destinations[]`
- `content/<persona>/items/<content_id>/draft.md`
- 若已准备平台发布包：`content/<persona>/items/<content_id>/publish_<account>.md`
- 若平台发布已完成：平台返回或公开验证得到的 `published_at`、`note_url`、实际展示标题

## 输出

- `content/<persona>/items/<content_id>/published.md`
- `content/content_index.yaml` 中对应 `destinations[]` 条目的发布字段：
  `account` / `platform` / `publish_format` / `state` / `scheduled_for` /
  `published_at` / `note_url` / `publish_title` / `stats_windows` / `note`

## 规则

1. 一条 item 可有多个发布目标，状态记账以 `destinations[]` 为单位。
2. 正式发布前，目标 item 必须存在，且通常应为 `current_state: ready_to_publish`；若只是回填一个用户已经发布并可公开验证的历史结果，可以作为补账处理，但必须写明证据来源。
3. 账号以 `content/accounts.yaml` 和 `destinations[].account` 为准，不凭记忆猜账号或 cookie/profile 名。
4. 某个目标发布成功后，先在该 item 目录写/更新 `published.md`，再把对应 destination 推进：
   - 有真实公开链接且可后续拉数：`state: observing`
   - 平台无可靠链接但已验证提交成功：`state: published`，并在 `note` 说明缺口
   - 仅定时/草稿：分别写 `scheduled` / `pending`，不要假装已发布
5. 发布链接、发布时间、发布账号缺一不可；不要把错误链接或旧笔记链接写进当前 item。
6. 对小红书、公众号等需要观察数据的平台，补 D+1 / D+3 / D+7 `stats_windows`。
7. 若平台 CLI 显示成功但公开页未刷出，继续用平台 reference 的验证方式查；仍查不到时停止并说明“已提交但未拿到可验证链接”，不要编造。

## 与平台发布的衔接

- 用户说“发到 / 发布到 / 同步到 / 创建草稿 / 上传文章 / 发小红书 / 发公众号 / 发视频号”：
  先用 `Agent-Publish` 完成实际平台动作，再回到本 skill 写状态。
- 用户说“发布包 / 标题正文封面 / 小红书卡片 / 公众号封面 / 预发布物料”：
  先用 `content-package-create`、`markdown-to-cards` 或对应素材 skill，用户确认后再发布。
- 用户要求“取消发布”且发布页已填好：
  按 `Agent-Publish` reference 保存草稿或保留现场，本 skill 只记录最终结果。
