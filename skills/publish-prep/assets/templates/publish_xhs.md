---
# 小红书 发布物料模板（form=both）。按 item.format 用下面对应一节；产出落 publish_<account>.md
platform: xiaohongshu
account: "{{account}}"          # 图文/长文默认张和号；口播切片默认 zh_xhs_main2（个人号）
title: "{{≤20字标题}}"          # UTF-16：汉字1/英数半角每2=1；dbs 公式 + title.md 守门
abstract: "{{20-200字，仅图文/长文}}"
keywords: ["{{10个}}"]          # build_keywords（count=10，去空格）
published: draft
---

<!-- ========== A. 图文 / 长文（form=article） ========== -->
## 标题候选（≤20 字 · dbs 公式 → title.md 守门）
- ✅ {{采用}}（#公式号）
1. {{备选1}}
2. {{备选2}}

## 封面标题（卡片首图文字，可与正文标题结合或独立）
- {{封面文字，从候选标题挑}}

## 正文（长文=排版全文 / 图文=≤1000字 首屏钩子 · 结尾金句无导流CTA）
{{正文}}

## 关键词标签（10）
#{{k1}} … #{{k10}}

<!-- ========== B. 视频（form=video） ========== -->
## 【视频】标题候选（≤20 字）
- ✅ {{采用}}
## 【视频】封面标题（3:4 · zh-video-cover 烧图）
- {{封面文字}}
## 【视频】描述正文（desc · 金句收尾无CTA）
{{正文，见 prompts/body_video.md}}
## 【视频】关键词（10）
#{{k1}} … #{{k10}}
