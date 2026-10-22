---
# 小红书 发布物料模板（platform key=xiaohongshu, form=both）。产出 → publish_<account>.md
# 下游：xiaohongshu extract_frontmatter.py —— keywords 必须是 YAML 块列表(- 项)，
#   title ≤20；description 单行或 | 块(280-1000)会作为发布页正文；keywords 块列表。图文/长文用 A 节，视频用 B 节。
platform: xiaohongshu
account: "{{account}}"          # 本条已确认的平台账号ID/可唯一解析的项目别名；不使用跨项目默认
title: "{{≤20字标题}}"          # UTF-16：汉字1/英数半角每2=1
abstract: "{{20-200字短摘要/内部摘要，仅图文/长文}}"
description: |
  {{280-1000字发布页正文/SEO描述。不是全文搬运，也不是一句摘要；要写清核心判断、关键场景、工具/方法名、目标人群和边界。小红书会在这里检索，信息密度要够。}}
keywords:                       # ⚠️ 必须块列表，不能 ["a","b"]（extractor 只认 - 项）
  - "{{k1}}"
  - "{{k2}}"
  - "{{k3}}"
  - "{{... 补满 10}}"
published: draft
---

## 标题候选（按 references/xiaohongshu-titles.md；现有≤20宽度检查）
- ✅ {{采用}}
1. {{备选1}}（写作角度；备选数量按需）
2. {{备选2}}（写作角度；备选数量按需）

## 封面标题（卡片首图文字 · 从候选标题挑，可与正文标题结合或独立）
{{封面文字}}

<!-- A. 图文/长文（form=article）：正文用于出卡片；description 用于发布页正文/SEO -->
<!-- B. 视频（form=video）：## 正文就是发布页正文/SEO 描述，目标300-800字，最低200；封面走 assistant_zh_video-cover(3:4)，abstract 可省 -->
## 正文（结尾金句 · 无导流CTA）
{{正文；长文见 prompts/body_article_adapt.md，视频见 prompts/body_video.md}}
