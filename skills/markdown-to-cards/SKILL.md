---
name: markdown-to-cards
description: 将 Markdown 文章转换为小红书风格卡片图片。当用户提到"生成卡片"、"转成卡片"、"小红书卡片"、"Markdown 转卡片"或要将文章/Markdown 输出为图片时使用。本项目默认使用本地 CLI，不使用 MCP 工具。
---

# Markdown 转卡片图片

## 使用方法

本项目默认调用本地 CLI：

```bash
node /Volumes/ExtSSD2601/AI_Assistant/tools/engines/markdown-to-cards/cli.js \
  --account "<ACCOUNT>" \
  --input "<markdown_file>" \
  --output-dir "<output_dir>"
```

不要调用 `markdown_to_cards` MCP 工具；Codex 当前未把该 MCP 作为可靠发布路径，且 `platform-publish/references/xiaohongshu.md` 明确要求使用本地 CLI。

常用 CLI 参数说明：

- `--input`（必填）：Markdown 文件路径；H1 标题会作为封面标题
- `--account`（可选）：小红书账号 slot；提供后从 `~/.xhs/accounts.json` 的 `card_config` 读取账号默认卡片配置，显式参数优先级更高
- `--output-dir`（可选）：图片保存目录，默认为临时目录
- `--base-dir`（可选）：解析 Markdown 相对图片路径的基准目录
- `--cover-bg`（可选）：文字封面的底图路径；legacy 默认配色会使用程序生成背景，只有未使用配色或显式传入时才使用底图
- `--cover-image`（可选）：图片封面样式使用的封面图片路径或 URL
- `--cover-style`（可选）：封面样式，`template`（纯文字）、`image`（文字+图片）或 `both`（两者都生成）；提供 `--cover-image` 时默认使用图片封面
- `--cover-template`（可选）：封面模板来源，`style`（默认，使用当前主题封面）或 `default`（正文用当前主题，封面强制使用默认 legacy 封面）
- `--style`（可选）：卡片模板风格，默认 `legacy`
- `--color-scheme`（可选）：仅适用于 `legacy` 默认模板的预设配色，默认 `claude-orange-light`
- `--chapter-label`（可选）：新主题封面/页眉标签，默认 `精选长图文`
- `--cover-variant`（可选）：新主题封面版式，`primary`、`alt` 或 `all`，默认 `primary`
- `--accent` / `--background` / `--text-color`（可选）：颜色手动覆盖
- `--font-size`（可选）：正文字号 px，默认 25

## 执行步骤

1. 获取 Markdown 内容（来自用户输入、文件路径或当前对话）
2. 若用户未指定输出目录，使用 item 目录下的 `assets/xhs_cards/` 或临时目录
3. 调用本地 CLI `node /Volumes/ExtSSD2601/AI_Assistant/tools/engines/markdown-to-cards/cli.js`
4. 返回生成的图片路径列表，告知用户共生成几张（含封面）

## 注意事项

- 文章第一行必须是 `# 标题` 格式，否则封面无标题
- 正文支持 Markdown 图片：`![说明](图片路径)`；本地相对路径会基于 `--base-dir` 解析
- 图片会自动居中缩放，避免超出正文卡片高度
- 默认 `legacy` 使用 `claude-orange-light`；`--color-scheme` 只用于 `legacy` 默认模板
- `--style` 为非 `legacy` 时不要传 `--color-scheme`；如需微调颜色，使用 `--accent`、`--background`、`--text-color`
- 不指定 `--style` 时保持旧版 `legacy` 输出；需要新样式时显式传入主题名；公众号主题名与 `gzh-publish` 对齐，`coral` 复用 AI PM 小助理同款卡片主题，`monograph_all_both` 是 `monograph` 的公众号兼容 ID
- 张和专业号的小红书长文默认使用账号配置：`--account 张和_专业号` → `style=unified-claude`、`chapter_label=张和 AI 产品实战派`、`cover_template=default`、`cover_style=template`
- 输出目录需要有写入权限
- 生成完成后列出所有文件路径方便用户查看
