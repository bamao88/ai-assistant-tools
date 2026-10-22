---
# 文章多平台同步模板（form=article）。知乎/掘金/CSDN/百家号/思否/今日头条
platform: wechatsync
targets: "{{zhihu,juejin,csdn,...}}"   # 逗号分隔平台
title: "{{标题——头条2-30字，余不限}}"
cover: "{{可选}}"
published: draft                       # 先 --dry-run
---

# {{标题}}

{{复用公众号排版全文（body_article_adapt.md「完整长文系」）；各平台后台人工复核排版/封面/图片/链接后再正式发布}}

<!-- 今日头条标题超30字先压缩并告知用户 -->
