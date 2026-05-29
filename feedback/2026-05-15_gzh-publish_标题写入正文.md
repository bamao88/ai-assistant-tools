# gzh-publish 标题写入正文

## 复现步骤

1. 准备一篇 Markdown，frontmatter 中包含 `title`。
2. 正文开头保留同名一级标题，例如 `# 文章标题`。
3. 使用 `gzh-publish` 创建公众号草稿或 dry-run 预览。

## 期望行为

公众号标题使用 frontmatter `title` 或正文首个一级标题，但正文内容不重复渲染这个标题。

## 实际行为

工具直接将 `parsed.content` 传入排版流程，导致正文开头的同名一级标题被渲染进公众号正文。

## 日志片段

dry-run 生成的 HTML body 中出现标题对应的 `<h1>` 内容。

## 处理状态

已在 `tools/engines/gzh-publish/src/index.ts` 增加开头标题解析与剥离逻辑。
