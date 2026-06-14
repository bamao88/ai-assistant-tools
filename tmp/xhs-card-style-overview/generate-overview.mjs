import fs from "fs/promises";
import path from "path";
import { createRequire } from "module";
import { fileURLToPath, pathToFileURL } from "url";

import {
  CARD_STYLE_IDS,
  COLOR_SCHEME_IDS,
  DEFAULT_COLOR_SCHEME_ID,
  renderMarkdownToCards,
} from "../../engines/markdown-to-cards/lib/render.js";
import { getCardTemplate, resolveColorScheme } from "../../engines/markdown-to-cards/lib/templates/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const requireFromEngine = createRequire(path.join(repoRoot, "engines/markdown-to-cards/package.json"));
const puppeteer = requireFromEngine("puppeteer");

const outDir = path.resolve(repoRoot, "tmp/xhs-card-style-overview");
const cardsDir = path.join(outDir, "cards");
const htmlPath = path.join(outDir, "xhs-card-style-overview.html");
const pngPath = path.join(outDir, "xhs-card-style-overview.png");

const sample = `# 卡片样式预览

小红书卡片需要在一屏里把观点、结构和节奏讲清楚。这个样稿用于对比不同主题的标题、正文、引用、列表和代码块效果。

## 一个稳定的工作流

- 先明确读者真正要保存的信息
- 再把长文拆成能滑动阅读的卡片
- 最后检查标题层级、留白和重点是否清楚

> 好的卡片不是把文章缩小，而是把信息重新编排成适合收藏和转发的形态。

### 关键判断

如果内容里有 \`hook\`、案例和行动建议，样式就应该帮它们分层，而不是抢走注意力。
`;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function relFromHtml(filePath) {
  return path.relative(path.dirname(htmlPath), filePath).split(path.sep).join("/");
}

async function renderPreview({ style, colorScheme }) {
  const dirName = colorScheme ? `legacy-${colorScheme}` : style;
  const outputDir = path.join(cardsDir, dirName);
  const result = await renderMarkdownToCards(sample, {
    output_dir: outputDir,
    base_dir: outDir,
    style,
    color_scheme: colorScheme,
    cover_style: "template",
    cover_variant: "primary",
    chapter_label: "小红书卡片",
  });

  const bodyFile = result.files.find((file) => !path.basename(file).includes("_cover")) || result.files[0];
  return bodyFile;
}

async function buildCards() {
  await fs.rm(cardsDir, { recursive: true, force: true });
  await fs.mkdir(cardsDir, { recursive: true });

  const styleCards = [];
  for (const style of CARD_STYLE_IDS) {
    const template = getCardTemplate(style);
    const preview = await renderPreview({ style });
    styleCards.push({
      id: style,
      name: template.name,
      tag: style === "legacy" ? `默认配色 ${DEFAULT_COLOR_SCHEME_ID}` : "style",
      preview,
    });
  }

  const legacyCards = [];
  for (const colorScheme of COLOR_SCHEME_IDS) {
    const scheme = resolveColorScheme(colorScheme);
    const preview = await renderPreview({ style: "legacy", colorScheme });
    legacyCards.push({
      id: colorScheme,
      name: scheme.name,
      tag: "legacy color_scheme",
      preview,
    });
  }

  return { styleCards, legacyCards };
}

function sectionHtml(title, description, cards) {
  return `
    <section class="section">
      <div class="section-head">
        <div>
          <h2>${escapeHtml(title)}</h2>
          <p>${escapeHtml(description)}</p>
        </div>
        <span>${cards.length} items</span>
      </div>
      <div class="grid">
        ${cards.map((card) => `
          <article class="item">
            <div class="meta">
              <div>
                <h3>${escapeHtml(card.name)}</h3>
                <code>${escapeHtml(card.id)}</code>
              </div>
              <span>${escapeHtml(card.tag)}</span>
            </div>
            <img src="${escapeHtml(relFromHtml(card.preview))}" alt="${escapeHtml(card.id)} preview">
          </article>
        `).join("\n")}
      </div>
    </section>`;
}

async function writeHtml(styleCards, legacyCards) {
  const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小红书卡片样式总览</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; background: #f4f5f7; color: #111827; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif; }
  body { padding: 34px; }
  #overview { width: 1440px; margin: 0 auto; }
  .hero { display: flex; justify-content: space-between; align-items: end; gap: 24px; margin-bottom: 24px; }
  .hero h1 { margin: 0; font-size: 38px; line-height: 1.12; letter-spacing: 0; }
  .hero p { margin: 10px 0 0; font-size: 15px; line-height: 1.55; color: #5b6472; }
  .badge { flex: 0 0 auto; border: 1px solid #d7dce3; background: #fff; border-radius: 999px; padding: 9px 14px; color: #374151; font-size: 13px; }
  .section { margin-top: 28px; }
  .section-head { display: flex; justify-content: space-between; align-items: end; margin-bottom: 14px; }
  .section-head h2 { margin: 0; font-size: 24px; line-height: 1.2; letter-spacing: 0; }
  .section-head p { margin: 6px 0 0; color: #6b7280; font-size: 13px; }
  .section-head span { color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
  .grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; align-items: start; }
  .item { background: #fff; border: 1px solid #e1e5eb; border-radius: 10px; padding: 10px; box-shadow: 0 12px 28px rgba(15,23,42,.08); overflow: hidden; }
  .meta { height: 76px; display: flex; flex-direction: column; justify-content: space-between; gap: 7px; padding-bottom: 8px; }
  .meta h3 { margin: 0 0 4px; font-size: 15px; line-height: 1.2; letter-spacing: 0; color: #111827; }
  .meta code { display: inline-block; max-width: 100%; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 5px; padding: 2px 5px; color: #374151; font-size: 10.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .meta span { color: #7b8494; font-size: 10px; text-transform: uppercase; letter-spacing: .06em; }
  .item img { display: block; width: 100%; aspect-ratio: 3 / 5; object-fit: cover; object-position: top center; border: 1px solid #e5e7eb; border-radius: 7px; background: #fff; }
</style>
</head>
<body>
  <main id="overview">
    <header class="hero">
      <div>
        <h1>小红书卡片样式总览</h1>
        <p>基于当前 markdown-to-cards 代码直接渲染。上半部分是可传给 <code>style</code> 的模板样式；下半部分是 <code>style=legacy</code> 专用旧配色。</p>
      </div>
      <div class="badge">${styleCards.length} styles + ${legacyCards.length} legacy schemes</div>
    </header>
    ${sectionHtml("可用 style", "这些值可以直接传给 --style / MCP style 参数。", styleCards)}
    ${sectionHtml("legacy 旧配色", "这些值只在 style=legacy 时传给 color_scheme。", legacyCards)}
  </main>
</body>
</html>`;
  await fs.writeFile(htmlPath, html);
}

async function screenshot() {
  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1510, height: 2600, deviceScaleFactor: 1 });
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle0" });
    await page.screenshot({ path: pngPath, fullPage: true });
  } finally {
    await browser.close();
  }
}

const { styleCards, legacyCards } = await buildCards();
await writeHtml(styleCards, legacyCards);
await screenshot();

console.log(JSON.stringify({
  html: htmlPath,
  png: pngPath,
  styles: styleCards.map((card) => card.id),
  legacy_color_schemes: legacyCards.map((card) => card.id),
}, null, 2));
