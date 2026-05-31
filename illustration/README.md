# illustration — 配图生成工具（源码层）

把文章内容渲染成美观配图：**HTML/CSS 模板 + Chrome 无头截图 → 高清 PNG**。零额外依赖（用本机已装的 Google Chrome）。

> 由 Manager 维护（`tools/` 唯一写入方）。Agent 通过 `shared/skills/illustration/SKILL.md` 调用。

## 设计思路

配图丑的根因不是"AI 不会画"，而是每次从零设计、或用 excalidraw/mermaid 自动出图，版式飘忽。
本工具把经过调校的版式固化成模板：**CSS 设计系统锁死，Agent 只改内容**，抬住质量下限。

## 结构

```
tools/illustration/
├── render.sh         # Chrome 无头 → PNG @2x；尺寸读 HTML 的 <meta name="render-size">
├── knowledge.md      # 配图设计知识（六条铁律 / 选型 / 风格 / 文案长度 / 避坑）
├── templates/        # 6 个模板
│   ├── cover-minimal.html      # 封面·极简科技(深色)
│   ├── cover-gradient.html     # 封面·明亮渐变(玻璃拟态)
│   ├── cover-editorial.html    # 封面·编辑杂志(浅色)
│   ├── diagram-flow.html       # 概念/架构示意图（横版，:root 可切 3 风格）
│   ├── quote-card.html         # 金句卡（竖版 4:5，:root 可切 3 风格）
│   └── data-card.html          # 数据/对比卡（竖版 4:5，:root 可切 3 风格）
└── examples/         # 各模板的渲染样例（用默认内容）
```

## 渲染

```bash
./render.sh <input.html> [output.png] [WxH]
```
- 不传尺寸则读 HTML 里的 `<meta name="render-size" content="WxH">`，默认 1600x900。
- 输出 @2x（`--force-device-scale-factor=2`），1600x900 实际产出 3200x1800。

## 环境依赖

- Google Chrome：`/Applications/Google Chrome.app`（已装）
- 中文字体：系统自带 PingFang SC，模板不引网络字体，渲染时无需联网。

## 重新生成样例

```bash
for t in cover-minimal cover-gradient cover-editorial diagram-flow quote-card data-card; do
  ./render.sh templates/$t.html examples/$t.png
done
```

## 扩展模板

新增模板时：① 顶部加 `<meta name="render-size">`；② 用 `:root` 管理颜色，提供 3 套风格预设注释；
③ 内容处加 `<!-- EDIT -->` 标注；④ 只用系统字体；⑤ 在 `examples/` 出一张样例，并更新 `knowledge.md` §2 表格。
