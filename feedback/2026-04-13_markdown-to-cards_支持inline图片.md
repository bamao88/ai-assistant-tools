---
date: 2026-04-13
tool: markdown-to-cards
type: feature-note
---

## 问题描述

markdown-to-cards 支持 inline 图片（`![alt](本地路径)` 格式）。

## 背景

文章「半年Claude Code，我改了对Agent选模型判断」正文中包含本地路径的 inline 图片引用，例如：

```
![OpenAI GPT-5.4 mini 定价页](/Volumes/ExtSSD2601/.../1_openai_pricing_final.png)
```

## 期望确认

1. markdown-to-cards 生成卡片时，是否会将 inline 图片渲染进卡片？
2. 还是只渲染文字内容，跳过图片？
3. 如果跳过，建议在文档或报错中明确说明，避免发布时漏图。

## 建议

若工具当前不支持 inline 图片渲染，建议：
- 在调用前 strip 掉 `![...]()` 语法，或
- 明确提示用户"图片需单独上传，卡片仅含文字"
