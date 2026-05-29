# markdown-to-cards 总览图本地图片未加载

## 复现步骤

1. 使用 `node cli.js --input test/fixtures/real_world_all_styles.md --base-dir test/fixtures --output-dir <dir> --color-scheme <scheme>` 生成多套配色 PNG。
2. 用 Puppeteer 生成封面总览图，HTML 中通过 `file://` 引用各配色目录下的 `card_00_cover.png`。
3. 执行 `page.setContent(..., { waitUntil: "load" })` 后直接 `page.screenshot()`。

## 期望行为

总览图应显示 10 张实际封面 PNG，方便横向比较配色。

## 实际行为

总览图中所有封面位置显示破图占位和 alt 文本，未渲染真实封面图片。单张卡片 PNG 本身有效，尺寸为 `1440x2400`。

## 日志片段

```text
overview_covers.png: PNG image data, 1600 x 1180, 8-bit/color RGB, non-interlaced
claude-orange-light/card_00_cover.png: PNG image data, 1440 x 2400, 8-bit/color RGB, non-interlaced
```

## 临时修正

将总览 HTML 中的封面图片改为 `data:image/png;base64,...` 内嵌，并在截图前等待：

```js
await page.waitForFunction(() =>
  Array.from(document.images).every((img) => img.complete && img.naturalWidth > 0)
);
```

修正后已重新生成 `/Volumes/ExtSSD2601/AI_Assistant/tools/engines/markdown-to-cards/tmp/color_schemes_default_20260513_160332/overview_covers.png`。
