#!/usr/bin/env node
import fs from "fs/promises";
import path from "path";
import puppeteer from "puppeteer";
import { CONFIG, renderMarkdownToHtmlPages } from "../lib/render.js";

const args = process.argv.slice(2);

function getArg(flag) {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : undefined;
}

function escapeXml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function textBlock(lines, x, y, opts = {}) {
  const {
    size = 25,
    weight = 400,
    fill = CONFIG.textColor,
    lineGap = Math.round(size * 1.78),
    family = "PingFang SC, Microsoft YaHei, sans-serif",
  } = opts;
  const tspans = lines.map((line, i) =>
    `<tspan x="${x}" dy="${i === 0 ? 0 : lineGap}">${escapeXml(line)}</tspan>`
  ).join("");
  return `<text x="${x}" y="${y}" font-family="${family}" font-size="${size}" font-weight="${weight}" fill="${fill}">${tspans}</text>`;
}

function frame(label, x, body) {
  return `
  <g id="${label}" transform="translate(${x}, 40)">
    <text x="0" y="-14" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700" fill="#444">${escapeXml(label)}</text>
    <rect x="0" y="0" width="720" height="1200" fill="${CONFIG.bodyBg}" stroke="#e5e7eb" stroke-width="1"/>
    ${body}
  </g>`;
}

function defaultCover() {
  return frame("01 Default Cover", 40, `
    <rect x="0" y="0" width="720" height="1200" fill="${CONFIG.coverBg}"/>
    <circle cx="150" cy="20" r="42" fill="#f7d2a3" opacity="0.7"/>
    <circle cx="228" cy="18" r="36" fill="#f7d2a3" opacity="0.7"/>
    ${textBlock(["Markdown 卡片", "样式导出", "Figma Handoff"], 72, 400, {
      size: 64,
      weight: 900,
      fill: "#836034",
      lineGap: 86,
      family: "Noto Serif SC, Songti SC, serif",
    })}
  `);
}

function componentFrame(name, x, y, width, height, body) {
  return `
  <g id="Component/${escapeXml(name)}" transform="translate(${x}, ${y})">
    <title>Component/${escapeXml(name)}</title>
    <rect x="0" y="0" width="${width}" height="${height}" rx="10" fill="#ffffff" stroke="#d9dee7" stroke-width="1.5"/>
    <text x="18" y="30" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="700" fill="#3f4652">${escapeXml(name)}</text>
    <g transform="translate(18, 54)">
      ${body}
    </g>
  </g>`;
}

function imageCover() {
  return frame("02 Image Cover", 800, `
    <rect x="0" y="0" width="720" height="1200" fill="${CONFIG.coverBg}"/>
    <rect x="0" y="0" width="720" height="696" fill="#dfe8e1"/>
    <path d="M0 520 C180 620 360 560 720 680 L720 0 L0 0 Z" fill="#c8d9cc" opacity="0.75"/>
    <text x="252" y="318" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="28" font-weight="700" fill="#315c42">Image Placeholder</text>
    <rect x="54" y="792" width="612" height="408" rx="8" fill="#fdfaf4" stroke="rgba(160,120,48,0.25)" stroke-width="2"/>
    ${textBlock(["精选长图文"], 92, 880, { size: 22, weight: 700, fill: CONFIG.accent, lineGap: 32 })}
    ${textBlock(["带图片封面", "标题样式"], 92, 958, {
      size: 58,
      weight: 900,
      fill: "#2b2419",
      lineGap: 72,
      family: "Noto Serif SC, Songti SC, serif",
    })}
    ${textBlock(["约 3 分钟阅读"], 92, 1130, { size: 20, fill: "rgba(43,36,25,0.62)", lineGap: 28 })}
  `);
}

function bodyPage() {
  const left = CONFIG.paddingH;
  return frame("03 Body Components", 1560, `
    ${textBlock(["基础段落与强调"], left + 20, 112, { size: 33, weight: 700, fill: CONFIG.accent, lineGap: 42 })}
    <rect x="${left}" y="78" width="5" height="44" fill="${CONFIG.accent}"/>
    ${textBlock([
      "这是一段正文，包含普通文本、粗体强调、链接、",
      "行内代码和中英文混排。段落需要按真实高度分页，",
      "不能整段跳页，也不能在跨页时漏字或重复。"
    ], left, 190, { size: 25, lineGap: 45 })}

    <rect x="${left}" y="360" width="612" height="118" rx="8" fill="rgba(245,237,216,0.8)"/>
    ${textBlock([
      "引用块：用于承载结论、提醒或关键判断，",
      "需要明显但不过度抢眼。"
    ], left + 22, 405, { size: 25, fill: "#555", lineGap: 42 })}

    <rect x="${left + 126}" y="548" width="360" height="206" rx="8" fill="#f8f6f1"/>
    <rect x="${left + 135}" y="557" width="342" height="188" rx="7" fill="#dfe8e1" stroke="#d6c9ae" stroke-width="1"/>
    <text x="${left + 306}" y="664" text-anchor="middle" font-family="PingFang SC, Arial, sans-serif" font-size="24" font-weight="700" fill="#315c42">Image Block</text>
    ${textBlock(["图片容器随图片尺寸变化，不固定撑满整行。"], left, 816, { size: 25, lineGap: 45 })}

    <g transform="translate(${left}, 900)">
      <rect x="0" y="0" width="612" height="150" fill="none" stroke="#e5e7eb" stroke-width="1.5"/>
      <rect x="0" y="0" width="612" height="48" fill="#f3f4f6"/>
      <line x1="180" y1="0" x2="180" y2="150" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="396" y1="0" x2="396" y2="150" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="0" y1="48" x2="612" y2="48" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="0" y1="99" x2="612" y2="99" stroke="#e5e7eb" stroke-width="1.5"/>
      ${textBlock(["场景"], 18, 32, { size: 20, weight: 700, lineGap: 26 })}
      ${textBlock(["期望行为"], 198, 32, { size: 20, weight: 700, lineGap: 26 })}
      ${textBlock(["风险"], 414, 32, { size: 20, weight: 700, lineGap: 26 })}
      ${textBlock(["长段落", "横向图片"], 18, 82, { size: 20, lineGap: 50 })}
      ${textBlock(["可拆分不丢字", "容器贴合图片"], 198, 82, { size: 20, lineGap: 50 })}
      ${textBlock(["页尾空白", "固定大框"], 414, 82, { size: 20, lineGap: 50 })}
    </g>
  `);
}

function figmaComponents() {
  const bodyW = CONFIG.cssWidth - CONFIG.paddingH * 2;
  const exampleW = 430;
  const paraGap = Math.round(CONFIG.fontSize * 0.88);
  const h2Size = Math.round(CONFIG.fontSize * 1.32);
  const h3Size = Math.round(CONFIG.fontSize * 1.12);
  const codeSize = Math.round(CONFIG.fontSize * 0.84);

  const components = [
    componentFrame("Cover / Template", 40, 64, 500, 390, `
      <rect x="0" y="0" width="430" height="300" rx="8" fill="${CONFIG.coverBg}" stroke="#e7ddc9"/>
      ${textBlock(["H1 封面标题", "自动适配字号"], 36, 116, {
        size: 42,
        weight: 900,
        fill: "#836034",
        lineGap: 58,
        family: "Noto Serif SC, Songti SC, serif",
      })}
    `),
    componentFrame("Cover / Image", 580, 64, 500, 390, `
      <rect x="0" y="0" width="430" height="300" rx="8" fill="${CONFIG.coverBg}" stroke="#e7ddc9"/>
      <rect x="0" y="0" width="430" height="160" rx="8" fill="#dfe8e1"/>
      <rect x="34" y="164" width="362" height="118" rx="8" fill="#fdfaf4" stroke="#dfd2b9"/>
      ${textBlock(["精选长图文"], 58, 202, { size: 16, weight: 700, fill: CONFIG.accent })}
      ${textBlock(["图片封面标题"], 58, 242, {
        size: 30,
        weight: 900,
        fill: "#2b2419",
        family: "Noto Serif SC, Songti SC, serif",
      })}
    `),
    componentFrame("Page / Body Canvas", 1120, 64, 500, 390, `
      <rect x="0" y="0" width="360" height="300" fill="${CONFIG.bodyBg}" stroke="#e7e7e7"/>
      <rect x="27" y="31" width="306" height="238" fill="none" stroke="#d9dee7" stroke-dasharray="8 6"/>
      ${textBlock(["720 x 1200 CSS px", `padding: ${CONFIG.paddingV}px ${CONFIG.paddingH}px`, "export: 1440 x 2400"], 54, 124, { size: 18, fill: "#555", lineGap: 32 })}
    `),
    componentFrame("Heading / H2", 40, 494, 500, 190, `
      <rect x="0" y="12" width="5" height="44" fill="${CONFIG.accent}"/>
      ${textBlock(["二级标题 H2"], 21, 48, { size: h2Size, weight: 700, fill: CONFIG.accent })}
      ${textBlock(["CSS: .md-body h2"], 0, 102, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Heading / H3", 580, 494, 500, 190, `
      ${textBlock(["三级标题 H3"], 0, 48, { size: h3Size, weight: 600, fill: CONFIG.textColor })}
      ${textBlock(["CSS: .md-body h3"], 0, 102, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Text / Paragraph", 1120, 494, 500, 250, `
      ${textBlock(["普通段落用于正文阅读，按真实高度分页。", "跨页时普通段落可以拆分，文本必须连续。"], 0, 38, { size: CONFIG.fontSize, lineGap: 45 })}
      ${textBlock(["CSS: .md-body p"], 0, 152, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Text / Inline Styles", 1660, 494, 500, 250, `
      ${textBlock(["普通文字  强调粗体  斜体语气"], 0, 38, { size: CONFIG.fontSize, lineGap: 45 })}
      ${textBlock(["链接文字"], 0, 90, { size: CONFIG.fontSize, fill: CONFIG.accent })}
      <line x1="0" y1="97" x2="96" y2="97" stroke="${CONFIG.accent}" stroke-width="1.4"/>
      <rect x="126" y="66" width="116" height="36" rx="4" fill="rgba(0,0,0,0.07)"/>
      ${textBlock(["inline code"], 136, 91, { size: codeSize, family: "SF Mono, Consolas, monospace" })}
      ${textBlock(["CSS: strong / em / a / code"], 0, 152, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Block / Quote", 40, 784, 500, 230, `
      <rect x="0" y="0" width="${exampleW}" height="112" rx="8" fill="rgba(245,237,216,0.8)"/>
      ${textBlock(["引用块用于承载结论、提醒或关键判断，", "需要明显但不过度抢眼。"], 22, 42, { size: CONFIG.fontSize, fill: "#555", lineGap: 42 })}
      ${textBlock(["CSS: .md-body blockquote"], 0, 156, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("List / Unordered", 580, 784, 500, 250, `
      ${textBlock(["•  无序列表第一项", "•  较长列表项换行后保持缩进", "•  无序列表第三项"], 0, 38, { size: CONFIG.fontSize, lineGap: 48 })}
      ${textBlock(["CSS: .md-body ul / li"], 0, 176, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("List / Ordered", 1120, 784, 500, 250, `
      ${textBlock(["1.  有序列表第一项", "2.  步骤说明第二项", "3.  有序列表第三项"], 0, 38, { size: CONFIG.fontSize, lineGap: 48 })}
      ${textBlock(["CSS: .md-body ol / li"], 0, 176, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Block / Code", 1660, 784, 500, 310, `
      <rect x="0" y="0" width="${exampleW}" height="172" rx="10" fill="#1e1e1e"/>
      ${textBlock(["const card = render(markdown);", "await card.screenshot({", "  type: 'png'", "});"], 24, 38, { size: codeSize, fill: "#d4d4d4", lineGap: 34, family: "SF Mono, Consolas, monospace" })}
      ${textBlock(["CSS: .md-body pre / pre code"], 0, 218, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Block / Table", 40, 1074, 680, 320, `
      <rect x="0" y="0" width="612" height="150" fill="none" stroke="#e5e7eb" stroke-width="1.5"/>
      <rect x="0" y="0" width="612" height="48" fill="#f3f4f6"/>
      <line x1="180" y1="0" x2="180" y2="150" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="396" y1="0" x2="396" y2="150" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="0" y1="48" x2="612" y2="48" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="0" y1="99" x2="612" y2="99" stroke="#e5e7eb" stroke-width="1.5"/>
      ${textBlock(["场景"], 18, 32, { size: 20, weight: 700 })}
      ${textBlock(["期望行为"], 198, 32, { size: 20, weight: 700 })}
      ${textBlock(["风险"], 414, 32, { size: 20, weight: 700 })}
      ${textBlock(["长段落", "横向图片"], 18, 82, { size: 20, lineGap: 50 })}
      ${textBlock(["可拆分不丢字", "容器贴合图片"], 198, 82, { size: 20, lineGap: 50 })}
      ${textBlock(["页尾空白", "固定大框"], 414, 82, { size: 20, lineGap: 50 })}
      ${textBlock(["CSS: .md-body table / th / td"], 0, 206, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Media / Landscape Image", 760, 1074, 500, 320, `
      <rect x="50" y="0" width="360" height="204" rx="8" fill="#f8f6f1"/>
      <rect x="60" y="10" width="340" height="184" rx="7" fill="#dfe8e1" stroke="#d6c9ae"/>
      <text x="230" y="112" text-anchor="middle" font-family="PingFang SC, Arial, sans-serif" font-size="22" font-weight="700" fill="#315c42">Landscape Image</text>
      ${textBlock(["CSS: p:has(> img.md-image:only-child)"], 0, 250, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Media / Portrait Image", 1300, 1074, 500, 390, `
      <rect x="142" y="0" width="176" height="264" rx="8" fill="#f8f6f1"/>
      <rect x="152" y="10" width="156" height="244" rx="7" fill="#f2eadb" stroke="#d6c9ae"/>
      <text x="230" y="140" text-anchor="middle" font-family="PingFang SC, Arial, sans-serif" font-size="20" font-weight="700" fill="#785a2c">Portrait</text>
      ${textBlock(["CSS: --image-max-height"], 0, 310, { size: 15, fill: "#6b7280" })}
    `),
    componentFrame("Block / Horizontal Rule", 1840, 1074, 360, 180, `
      <line x1="0" y1="48" x2="300" y2="48" stroke="#e5e7eb" stroke-width="1.5"/>
      ${textBlock(["CSS: .md-body hr"], 0, 102, { size: 15, fill: "#6b7280" })}
    `),
  ];

  return `<svg xmlns="http://www.w3.org/2000/svg" width="2240" height="1510" viewBox="0 0 2240 1510">
  <rect width="2240" height="1510" fill="#f5f5f5"/>
  <text x="40" y="34" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="800" fill="#222">Markdown-to-Cards Component Library</text>
  ${components.join("\n")}
</svg>
  `;
}

async function fileToDataUrl(filePath) {
  const buf = await fs.readFile(filePath);
  return `data:image/png;base64,${buf.toString("base64")}`;
}

async function renderedCardsLayout(cardsDir) {
  const names = (await fs.readdir(cardsDir))
    .filter((name) => /^card_.*\.png$/i.test(name))
    .sort();
  const files = names.map((name) => path.join(cardsDir, name));
  const cardW = CONFIG.cssWidth;
  const cardH = CONFIG.cssHeight;
  const gap = 40;
  const margin = 40;
  const width = margin * 2 + files.length * cardW + Math.max(0, files.length - 1) * gap;
  const height = 1320;

  const cards = [];
  for (let i = 0; i < files.length; i++) {
    const x = margin + i * (cardW + gap);
    const label = names[i].replace(".png", "");
    const dataUrl = await fileToDataUrl(files[i]);
    cards.push(`
  <g id="RealRender/${escapeXml(label)}" transform="translate(${x}, 70)">
    <title>RealRender/${escapeXml(label)}</title>
    <text x="0" y="-14" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700" fill="#444">${escapeXml(label)}</text>
    <rect x="0" y="0" width="${cardW}" height="${cardH}" fill="#fff" stroke="#d9dee7" stroke-width="1.5"/>
    <image href="${dataUrl}" x="0" y="0" width="${cardW}" height="${cardH}" preserveAspectRatio="xMidYMid meet"/>
  </g>`);
  }

  return {
    files,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="${width}" height="${height}" fill="#f5f5f5"/>
  <text x="40" y="34" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="800" fill="#222">Markdown-to-Cards Real Render Layout</text>
  ${cards.join("\n")}
</svg>
`,
  };
}

function num(value) {
  return Number.parseFloat(Number(value || 0).toFixed(2));
}

function paintAttrs(color, attr) {
  const raw = String(color || "").trim();
  if (!raw || raw === "transparent") return `${attr}="none"`;

  const rgba = raw.match(/^rgba?\(([^)]+)\)$/i);
  if (!rgba) return `${attr}="${escapeXml(raw)}"`;

  const parts = rgba[1].split(",").map((part) => part.trim());
  const [r, g, b] = parts.slice(0, 3).map((part) => Math.round(Number.parseFloat(part)));
  const alpha = parts.length > 3 ? Number.parseFloat(parts[3]) : 1;
  const opacity = Number.isFinite(alpha) && alpha < 1 ? ` ${attr}-opacity="${num(alpha)}"` : "";
  return `${attr}="rgb(${r}, ${g}, ${b})"${opacity}`;
}

function renderEditableLayer(layer, defs, clipState) {
  if (layer.type === "rect") {
    return `<rect x="${num(layer.x)}" y="${num(layer.y)}" width="${num(layer.width)}" height="${num(layer.height)}" rx="${num(layer.rx || 0)}" ${paintAttrs(layer.fill, "fill")}/>`;
  }

  if (layer.type === "strokedRect") {
    return `<rect x="${num(layer.x)}" y="${num(layer.y)}" width="${num(layer.width)}" height="${num(layer.height)}" rx="${num(layer.rx || 0)}" fill="none" ${paintAttrs(layer.stroke, "stroke")} stroke-width="${num(layer.strokeWidth || 1)}"/>`;
  }

  if (layer.type === "line") {
    return `<line x1="${num(layer.x1)}" y1="${num(layer.y1)}" x2="${num(layer.x2)}" y2="${num(layer.y2)}" ${paintAttrs(layer.stroke, "stroke")} stroke-width="${num(layer.strokeWidth || 1)}" stroke-linecap="square"/>`;
  }

  if (layer.type === "image") {
    const preserve = layer.preserveAspectRatio || "xMidYMid meet";
    let clip = "";
    if (layer.rx > 0) {
      const clipId = `editable-image-clip-${clipState.next++}`;
      defs.push(`<clipPath id="${clipId}"><rect x="${num(layer.x)}" y="${num(layer.y)}" width="${num(layer.width)}" height="${num(layer.height)}" rx="${num(layer.rx)}"/></clipPath>`);
      clip = ` clip-path="url(#${clipId})"`;
    }
    return `<image href="${escapeXml(layer.href)}" x="${num(layer.x)}" y="${num(layer.y)}" width="${num(layer.width)}" height="${num(layer.height)}" preserveAspectRatio="${escapeXml(preserve)}"${clip}/>`;
  }

  return "";
}

function normalizeFontFamily(fontFamily) {
  const raw = String(fontFamily || "");
  if (/Noto Serif SC|Songti SC|serif/i.test(raw)) return "Noto Serif SC, Songti SC, serif";
  if (/SF Mono|Fira Code|Consolas|monospace/i.test(raw)) return "SF Mono, Consolas, monospace";
  if (/PingFang SC|Microsoft YaHei|微软雅黑|Heiti SC|Hiragino Sans GB/i.test(raw)) {
    return "PingFang SC, Microsoft YaHei, sans-serif";
  }
  if (/Inter|Arial/i.test(raw)) return "Inter, Arial, sans-serif";
  return "PingFang SC, Microsoft YaHei, sans-serif";
}

function renderEditableText(text) {
  const baselineY = text.baselineY ?? (text.y + text.fontSize * 0.86);
  const attrs = [
    `x="${num(text.x)}"`,
    `y="${num(baselineY)}"`,
    `font-family="${escapeXml(normalizeFontFamily(text.fontFamily))}"`,
    `font-size="${num(text.fontSize)}"`,
    `font-weight="${escapeXml(text.fontWeight)}"`,
    `font-style="${escapeXml(text.fontStyle)}"`,
    paintAttrs(text.fill, "fill"),
  ];

  if (text.preserveWhitespace) attrs.push(`xml:space="preserve"`);

  if (text.decoration && text.decoration !== "none") {
    attrs.push(`text-decoration="${escapeXml(text.decoration)}"`);
  }
  if (text.letterSpacing && text.letterSpacing !== "normal" && text.letterSpacing !== "0px") {
    attrs.push(`letter-spacing="${escapeXml(text.letterSpacing)}"`);
  }

  const value = text.preserveWhitespace
    ? String(text.text).replace(/ /g, "\u00a0")
    : String(text.text).replace(/\s+/g, " ").trim();

  return value ? `<text ${attrs.join(" ")}>${escapeXml(value)}</text>` : "";
}

async function collectEditablePageModel(page, rootSelector) {
  return page.evaluate((selector) => {
    const root = document.querySelector(selector);
    if (!root) throw new Error(`Missing SVG export root: ${selector}`);

    const rootRect = root.getBoundingClientRect();
    const layers = [];
    const texts = [];

    function px(value) {
      const n = Number.parseFloat(value);
      return Number.isFinite(n) ? n : 0;
    }

    function colorVisible(color) {
      if (!color || color === "transparent") return false;
      const rgba = String(color).match(/^rgba?\(([^)]+)\)$/i);
      if (!rgba) return true;
      const parts = rgba[1].split(",").map((part) => part.trim());
      return parts.length < 4 || Number.parseFloat(parts[3]) > 0;
    }

    function elementVisible(el) {
      const style = getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || Number.parseFloat(style.opacity || "1") === 0) {
        return false;
      }
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 &&
        rect.right > rootRect.left && rect.left < rootRect.right &&
        rect.bottom > rootRect.top && rect.top < rootRect.bottom;
    }

    function relRect(el) {
      const rect = el.getBoundingClientRect();
      return {
        x: rect.left - rootRect.left,
        y: rect.top - rootRect.top,
        width: rect.width,
        height: rect.height,
      };
    }

    function radius(style) {
      return Math.max(
        px(style.borderTopLeftRadius),
        px(style.borderTopRightRadius),
        px(style.borderBottomRightRadius),
        px(style.borderBottomLeftRadius)
      );
    }

    function cssUrl(value) {
      const match = String(value || "").match(/url\(["']?(.+?)["']?\)/);
      return match ? match[1] : "";
    }

    function addBorders(rect, style) {
      const sides = [
        ["Top", rect.x, rect.y, rect.x + rect.width, rect.y],
        ["Right", rect.x + rect.width, rect.y, rect.x + rect.width, rect.y + rect.height],
        ["Bottom", rect.x, rect.y + rect.height, rect.x + rect.width, rect.y + rect.height],
        ["Left", rect.x, rect.y, rect.x, rect.y + rect.height],
      ];

      const widths = sides.map(([side]) => px(style[`border${side}Width`]));
      const colors = sides.map(([side]) => style[`border${side}Color`]);
      const styles = sides.map(([side]) => style[`border${side}Style`]);
      const allSame = widths.every((w) => w > 0 && Math.abs(w - widths[0]) < 0.1) &&
        colors.every((c) => c === colors[0]) &&
        styles.every((s) => s !== "none" && s === styles[0]) &&
        colorVisible(colors[0]);

      if (allSame) {
        layers.push({
          type: "strokedRect",
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          rx: radius(style),
          stroke: colors[0],
          strokeWidth: widths[0],
        });
        return;
      }

      for (let i = 0; i < sides.length; i++) {
        const [side, x1, y1, x2, y2] = sides[i];
        const width = widths[i];
        const color = colors[i];
        const borderStyle = styles[i];
        if (width <= 0 || borderStyle === "none" || !colorVisible(color)) continue;
        layers.push({ type: "line", x1, y1, x2, y2, stroke: color, strokeWidth: width });
      }
    }

    function addElementPaint(el) {
      if (!elementVisible(el) || ["SCRIPT", "STYLE"].includes(el.tagName)) return;

      const style = getComputedStyle(el);
      const rect = relRect(el);
      const bg = style.backgroundColor;
      if (colorVisible(bg)) {
        layers.push({
          type: "rect",
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          rx: radius(style),
          fill: bg,
        });
      }

      const bgUrl = cssUrl(style.backgroundImage);
      if (bgUrl) {
        layers.push({
          type: "image",
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          rx: radius(style),
          href: bgUrl,
          preserveAspectRatio: String(style.backgroundSize).includes("cover") ? "xMidYMid slice" : "xMidYMid meet",
        });
      }

      addBorders(rect, style);

      if (el.tagName === "IMG") {
        layers.push({
          type: "image",
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          rx: radius(style),
          href: el.currentSrc || el.src || el.getAttribute("src") || "",
          preserveAspectRatio: "xMidYMid meet",
        });
      }
    }

    function textNodeVisible(node) {
      const parent = node.parentElement;
      if (!parent || !root.contains(parent) || ["SCRIPT", "STYLE"].includes(parent.tagName)) return false;
      if (!node.textContent || !node.textContent.trim()) return false;
      return elementVisible(parent);
    }

    function addTextNode(node) {
      const parent = node.parentElement;
      const style = getComputedStyle(parent);
      const preserveWhitespace = style.whiteSpace.includes("pre");
      const fontSize = px(style.fontSize);
      if (!fontSize || !colorVisible(style.color)) return;

      const groups = [];
      let current = null;
      const text = node.textContent || "";

      function startGroup(rect, ch) {
        current = {
          x: rect.left - rootRect.left,
          y: rect.top - rootRect.top,
          lastX: rect.left - rootRect.left,
          text: ch,
        };
        groups.push(current);
      }

      for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (ch === "\n") {
          if (preserveWhitespace) current = null;
          continue;
        }

        const range = document.createRange();
        range.setStart(node, i);
        range.setEnd(node, i + 1);
        const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0 || rect.height > 0);
        range.detach?.();

        if (!rects.length) {
          if (preserveWhitespace && /\s/.test(ch) && current) current.text += ch;
          continue;
        }

        const rect = rects[0];
        if (
          rect.right < rootRect.left || rect.left > rootRect.right ||
          rect.bottom < rootRect.top || rect.top > rootRect.bottom
        ) {
          continue;
        }

        const x = rect.left - rootRect.left;
        const y = rect.top - rootRect.top;
        const normalizedChar = ch === "\u00a0" ? " " : ch;
        const startsNewLine = !current ||
          Math.abs(y - current.y) > 2 ||
          (x < current.lastX - 2 && !/\s/.test(normalizedChar));

        if (startsNewLine) {
          startGroup(rect, normalizedChar);
        } else {
          current.text += normalizedChar;
          current.x = Math.min(current.x, x);
          current.y = Math.min(current.y, y);
          current.lastX = x;
        }
      }

      for (const group of groups) {
        let value = group.text.replace(/\u00a0/g, " ");
        if (!preserveWhitespace) value = value.replace(/\s+/g, " ");
        if (!value.trim()) continue;
        texts.push({
          x: group.x,
          y: group.y,
          baselineY: group.y + fontSize * 0.86,
          text: value,
          fontFamily: style.fontFamily,
          fontSize,
          fontWeight: style.fontWeight,
          fontStyle: style.fontStyle,
          fill: style.color,
          decoration: style.textDecorationLine && style.textDecorationLine !== "none" ? style.textDecorationLine : "",
          letterSpacing: style.letterSpacing,
          preserveWhitespace,
        });
      }
    }

    for (const el of [root, ...Array.from(root.querySelectorAll("*"))]) {
      addElementPaint(el);
    }

    const textWalker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return textNodeVisible(node) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    while (textWalker.nextNode()) addTextNode(textWalker.currentNode);

    return {
      width: rootRect.width,
      height: rootRect.height,
      layers,
      texts,
    };
  }, rootSelector);
}

async function editableFullLayoutFromMarkdown(fixturePath, renderOptions) {
  const markdownText = await fs.readFile(fixturePath, "utf-8");
  const htmlLayout = await renderMarkdownToHtmlPages(markdownText, renderOptions);
  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({
      width: htmlLayout.cfg.cssWidth,
      height: htmlLayout.cfg.cssHeight,
      deviceScaleFactor: 1,
    });

    const models = [];
    for (const doc of htmlLayout.pages) {
      await page.setContent(doc.html, { waitUntil: "load", timeout: 60000 });
      await page.evaluate(async () => {
        await document.fonts.ready.catch(() => {});
        await Promise.all(Array.from(document.images).map((img) => {
          if (img.complete) return img.decode ? img.decode().catch(() => {}) : Promise.resolve();
          return new Promise((resolve) => {
            const done = () => resolve();
            img.addEventListener("load", done, { once: true });
            img.addEventListener("error", done, { once: true });
            setTimeout(done, 5000);
          });
        }));
      });
      models.push({ ...doc, model: await collectEditablePageModel(page, doc.selector) });
    }

    const cardW = htmlLayout.cfg.cssWidth;
    const cardH = htmlLayout.cfg.cssHeight;
    const gap = 40;
    const margin = 40;
    const top = 70;
    const width = margin * 2 + models.length * cardW + Math.max(0, models.length - 1) * gap;
    const height = top + cardH + 50;
    const defs = [];
    const clipState = { next: 1 };

    const cards = models.map((doc, index) => {
      const x = margin + index * (cardW + gap);
      const layers = doc.model.layers.map((layer) => renderEditableLayer(layer, defs, clipState)).filter(Boolean).join("\n      ");
      const text = doc.model.texts.map((line) => renderEditableText(line)).join("\n      ");
      return `
  <g id="Editable/${escapeXml(doc.label)}" transform="translate(${x}, ${top})">
    <title>Editable/${escapeXml(doc.label)}</title>
    <text x="0" y="-14" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700" fill="#444">${escapeXml(doc.label)}</text>
    <g id="EditableContent/${escapeXml(doc.label)}">
      ${layers}
      ${text}
    </g>
    <rect x="0" y="0" width="${cardW}" height="${cardH}" fill="none" stroke="#d9dee7" stroke-width="1.5"/>
  </g>`;
    });

    return {
      warnings: htmlLayout.warnings,
      pages: models.map((doc, index) => ({
        page: index,
        label: doc.label,
        kind: doc.kind,
        textObjects: doc.model.texts.length,
        paintObjects: doc.model.layers.length,
        figmaWidth: cardW,
        figmaHeight: cardH,
      })),
      svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    ${defs.join("\n    ")}
  </defs>
  <rect width="${width}" height="${height}" fill="#f5f5f5"/>
  <text x="40" y="34" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="800" fill="#222">Markdown-to-Cards Editable Full Layout</text>
  ${cards.join("\n")}
</svg>
`,
    };
  } finally {
    await browser.close();
  }
}

function layoutCard(label, x, y, body, bg = CONFIG.bodyBg) {
  return `
  <g id="FullLayout/${escapeXml(label)}" transform="translate(${x}, ${y})">
    <title>FullLayout/${escapeXml(label)}</title>
    <text x="0" y="-14" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700" fill="#444">${escapeXml(label)}</text>
    <rect x="0" y="0" width="${CONFIG.cssWidth}" height="${CONFIG.cssHeight}" fill="${bg}" stroke="#d9dee7" stroke-width="1.5"/>
    ${body}
  </g>`;
}

function fullCardLayout() {
  const left = CONFIG.paddingH;
  const top = CONFIG.paddingV;
  const bodyW = CONFIG.cssWidth - CONFIG.paddingH * 2;
  const h2Size = Math.round(CONFIG.fontSize * 1.32);
  const h3Size = Math.round(CONFIG.fontSize * 1.12);
  const codeSize = Math.round(CONFIG.fontSize * 0.84);

  const defaultCoverCard = layoutCard("01 Cover Template", 40, 70, `
    <rect x="0" y="0" width="720" height="1200" fill="${CONFIG.coverBg}"/>
    <circle cx="150" cy="18" r="42" fill="#f7d2a3" opacity="0.72"/>
    <circle cx="228" cy="16" r="36" fill="#f7d2a3" opacity="0.72"/>
    ${textBlock(["Markdown", "全样式卡片", "排版预览"], 72, 384, {
      size: 68,
      weight: 900,
      fill: "#836034",
      lineGap: 90,
      family: "Noto Serif SC, Songti SC, serif",
    })}
  `, CONFIG.coverBg);

  const imageCoverCard = layoutCard("02 Cover Image", 800, 70, `
    <rect x="0" y="0" width="720" height="1200" fill="${CONFIG.coverBg}"/>
    <rect x="0" y="0" width="720" height="696" fill="#dfe8e1"/>
    <path d="M0 482 C158 610 338 542 720 672 L720 0 L0 0 Z" fill="#c6d9ce" opacity="0.86"/>
    <circle cx="140" cy="176" r="64" fill="#b8cdbd" opacity="0.9"/>
    <rect x="294" y="172" width="284" height="190" rx="18" fill="#eef3ef" opacity="0.88"/>
    <text x="436" y="282" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="28" font-weight="700" fill="#315c42">Cover Image</text>
    <rect x="54" y="792" width="612" height="408" rx="8" fill="#fdfaf4" stroke="rgba(160,120,48,0.25)" stroke-width="2"/>
    ${textBlock(["精选长图文"], 92, 880, { size: 22, weight: 700, fill: CONFIG.accent })}
    ${textBlock(["图片封面", "完整标题样式"], 92, 958, {
      size: 58,
      weight: 900,
      fill: "#2b2419",
      lineGap: 72,
      family: "Noto Serif SC, Songti SC, serif",
    })}
    ${textBlock(["约 3 分钟阅读"], 92, 1130, { size: 20, fill: "rgba(43,36,25,0.62)" })}
  `, CONFIG.coverBg);

  const bodyCardOne = layoutCard("03 Body Mixed", 1560, 70, `
    <rect x="${left}" y="${top + 6}" width="5" height="44" fill="${CONFIG.accent}"/>
    ${textBlock(["1. 标题、段落和引用"], left + 20, top + 40, { size: h2Size, weight: 700, fill: CONFIG.accent })}
    ${textBlock([
      "这是一张完整正文卡片，包含普通段落、",
      "粗体强调、链接、行内代码和中英文混排。",
      "段落用于观察页面边距、行高和分页节奏。"
    ], left, top + 112, { size: CONFIG.fontSize, lineGap: 45 })}
    <rect x="${left}" y="${top + 286}" width="${bodyW}" height="122" rx="8" fill="rgba(245,237,216,0.8)"/>
    ${textBlock([
      "引用块：承载结论、提醒或关键判断，",
      "保持浅色底和舒适内边距。"
    ], left + 22, top + 334, { size: CONFIG.fontSize, fill: "#555", lineGap: 42 })}
    ${textBlock(["三级标题 H3"], left, top + 488, { size: h3Size, weight: 600 })}
    ${textBlock([
      "三级标题下面继续放正文，检查标题和正文之间",
      "的距离是否稳定。"
    ], left, top + 550, { size: CONFIG.fontSize, lineGap: 45 })}
    ${textBlock([
      "• 无序列表第一项：验证 bullet 和缩进",
      "• 较长列表项换行后仍应保持对齐",
      "• 列表后面可以继续正文"
    ], left, top + 704, { size: CONFIG.fontSize, lineGap: 50 })}
    ${textBlock([
      "1. 有序列表第一项",
      "2. 步骤说明第二项",
      "3. 有序列表第三项"
    ], left, top + 900, { size: CONFIG.fontSize, lineGap: 50 })}
  `);

  const bodyCardTwo = layoutCard("04 Media Code Table", 2320, 70, `
    <rect x="${left}" y="${top + 6}" width="5" height="44" fill="${CONFIG.accent}"/>
    ${textBlock(["2. 图片、代码和表格"], left + 20, top + 40, { size: h2Size, weight: 700, fill: CONFIG.accent })}
    <rect x="${left + 80}" y="${top + 96}" width="452" height="258" rx="8" fill="#f8f6f1"/>
    <rect x="${left + 90}" y="${top + 106}" width="432" height="238" rx="7" fill="#dfe8e1" stroke="#d6c9ae"/>
    <text x="${left + 306}" y="${top + 238}" text-anchor="middle" font-family="PingFang SC, Arial, sans-serif" font-size="26" font-weight="700" fill="#315c42">Landscape Image</text>
    ${textBlock(["图片容器贴合图片尺寸，不固定撑满整行。"], left, top + 420, { size: CONFIG.fontSize })}
    <line x1="${left}" y1="${top + 500}" x2="${left + bodyW}" y2="${top + 500}" stroke="#e5e7eb" stroke-width="1.5"/>
    <rect x="${left}" y="${top + 552}" width="${bodyW}" height="176" rx="10" fill="#1e1e1e"/>
    ${textBlock(["const card = render(markdown);", "await card.screenshot({", "  type: 'png'", "});"], left + 24, top + 592, { size: codeSize, fill: "#d4d4d4", lineGap: 34, family: "SF Mono, Consolas, monospace" })}
    <g transform="translate(${left}, ${top + 800})">
      <rect x="0" y="0" width="${bodyW}" height="150" fill="none" stroke="#e5e7eb" stroke-width="1.5"/>
      <rect x="0" y="0" width="${bodyW}" height="48" fill="#f3f4f6"/>
      <line x1="180" y1="0" x2="180" y2="150" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="396" y1="0" x2="396" y2="150" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="0" y1="48" x2="${bodyW}" y2="48" stroke="#e5e7eb" stroke-width="1.5"/>
      <line x1="0" y1="99" x2="${bodyW}" y2="99" stroke="#e5e7eb" stroke-width="1.5"/>
      ${textBlock(["场景"], 18, 32, { size: 20, weight: 700 })}
      ${textBlock(["期望行为"], 198, 32, { size: 20, weight: 700 })}
      ${textBlock(["风险"], 414, 32, { size: 20, weight: 700 })}
      ${textBlock(["长段落", "横向图片"], 18, 82, { size: 20, lineGap: 50 })}
      ${textBlock(["可拆分不丢字", "容器贴合图片"], 198, 82, { size: 20, lineGap: 50 })}
      ${textBlock(["页尾空白", "固定大框"], 414, 82, { size: 20, lineGap: 50 })}
    </g>
  `);

  const bodyCardThree = layoutCard("05 Portrait And Closing", 3080, 70, `
    <rect x="${left}" y="${top + 6}" width="5" height="44" fill="${CONFIG.accent}"/>
    ${textBlock(["3. 竖图和收尾"], left + 20, top + 40, { size: h2Size, weight: 700, fill: CONFIG.accent })}
    <rect x="${left + 192}" y="${top + 106}" width="228" height="342" rx="8" fill="#f8f6f1"/>
    <rect x="${left + 202}" y="${top + 116}" width="208" height="322" rx="7" fill="#f2eadb" stroke="#d6c9ae"/>
    <text x="${left + 306}" y="${top + 288}" text-anchor="middle" font-family="PingFang SC, Arial, sans-serif" font-size="24" font-weight="700" fill="#785a2c">Portrait Image</text>
    ${textBlock([
      "竖向图片用于检查页尾缩放、独立成页和",
      "后续正文衔接。真实内容里常见于长截图、",
      "检查表、清单卡片和移动端页面。"
    ], left, top + 520, { size: CONFIG.fontSize, lineGap: 45 })}
    ${textBlock(["收尾段落"], left, top + 720, { size: h3Size, weight: 600 })}
    ${textBlock([
      "最后一段确认所有复杂块之后仍然能回到",
      "普通正文节奏。页面底部应该保留自然空白，",
      "但不应因为整块跳页产生明显断裂。"
    ], left, top + 786, { size: CONFIG.fontSize, lineGap: 45 })}
  `);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="3840" height="1350" viewBox="0 0 3840 1350">
  <rect width="3840" height="1350" fill="#f5f5f5"/>
  <text x="40" y="34" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="800" fill="#222">Markdown-to-Cards Full Layout</text>
  ${defaultCoverCard}
  ${imageCoverCard}
  ${bodyCardOne}
  ${bodyCardTwo}
  ${bodyCardThree}
</svg>
`;
}

const outputDir = path.resolve(getArg("--output-dir") || path.join(process.cwd(), "tmp", `figma_${Date.now()}`));
await fs.mkdir(outputDir, { recursive: true });
const fixturePath = path.resolve(getArg("--fixture") || "test/fixtures/real_world_all_styles.md");
const cardsDir = getArg("--cards-dir") ? path.resolve(getArg("--cards-dir")) : null;
const baseDir = path.resolve(getArg("--base-dir") || path.dirname(fixturePath));
const coverImagePath = getArg("--cover-image");
const coverStyle = getArg("--cover-style") || "image";
const style = getArg("--style") || "legacy";
const chapterLabel = getArg("--chapter-label") || "精选长图文";
const coverVariant = getArg("--cover-variant") || "primary";

const tokens = {
  canvas: {
    cssWidth: CONFIG.cssWidth,
    cssHeight: CONFIG.cssHeight,
    deviceScaleFactor: CONFIG.deviceScaleFactor,
    exportSize: `${CONFIG.cssWidth * CONFIG.deviceScaleFactor}x${CONFIG.cssHeight * CONFIG.deviceScaleFactor}`,
  },
  colors: {
    accent: CONFIG.accent,
    coverBg: CONFIG.coverBg,
    bodyBg: CONFIG.bodyBg,
    textColor: CONFIG.textColor,
    quoteBg: "rgba(245,237,216,0.8)",
    imageBg: "#f8f6f1",
  },
  typography: {
    bodyFontFamily: CONFIG.fontFamily,
    bodyFontSize: CONFIG.fontSize,
    bodyLineHeight: CONFIG.lineHeight,
    h2Size: Math.round(CONFIG.fontSize * 1.32),
    h3Size: Math.round(CONFIG.fontSize * 1.12),
    codeSize: Math.round(CONFIG.fontSize * 0.84),
  },
  spacing: {
    paddingH: CONFIG.paddingH,
    paddingV: CONFIG.paddingV,
    paragraphGap: Math.round(CONFIG.fontSize * 0.88),
    imagePadding: Math.round(CONFIG.fontSize * 0.35),
  },
  theme: {
    style,
    chapterLabel,
    coverVariant,
  },
};

const componentManifest = [
  { component: "Cover / Template", markdown: "# H1", selector: "#cover-page / #cover-title", code: "lib/render.js buildTemplateCoverHtml" },
  { component: "Cover / Image", markdown: "# H1 + cover_image_path", selector: "#cover-page / #cover-hero / #cover-panel", code: "lib/render.js buildImageCoverHtml" },
  { component: "Page / Body Canvas", markdown: "body page", selector: "#capture-page", code: "lib/render.js buildBodyPageHtml" },
  { component: "Heading / H2", markdown: "## Heading", selector: ".md-body h2", code: "lib/render.js buildBodyPageHtml" },
  { component: "Heading / H3", markdown: "### Heading", selector: ".md-body h3", code: "lib/render.js buildBodyPageHtml" },
  { component: "Text / Paragraph", markdown: "paragraph", selector: ".md-body p", code: "lib/render.js buildBodyPageHtml + paginateBodyHtml" },
  { component: "Text / Inline Styles", markdown: "**bold**, *em*, [link](url), `code`", selector: ".md-body strong / em / a / code", code: "lib/render.js buildBodyPageHtml" },
  { component: "Block / Quote", markdown: "> quote", selector: ".md-body blockquote", code: "lib/render.js buildBodyPageHtml" },
  { component: "List / Unordered", markdown: "- item", selector: ".md-body ul / li", code: "lib/render.js buildBodyPageHtml" },
  { component: "List / Ordered", markdown: "1. item", selector: ".md-body ol / li", code: "lib/render.js buildBodyPageHtml" },
  { component: "Block / Code", markdown: "```code```", selector: ".md-body pre / pre code", code: "lib/render.js buildBodyPageHtml" },
  { component: "Block / Table", markdown: "| table |", selector: ".md-body table / th / td", code: "lib/render.js buildBodyPageHtml" },
  { component: "Media / Landscape Image", markdown: "![alt](landscape)", selector: ".md-body p:has(> img.md-image:only-child)", code: "lib/render.js prepareMarkdownHtml + buildBodyPageHtml" },
  { component: "Media / Portrait Image", markdown: "![alt](portrait)", selector: ".md-body img.md-image / --image-max-height", code: "lib/render.js paginateBodyHtml" },
  { component: "Block / Horizontal Rule", markdown: "---", selector: ".md-body hr", code: "lib/render.js buildBodyPageHtml" }
];

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="2320" height="1280" viewBox="0 0 2320 1280">
  <rect width="2320" height="1280" fill="#f5f5f5"/>
  ${defaultCover()}
  ${imageCover()}
  ${bodyPage()}
</svg>
`;

const readme = `# Figma Handoff

- Import \`figma_handoff.svg\` into Figma.
- Import \`figma_components.svg\` into Figma for component-by-component editing.
- Import \`figma_full_layout.svg\` into Figma to edit the complete card pages generated from the coverage Markdown.
- The SVG uses design CSS pixels: 720 x 1200. Runtime PNG export is 2x: 1440 x 2400.
- Edit colors, type scale, spacing, image block shape, or cover composition in Figma.
- Send the edited SVG or screenshots back; code mapping lives mainly in \`lib/render.js\`.
- In Figma, select each \`Component/...\` group and run "Create component" if you want native Figma components.
- \`figma_full_layout.svg\` is exported from the renderer DOM after real pagination. Text is SVG text, cards are groups, and Markdown images remain separate image nodes.
- When this exporter receives \`--cards-dir\`, \`figma_rendered_reference.svg\` is also written as a PNG reference board for pixel comparison.

Files:
- \`figma_handoff.svg\`: editable visual style board for Figma.
- \`figma_components.svg\`: one editable group per Markdown component.
- \`figma_full_layout.svg\`: editable complete card layout pages from \`${path.basename(fixturePath)}\`.
- \`figma_rendered_reference.svg\`: optional raster reference board, only generated when \`--cards-dir\` is supplied.
- \`style_tokens.json\`: current renderer tokens.
- \`component_manifest.json\`: mapping from Markdown syntax to component and renderer selector.
- \`editable_cards_manifest.json\`: object counts for each editable card page.
- \`coverage_case.md\`: Markdown fixture used for full renderer coverage.
`;

const editableLayout = await editableFullLayoutFromMarkdown(fixturePath, {
  base_dir: baseDir,
  cover_style: coverStyle,
  cover_image_path: coverImagePath,
  style,
  chapter_label: chapterLabel,
  cover_variant: coverVariant,
});
const renderedLayout = cardsDir ? await renderedCardsLayout(cardsDir) : null;
const renderedCardsManifest = renderedLayout
  ? renderedLayout.files.map((file, index) => ({
      page: index,
      file,
      figmaWidth: CONFIG.cssWidth,
      figmaHeight: CONFIG.cssHeight,
    }))
  : null;

await fs.writeFile(path.join(outputDir, "figma_handoff.svg"), svg, "utf-8");
await fs.writeFile(path.join(outputDir, "figma_components.svg"), figmaComponents(), "utf-8");
await fs.writeFile(path.join(outputDir, "figma_full_layout.svg"), editableLayout.svg, "utf-8");
await fs.writeFile(path.join(outputDir, "style_tokens.json"), JSON.stringify(tokens, null, 2), "utf-8");
await fs.writeFile(path.join(outputDir, "component_manifest.json"), JSON.stringify(componentManifest, null, 2), "utf-8");
await fs.writeFile(path.join(outputDir, "editable_cards_manifest.json"), JSON.stringify({
  fixture: fixturePath,
  base_dir: baseDir,
  cover_style: coverStyle,
  style,
  chapter_label: chapterLabel,
  cover_variant: coverVariant,
  warnings: editableLayout.warnings,
  pages: editableLayout.pages,
}, null, 2), "utf-8");
if (renderedCardsManifest) {
  await fs.writeFile(path.join(outputDir, "figma_rendered_reference.svg"), renderedLayout.svg, "utf-8");
  await fs.writeFile(path.join(outputDir, "rendered_cards_manifest.json"), JSON.stringify(renderedCardsManifest, null, 2), "utf-8");
}
await fs.writeFile(path.join(outputDir, "README.md"), readme, "utf-8");
await fs.copyFile(fixturePath, path.join(outputDir, "coverage_case.md")).catch(() => {});
const outputFiles = [
  path.join(outputDir, "figma_handoff.svg"),
  path.join(outputDir, "figma_components.svg"),
  path.join(outputDir, "figma_full_layout.svg"),
  path.join(outputDir, "style_tokens.json"),
  path.join(outputDir, "component_manifest.json"),
  path.join(outputDir, "editable_cards_manifest.json"),
  path.join(outputDir, "README.md"),
  path.join(outputDir, "coverage_case.md"),
];
if (renderedCardsManifest) {
  outputFiles.push(path.join(outputDir, "figma_rendered_reference.svg"));
  outputFiles.push(path.join(outputDir, "rendered_cards_manifest.json"));
}

console.log(JSON.stringify({
  output_dir: outputDir,
  files: outputFiles,
  warnings: editableLayout.warnings,
}) + "\n");
