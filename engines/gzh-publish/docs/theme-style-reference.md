# 主题样式参考手册

每个主题定义在 `src/lib/themes/` 下，结构为 `{ id, name, description, styles }`。

`styles` 是一个 `Record<string, string>`，key 对应 HTML 元素选择器或控制标记，value 是内联 CSS 字符串。

---

## CSS 元素样式（21 个）

所有主题必须包含以下 key，渲染管线会通过 `querySelectorAll(key)` 查找元素并注入对应的内联样式。

| # | Key | 对应元素 | 控制内容 | 备注 |
|---|-----|---------|---------|------|
| 1 | `container` | 最外层 `<div>` | 字体族、基准字号、行高、正文色、背景色、内边距 | 所有子元素的默认继承源 |
| 2 | `h1` | `<h1>` | 字号、字重、颜色、行高、上下边距 | |
| 3 | `h2` | `<h2>` | 同上 | |
| 4 | `h3` | `<h3>` | 同上 | |
| 5 | `h4` | `<h4>` | 同上 | |
| 6 | `p` | `<p>` | 段间距（margin）、行高、颜色 | 段间距是阅读节奏的核心参数 |
| 7 | `strong` | `<strong>` | 字重、颜色、可选背景高亮 | 标题内的 strong 会被覆盖为 `color: inherit` |
| 8 | `em` | `<em>` | 斜体、颜色 | 标题内同上 |
| 9 | `a` | `<a>` | 链接颜色、下划线样式 | 标题内链接会继承标题色 |
| 10 | `ul` | `<ul>` | 外边距、左缩进 | `list-style-type` 由管线自动补 disc/circle/square |
| 11 | `ol` | `<ol>` | 外边距、左缩进 | `list-style-type` 由管线自动补 decimal |
| 12 | `li` | `<li>` | 项间距、行高、颜色 | |
| 13 | `blockquote` | `<blockquote>` | 边距、内边距、背景色、左边框、颜色、圆角、字体样式 | |
| 14 | `code` | 行内 `<code>` | 字体族、padding、背景色、颜色、圆角、字号 | **不会**应用到 `<pre>` 内的 `<code>` |
| 15 | `pre` | `<pre>` 代码块 | 边距、padding、背景色、圆角、字号 | 管线额外追加 `font-variant-ligatures: none; tab-size: 2` |
| 16 | `hr` | `<hr>` | 上下边距、高度、背景色 | |
| 17 | `img` | `<img>` | 最大宽度、边距、圆角、阴影 | 若定义了此 key，管线不再注入默认的圆角/阴影/padding/border |
| 18 | `table` | `<table>` | 宽度、边距、border-collapse、字号 | |
| 19 | `th` | `<th>` | 背景色、padding、对齐、字重、颜色、边框 | |
| 20 | `td` | `<td>` | padding、边框、颜色 | |
| 21 | `tr` | `<tr>` | 边框 | 通常设为 `border: none` |

---

## 控制标记样式（2 个）

这些 key 不是 CSS 选择器，而是控制渲染管线行为的标记。

| # | Key | 值 | 默认行为 | 说明 |
|---|-----|----|---------|------|
| 22 | `codeDots` | `'none'` = 隐藏 | 显示红黄绿三圆点 | 控制代码块顶部的 macOS 窗口装饰圆点 |
| 23 | `codeHighlight` | `'github'` / `'mono'` | `'github'`（彩色） | 代码语法高亮配色方案 |

---

## 渲染管线自动注入的样式

以下样式由 `markdown.ts` 的 `applyTheme()` 自动处理，不需要在主题中定义：

| 行为 | 条件 | 注入内容 |
|------|------|---------|
| 列表符号 | 所有 `<ul>` / `<ol>` | `list-style-type: disc/circle/square/decimal` |
| 标题内行内元素覆盖 | `<h1>`~`<h6>` 内的 strong/em/a/code | `color: inherit; background: transparent` 防止继承冲突 |
| 代码块内 code 样式 | `<pre>` 内的 `<code>` | `display: block; font-size/line-height: inherit; white-space: pre` |
| 代码块排版 | 所有 `<pre>` | `font-variant-ligatures: none; tab-size: 2` |
| 图片默认装饰 | 主题**未定义** `img` key 时 | `border-radius: 14px; box-shadow: ...; border: 1px solid ...; padding: 8px` |
| 图片基础布局 | 主题**已定义** `img` key 时 | 仅 `display: block; width: 100%; box-sizing: border-box`，其余由主题控制 |
| 多图并排 | 连续多张图片 | 自动组合为 flex 横排布局，圆角/阴影跟随主题 `img` 设置 |

---

## 各主题当前配置对比

### 基础参数

| 参数 | claude | medium | minimal | openai | cards-claude | coral | monograph_all_both |
|------|--------|--------|---------|--------|--------------|-------|--------------------|
| 字体族 | system sans | system sans | system sans | PingFang SC | 正文 Noto Serif SC/Songti SC；标题 Noto Sans SC/Source Han Sans SC | Noto Serif SC/Songti SC | Noto Serif SC/Songti SC |
| 基准字号 | 16px | 16px | 16px | 17px | 16px | 16px | 17px |
| 行高 | 1.7 | 1.85 | 1.8 | 1.6 | 1.8 | 1.95 | 2 |
| 正文色 | #2b2b2b | #242424 | #333333 | #000000 | #141413 | #0f1216 | #111111 |
| 背景色 | #f8f6f0 | #fcfcfc | #ffffff | #ffffff | #faf9f5 | #fdfcf9 | #ffffff |
| 侧边距 | 20px | 20px | 20px | 20px | 20px | 20px | 20px |

### 标题

| 参数 | claude | medium | minimal | openai | cards-claude | coral | monograph_all_both |
|------|--------|--------|---------|--------|--------------|-------|--------------------|
| H1 字号 | 32px | 32px | 28px | 26px | 26px | 28px | 26px |
| H2 字号 | 26px | 26px | 22px | 26px | 22px | 22px | 21px |
| H3 字号 | 21px | 21px | 18px | 20px | 18px | 18px | 18px |
| 标题字重 | 700/600 | 700/600 | 700/600 | 500 | 700/600 | 700 | 500/600 |
| 标题色 | #b75c3d | #111 | #111111 | #000000 | H1 #141413 / H2 #d97757 | #ff515a | #111111 |
| H2 装饰 | - | - | - | - | 4px 左侧强调线 | 居中 + 底部分隔线 | 书页式字距 |

### 段落与加粗

| 参数 | claude | medium | minimal | openai | cards-claude | coral | monograph_all_both |
|------|--------|--------|---------|--------|--------------|-------|--------------------|
| 段间距 | 18px | 24px | 16px | 24px | 18px | 18px | 18px |
| 加粗字重 | 700 | 700 | 700 | 600 | 700 | 700 | 700 |
| 加粗色 | #b75c3d + 背景 | #000 | #111111 | #000000 | #d97757 + 淡橙背景 | #db2a3d + 淡珊瑚背景 | #111111，无背景 |

### 引用块

| 参数 | claude | medium | minimal | openai | cards-claude | coral | monograph_all_both |
|------|--------|--------|---------|--------|--------------|-------|--------------------|
| 背景 | rgba 淡色 | 透明 | 透明 | 透明 | rgba(217,119,87,.09) | rgba(255,81,90,.06) | 透明 |
| 左边框 | 4px #b75c3d | 3px #1a8917 | 3px #cccccc | 2px #d1d5db | 3px #d97757 | 无，改上下线 | 无 |
| 圆角 | 4px | 0 | 0 | 0 | 8px | 0 | 0 |
| 斜体 | - | - | - | italic | italic | italic | italic |

### 代码

| 参数 | claude | medium | minimal | openai | cards-claude | coral | monograph_all_both |
|------|--------|--------|---------|--------|--------------|-------|--------------------|
| 代码背景 | #f0ece4 | #f2f3f5 | #f5f5f5 | rgba(0,0,0,0.04) | 行内淡橙 / 块级 #1e1e1c | rgba(255,81,90,.06/.08) | 行内 #f1f1f1 / 块级透明 |
| 代码块圆角 | 8px | 8px | 4px | 6px | 10px | 0 | 0 |
| 代码字号 | 12px | 12px | 13px | 14px | 13px | 13px | 14px |
| 圆点装饰 | 显示 | 显示 | 显示 | 隐藏 | 隐藏 | 隐藏 | 隐藏 |
| 高亮配色 | github | github | github | mono | mono | mono | mono |

### 图片

| 参数 | claude | medium | minimal | openai | cards-claude | coral | monograph_all_both |
|------|--------|--------|---------|--------|--------------|-------|--------------------|
| 圆角 | 4px | 4px | 4px | 0 | 10px | 4px | 0 |
| 阴影 | 默认装饰 | 默认装饰 | 默认装饰 | none | 轻量柔和阴影 | none，上下珊瑚线 | none，黑白化 |

### 表格

| 参数 | claude | medium | minimal | openai | cards-claude | coral | monograph_all_both |
|------|--------|--------|---------|--------|--------------|-------|--------------------|
| 表头背景 | #f0ece4 | #f2f3f5 | #f5f5f5 | 透明 | #e8e6dc | 透明 | 透明 |
| 边框样式 | 全边框 | 全边框 | 全边框 | 仅行线 | 全边框 | 顶线 + 虚线行线 | 黑色上下线 |
| 字号 | 15px | 15px | 15px | 13px | 14px | 14px | 14px |

### 链接

| 参数 | claude | medium | minimal | openai | cards-claude | coral | monograph_all_both |
|------|--------|--------|---------|--------|--------------|-------|--------------------|
| 颜色 | #b75c3d | #1a8917 | #333333 | #000000 | #d97757 | #db2a3d | #111111 |
| 下划线 | 底部边框 | 底部边框 | text-decoration | text-decoration | 底部边框 | 底部边框 | 底部边框 |
