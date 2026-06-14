import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import {
  DEFAULT_CHAPTER_LABEL,
  EXTRA_BASE_HEIGHT,
  coverDoc,
  coverImageHtml,
  coverY,
  createThemedTemplate,
  escapeHtml,
  pad2,
  sc,
} from "../shared/themed.js";

const specPath = fileURLToPath(new URL("../../../../../shared/unified-publish-themes/spec.json", import.meta.url));
const sharedThemeFile = JSON.parse(readFileSync(specPath, "utf8"));

const baseDefaults = {
  paddingH: sc(38),
  contentWidth: sc(344),
  contentTop: sc(82),
  maxContentHeight: sc(410 + EXTRA_BASE_HEIGHT),
  headerTop: sc(36),
  footerBottom: sc(30),
  fontSize: sc(12.5),
  h1Size: sc(23),
  h2Size: sc(15),
  h3Size: sc(13),
  codeSize: sc(11),
  tableSize: sc(11.5),
  paraGap: sc(10),
  lineHeight: 1.82,
};

function mergedDefaults(spec) {
  const { colors, typography } = spec;
  return {
    ...baseDefaults,
    mode: spec.mode,
    sourceId: spec.id,
    font: spec.font,
    paper: colors.paper,
    ink: colors.ink,
    muted: colors.muted,
    accent: colors.accent,
    accentDeep: colors.accentDeep,
    accentSoft: colors.accentSoft,
    rule: colors.rule,
    codeBg: colors.codeBg,
    codeText: colors.codeText,
    fontSize: sc(typography.cardBody || 12.5),
    h1Size: sc(Math.min(24, Math.max(20, typography.h1 * 0.82))),
    h2Size: sc(Math.min(17, Math.max(14, typography.h2 * 0.68))),
    h3Size: sc(Math.min(14, Math.max(12.5, typography.h3 * 0.72))),
    lineHeight: typography.cardLine || 1.82,
  };
}

function bodyCss(theme) {
  const quiet = theme.mode === "openai" || theme.mode === "minimal";
  const headingAlign = theme.mode === "coral" || theme.mode === "monograph" ? "center" : "left";
  const paragraphAlign = quiet ? "left" : "justify";
  const h1Weight = theme.mode === "openai" || theme.mode === "monograph" ? 500 : 700;
  const h2Weight = theme.mode === "openai" ? 500 : 700;
  const tableRule = quiet ? "1px solid var(--rule)" : "1px dashed var(--rule)";
  const headingFont = theme.mode === "medium" || theme.mode === "monograph" ? "var(--serif-cn)" : "var(--sans-cn)";
  const bodyFont = theme.mode === "openai" || theme.mode === "minimal" || theme.mode === "claude" ? "var(--sans-cn)" : "var(--serif-cn)";

  let headingExtra = "";
  let blockquote = `border-left: ${sc(3)}px solid var(--accent); padding: ${sc(12)}px ${sc(16)}px; background: var(--accent-soft); color: var(--muted); border-radius: ${sc(6)}px;`;
  let codeBlock = `background: ${theme.codeBg}; color: ${theme.codeText}; border-radius: ${sc(6)}px; padding: ${sc(11)}px ${sc(14)}px;`;
  let image = `border-radius: ${sc(8)}px;`;

  if (theme.mode === "claude") {
    headingExtra = `
  .md-body h1, .md-body h2 { color: var(--accent); }
  .md-body strong { color: var(--accent); background: var(--accent-soft); padding: 0 ${sc(3)}px; border-radius: ${sc(3)}px; }`;
    blockquote = `border-left: ${sc(4)}px solid var(--accent); padding: ${sc(12)}px ${sc(16)}px; background: rgba(183,92,61,0.045); color: var(--muted); border-radius: ${sc(4)}px;`;
    image = `border-radius: ${sc(12)}px; padding: ${sc(5)}px; border: 1px solid rgba(15,23,42,0.1); box-shadow: 0 ${sc(10)}px ${sc(22)}px rgba(15,23,42,0.14);`;
  } else if (theme.mode === "cards-claude") {
    headingExtra = `
  .md-body h2 { border-left: ${sc(4)}px solid var(--accent); padding-left: ${sc(10)}px; }
  .md-body strong { color: var(--accent); background: var(--accent-soft); padding: 0 ${sc(3)}px; border-radius: ${sc(3)}px; }`;
    blockquote = `border-left: ${sc(3)}px solid var(--accent); padding: ${sc(12)}px ${sc(16)}px; background: var(--accent-soft); color: var(--muted); border-radius: ${sc(8)}px; font-style: italic;`;
    codeBlock = `background: #1e1e1c; color: #e8e6dc; border-radius: ${sc(8)}px; padding: ${sc(12)}px ${sc(14)}px;`;
    image = `border-radius: ${sc(10)}px; padding: ${sc(4)}px; background: #f8f6f1; border: 1px solid var(--rule); box-shadow: 0 ${sc(8)}px ${sc(18)}px rgba(20,20,19,0.1);`;
  } else if (theme.mode === "medium") {
    blockquote = `border-left: ${sc(3)}px solid #d1d5db; padding: ${sc(12)}px ${sc(16)}px; background: #f5f5f5; color: #555; border-radius: ${sc(4)}px;`;
    image = `border-radius: ${sc(6)}px; padding: ${sc(4)}px; border: 1px solid rgba(15,23,42,0.08); box-shadow: 0 ${sc(8)}px ${sc(18)}px rgba(15,23,42,0.1);`;
  } else if (theme.mode === "minimal") {
    blockquote = `border-left: ${sc(3)}px solid #cccccc; padding: ${sc(10)}px ${sc(14)}px; color: var(--muted); background: transparent;`;
    image = `border-radius: ${sc(12)}px; padding: ${sc(5)}px; border: 1px solid rgba(15,23,42,0.08);`;
  } else if (theme.mode === "openai") {
    headingExtra = `
  .md-body strong { font-weight: 700; }
  .md-body a { color: #000; text-decoration-thickness: 1px; }`;
    blockquote = `border-left: ${sc(2)}px solid #d1d5db; padding: ${sc(10)}px ${sc(16)}px; background: transparent; color: #000; font-style: italic;`;
    image = `border-radius: 0;`;
  } else if (theme.mode === "coral") {
    headingExtra = `
  .md-body h1 { border-top: 1px solid var(--accent); border-bottom: 1px solid var(--accent); padding: ${sc(5)}px 0; }
  .md-body h2 { color: var(--accent); border-bottom: 1px solid var(--rule); padding-bottom: ${sc(4)}px; }
  .md-body strong { color: var(--accent); background: var(--accent-soft); padding: 0 ${sc(3)}px; border-radius: ${sc(3)}px; }`;
    blockquote = `border-top: 1px solid var(--accent); border-bottom: 1px solid var(--accent); padding: ${sc(12)}px ${sc(16)}px; background: ${theme.codeBg}; color: var(--accent-deep); text-align: center; font-style: italic;`;
    codeBlock = `background: ${theme.codeBg}; color: var(--ink); border-top: 1px solid var(--accent); border-bottom: 1px solid var(--accent); padding: ${sc(12)}px ${sc(14)}px;`;
    image = `border-radius: ${sc(4)}px;`;
  } else if (theme.mode === "monograph") {
    headingExtra = `
  #capture-body.md-body { display: flex; flex-direction: column; justify-content: flex-end; }
  .md-body h1 { letter-spacing: .04em; }
  .md-body h2 { letter-spacing: .03em; }
  .md-body strong { color: var(--ink); background: transparent; }`;
    blockquote = `padding: 0 ${sc(22)}px; color: #333; font-style: italic; text-align: justify;`;
    codeBlock = `border-top: 1px solid #111; border-bottom: 1px solid #111; padding: ${sc(10)}px 0; color: #111; background: transparent;`;
    image = `filter: grayscale(1);`;
  }

  return `
  .md-body { font-family: ${bodyFont}; }
  .md-body h1 {
    font-family: ${headingFont}; font-size: ${theme.h1Size}px; line-height: 1.36; text-align: ${headingAlign};
    font-weight: ${h1Weight}; margin-bottom: ${theme.paraGap}px; color: var(--ink);
  }
  .md-body h2 {
    font-family: ${headingFont}; font-size: ${theme.h2Size}px; line-height: 1.42; text-align: ${headingAlign};
    font-weight: ${h2Weight}; margin-bottom: ${Math.round(theme.paraGap * 0.8)}px; color: var(--ink);
  }
  .md-body h3 { font-family: ${headingFont}; font-size: ${theme.h3Size}px; line-height: 1.45; font-weight: 600; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; color: var(--ink); }
  .md-body p { text-indent: 0; text-align: ${paragraphAlign}; color: var(--ink); }
  .md-body blockquote { ${blockquote} }
  .md-body pre { ${codeBlock} }
  .md-body code { background: var(--accent-soft); color: var(--accent-deep); padding: .08em .38em; border-radius: ${sc(3)}px; }
  .md-body table { border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }
  .md-body th { color: ${quiet || theme.mode === "medium" || theme.mode === "monograph" ? "var(--ink)" : "var(--accent)"}; font-weight: 700; border-bottom: ${tableRule}; }
  .md-body td { border-bottom: ${tableRule}; }
  .md-body p:has(> img.md-image:only-child) { padding: ${sc(5)}px; background: transparent; }
  .md-body img.md-image { ${image} }
  .md-body hr { border-top: 1px solid var(--rule); }
  ${headingExtra}`;
}

function headerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  if (theme.mode === "openai" || theme.mode === "minimal") {
    return `<div id="theme-header" class="theme-header-unified theme-header-unified-quiet"><span data-chapter-label>${chapter}</span><span data-page-num>${pageNum}</span></div>`;
  }
  if (theme.mode === "monograph") {
    return `<div id="theme-header" class="theme-header-unified-mono"><span data-page-num>${pageNum}</span><span data-chapter-label>${chapter}</span></div>`;
  }
  return `<div id="theme-header" class="theme-header-unified"><span data-page-num>${pad2(pageNum)}</span><i></i><span data-chapter-label>${chapter}</span></div>`;
}

function footerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  if (theme.mode === "openai" || theme.mode === "minimal") {
    return `<div id="theme-footer" class="theme-footer-unified theme-footer-unified-quiet"><i></i><span><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></span></div>`;
  }
  return `<div id="theme-footer" class="theme-footer-unified"><span>henry gpt 2024</span><strong><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></strong></div>`;
}

function chromeCss(theme) {
  return `
  .theme-header-unified {
    display: flex; align-items: center; gap: ${sc(10)}px;
    font-family: var(--sans-cn); font-size: ${sc(10)}px; color: var(--accent) !important;
    letter-spacing: .18em; font-weight: 700;
  }
  .theme-header-unified i { flex: 1; height: 1px; background: var(--rule); }
  .theme-header-unified-quiet { justify-content: space-between; color: var(--muted) !important; letter-spacing: .08em; font-weight: 500; }
  .theme-header-unified-mono { font-family: var(--serif-cn); color: #111 !important; display: flex; justify-content: space-between; align-items: baseline; }
  .theme-header-unified-mono span:first-child { font-size: ${sc(22)}px; font-weight: 500; line-height: 1; letter-spacing: .05em; }
  .theme-header-unified-mono span:last-child { font-size: ${sc(12)}px; font-weight: 500; letter-spacing: .08em; }
  .theme-footer-unified {
    display: flex; justify-content: space-between; align-items: baseline;
    font-family: ${theme.mode === "medium" || theme.mode === "cards-claude" || theme.mode === "monograph" ? "var(--serif-cn)" : "var(--sans-cn)"};
    color: var(--muted) !important; font-size: ${sc(10)}px;
  }
  .theme-footer-unified > span:first-child { letter-spacing: 0; }
  .theme-footer-unified strong { color: var(--accent); font-size: ${sc(12)}px; }
  .theme-footer-unified-quiet { flex-direction: column; gap: ${sc(7)}px; align-items: stretch; }
  .theme-footer-unified-quiet i { height: 1px; background: var(--rule); }
  .theme-footer-unified-quiet span { text-align: right; }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  const quiet = theme.mode === "openai" || theme.mode === "minimal" || theme.mode === "medium";
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute; inset:0; padding:${coverY(58)}px ${sc(42)}px ${coverY(44)}px; display:flex; flex-direction:column; font-family:${quiet ? "var(--sans-cn)" : "var(--serif-cn)"}; color:var(--ink);">
          <div style="display:flex;align-items:center;gap:${sc(12)}px;color:var(--accent);font-size:${sc(10)}px;letter-spacing:.32em;font-weight:${quiet ? 500 : 800};">
            <span>${chapter}</span><i style="flex:1;height:1px;background:var(--rule);"></i>
          </div>
          ${coverImageSrc ? `<div style="width:100%; aspect-ratio:4/3; margin-top:${coverY(24)}px; overflow:hidden; border:${quiet ? "1px solid var(--rule)" : "none"};">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div class="fit-box" style="flex:1;width:100%;display:flex;align-items:center;justify-content:${quiet ? "flex-start" : "center"};">
            <h1 class="fit-title" data-min="${sc(16)}" data-max="${coverImageSrc ? sc(24) : sc(34)}" style="line-height:${quiet ? 1.25 : 1.42};font-weight:${theme.mode === "openai" || theme.mode === "monograph" ? 500 : 800};text-align:${quiet ? "left" : "center"};color:var(--ink);">${safeTitle}</h1>
          </div>
          <div style="height:${quiet ? "1px" : sc(2) + "px"};width:${quiet ? "100%" : sc(70) + "px"};background:var(--accent);opacity:${quiet ? ".25" : "1"};"></div>
        </div>
      </div>`, fontOpts);
}

function altCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute;inset:0;background:var(--paper);"></div>
        <div style="position:absolute;left:${sc(34)}px;right:${sc(34)}px;top:${coverY(42)}px;bottom:${coverY(36)}px;display:flex;flex-direction:column;font-family:var(--sans-cn);color:var(--ink);">
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:${sc(10)}px;letter-spacing:.2em;color:var(--muted);"><span>${chapter}</span><span>${theme.id}</span></div>
          <div style="height:1px;background:var(--rule);margin-top:${coverY(14)}px;"></div>
          ${coverImageSrc ? `<div style="margin-top:${coverY(24)}px;width:100%;aspect-ratio:1/1;overflow:hidden;">${coverImageHtml(coverImageSrc)}</div>` : `<div style="margin-top:${coverY(28)}px;flex:1;border:1px solid var(--rule);background:var(--accent-soft);display:flex;align-items:center;justify-content:center;color:var(--accent);font-size:${sc(52)}px;font-family:var(--serif-cn);">共</div>`}
          <div class="fit-box" style="height:${coverImageSrc ? coverY(116) : coverY(150)}px;margin-top:${coverY(24)}px;"><h1 class="fit-title" data-min="${sc(14)}" data-max="${coverImageSrc ? sc(20) : sc(26)}" style="line-height:1.32;font-weight:800;color:var(--ink);">${safeTitle}</h1></div>
        </div>
      </div>`, fontOpts);
}

function makeTemplate(spec) {
  return createThemedTemplate({
    id: `${sharedThemeFile.prefix}-${spec.id}`,
    name: `共用 ${spec.name}`,
    defaults: mergedDefaults(spec),
    bodyCss,
    headerHtml,
    footerHtml,
    chromeCss,
    primaryCover,
    altCover,
  });
}

export const unifiedTemplates = sharedThemeFile.themes.map(makeTemplate);
