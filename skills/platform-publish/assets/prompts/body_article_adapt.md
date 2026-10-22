---
doc: 长文 → 各平台正文改写 指引
consumes: 已定稿 draft.md（生产态出口）
produces: 各平台适配正文（进 publish_<account>.md 的正文段）
reuse: platform-publish/references/_core-brief.md + assets/platform_rules.yaml
---

# 长文 → 各平台正文改写

长文 item（公众号/知乎/…）进入发布包生成阶段时，`draft.md` 是全文真源。按目标平台的 `body` 规则（`platform_rules.yaml`）改写：

| 目标 | 正文形态 | 怎么改 |
|---|---|---|
| 完整长文系（gzh / wechatsync 文章） | 全文 + 排版优化 | 不压缩；加粗金句、引用块、列表、`---` 分节、图注（范例 `content/zh_assistant/items/ZHC20260616_182817_001/publish_gzh.md`） |
| 压缩系（小红书图文） | 卡片正文 ≤1000 字 + 发布页 description 280-1000 字 | 卡片正文回到 `core_brief.md` 的核心判断和标题/封面种子重写；发布页 description 单独写 SEO 描述，目标 400-800 字，放核心判断、场景词、工具词、目标人群和边界；结尾不挂 CTA（`feedback_xhs_no_cta_hook_in_body`） |
| 视频 desc 系（视频号/B站/抖音） | 短 desc + tags | 正文来自切片管线（`body_video.md`），不从长文生成 |

- 不裸搬：各平台字数/形态不同，按 `platform_rules.yaml` 和对应 reference 重排，不是一稿照贴。
- 不跨平台取材：不能从小红书标题、视频号短标题、B站简介等已经压缩过的成品字段继续改；一律回到 `core_brief.md` 的平台无关种子重新生成。
- 小红书图文不要只写 50-100 字摘要。发布页 description 是检索入口，应覆盖标题里的核心词、正文里的关键判断、卡片没有展开但用户会搜的词；热词只能在真实相关时进入，不为蹭词硬塞。
- persona 声音不破：主号张和第一人称/企业AI落地；副号课代表视角。
- 文章表达润色在 ready_to_publish 前应由 `article-expression-polish` 完成，本阶段不重复。
