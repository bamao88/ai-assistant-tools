---
# 小红书 发布物料模板（platform key=xiaohongshu, form=both）。产出 → publish_<account>.md
# 下游：xiaohongshu extract_frontmatter.py —— keywords 必须是 YAML 块列表(- 项)，
#   abstract 单行或 | 块(>20 & ≤200)，title ≤20。图文/长文用 A 节，视频用 B 节。
platform: xiaohongshu
account: "{{account}}"          # 口播切片默认 zh_xhs_main2（个人号）
title: "{{≤20字标题}}"          # UTF-16：汉字1/英数半角每2=1
abstract: "{{20-200字摘要，仅图文/长文}}"
keywords:                       # ⚠️ 必须块列表，不能 ["a","b"]（extractor 只认 - 项）
  - "{{k1}}"
  - "{{k2}}"
  - "{{k3}}"
  - "{{... 补满 10}}"
published: draft
---

## 标题候选（≤20 字 · dbs 公式 → title.md 守门）
- ✅ {{采用}}
1. {{备选1}}（#公式号）
2. {{备选2}}（#公式号）

## 封面标题（卡片首图文字 · 从候选标题挑，可与正文标题结合或独立）
{{封面文字}}

<!-- A. 图文/长文（form=article）：排版全文 / 压 ≤1000 首屏钩子 -->
<!-- B. 视频（form=video）：desc；封面走 zh-video-cover(3:4)，abstract 可省 -->
## 正文（结尾金句 · 无导流CTA）
{{正文；长文见 prompts/body_article_adapt.md，视频见 prompts/body_video.md}}
