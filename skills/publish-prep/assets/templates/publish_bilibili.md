---
# B站视频 发布物料模板（form=video）
platform: bilibili
account: zh_bilibili
title: "{{标题 ≤80字}}"
tid: "{{分区id，必填——拿不准问用户}}"
tags: "{{逗号分隔，≤10}}"
video: 成片.mp4
published: draft         # 注意：B站 upload-video 即投稿，无纯草稿态；发前逐项确认
---

## 标题候选（≤80 字 · dbs 公式 → title.md 守门）
- ✅ {{采用}}

## 简介 desc（发布页正文/SEO 描述 · 目标300-1200字 · 张和第一人称 · 企业AI落地 · 无导流CTA）
{{正文，见 prompts/body_video.md}}

## 标签（逗号分隔，≤10）
{{tag1,tag2,...}}
