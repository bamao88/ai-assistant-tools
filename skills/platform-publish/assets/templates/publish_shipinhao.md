---
# 视频号 发布物料模板（platform key=shipinhao, form=video）
# 产出 → content/<persona>/items/<id>/publish_<account>.md
# 下游：tencent-video-publish `publish-item --copy-file publish_<account>.md`
#   契约(tvp/item.py)：## 标题候选 恰一个 - ✅ / ## 正文 / 「视频号精简」+#标签 同一行
platform: shipinhao
account: "{{account}}"        # 张和号 destination；引擎 slot=zhanghe（别用 default=aipm 副号）
video: 成片.mp4
cover: cover.png
published: draft
---

## 标题候选（6–16 字短标题 · dbs 公式 → title.md 守门 · 视频卡片显示）
- ✅ {{采用短标题}}
1. {{备选1}}（#公式号 · 理由）
2. {{备选2}}（#公式号）

## 封面标题（可省 · 从候选标题挑，无 ✅）
{{封面文字}}

## 正文（desc · 发布页正文/SEO 描述 · 目标300-800字 · 张和第一人称 · 企业AI落地主线 · 金句收尾无导流CTA）
{{正文，见 prompts/body_video.md}}

## 视频号精简（5 个）
视频号精简（5 个）：#{{k1}} #{{k2}} #{{k3}} #{{k4}} #{{k5}}

## ⚠️ 守门备注
- ASR 误听已核（Claude Code / Codex / Anthropic …）；标题正文数字均可溯源；无导流 CTA；无训练营口径。
