---
name: assistant_zh_platform-adapt
description: |
  一条已定稿内容要发到多个平台时的跨平台改写统一入口。把某 persona 的主发版本改写成小红书、B站、视频号、知乎、头条、CSDN、掘金等目标平台形态，而不是裸搬或临时压短。
  用户说"发小红书版""改成小红书/B站/视频号/知乎版""一稿多发""同步到 X 平台""把这篇压成卡片"，且源稿已定稿时使用。
  不处理从 0 写主发稿；不处理纯发布上传（走 Agent-Publish）；不处理发布前上传素材生成（走 content-package-create / markdown-to-cards）。
compatibility: Codex
---

# 跨平台改写

## 项目与路径

这是 `assistant_zh` 项目专属 Skill，不能作为其他账号的默认方法。业务资料、账号、状态和产物的相对路径统一以 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/` 为根；先读取该项目 `AGENTS.md` 及其指定的权威政策。Skill 自带的 `reference/`、`references/`、`scripts/`、`templates/` 等路径则从本 Skill 的 canonical 目录解析，不能从项目工作目录或旧 Claude 安装目录猜路径。

唯一维护源在 `tools/skills/`；原项目 `.agents/skills/` 路径为兼容软链。业务数据与运行产物留在项目，不写进本 Skill 包。


本 skill 负责把已经定稿的源稿改成目标平台版本。它只换平台形态，不换 persona。

发布字段的长度、关键词与模板以 `content-package-create` 当前引用的通用平台规格为准；本目录维护张和账号的内容改写和 persona 约束，不维护第二套发布字段规格。

## 输入 / 输出

- 输入：`content/<persona>/items/<content_id>/draft.md` 或已定稿主发版本，`persona` 为 `zh_main` / `zh_assistant`
- 输入：目标平台和目标 account（以 `content/accounts.yaml` / `content/content_index.yaml` 为准）
- 输出：`content/<persona>/items/<content_id>/adapt_<platform>.md` 或 `publish_<account>.md`
- 输出：必要时回填对应 destination 的 `publish_title` / `publish_body_ref` / `tags` / `cover_ref`

## 决策顺序

1. 先确认源稿已经定稿。未定稿时回到内容生产流程，不做跨平台改写。
2. 确认 persona：
   - `zh_main`：张和本人视角，保持企业 AI 落地、AI 产品 / Agent 工程 / 一线判断的声音，不写成课代表或营销号。
   - `zh_assistant`：AI PM 超级小助理 / 课代表视角，不冒充张和本人，不使用张和个人经历。
3. 确认目标平台，并按下方 rubric 改写。
4. 改写后做一次独立自检：persona 是否破、是否裸搬、是否符合目标平台信息密度、是否有 AI 味。

## 平台 Rubric

### 小红书图文 / 卡片

- 平台标题要有搜索场景词，优先覆盖目标人群和问题，例如企业 AI 落地、AI 解决方案、AI 服务商、AI 售前、ToB 供应商、FDE。
- 封面标题更短，直接给判断或反差，不等于平台标题。
- 发布页正文用多段，不写成一整段；精选原文核心判断，长度按 `content-package-create` 当前平台规格核对，关键词另放独立字段。
- 卡片一页一个意思，首图是钩子卡，后续卡片承接论证。
- 生成卡片走 `markdown-to-cards`；实际发布走 `Agent-Publish` 的小红书 reference。

### B站 / 视频号

- 开头 5 秒直接抛结论或冲突。
- 书面长句拆成口播短句，一句一信息点。
- 字幕友好，避免复杂长从句。
- 视频号更短、更钩子前置。

### 知乎 / 头条 / CSDN / 掘金等文章平台

- 这些属于长文平台，通常轻改，不要过度压缩。
- 知乎更问题导向，论证要完整。
- 头条标题更直白，信息差前置。
- CSDN / 掘金可保留技术术语、架构、代码和工程细节。

## 边界

- 改写不是发布。发布上传必须走 `Agent-Publish`。
- 改写不是发布前状态记账。发布结果回填必须走 `assistant_zh_publication-record`。
- 不凭记忆猜账号，不把一个 persona 的声音改成另一个 persona。
