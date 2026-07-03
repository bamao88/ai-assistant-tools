---
# 公众号 发布物料模板（form=article）。范例：content/zh_assistant/items/ZHC20260616_182817_001/publish_gzh.md
title: "{{文章标题 ≤64字}}"
author: "{{作者/发布身份，见 gongzhonghao.md 账号表}}"
cover: assets/cover.png
theme: "{{coral | claude}}"     # 按账号固定：wxp-ai=coral / mdx=claude
digest: >-
  {{≤120字摘要——即「公众号100字以内」那栏，不是正文}}
published: draft
---

# {{文章标题}}

{{排版全文——加粗金句 / 引用块 / 列表 / --- 分节 / 图注（图引本地 assets/），不压缩。
正文重写指引见 prompts/body_article_adapt.md；配图走 diagram-design（暖色纸感·手机优先）}}

<!-- 封面标题（cover-kit，≠文章标题）：由 title 自动拆
     title_primary / title_secondary（每段≤10中文等效）+ 右侧关键词 keyword_top/keyword_bottom（各≤3字）
     普通原创→generate_cover.py article；视频/转写类→数据源封面 -->
