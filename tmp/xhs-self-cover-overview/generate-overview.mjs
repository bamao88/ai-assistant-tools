import fs from "fs/promises";
import path from "path";
import { createRequire } from "module";
import { fileURLToPath, pathToFileURL } from "url";

import { CARD_STYLE_IDS, renderMarkdownToCards } from "../../engines/markdown-to-cards/lib/render.js";
import { getCardTemplate } from "../../engines/markdown-to-cards/lib/templates/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const requireFromEngine = createRequire(path.join(repoRoot, "engines/markdown-to-cards/package.json"));
const puppeteer = requireFromEngine("puppeteer");

const outDir = path.resolve(repoRoot, "tmp/xhs-self-cover-overview");
const cardsDir = path.join(outDir, "cards");
const htmlPath = path.join(outDir, "overview.html");
const pngPath = path.join(outDir, "overview.png");

const sample = `# 小红书长文封面模板测试

这是一次用于观察小红书长文封面模板的测试内容。我们关注封面版式、标题层级、背景色、图文组合方式和模板气质。

## 一个稳定的工作流

- 先明确读者真正要保存的信息
- 再把长文拆成能滑动阅读的卡片
- 最后检查标题层级、留白和重点是否清楚
`;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;");
}

function rel(filePath) {
  return path.relative(path.dirname(htmlPath), filePath).split(path.sep).join("/");
}

await fs.rm(cardsDir, { recursive: true, force: true });
await fs.mkdir(cardsDir, { recursive: true });

const styles = CARD_STYLE_IDS.filter((style) => style.startsWith("xhs-"));
const cards = [];
for (const style of styles) {
  const dir = path.join(cardsDir, style);
  const result = await renderMarkdownToCards(sample, {
    output_dir: dir,
    style,
    cover_style: "template",
    chapter_label: "小红书长文",
  });
  const cover = result.files.find((file) => path.basename(file).includes("cover"));
  const template = getCardTemplate(style);
  cards.push({ id: style, name: template.name, cover });
}

const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>自研小红书封面模板</title><style>
*{box-sizing:border-box}html,body{margin:0;background:#f4f5f7;color:#111827;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Noto Sans SC",sans-serif}body{padding:32px}.wrap{width:1440px;margin:0 auto}.head{display:flex;justify-content:space-between;align-items:end;margin-bottom:20px}.head h1{margin:0;font-size:34px;line-height:1.15;letter-spacing:0}.head p{margin:8px 0 0;color:#667085;font-size:14px}.badge{border:1px solid #d8dee8;background:#fff;border-radius:999px;padding:8px 13px;font-size:13px;color:#475467}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;align-items:start}.item{background:#fff;border:1px solid #e3e8ef;border-radius:10px;padding:10px;box-shadow:0 12px 28px rgba(15,23,42,.08);overflow:hidden}.meta{height:58px;display:flex;flex-direction:column;gap:5px;justify-content:center}.meta strong{font-size:15px;line-height:1.2}.meta code{font-size:10px;color:#667085;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.item img{display:block;width:100%;aspect-ratio:3/5;object-fit:cover;object-position:top center;border:1px solid #e5e7eb;border-radius:7px;background:#fafafa}
</style></head><body><main class="wrap"><header class="head"><div><h1>自研小红书封面模板</h1><p>基于官方模板截图抽象的本地自研版。只复刻版式气质，不使用小红书源码。</p></div><div class="badge">${cards.length} templates</div></header><section class="grid">${cards.map((card, index) => `<article class="item"><div class="meta"><strong>${index + 1}. ${escapeHtml(card.name)}</strong><code>${escapeHtml(card.id)}</code></div><img src="${escapeHtml(rel(card.cover))}" alt="${escapeHtml(card.name)}"></article>`).join("\n")}</section></main></body></html>`;
await fs.writeFile(htmlPath, html);
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-setuid-sandbox"] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1510, height: 2800, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle0" });
  await page.screenshot({ path: pngPath, fullPage: true });
} finally {
  await browser.close();
}
console.log(JSON.stringify({ html: htmlPath, png: pngPath, styles }, null, 2));
