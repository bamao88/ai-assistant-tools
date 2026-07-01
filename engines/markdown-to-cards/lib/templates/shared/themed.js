export const DEFAULT_CHAPTER_LABEL = "精选长图文";
export const DEFAULT_COVER_VARIANT = "primary";

export const FONT_STACKS = {
  serif: "'Noto Serif SC', 'Songti SC', serif",
  sans: "'Noto Sans SC', 'PingFang SC', sans-serif",
  xhsSans: "'PingFang SC', 'Hiragino Sans GB', 'Noto Sans SC', sans-serif",
  display: "'Noto Serif SC', 'Playfair Display', 'Songti SC', serif",
  mono: "'SF Mono', 'Fira Code', 'Consolas', monospace",
};

const DESIGN_W = 420;
const TARGET_W = 720;
export const SCALE = TARGET_W / DESIGN_W;
export const EXTRA_BASE_HEIGHT = 140;

export function sc(value) {
  return Math.round(value * SCALE);
}

export function coverY(value) {
  return sc(value);
}

export const CARD_RADIUS = sc(14);

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function escapeCssUrl(value) {
  return String(value ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/'/g, "\\'")
    .replace(/\n/g, "");
}

export function clampFontSize(value, fallback) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return fallback;
  return Math.max(18, Math.min(34, n));
}

export function normaliseColor(value, fallback) {
  return String(value || fallback).trim();
}

export function pad2(value) {
  return String(value).padStart(2, "0");
}

export function normalizeCoverVariant(value) {
  const variant = String(value || DEFAULT_COVER_VARIANT).trim().toLowerCase();
  if (variant === "primary" || variant === "alt" || variant === "all") return variant;
  throw new Error(`Unknown cover_variant: ${value}. Available variants: primary, alt, all`);
}

export function rootVars(theme) {
  return `
:root {
  --paper: ${theme.paper};
  --ink: ${theme.ink};
  --muted: ${theme.muted};
  --accent: ${theme.accent};
  --accent-deep: ${theme.accentDeep};
  --accent-soft: ${theme.accentSoft};
  --rule: ${theme.rule};
  --serif-cn: ${theme.serifFont};
  --sans-cn: ${theme.sansFont};
  --mono: ${theme.monoFont};
}`;
}

export function baseBodyCss(cfg, theme) {
  const imagePad = Math.round(theme.fontSize * 0.42);
  const maxImageWidth = theme.contentWidth - imagePad * 2;
  const maxImageHeight = Math.round(theme.maxContentHeight * 0.5);
  return `
  ${theme.fontCss || ""}
  ${rootVars(theme)}
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: ${cfg.cssWidth}px; background: var(--paper); color: var(--ink);
    font-family: ${theme.bodyFont}; -webkit-font-smoothing: antialiased;
  }
  #measure-wrap {
    width: ${theme.contentWidth}px; position: absolute; top: -9999px; left: 0;
    visibility: hidden; overflow: hidden; font-family: ${theme.bodyFont};
    font-size: ${theme.fontSize}px; line-height: ${theme.lineHeight};
  }
  #capture-page {
    width: ${cfg.cssWidth}px; height: ${cfg.cssHeight}px; overflow: hidden;
    position: relative; background: var(--paper); color: var(--ink);
    font-family: ${theme.bodyFont}; border-radius: ${CARD_RADIUS}px;
  }
  #theme-header, #theme-footer {
    position: absolute; left: ${theme.paddingH}px; right: ${theme.paddingH}px;
    z-index: 2; color: var(--accent);
  }
  #theme-header { top: ${theme.headerTop}px; }
  #theme-footer { bottom: ${theme.footerBottom}px; }
  #capture-body {
    position: absolute; left: ${theme.paddingH}px; top: ${theme.contentTop}px;
    width: ${theme.contentWidth}px; height: ${theme.maxContentHeight}px;
    overflow: hidden; font-size: ${theme.fontSize}px; line-height: ${theme.lineHeight};
  }
  .md-body { width: ${theme.contentWidth}px; color: var(--ink); }
  .md-body > :first-child { margin-top: 0 !important; }
  .md-body > :last-child { margin-bottom: 0 !important; }
  .md-body p {
    font-size: ${theme.fontSize}px; line-height: ${theme.lineHeight};
    margin-bottom: ${theme.paraGap}px; word-break: normal; overflow-wrap: anywhere;
  }
  .md-body p[data-split-part="start"], .md-body p[data-split-part="middle"] { margin-bottom: 0; }
  .md-body strong { font-weight: 700; color: inherit; }
  .md-body em { font-style: italic; }
  .md-body a { color: var(--accent); text-decoration: underline; text-underline-offset: 4px; }
  .md-body code {
    font-family: var(--mono); font-size: ${theme.codeSize}px; line-height: 1.55;
    white-space: nowrap; word-break: keep-all; overflow-wrap: normal;
  }
  .md-body :not(pre) > code {
    padding: ${sc(1)}px ${sc(5)}px; border-radius: ${sc(4)}px;
    background: color-mix(in oklab, currentColor 10%, transparent);
    font-size: .88em; color: inherit;
  }
  .md-body pre {
    margin-bottom: ${theme.paraGap}px; overflow: hidden;
  }
  .md-body pre code {
    display: block; background: transparent; padding: 0; white-space: pre-wrap;
    word-break: break-word; overflow-wrap: anywhere; color: inherit;
  }
  .md-body blockquote { margin-bottom: ${theme.paraGap}px; }
  .md-body blockquote p { margin-bottom: 0; }
  .md-body ul, .md-body ol {
    margin-bottom: ${theme.paraGap}px; padding-left: ${Math.round(theme.fontSize * 1.35)}px;
  }
  .md-body li { margin-bottom: ${Math.round(theme.fontSize * 0.35)}px; line-height: ${theme.lineHeight}; }
  .md-body li[data-split-part="start"], .md-body li[data-split-part="middle"] { margin-bottom: 0; }
  .md-body li::marker { color: var(--accent); font-weight: 800; }
  .md-body hr { border: none; margin: ${Math.round(theme.paraGap * 0.9)}px 0; }
  .md-body table {
    width: 100%; border-collapse: collapse; margin-bottom: ${theme.paraGap}px;
    font-size: ${theme.tableSize}px; line-height: 1.55;
  }
  .md-body th, .md-body td {
    padding: ${Math.round(theme.fontSize * 0.34)}px ${Math.round(theme.fontSize * 0.42)}px;
    vertical-align: top; text-align: left;
  }
  .md-body p:has(> img.md-image:only-child) {
    width: fit-content; max-width: 100%; margin: ${Math.round(theme.paraGap * 0.35)}px auto ${theme.paraGap}px;
    padding: ${imagePad}px; display: flex; align-items: center; justify-content: center;
  }
  .md-body img.md-image {
    display: block; max-width: ${maxImageWidth}px;
    max-height: var(--image-max-height, ${maxImageHeight}px);
    width: auto; height: auto; object-fit: contain;
  }`;
}

export function inlineResetCss() {
  return `
  .md-body strong { font-weight: 700; color: inherit; }
  .md-body :not(pre) > code {
    padding: ${sc(1)}px ${sc(5)}px !important;
    border-radius: ${sc(4)}px !important;
    background: color-mix(in oklab, currentColor 10%, transparent) !important;
    color: inherit !important;
    font-size: .88em !important;
    font-family: var(--mono) !important;
  }`;
}

export function coverImageHtml(coverImageSrc, className = "cover-img") {
  if (!coverImageSrc) return "";
  return `<img class="${className}" src="${escapeHtml(coverImageSrc)}" alt="">`;
}

export function coverCss(cfg, theme, extraCss = "") {
  return `
  ${extraCss}
  ${theme.fontCss || ""}
  ${rootVars(theme)}
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { width: ${cfg.cssWidth}px; font-family: ${theme.bodyFont}; -webkit-font-smoothing: antialiased; }
  #cover-page {
    width: ${cfg.cssWidth}px; height: ${cfg.cssHeight}px; overflow: hidden; position: relative;
    background: var(--paper); color: var(--ink); font-family: ${theme.bodyFont};
    border-radius: ${CARD_RADIUS}px;
  }
  .cover-img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .cover-placeholder {
    width: 100%; height: 100%; min-height: 220px; display: flex; align-items: center; justify-content: center;
    font-size: 18px; letter-spacing: .3em; color: var(--accent);
    background: repeating-linear-gradient(135deg, rgba(0,0,0,.045) 0 12px, transparent 12px 24px);
  }
  .fit-box { overflow: hidden; }
  .fit-title { word-break: normal; overflow-wrap: break-word; }`;
}

export function coverDoc(cfg, theme, body, fontOpts = {}) {
  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>${coverCss(cfg, theme, fontOpts.css || "")}</style></head>
<body>${body}
<script>
document.fonts.ready.then(() => {
  for (const el of document.querySelectorAll('.fit-title')) {
    const box = el.closest('.fit-box') || el.parentElement;
    const min = Number(el.dataset.min || 22);
    let lo = min, hi = Number(el.dataset.max || 74), best = min;
    while (lo <= hi) {
      const mid = Math.floor((lo + hi) / 2);
      el.style.fontSize = mid + 'px';
      if (el.scrollHeight <= box.clientHeight && el.scrollWidth <= box.clientWidth + 1) {
        best = mid; lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }
    el.style.fontSize = best + 'px';
  }
});
</script>
</body></html>`;
}

function resolveTheme(template, cfg, options = {}) {
  const def = template.defaults;
  const hasExplicitFontSize = options.font_size !== undefined &&
    options.font_size !== null &&
    String(options.font_size).trim() !== "";
  const defaultFontSize = Math.max(def.fontSize, cfg.fontSize || def.fontSize);
  const fontSize = clampFontSize(hasExplicitFontSize ? options.font_size : undefined, defaultFontSize);
  const paddingH = def.paddingH;
  const fontScale = fontSize / def.fontSize;
  return {
    ...def,
    id: template.id,
    name: template.name,
    template,
    chapterLabel: String(options.chapter_label || DEFAULT_CHAPTER_LABEL),
    coverVariant: normalizeCoverVariant(options.cover_variant),
    paper: normaliseColor(options.background_color, def.paper),
    ink: normaliseColor(options.text_color, def.ink),
    muted: normaliseColor(options.muted_color, def.muted),
    accent: normaliseColor(options.accent_color, def.accent),
    accentDeep: normaliseColor(options.accent_deep_color || options.accent_color, def.accentDeep),
    accentSoft: normaliseColor(options.accent_soft_color, def.accentSoft),
    rule: normaliseColor(options.rule_color, def.rule),
    cover: def.cover,
    fontSize,
    h1Size: Math.round((def.h1Size || fontSize * 1.48) * fontScale),
    h2Size: Math.round((def.h2Size || fontSize * 1.16) * fontScale),
    h3Size: Math.round((def.h3Size || fontSize * 1.02) * fontScale),
    codeSize: Math.round((def.codeSize || fontSize * 0.84) * fontScale),
    tableSize: Math.round((def.tableSize || fontSize * 0.82) * fontScale),
    paraGap: Math.round((def.paraGap || fontSize * 0.78) * fontScale),
    contentWidth: def.contentWidth || cfg.cssWidth - paddingH * 2,
    bodyFont: FONT_STACKS[def.font],
    serifFont: def.serifFont || FONT_STACKS.serif,
    sansFont: def.sansFont || FONT_STACKS.sans,
    monoFont: FONT_STACKS.mono,
  };
}

export function createThemedTemplate({
  id,
  name,
  defaults,
  bodyCss,
  headerHtml,
  footerHtml,
  chromeCss,
  primaryCover,
  altCover,
}) {
  const template = {
    id,
    name,
    defaults,
    supportedCoverVariants: altCover ? ["primary", "alt"] : ["primary"],
    resolve(cfg, options = {}) {
      return resolveTheme(template, cfg, options);
    },
    renderBodyPage(cfg, theme, meta = {}, pageHtml = "") {
      return `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  ${baseBodyCss(cfg, theme)}
  ${bodyCss(theme)}
  ${chromeCss(theme)}
  ${inlineResetCss()}
</style></head>
<body>
  <div id="measure-wrap"><div id="measure-content"></div></div>
  <div id="capture-page" data-card-style="${theme.id}">
    ${headerHtml(theme, meta)}
    <div class="md-body" id="capture-body">${pageHtml}</div>
    ${footerHtml(theme, meta)}
  </div>
</body></html>`;
    },
    renderCover(args) {
      const variant = normalizeCoverVariant(args.coverVariant || args.theme.coverVariant);
      return variant === "alt" && altCover ? altCover(args) : primaryCover(args);
    },
  };
  return template;
}
