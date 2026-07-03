---
# 视频号 发布物料模板（form=video）。产出落 content/<persona>/items/<id>/publish_<account>.md
platform: shipinhao
account: "{{account}}"              # 如 zh_shipinhao（张和号实跑 slot=zhanghe）
short_title: "{{6-16字短标题}}"    # 卡片显示，dbs 公式 + title.md 守门
cover_title: "{{封面文字，可省}}"  # 从标题候选挑，zh-video-cover 烧图用
tags: ["{{5个}}"]                  # build_keywords（视频号 count=5）
video: 成片.mp4
cover: cover.png
published: draft
---

## 短标题候选（6–16 字 · dbs 公式 → title.md 守门）
- ✅ {{采用}}（#公式号 · 理由）
1. {{备选1}}
2. {{备选2}}

## 描述/正文（desc · layout: 标题→正文→标签 · 张和第一人称 · 企业AI落地主线 · 金句收尾无CTA）
{{正文，见 prompts/body_video.md}}

## 关键词（视频号精简 5 个）
#{{k1}} #{{k2}} #{{k3}} #{{k4}} #{{k5}}

## ⚠️ 守门备注
- ASR 误听已核（Claude Code / Codex / Anthropic …）；标题正文数字均可溯源；无导流 CTA；无训练营口径。
