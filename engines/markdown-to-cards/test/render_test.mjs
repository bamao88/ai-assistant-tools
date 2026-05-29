/**
 * 卡片样式测试脚本
 * 用法: node test/render_test.mjs
 *
 * 版本记录：
 *   v1 - 蓝色强调 + 顶部渐变条 + 底部品牌/页码，1080×1440 (3:4)
 *   v2 - 纯微信风：纯白底、纯黑字、无装饰，1080×1440 (3:4)
 *   v3 - 封面独立页 + 金棕配色协调正文，1440×2400 (3:5，对齐参考图)
 */
import puppeteer from "puppeteer";
import { marked } from "marked";
import path from "path";
import fs from "fs/promises";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ============================================================
// 全局配置 v3
// ============================================================
const CONFIG = {
  // 输出尺寸：CSS 像素 × deviceScaleFactor = 物理像素
  // 720×1200 × 2 = 1440×2400（对齐参考图）
  cssWidth: 720,
  cssHeight: 1200,
  deviceScaleFactor: 2,

  // 字体
  fontFamily: `'Microsoft YaHei', '微软雅黑', 'PingFang SC', 'Heiti SC', 'Hiragino Sans GB', '黑体', sans-serif`,

  // 配色
  accent: "#A07830",          // 金棕（封面 + 正文强调）
  accentLight: "#F5EDD8",     // 金棕浅底（引用块背景）
  coverBg: "#FDFAF4",         // 封面奶白底
  bodyBg: "#FFFFFF",          // 正文纯白底
  textColor: "#111111",       // 正文主色
  mutedColor: "#666666",      // 辅助灰

  // 封面底图路径
  coverBgPath: path.join(__dirname, "../Cover_template/xhs_blog.png"),

  // 封面字体（默认：思源宋体 Black + 1px 描边）
  coverFontOpts: {
    family:   "'Noto Serif SC', serif",
    weight:   900,
    cssPaths: [
      path.join(__dirname, "../node_modules/@fontsource/noto-serif-sc/chinese-simplified-900.css"),
      path.join(__dirname, "../node_modules/@fontsource/noto-serif-sc/latin-900.css"),
      path.join(__dirname, "../node_modules/@fontsource/noto-serif-sc/latin-ext-900.css"),
    ],
  },

  // 正文排版（CSS px，at 720px 宽度）
  paddingH: 54,               // 左右边距 → 物理 108px
  paddingV: 62,               // 上下边距 → 物理 124px
  fontSize: 25,               // 正文 → 物理 50px，手机舒适阅读
  lineHeight: 1.78,
};
// ============================================================

// --- 工具函数 ---

/** 从 markdown 提取第一个 H1 标题文本 */
function extractTitle(mdText) {
  const m = mdText.match(/^#\s+(.+)$/m);
  return m ? m[1].trim() : "";
}

/** 去掉 markdown 中的第一个 H1 行 */
function removeTitle(mdText) {
  return mdText.replace(/^#\s+.+\n?/m, "").trimStart();
}

/** 统计字数（中文字符 + 英文单词） */
function countWords(mdText) {
  const clean = mdText.replace(/```[\s\S]*?```/g, "")
                      .replace(/[#*`_~\[\]()\->|]/g, " ")
                      .replace(/\s+/g, " ").trim();
  const zhCount = (clean.match(/[\u4e00-\u9fa5]/g) || []).length;
  const enWords = clean.replace(/[\u4e00-\u9fa5]/g, " ")
                       .split(/\s+/).filter(w => /[a-zA-Z0-9]/.test(w)).length;
  return zhCount + enWords;
}

// --- 读取 fontsource CSS，将相对路径转为 file:// 绝对路径 ---
async function loadFontCSS(cssFilePath) {
  const dir = path.dirname(cssFilePath);
  const css = await fs.readFile(cssFilePath, "utf-8");
  return css.replace(/url\(\.(\/files\/[^)]+)\)/g, (_, rel) =>
    `url('file://${path.resolve(dir, "." + rel)}')`
  );
}

// --- 封面 HTML ---
// coverBgDataUrl: 底图的 base64 data URL（可选，无则退回程序生成背景）
// fontOpts: { css: string, family: string, weight: number }（可选，覆盖封面字体）
function buildCoverHtml(title, wordCount, cfg, coverBgDataUrl, fontOpts = {}) {
  const { cssWidth, cssHeight, fontFamily, accent, coverBg } = cfg;
  const titleFamily = fontOpts.family || "'Songti SC', 'STSong', serif";
  const titleWeight = fontOpts.weight || 900;
  const extraCss    = fontOpts.css    || "";
  const readMins = Math.max(1, Math.ceil(wordCount / 300));

  // 文本框区域（对齐底图中间空白区域，约 10%~90% 宽、27%~73% 高）
  const boxLeft   = Math.round(cssWidth * 0.10);   // 72px @ 720
  const boxTop    = Math.round(cssHeight * 0.265);  // 318px @ 1200
  const boxWidth  = Math.round(cssWidth * 0.80);    // 576px
  const boxHeight = Math.round(cssHeight * 0.465);  // 558px

  const bgStyle = coverBgDataUrl
    ? `background: url('${coverBgDataUrl}') center center / cover no-repeat;`
    : `background-color: ${coverBg};
       background-image: radial-gradient(circle, rgba(160,120,48,0.13) 1.5px, transparent 1.5px);
       background-size: 26px 26px;`;

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  ${extraCss}
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: ${cssWidth}px;
    font-family: ${fontFamily};
    -webkit-font-smoothing: antialiased;
  }
  #cover-page {
    width: ${cssWidth}px;
    height: ${cssHeight}px;
    ${bgStyle}
    overflow: hidden;
    position: relative;
  }

  /* 文本框：绝对定位，垂直居中，左对齐 */
  #text-box {
    position: absolute;
    left: ${boxLeft}px;
    top: ${boxTop}px;
    width: ${boxWidth}px;
    height: ${boxHeight}px;
    display: flex;
    align-items: center;
    justify-content: flex-start;
  }

  #cover-title {
    font-family: ${titleFamily};
    font-weight: ${titleWeight};
    color: #836034;
    -webkit-text-stroke: 1px #836034;
    line-height: 1.2;
    letter-spacing: 0.04em;
    word-break: normal;        /* 英文单词不强制断行 */
    overflow-wrap: break-word; /* 实在放不下才断 */
    text-align: left;
    width: 100%;
    /* 初始字号由 JS 自适应调整 */
    font-size: 72px;
  }
</style>
</head>
<body>
  <div id="cover-page">
    <div id="text-box">
      <div id="cover-title">${title}</div>
    </div>
  </div>
  <script>
    // 自适应字号：二分查找最大可放入 text-box 的字号
    const titleEl = document.getElementById('cover-title');
    const BOX_H = ${boxHeight};
    let lo = 20, hi = 80, best = 20;
    while (lo <= hi) {
      const mid = Math.floor((lo + hi) / 2);
      titleEl.style.fontSize = mid + 'px';
      if (titleEl.scrollHeight <= BOX_H) {
        best = mid;
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }
    titleEl.style.fontSize = best + 'px';
  </script>
</body>
</html>`;
}

// --- 正文页 HTML 模板 ---
function buildBodyPageHtml(cfg) {
  const {
    cssWidth, cssHeight, paddingH, paddingV,
    fontSize, lineHeight, fontFamily,
    bodyBg, textColor, accent, accentLight, mutedColor,
  } = cfg;

  const h2Size   = Math.round(fontSize * 1.32);  // ~33px
  const h3Size   = Math.round(fontSize * 1.12);  // ~28px
  const codeSize = Math.round(fontSize * 0.84);  // ~21px
  const tableFs  = Math.round(fontSize * 0.88);  // ~22px
  const paraGap  = Math.round(fontSize * 0.88);  // ~22px

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    width: ${cssWidth}px;
    background: ${bodyBg};
    color: ${textColor};
    font-size: ${fontSize}px;
    line-height: ${lineHeight};
    font-family: ${fontFamily};
    -webkit-font-smoothing: antialiased;
  }

  /* 测量容器（隐藏） */
  #measure-wrap {
    width: ${cssWidth - paddingH * 2}px;
    position: absolute;
    top: -9999px;
    left: 0;
    visibility: hidden;
    overflow: hidden;
    font-size: ${fontSize}px;
    line-height: ${lineHeight};
    font-family: ${fontFamily};
  }

  /* 卡片主容器 */
  #capture-page {
    width: ${cssWidth}px;
    height: ${cssHeight}px;
    overflow: hidden;
    background: ${bodyBg};
    padding: ${paddingV}px ${paddingH}px;
  }

  /* H2：金色左边框 + 加粗，标题与边框同色 */
  .md-body h2 {
    font-size: ${h2Size}px;
    font-weight: 700;
    line-height: 1.35;
    color: ${accent};
    border-left: 5px solid ${accent};
    padding-left: 16px;
    margin-top: ${Math.round(paraGap * 0.5)}px;
    margin-bottom: ${Math.round(paraGap * 0.8)}px;
  }

  .md-body h3 {
    font-size: ${h3Size}px;
    font-weight: 600;
    line-height: 1.4;
    color: ${textColor};
    margin-top: ${Math.round(paraGap * 0.3)}px;
    margin-bottom: ${Math.round(paraGap * 0.6)}px;
  }

  .md-body p {
    margin-bottom: ${paraGap}px;
    word-break: break-all;
    overflow-wrap: break-word;
  }

  /* 无序列表 */
  .md-body ul {
    margin-bottom: ${paraGap}px;
    padding-left: ${Math.round(fontSize * 1.3)}px;
    list-style-type: disc;
  }

  /* 有序列表 */
  .md-body ol {
    margin-bottom: ${paraGap}px;
    padding-left: ${Math.round(fontSize * 1.6)}px;
    list-style-type: decimal;
  }

  .md-body li {
    margin-bottom: ${Math.round(fontSize * 0.35)}px;
    line-height: ${lineHeight};
  }
  .md-body li > ul,
  .md-body li > ol {
    margin-top: ${Math.round(fontSize * 0.2)}px;
    margin-bottom: 0;
  }

  /* 粗体：金色 */
  .md-body strong {
    font-weight: 700;
    color: ${accent};
  }
  .md-body em { font-style: italic; }

  /* 行内代码：中性灰，无强调色 */
  .md-body code {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: ${codeSize}px;
    background: rgba(0, 0, 0, 0.07);
    padding: 0.12em 0.4em;
    border-radius: 4px;
    color: ${textColor};
  }

  /* 代码块：深色 */
  .md-body pre {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: ${Math.round(fontSize * 0.9)}px ${Math.round(fontSize)}px;
    border-radius: 10px;
    margin-bottom: ${paraGap}px;
    overflow: hidden;
  }
  .md-body pre code {
    background: none;
    padding: 0;
    color: inherit;
    font-size: ${codeSize}px;
    line-height: 1.6;
  }

  /* 引用块：金色浅底（透明度80%），无描边 */
  .md-body blockquote {
    background: rgba(245, 237, 216, 0.8);
    padding: ${Math.round(fontSize * 0.5)}px ${Math.round(fontSize * 0.85)}px;
    border-radius: 8px;
    margin-bottom: ${paraGap}px;
    color: #555;
    font-style: italic;
  }
  .md-body blockquote p { margin-bottom: 0; }

  /* 分割线 */
  .md-body hr {
    border: none;
    border-top: 1.5px solid #e5e7eb;
    margin: ${Math.round(paraGap * 0.7)}px 0;
  }

  /* 表格 */
  .md-body table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: ${paraGap}px;
    font-size: ${tableFs}px;
    line-height: 1.5;
  }
  .md-body th {
    background: #f3f4f6;
    color: ${textColor};
    font-weight: 700;
    padding: ${Math.round(fontSize * 0.4)}px ${Math.round(fontSize * 0.5)}px;
    border: 1.5px solid #ddd;
    text-align: left;
  }
  .md-body td {
    padding: ${Math.round(fontSize * 0.38)}px ${Math.round(fontSize * 0.5)}px;
    border: 1.5px solid #e5e7eb;
    vertical-align: top;
  }
  .md-body tr:nth-child(even) td { background: #fafafa; }

  .md-body a { color: ${accent}; text-decoration: underline; text-underline-offset: 3px; }
</style>
</head>
<body>
  <div id="measure-wrap"><div id="measure-content"></div></div>
  <div id="capture-page">
    <div class="md-body" id="capture-body"></div>
  </div>
</body>
</html>`;
}

// --- 主渲染函数 ---
async function renderMarkdownToCards(mdFile, outputDir, cfg = CONFIG) {
  const mdText = await fs.readFile(mdFile, "utf-8");
  const title = extractTitle(mdText);
  const bodyMd = removeTitle(mdText);
  const wordCount = countWords(mdText);
  const bodyHtml = marked.parse(bodyMd);

  await fs.mkdir(outputDir, { recursive: true });

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const files = [];

    // ── 0. 加载封面底图 + 封面字体 CSS ──
    let coverBgDataUrl = null;
    if (cfg.coverBgPath) {
      try {
        const buf = await fs.readFile(cfg.coverBgPath);
        coverBgDataUrl = `data:image/png;base64,${buf.toString("base64")}`;
      } catch (e) {
        console.warn("封面底图加载失败，退回程序生成背景:", e.message);
      }
    }

    let fontOpts = {};
    if (cfg.coverFontOpts) {
      let cssCombined = "";
      for (const p of (cfg.coverFontOpts.cssPaths || [])) {
        cssCombined += await loadFontCSS(p) + "\n";
      }
      fontOpts = { ...cfg.coverFontOpts, css: cssCombined };
    }

    // ── 1. 封面页 ──
    {
      const coverPage = await browser.newPage();
      await coverPage.setViewport({
        width: cfg.cssWidth,
        height: cfg.cssHeight,
        deviceScaleFactor: cfg.deviceScaleFactor,
      });
      await coverPage.setContent(buildCoverHtml(title, wordCount, cfg, coverBgDataUrl, fontOpts), {
        waitUntil: "networkidle0",
      });
      // 等待自定义字体加载完成
      await coverPage.waitForFunction(() => document.fonts.status === "loaded", { timeout: 5000 }).catch(() => {});
      const coverEl = await coverPage.$("#cover-page");
      const coverFile = path.join(outputDir, "card_00_cover.png");
      await coverEl.screenshot({ path: coverFile, type: "png" });
      console.log(`封面: ${coverFile}`);
      files.push(coverFile);
      await coverPage.close();
    }

    // ── 2. 正文页 ──
    {
      const bodyPage = await browser.newPage();
      await bodyPage.setViewport({
        width: cfg.cssWidth,
        height: cfg.cssHeight,
        deviceScaleFactor: cfg.deviceScaleFactor,
      });
      await bodyPage.setContent(buildBodyPageHtml(cfg), {
        waitUntil: "networkidle0",
      });

      // 有效内容高度
      const maxHeight = cfg.cssHeight - cfg.paddingV * 2;

      // DOM 分页
      const pages = await bodyPage.evaluate(
        (htmlContent, maxHeight) => {
          const mc = document.getElementById("measure-content");
          const tmp = document.createElement("div");
          tmp.innerHTML = htmlContent;
          const blocks = [];
          for (const node of tmp.childNodes) {
            if (node.nodeType === 3 && !node.textContent.trim()) continue;
            const wrap = document.createElement("div");
            wrap.appendChild(node.cloneNode(true));
            blocks.push(wrap.innerHTML);
          }
          const pages = [];
          let current = "";
          for (const block of blocks) {
            const candidate = current + block;
            mc.innerHTML = `<div class="md-body">${candidate}</div>`;
            if (mc.scrollHeight > maxHeight) {
              if (!current) { pages.push(block); current = ""; }
              else { pages.push(current); current = block; }
            } else {
              current = candidate;
            }
          }
          if (current) pages.push(current);
          return pages.length ? pages : [htmlContent];
        },
        bodyHtml,
        maxHeight
      );

      console.log(`正文页数: ${pages.length}`);
      const captureEl = await bodyPage.$("#capture-page");

      for (let i = 0; i < pages.length; i++) {
        await bodyPage.evaluate(
          (html) => { document.getElementById("capture-body").innerHTML = html; },
          pages[i]
        );
        const filename = path.join(outputDir, `card_${String(i + 1).padStart(2, "0")}.png`);
        await captureEl.screenshot({ path: filename, type: "png" });
        console.log(`正文 ${i + 1}/${pages.length}: ${filename}`);
        files.push(filename);
      }
      await bodyPage.close();
    }

    return files;
  } finally {
    await browser.close();
  }
}

// 运行
const mdFile = path.join(__dirname, "test/test_blog.md");
const outputDir = path.join(__dirname, "output/v4");
await renderMarkdownToCards(mdFile, outputDir);
console.log("完成！");
