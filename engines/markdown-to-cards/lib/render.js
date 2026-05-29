import puppeteer from "puppeteer";
import { marked } from "marked";
import path from "path";
import fs from "fs/promises";
import os from "os";
import { fileURLToPath } from "url";
import {
  CARD_STYLE_IDS,
  COLOR_SCHEME_IDS,
  DEFAULT_COLOR_SCHEME_ID,
  buildThemedBodyPageHtml,
  buildThemedCoverHtml,
  getCardTemplate,
  isThemedStyle,
  normalizeCardStyle,
  normalizeCoverVariant,
  resolveColorScheme,
  resolveCardTheme,
} from "./templates/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_DIR = path.resolve(__dirname, "..");

export { CARD_STYLE_IDS, COLOR_SCHEME_IDS, DEFAULT_COLOR_SCHEME_ID };

// ============================================================
// 默认配置
// ============================================================
export const CONFIG = {
  cssWidth: 720,
  cssHeight: 1200,
  deviceScaleFactor: 2,
  fontFamily: `'Noto Serif SC', 'Songti SC', Georgia, serif`,
  headingFontFamily: `'Noto Sans SC', 'Source Han Sans SC', 'PingFang SC', sans-serif`,
  accent: "#A07830",
  coverBg: "#FDFAF4",
  bodyBg: "#FFFFFF",
  textColor: "#111111",
  accentTint: "rgba(245,237,216,0.8)",
  subtleBg: "#f8f6f1",
  mutedText: "#555555",
  inlineCodeBg: "rgba(0,0,0,0.07)",
  codeBg: "#1e1e1e",
  codeText: "#d4d4d4",
  blockquoteBorder: "none",
  ruleColor: "#e5e7eb",
  tableHeadBg: "#f3f4f6",
  tableHeadBorder: "#dddddd",
  tableCellBorder: "#e5e7eb",
  tableAltBg: "#fafafa",
  paddingH: 54,
  paddingV: 62,
  fontSize: 25,
  lineHeight: 1.78,
  coverBgPath: path.join(PROJECT_DIR, "Cover_template/xhs_blog.png"),
  coverFontOpts: {
    family: "'Noto Serif SC', serif",
    weight: 900,
    cssPaths: [
      path.join(PROJECT_DIR, "node_modules/@fontsource/noto-serif-sc/chinese-simplified-900.css"),
      path.join(PROJECT_DIR, "node_modules/@fontsource/noto-serif-sc/latin-900.css"),
      path.join(PROJECT_DIR, "node_modules/@fontsource/noto-serif-sc/latin-ext-900.css"),
    ],
  },
};

function numOption(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function normalizeCoverStyle(value) {
  const style = String(value || "").trim().toLowerCase();
  if (!style) return "";
  if (style === "template" || style === "image" || style === "both") return style;
  throw new Error(`Unknown cover_style: ${value}. Available styles: template, image, both`);
}

function hasExplicitColorScheme(options = {}) {
  return options.color_scheme !== undefined && String(options.color_scheme || "").trim() !== "";
}

function buildRenderContext(options = {}) {
  const style = normalizeCardStyle(options.style);
  if (style !== "legacy" && hasExplicitColorScheme(options)) {
    throw new Error("color_scheme is only supported when style=legacy. For other styles, use accent_color, background_color, text_color, or font_size overrides.");
  }

  const colorScheme = style === "legacy"
    ? resolveColorScheme(options.color_scheme || DEFAULT_COLOR_SCHEME_ID)
    : null;
  const accent = options.accent_color || colorScheme?.accent || CONFIG.accent;
  const bodyBg = options.background_color || colorScheme?.paper || CONFIG.bodyBg;
  const textColor = options.text_color || colorScheme?.ink || CONFIG.textColor;
  const cfg = {
    ...CONFIG,
    colorScheme,
    accent,
    bodyBg,
    coverBg: colorScheme ? bodyBg : CONFIG.coverBg,
    textColor,
    accentTint: colorScheme?.accentTint || CONFIG.accentTint,
    subtleBg: colorScheme?.subtle || CONFIG.subtleBg,
    mutedText: colorScheme?.muted || CONFIG.mutedText,
    inlineCodeBg: colorScheme?.accentTint || CONFIG.inlineCodeBg,
    inlineCodeText: colorScheme ? accent : textColor,
    codeBg: colorScheme?.codeBg || CONFIG.codeBg,
    codeText: colorScheme?.codeText || CONFIG.codeText,
    blockquoteText: colorScheme?.bqText || CONFIG.mutedText,
    blockquoteBorder: colorScheme ? `3px solid ${accent}` : CONFIG.blockquoteBorder,
    ruleColor: colorScheme?.subtle || CONFIG.ruleColor,
    tableHeadBg: colorScheme?.subtle || CONFIG.tableHeadBg,
    tableHeadBorder: colorScheme?.subtle || CONFIG.tableHeadBorder,
    tableCellBorder: colorScheme?.subtle || CONFIG.tableCellBorder,
    tableAltBg: colorScheme ? colorScheme.accentTint : CONFIG.tableAltBg,
    fontSize: numOption(options.font_size, CONFIG.fontSize),
  };
  const theme = isThemedStyle(style) ? resolveCardTheme(style, cfg, options) : null;
  return {
    cfg,
    style,
    colorScheme,
    theme,
    chapterLabel: String(options.chapter_label || "精选长图文"),
    coverVariant: normalizeCoverVariant(options.cover_variant),
    coverStyleOption: normalizeCoverStyle(options.cover_style),
  };
}

// ============================================================
// 工具函数
// ============================================================
function extractTitle(mdText) {
  const m = mdText.match(/^#\s+(.+)$/m);
  return m ? m[1].trim() : "";
}

function stripFrontMatter(mdText) {
  const text = String(mdText || "");
  if (!text.startsWith("---\n") && !text.startsWith("---\r\n")) return text;

  const newline = text.startsWith("---\r\n") ? "\r\n" : "\n";
  const closeMarker = `${newline}---${newline}`;
  const closeIndex = text.indexOf(closeMarker, 4);
  if (closeIndex === -1) return text;

  const frontMatter = text.slice(4, closeIndex);
  if (!/^[A-Za-z0-9_-]+\s*:/m.test(frontMatter)) return text;
  return text.slice(closeIndex + closeMarker.length);
}

function removeTitle(mdText) {
  return mdText.replace(/^#\s+.+\n?/m, "").trimStart();
}

function countWords(mdText) {
  const clean = mdText.replace(/```[\s\S]*?```/g, "")
                      .replace(/[#*`_~\[\]()\->|]/g, " ")
                      .replace(/\s+/g, " ").trim();
  const zhCount = (clean.match(/[\u4e00-\u9fa5]/g) || []).length;
  const enWords = clean.replace(/[\u4e00-\u9fa5]/g, " ")
                       .split(/\s+/).filter(w => /[a-zA-Z0-9]/.test(w)).length;
  return zhCount + enWords;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/\n/g, " ");
}

async function loadFontCSS(cssFilePath) {
  const dir = path.dirname(cssFilePath);
  const css = await fs.readFile(cssFilePath, "utf-8");
  return css.replace(/url\(\.(\/files\/[^)]+)\)/g, (_, rel) =>
    `url('file://${path.resolve(dir, "." + rel)}')`
  );
}

const LEGACY_FONT_CSS_PATHS = [
  ...["400", "600", "700", "900"].flatMap((weight) => [
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-serif-sc/chinese-simplified-${weight}.css`),
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-serif-sc/latin-${weight}.css`),
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-serif-sc/latin-ext-${weight}.css`),
  ]),
  ...["400", "600", "700", "900"].flatMap((weight) => [
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-sans-sc/chinese-simplified-${weight}.css`),
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-sans-sc/latin-${weight}.css`),
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-sans-sc/latin-ext-${weight}.css`),
  ]),
];

const THEMED_FONT_CSS_PATHS = [
  ...["400", "500", "600", "700", "800", "900"].flatMap((weight) => [
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-serif-sc/chinese-simplified-${weight}.css`),
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-serif-sc/latin-${weight}.css`),
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-serif-sc/latin-ext-${weight}.css`),
  ]),
  ...["400", "500", "600", "700", "800", "900"].flatMap((weight) => [
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-sans-sc/chinese-simplified-${weight}.css`),
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-sans-sc/latin-${weight}.css`),
    path.join(PROJECT_DIR, `node_modules/@fontsource/noto-sans-sc/latin-ext-${weight}.css`),
  ]),
];

async function loadFontCssBundle(paths) {
  let cssCombined = "";
  for (const p of paths) {
    try { cssCombined += await loadFontCSS(p) + "\n"; } catch (e) { /* 字体文件缺失则跳过 */ }
  }
  return cssCombined;
}

async function loadLegacyFontCSS() {
  return loadFontCssBundle(LEGACY_FONT_CSS_PATHS);
}

async function loadThemedFontCSS() {
  return loadFontCssBundle(THEMED_FONT_CSS_PATHS);
}

async function loadCoverFontOpts(cfg) {
  if (!cfg.coverFontOpts) return {};
  let cssCombined = "";
  for (const p of (cfg.coverFontOpts.cssPaths || [])) {
    try { cssCombined += await loadFontCSS(p) + "\n"; } catch (e) { /* 字体文件缺失则跳过 */ }
  }
  return { ...cfg.coverFontOpts, css: cssCombined };
}

function isRemoteAsset(src) {
  return /^https?:\/\//i.test(src) || /^\/\//.test(src);
}

function isDataAsset(src) {
  return /^data:/i.test(src);
}

function mimeTypeForPath(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const map = {
    ".apng": "image/apng",
    ".avif": "image/avif",
    ".gif": "image/gif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
  };
  return map[ext] || "application/octet-stream";
}

function normalizeLocalAssetPath(src, baseDir) {
  const withoutFragment = String(src).replace(/[?#].*$/, "");
  if (/^file:\/\//i.test(withoutFragment)) return fileURLToPath(withoutFragment);
  if (path.isAbsolute(withoutFragment)) return withoutFragment;
  return path.resolve(baseDir || process.cwd(), withoutFragment);
}

async function fileToDataUrl(filePath) {
  const buf = await fs.readFile(filePath);
  return `data:${mimeTypeForPath(filePath)};base64,${buf.toString("base64")}`;
}

async function resolveAssetSource(src, baseDir, label) {
  const raw = String(src || "").trim();
  if (!raw) return { src: "" };
  if (isDataAsset(raw)) return { src: raw };
  if (isRemoteAsset(raw)) return { src: raw.startsWith("//") ? `https:${raw}` : raw };

  const filePath = normalizeLocalAssetPath(raw, baseDir);
  try {
    return { src: await fileToDataUrl(filePath), filePath };
  } catch (err) {
    return {
      src: raw,
      warning: `${label}读取失败: ${raw} (${err.message})`,
    };
  }
}

function walkMarkedTokens(tokens, visitor) {
  for (const token of tokens || []) {
    visitor(token);
    if (token.tokens) walkMarkedTokens(token.tokens, visitor);
    if (token.items) {
      for (const item of token.items) {
        if (item.tokens) walkMarkedTokens(item.tokens, visitor);
      }
    }
  }
}

function collectMarkdownImageRefs(mdText) {
  const refs = [];
  const seen = new Set();
  const tokens = marked.lexer(mdText);
  walkMarkedTokens(tokens, (token) => {
    if (token.type !== "image" || !token.href || seen.has(token.href)) return;
    seen.add(token.href);
    refs.push(token.href);
  });
  return refs;
}

async function prepareMarkdownHtml(mdText, options) {
  const baseDir = options.base_dir || process.cwd();
  const imageRefs = collectMarkdownImageRefs(mdText);
  const imageSources = new Map();
  const warnings = [];
  let firstImageSrc = null;

  for (const href of imageRefs) {
    const resolved = await resolveAssetSource(href, baseDir, "正文图片");
    if (resolved.warning) warnings.push(resolved.warning);
    if (resolved.src) {
      imageSources.set(href, resolved.src);
      if (!firstImageSrc && !resolved.warning) firstImageSrc = resolved.src;
    }
  }

  const renderer = new marked.Renderer();
  renderer.image = (tokenOrHref, title, text) => {
    const token = typeof tokenOrHref === "object"
      ? tokenOrHref
      : { href: tokenOrHref, title, text };
    const href = token.href || "";
    const src = imageSources.get(href) || href;
    const titleAttr = token.title ? ` title="${escapeAttribute(token.title)}"` : "";
    return `<img class="md-image" src="${escapeAttribute(src)}" alt="${escapeAttribute(token.text || "")}"${titleAttr}>`;
  };

  return {
    html: marked.parse(mdText, { renderer }),
    firstImageSrc,
    warnings,
  };
}

async function waitForImages(page, rootSelector) {
  await page.evaluate(async (selector) => {
    const root = document.querySelector(selector) || document;
    const images = Array.from(root.querySelectorAll("img"));
    await Promise.all(images.map((img) => {
      if (img.complete) {
        return img.decode ? img.decode().catch(() => {}) : Promise.resolve();
      }
      return new Promise((resolve) => {
        const done = () => resolve();
        img.addEventListener("load", done, { once: true });
        img.addEventListener("error", done, { once: true });
        setTimeout(done, 5000);
      });
    }));
  }, rootSelector);
}

// ============================================================
// 封面 HTML
// ============================================================
function buildCoverHtml(title, wordCount, cfg, coverBgSrc, fontOpts = {}, coverImageSrc = null, coverStyle = "template", theme = null, coverVariant = "primary") {
  if (theme) {
    const themedCoverImage = coverStyle === "template" ? null : coverImageSrc;
    return buildThemedCoverHtml(title, wordCount, cfg, theme, themedCoverImage, fontOpts, coverVariant);
  }
  return getCardTemplate("legacy").renderCover({
    title,
    wordCount,
    cfg,
    coverBgSrc,
    fontOpts,
    coverImageSrc,
    coverStyle,
  });
}

function coverVariantsFor(theme, coverVariant) {
  if (!theme) return ["primary"];
  return coverVariant === "all" ? ["primary", "alt"] : [coverVariant];
}

function coverStylesFor(coverStyle, coverImageSrc) {
  if (coverStyle === "both") {
    return coverImageSrc ? ["template", "image"] : ["template"];
  }
  return [coverStyle];
}

function coverLabelFor(index, coverCount, variant, style) {
  if (coverCount === 1) return "card_00_cover";
  const suffix = `${variant}_${style === "image" ? "image" : "text"}`;
  return `card_${String(index).padStart(2, "0")}_cover_${suffix}`;
}

function buildCoverPageSpecs(title, wordCount, cfg, coverBgSrc, fontOpts, coverImageSrc, coverStyle, theme, coverVariant) {
  const variants = coverVariantsFor(theme, coverVariant);
  const styles = coverStylesFor(coverStyle, coverImageSrc);
  const specs = [];
  for (const variant of variants) {
    for (const style of styles) {
      specs.push({ variant, style });
    }
  }

  return specs.map((spec, index) => ({
    kind: "cover",
    label: coverLabelFor(index, specs.length, spec.variant, spec.style),
    selector: "#cover-page",
    html: buildCoverHtml(title, wordCount, cfg, coverBgSrc, fontOpts, coverImageSrc, spec.style, theme, spec.variant),
    cover_variant: spec.variant,
    cover_style: spec.style,
  }));
}

// ============================================================
// 正文页 HTML
// ============================================================
function buildBodyPageHtml(cfg, theme = null, pageMeta = {}, pageHtml = "") {
  if (theme) return buildThemedBodyPageHtml(cfg, theme, pageMeta, pageHtml);
  return getCardTemplate("legacy").renderBodyPage(cfg, null, pageMeta, pageHtml);
}

async function paginateBodyHtml(bodyPage, bodyHtml, maxHeight, imageMaxHeight) {
  await bodyPage.evaluate((htmlContent) => {
    document.getElementById("measure-content").innerHTML = `<div class="md-body">${htmlContent}</div>`;
  }, bodyHtml);
  await waitForImages(bodyPage, "#measure-content");

  return bodyPage.evaluate((htmlContent, maxH, imageMaxH) => {
    const mc = document.getElementById("measure-content");

    function htmlFromNode(node) {
      const wrap = document.createElement("div");
      wrap.appendChild(node.cloneNode(true));
      return wrap.innerHTML;
    }

    function measure(html) {
      mc.innerHTML = `<div class="md-body">${html}</div>`;
      return mc.scrollHeight;
    }

    function fits(html) {
      return measure(html) <= maxH;
    }

    function isSplittableParagraph(node) {
      return node.nodeType === Node.ELEMENT_NODE &&
        node.tagName === "P" &&
        node.textContent.trim().length > 0 &&
        !node.querySelector("img, table, pre, iframe, video, canvas, svg");
    }

    function isImageOnlyBlock(node) {
      if (node.nodeType !== Node.ELEMENT_NODE || node.tagName !== "P") return false;
      let imageCount = 0;
      for (const child of node.childNodes) {
        if (child.nodeType === Node.TEXT_NODE && !child.textContent.trim()) continue;
        if (child.nodeType === Node.ELEMENT_NODE && child.tagName === "IMG" && child.classList.contains("md-image")) {
          imageCount += 1;
          continue;
        }
        return false;
      }
      return imageCount === 1;
    }

    function cloneImageWithMaxHeight(node, height) {
      const clone = node.cloneNode(true);
      clone.style.setProperty("--image-max-height", `${Math.max(80, Math.floor(height))}px`);
      return clone;
    }

    function fitImageIntoCurrentPage(block) {
      if (!current || !isImageOnlyBlock(block)) return false;

      const remaining = maxH - measure(current);
      const minImageH = Math.min(260, Math.round(imageMaxH * 0.58));
      if (remaining < minImageH) return false;

      let lo = 80;
      let hi = Math.min(imageMaxH, Math.max(80, remaining));
      let best = 0;
      while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        const candidate = current + htmlFromNode(cloneImageWithMaxHeight(block, mid));
        if (fits(candidate)) {
          best = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }

      if (best < minImageH) return false;
      current += htmlFromNode(cloneImageWithMaxHeight(block, best));
      pages.push(current);
      current = "";
      return true;
    }

    function shrinkOversizedImagePage(block) {
      if (!isImageOnlyBlock(block)) return null;
      let lo = 80;
      let hi = imageMaxH;
      let best = 0;
      while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        const candidate = htmlFromNode(cloneImageWithMaxHeight(block, mid));
        if (fits(candidate)) {
          best = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }
      return best ? htmlFromNode(cloneImageWithMaxHeight(block, best)) : null;
    }

    function textLength(node) {
      return node.textContent.length;
    }

    function cloneTextRange(node, start, end) {
      if (start >= end) return null;

      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
      let pos = 0;
      let startNode = null;
      let startOffset = 0;
      let endNode = null;
      let endOffset = 0;
      let lastNode = null;

      while (walker.nextNode()) {
        const textNode = walker.currentNode;
        const len = textNode.textContent.length;
        const next = pos + len;
        lastNode = textNode;

        if (!startNode && start <= next) {
          startNode = textNode;
          startOffset = Math.max(0, start - pos);
        }
        if (!endNode && end <= next) {
          endNode = textNode;
          endOffset = Math.max(0, end - pos);
          break;
        }
        pos = next;
      }

      if (!startNode || !endNode) {
        if (!startNode || !lastNode) return null;
        endNode = lastNode;
        endOffset = lastNode.textContent.length;
      }

      const range = document.createRange();
      range.setStart(startNode, startOffset);
      range.setEnd(endNode, endOffset);

      const clone = node.cloneNode(false);
      clone.appendChild(range.cloneContents());
      return clone.textContent.trim() ? clone : null;
    }

    function trimLeadingWhitespace(node) {
      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
      const first = walker.nextNode();
      if (first) first.textContent = first.textContent.replace(/^\s+/, "");
    }

    function adjustCutToBoundary(text, best, total) {
      if (best >= total) return best;
      const windowStart = Math.max(1, best - 48);
      for (let i = best; i >= windowStart; i--) {
        if (/[\s，。！？；：、,.!?;:]/.test(text[i - 1])) return i;
      }
      return best;
    }

    function splitParagraphForFit(node, prefixHtml) {
      const total = textLength(node);
      let lo = 1;
      let hi = total;
      let best = 0;

      while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        const prefixNode = cloneTextRange(node, 0, mid);
        if (prefixNode && mid < total) prefixNode.setAttribute("data-split-part", "start");
        const candidate = prefixNode ? prefixHtml + htmlFromNode(prefixNode) : prefixHtml;
        if (prefixNode && fits(candidate)) {
          best = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }

      if (best <= 0) return { beforeHtml: "", afterNode: node };

      best = adjustCutToBoundary(node.textContent || "", best, total);
      const beforeNode = cloneTextRange(node, 0, best);
      if (!beforeNode) return { beforeHtml: "", afterNode: node };
      if (best < total) beforeNode.setAttribute("data-split-part", "start");

      const afterNode = cloneTextRange(node, best, total);
      if (afterNode) trimLeadingWhitespace(afterNode);

      return {
        beforeHtml: htmlFromNode(beforeNode),
        afterNode: afterNode && afterNode.textContent.trim() ? afterNode : null,
      };
    }

    const tmp = document.createElement("div");
    tmp.innerHTML = htmlContent;
    const blocks = [];
    for (const node of tmp.childNodes) {
      if (node.nodeType === Node.TEXT_NODE && !node.textContent.trim()) continue;
      blocks.push(node.cloneNode(true));
    }

    const pages = [];
    let current = "";

    function appendBlock(block) {
      const blockHtml = htmlFromNode(block);
      if (fits(current + blockHtml)) {
        current += blockHtml;
        return;
      }

      if (fitImageIntoCurrentPage(block)) return;

      if (isSplittableParagraph(block)) {
        const split = splitParagraphForFit(block, current);
        if (split.beforeHtml) {
          current += split.beforeHtml;
          pages.push(current);
          current = "";
          if (split.afterNode) appendBlock(split.afterNode);
          return;
        }

        if (current) {
          pages.push(current);
          current = "";
          appendBlock(block);
          return;
        }

        pages.push(blockHtml);
        return;
      }

      if (current) {
        pages.push(current);
        current = "";
        appendBlock(block);
        return;
      }

      pages.push(shrinkOversizedImagePage(block) || blockHtml);
    }

    for (const block of blocks) appendBlock(block);
    if (current) pages.push(current);
    return pages.length ? pages : [htmlContent];
  }, bodyHtml, maxHeight, imageMaxHeight);
}

function buildBodyPageDocument(cfg, pageHtml, theme = null, pageMeta = {}) {
  return buildBodyPageHtml(cfg, theme, pageMeta, pageHtml);
}

export async function renderMarkdownToHtmlPages(markdownText, options = {}) {
  const baseDir = options.base_dir ? path.resolve(options.base_dir) : process.cwd();
  let { cfg, style, colorScheme, theme, chapterLabel, coverVariant, coverStyleOption } = buildRenderContext(options);
  const contentText = stripFrontMatter(markdownText);

  const title     = extractTitle(contentText);
  const bodyMd    = removeTitle(contentText);
  const wordCount = countWords(contentText);
  const prepared  = await prepareMarkdownHtml(bodyMd, { ...options, base_dir: baseDir });
  const bodyHtml  = prepared.html;
  const warnings  = [...prepared.warnings];

  let coverBgSrc = null;
  const bgPath = options.cover_bg_path || (!theme ? cfg.coverBgPath : null);
  if (bgPath) {
    const resolvedBg = await resolveAssetSource(bgPath, baseDir, "封面底图");
    if (resolvedBg.src && !resolvedBg.warning) coverBgSrc = resolvedBg.src;
    if (resolvedBg.warning && options.cover_bg_path) warnings.push(resolvedBg.warning);
  }

  let coverImageSrc = null;
  if (options.cover_image_path) {
    const resolvedCover = await resolveAssetSource(options.cover_image_path, baseDir, "封面图片");
    if (resolvedCover.src && !resolvedCover.warning) coverImageSrc = resolvedCover.src;
    if (resolvedCover.warning) warnings.push(resolvedCover.warning);
  } else if (coverStyleOption === "image" || coverStyleOption === "both") {
    coverImageSrc = prepared.firstImageSrc;
    if (!coverImageSrc) warnings.push(`cover_style=${coverStyleOption} 但未找到 cover_image_path 或正文图片，已退回纯文字封面`);
  }
  const coverStyle = coverStyleOption || (coverImageSrc ? "image" : "template");

  const fontOpts = theme ? {} : await loadCoverFontOpts(cfg);
  if (theme) {
    theme = { ...theme, fontCss: await loadThemedFontCSS() };
  } else {
    cfg = { ...cfg, fontCss: await loadLegacyFontCSS() };
  }

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const bodyPage = await browser.newPage();
    await bodyPage.setViewport({ width: cfg.cssWidth, height: cfg.cssHeight, deviceScaleFactor: cfg.deviceScaleFactor });
    await bodyPage.setContent(buildBodyPageHtml(cfg, theme, { chapterLabel, pageNum: 2, totalPages: 2 }), { waitUntil: "load", timeout: 60000 });
    await bodyPage.waitForFunction(() => document.fonts.status === "loaded", { timeout: 5000 }).catch(() => {});

    const maxHeight = theme ? theme.maxContentHeight : cfg.cssHeight - cfg.paddingV * 2;
    const imageMaxHeight = Math.round(maxHeight * 0.48);
    const pageFragments = await paginateBodyHtml(bodyPage, bodyHtml, maxHeight, imageMaxHeight);
    await bodyPage.close();
    const coverPages = buildCoverPageSpecs(title, wordCount, cfg, coverBgSrc, fontOpts, coverImageSrc, coverStyle, theme, coverVariant);
    const totalPages = pageFragments.length + coverPages.length;

    return {
      cfg,
      style,
      color_scheme: colorScheme?.id || null,
      title,
      wordCount,
      warnings,
      pages: [
        ...coverPages,
        ...pageFragments.map((fragment, index) => ({
          kind: "body",
          label: `card_${String(index + coverPages.length).padStart(2, "0")}`,
          selector: "#capture-page",
          html: buildBodyPageDocument(cfg, fragment, theme, {
            chapterLabel,
            pageNum: index + coverPages.length + 1,
            totalPages,
          }),
        })),
      ],
    };
  } finally {
    await browser.close();
  }
}

// ============================================================
// 核心渲染函数
// ============================================================
export async function renderMarkdownToCards(markdownText, options = {}) {
  const baseDir = options.base_dir ? path.resolve(options.base_dir) : process.cwd();
  let { cfg, style, colorScheme, theme, chapterLabel, coverVariant, coverStyleOption } = buildRenderContext(options);
  const contentText = stripFrontMatter(markdownText);

  let outputDir = options.output_dir;
  if (!outputDir) outputDir = path.join(os.tmpdir(), `md2card_${Date.now()}`);
  await fs.mkdir(outputDir, { recursive: true });

  const title     = extractTitle(contentText);
  const bodyMd    = removeTitle(contentText);
  const wordCount = countWords(contentText);
  const prepared  = await prepareMarkdownHtml(bodyMd, { ...options, base_dir: baseDir });
  const bodyHtml  = prepared.html;
  const warnings  = [...prepared.warnings];

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const files = [];

    // 封面底图
    let coverBgSrc = null;
    const bgPath = options.cover_bg_path || (!theme ? cfg.coverBgPath : null);
    if (bgPath) {
      const resolvedBg = await resolveAssetSource(bgPath, baseDir, "封面底图");
      if (resolvedBg.src && !resolvedBg.warning) coverBgSrc = resolvedBg.src;
      if (resolvedBg.warning && options.cover_bg_path) warnings.push(resolvedBg.warning);
    }

    // 封面图片
    let coverImageSrc = null;
    if (options.cover_image_path) {
      const resolvedCover = await resolveAssetSource(options.cover_image_path, baseDir, "封面图片");
      if (resolvedCover.src && !resolvedCover.warning) coverImageSrc = resolvedCover.src;
      if (resolvedCover.warning) warnings.push(resolvedCover.warning);
    } else if (coverStyleOption === "image" || coverStyleOption === "both") {
      coverImageSrc = prepared.firstImageSrc;
      if (!coverImageSrc) warnings.push(`cover_style=${coverStyleOption} 但未找到 cover_image_path 或正文图片，已退回纯文字封面`);
    }
    const coverStyle = coverStyleOption || (coverImageSrc ? "image" : "template");

    // 字体 CSS
    const fontOpts = theme ? {} : await loadCoverFontOpts(cfg);
    if (theme) {
      theme = { ...theme, fontCss: await loadThemedFontCSS() };
    } else {
      cfg = { ...cfg, fontCss: await loadLegacyFontCSS() };
    }

    const coverPages = buildCoverPageSpecs(title, wordCount, cfg, coverBgSrc, fontOpts, coverImageSrc, coverStyle, theme, coverVariant);

    // 封面页
    for (const coverSpec of coverPages) {
      const coverPage = await browser.newPage();
      await coverPage.setViewport({ width: cfg.cssWidth, height: cfg.cssHeight, deviceScaleFactor: cfg.deviceScaleFactor });
      await coverPage.setContent(coverSpec.html, { waitUntil: "load", timeout: 60000 });
      await coverPage.waitForFunction(() => document.fonts.status === "loaded", { timeout: 5000 }).catch(() => {});
      const coverEl = await coverPage.$("#cover-page");
      const coverFile = path.join(outputDir, `${coverSpec.label}.png`);
      await coverEl.screenshot({ path: coverFile, type: "png" });
      files.push(coverFile);
      await coverPage.close();
    }

    // 正文页
    const bodyPage = await browser.newPage();
    await bodyPage.setViewport({ width: cfg.cssWidth, height: cfg.cssHeight, deviceScaleFactor: cfg.deviceScaleFactor });
    await bodyPage.setContent(buildBodyPageHtml(cfg, theme, { chapterLabel, pageNum: 2, totalPages: 2 }), { waitUntil: "load", timeout: 60000 });
    await bodyPage.waitForFunction(() => document.fonts.status === "loaded", { timeout: 5000 }).catch(() => {});

    const maxHeight = theme ? theme.maxContentHeight : cfg.cssHeight - cfg.paddingV * 2;
    const imageMaxHeight = Math.round(maxHeight * 0.48);
    const pages = await paginateBodyHtml(bodyPage, bodyHtml, maxHeight, imageMaxHeight);
    const totalPages = pages.length + coverPages.length;

    const captureEl = await bodyPage.$("#capture-page");
    for (let i = 0; i < pages.length; i++) {
      await bodyPage.evaluate((html, meta) => {
        document.getElementById("capture-body").innerHTML = html;
        document.querySelectorAll("[data-page-num]").forEach((el) => {
          const n = Number(meta.pageNum);
          const shouldPad = el.hasAttribute("data-page-num-pad") || el.classList.contains("coral-page");
          el.textContent = shouldPad ? String(n).padStart(2, "0") : String(n);
        });
        document.querySelectorAll("[data-page-total]").forEach((el) => {
          const n = Number(meta.totalPages);
          el.textContent = el.hasAttribute("data-page-total-pad") ? String(n).padStart(2, "0") : String(n);
        });
        document.querySelectorAll("[data-chapter-label]").forEach((el) => {
          el.textContent = meta.chapterLabel;
        });
      }, pages[i], { pageNum: i + coverPages.length + 1, totalPages, chapterLabel });
      await waitForImages(bodyPage, "#capture-body");
      const filename = path.join(outputDir, `card_${String(i + coverPages.length).padStart(2, "0")}.png`);
      await captureEl.screenshot({ path: filename, type: "png" });
      files.push(filename);
    }
    await bodyPage.close();

    return { files, total_pages: totalPages, output_dir: outputDir, style, color_scheme: colorScheme?.id || null, warnings };
  } finally {
    await browser.close();
  }
}
