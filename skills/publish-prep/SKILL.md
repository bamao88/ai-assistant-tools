---
name: publish-prep
description: |
  发布前「素材准备」统一入口（scope: assistant_zh）。把一条已定稿 item（视频切片 / 长文）在真正上传前，
  按每个目标平台产出标准发布物料 publish_<account>.md：标题候选 / 各平台正文 / 封面标题文案 / 摘要 / 关键词。
  卡在 current_state==ready_to_publish 之后、实际上传（platform-publish）之前，是发布管线 step3「资产生成」的展开。
  当用户说"准备发布物料""生成标题/正文/关键词/封面标题""各平台文案""publish_copy""把这条切片配文做齐"
  "发前 prep""按平台适配正文"时使用。
  本 skill 不处理：实际上传/分发（用 platform-publish）、封面图渲染本身（视频→zh-video-cover / 长文→gzh 封面卡 / markdown-to-cards）、
  起标题公式库本体（用 dbs-xhs-title）、内容抓取（platform-fetch）、剪辑成片（video-clip）。
---

# 发布前素材准备（publish-prep）

你是「发布前素材准备器」。输入=一条 `ready_to_publish` 的 item（`content/<persona>/items/<id>/`，视频=成片+校正SRT / 长文=draft.md）；
输出=**按 destination 逐个产** `publish_<account>.md`（纯文字素材），交回发布管线上传。

## 结构（主轴=平台，form=内容形式副轴）

- 各平台素材规格 **单一真源** = `assets/platform_rules.yaml`（标题字数 / 正文形态 / 摘要 / 关键词数 / 封面规格 / form）。**不要凭记忆拼字数，照它抄。**
- 关键词池 = `assets/keyword_pool.yaml`（确定性，engine `build_keywords.py` 读它，数量按平台）。
- 模板 = `assets/templates/publish_<platform-key>.md`（**文件名 = platform_rules 的平台键**：xiaohongshu/gongzhonghao/shipinhao/bilibili/douyin/wechatsync）。模板内含各平台**下游解析契约**注释，照它填，别改 section 名。
- prompt = `assets/prompts/body_video.md`（视频正文，企业AI落地口径）/ `body_article_adapt.md`（长文→各平台改写）。
- 代码 = engine `tools/engines/publish-prep/`（`gen_copy.py` 正文 / `gen_title.py` 标题 / `build_keywords.py` 关键词 / `check.py` 校验）。

## 流程

**步骤 1 — 定契约（每 item）**：确认 persona；列 item 的 destinations（账号→平台→form）。账号→引擎参数真源 `content/accounts.yaml` + `workflow/publish_pipeline/resolve_account.py`。

**步骤 2 — 逐 destination 跑 6 子步**（读 `platform_rules.yaml[平台]`，both 平台按 `item.format` 取 variant）：

1. **正文**：视频→engine `gen_copy.py`（Kimi 读 `body_video.md`，`--platform`）→ **Claude 守门/重写**（我方优化，非直接采纳）；长文→按 `body_article_adapt.md` 各平台改写（复用 `zh-cross-platform-adapt`）。
2. **标题候选**：engine `gen_title.py --platform <平台> [--form <form>]`（dbs 75 公式，**字数上限自动从 platform_rules 按平台解析**：小红书20/视频号6-16/公众号64/B站80/抖音55）→ `workflow/writing_playbook/title.md` 三规律+红线守门 → 采用1+备选2-3（标公式号）。
3. **封面标题文案**（统一抽象·长文视频都产，非必填）：独立字段，≠正文标题；可与标题结合或独立；从候选标题挑（`feedback_cover_text_from_titles`）。
4. **摘要**：gzh digest ≤120 / xhs abstract 20–200，Claude 写。
5. **关键词**：engine `build_keywords.py <正文> --platform <平台>`（确定性，数量自动按平台）。gzh 无 hashtag（封面嵌词）。
6. **配图**（仅长文）：`diagram-design`（暖色纸感·手机优先）。

**步骤 3 — 落盘 + 校验**：按对应 `templates/publish_<platform-key>.md` 写 `content/<persona>/items/<id>/publish_<account>.md`，mark ✅ 采用标题。**跑 `python3 tools/engines/publish-prep/check.py <file> --platform <平台> [--form <form>]`**（校验下游可解析 + 字数/关键词数/摘要区间/无导流CTA/无 raw mermaid）；红了先修再交。

**步骤 4 — 交回上传**：
- **视频号**：`tencent-video-publish publish-item --item-dir <item> --copy-file publish_<account>.md`（引擎已支持读 publish_<account>.md，缺失回落 publish_copy.md）。
- **小红书/其他**：交回 `platform-publish`（读 publish_<account>.md 的 frontmatter/section）。
- **封面图渲染是下一步**（视频→`zh-video-cover`；长文→gzh 封面卡/`markdown-to-cards`）：读本阶段定好的封面标题文案。

## 灵活性：原子是加速器，不是闸门

engine 的 `gen_copy`/`gen_title` 只是「换个干净脑子」的便利加速器，**不是必经关卡**。任一失败都别卡住流程，自己判断走下去：

- **配额/限流**：`--provider auto` 已自动 kimi↔minimax 兜底；两家都满/网络断时——
- **你（Claude）直接写**：`gen_copy` 的 SYSTEM/USER 就在 `assets/prompts/body_video.md`，标题红线在 `writing_playbook/title.md` + `dbs-xhs-title`。脚本挂了，你照同一套 prompt/规则**亲自写正文和标题**即可，产物一样进模板。
- `build_keywords` 是纯确定性（不调模型），基本不会挂；真挂了照 `keyword_pool.yaml` 三层规则手挑。
- 无论正文/标题来自脚本还是你亲写，**最后都跑 `check.py` 校验**（下游可解析 + 字数 + 无 CTA）。守门只认产物合不合规，不认它谁写的。

一句话：有自主解决问题的能力，脚本是工具不是依赖，别让一个 403 把整条 SOP 顶死。

## 稳定性分工

| 层 | 谁 | 管 |
|---|---|---|
| 脚本 | `build_keywords`(确定性) / `gen_copy`·`gen_title`(LLM,平台字数) / `dbs-xhs-title` / **`check.py`**(下游可解析+字数+CTA lint) | 流程一致、字数、固定盘关键词、契约校验 |
| 守门 | Claude | 编造数字 / 句式撞车 / 逻辑写反 / 复述视频 / 破折号 / 导流钩子 / 训练营旧口径（check.py 兜字数/契约，软质量仍靠人+Claude） |
| 抽检 | 人 | 软质量：火不火、调性、排版 |

## 边界

实际上传→`platform-publish`；封面图渲染→`zh-video-cover`(视频)/gzh 封面 kit/`markdown-to-cards`(长文)；标题公式库→`dbs-xhs-title`；剪辑→`video-clip`；配图→`diagram-design`。本 skill 只产**文字素材** + 触发封面制作，不上传。
