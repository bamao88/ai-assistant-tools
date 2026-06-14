---
name: markdown-to-cards
description: 将 Markdown 文章转换为小红书风格卡片图片。当用户提到"生成卡片"、"转成卡片"、"小红书卡片"或要将文章/Markdown输出为图片时使用。
---

# Markdown 转卡片图片

## 使用方法

调用 MCP 工具 `markdown_to_cards`，参数说明：

- `markdown`（必填）：完整的 Markdown 文章内容，H1 标题会作为封面标题
- `account`（可选）：小红书账号 slot；提供后从 `~/.xhs/accounts.json` 的 `card_config` 读取账号默认卡片配置，显式传入的参数优先级更高
- `output_dir`（可选）：图片保存目录，默认为临时目录
- `base_dir`（可选）：解析 Markdown 相对图片路径的基准目录
- `cover_bg_path`（可选）：文字封面的底图路径；legacy 默认配色会使用程序生成背景，只有未使用配色或显式传入时才使用底图
- `cover_image_path`（可选）：图片封面样式使用的封面图片路径或 URL
- `cover_style`（可选）：封面样式，`template`（纯文字）、`image`（文字+图片）或 `both`（两者都生成）；提供 `cover_image_path` 时默认使用图片封面
- `cover_template`（可选）：封面模板来源，`style`（默认，使用当前主题封面）或 `default`（正文用当前主题，封面强制使用默认 legacy 封面）
- `style`（可选）：卡片模板风格，默认 `legacy`；可选 `legacy`、`coral`、`lavender`、`editorial`、`sage`、`prologue`、`classic`、`monograph`；公众号同款主题也可直接用 `claude`、`medium`、`minimal`、`openai`、`cards-claude`、`monograph_all_both`；共用模板实验可用 `unified-claude`、`unified-medium`、`unified-minimal`、`unified-openai`、`unified-cards-claude`、`unified-coral`、`unified-monograph`；小红书官方风格启发的封面模板可用 `xhs-rational-modern`、`xhs-logic-structure`、`xhs-plain-texture`、`xhs-magazine-vanguard`、`xhs-cross-topology`、`xhs-mono-minimal`、`xhs-clear-bright`、`xhs-dusty-notes`、`xhs-simple-basic`、`xhs-elegant-geometry`、`xhs-inspiration-memo`、`xhs-plain-narrative`、`xhs-dusk-manuscript`、`xhs-literary-fresh`、`xhs-handbook`、`xhs-retro-lines`、`xhs-color-block`、`xhs-light-bright`、`xhs-photo-feature`、`xhs-doodle-marker`
- `color_scheme`（可选）：仅适用于 `legacy` 默认模板的预设配色，默认 `claude-orange-light`；可选 `claude-orange-light`、`claude-orange-dark`、`claude-blue-light`、`claude-green-light`、`tech-blue`、`sandstone`、`sustainable-green`、`premium-neutral`、`creative-purple`、`growth-coral`
- `chapter_label`（可选）：新主题封面/页眉标签，默认 `精选长图文`
- `cover_variant`（可选）：新主题封面版式，`primary`、`alt` 或 `all`，默认 `primary`
- `accent_color`（可选）：强调色手动覆盖；所有模板风格都支持
- `background_color`（可选）：正文/模板背景色手动覆盖；所有模板风格都支持
- `text_color`（可选）：正文文字色手动覆盖；所有模板风格都支持
- `font_size`（可选）：正文字号 px，默认 25

## 执行步骤

1. 获取 Markdown 内容（来自用户输入、文件路径或当前对话）
2. 若用户未指定输出目录，询问或使用默认临时目录
3. 调用 `markdown_to_cards` 工具
4. 返回生成的图片路径列表，告知用户共生成几张（含封面）

## 注意事项

- 文章第一行必须是 `# 标题` 格式，否则封面无标题
- 正文支持 Markdown 图片：`![说明](图片路径)`；本地相对路径会基于 `base_dir` 解析
- 图片会自动居中缩放，避免超出正文卡片高度
- 默认 `legacy` 使用 `claude-orange-light`；10 个 `color_scheme` 只用于 `legacy` 默认模板
- `style` 为非 `legacy` 时不要传 `color_scheme`；如需微调颜色，使用 `accent_color`、`background_color`、`text_color`
- 不指定 `style` 时保持旧版 `legacy` 输出；需要新样式时显式传入主题名；公众号主题名与 `gzh-publish` 对齐，`coral` 复用 AI PM 小助理同款卡片主题，`monograph_all_both` 是 `monograph` 的公众号兼容 ID
- 张和专业号的小红书长文默认使用账号配置：`account=张和_专业号` → `style=unified-claude`、`chapter_label=张和 AI 产品实战派`、`cover_template=default`、`cover_style=template`
- 输出目录需要有写入权限
- 生成完成后列出所有文件路径方便用户查看
