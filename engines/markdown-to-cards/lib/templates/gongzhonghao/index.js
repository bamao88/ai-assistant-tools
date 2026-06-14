import {
  DEFAULT_CHAPTER_LABEL,
  EXTRA_BASE_HEIGHT,
  coverDoc,
  coverImageHtml,
  coverY,
  createThemedTemplate,
  escapeHtml,
  sc,
  pad2,
} from "../shared/themed.js";

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

const themeSpecs = [
  {
    id: "claude",
    name: "Claude",
    mode: "claude",
    defaults: {
      font: "sans",
      paper: "#f8f6f0",
      ink: "#2b2b2b",
      muted: "#666666",
      accent: "#b75c3d",
      accentDeep: "#9b4a30",
      accentSoft: "rgba(183,92,61,0.08)",
      rule: "rgba(183,92,61,0.28)",
      lineHeight: 1.78,
    },
  },
  {
    id: "medium",
    name: "Medium",
    mode: "medium",
    defaults: {
      font: "serif",
      paper: "#fcfcfc",
      ink: "#242424",
      muted: "#666666",
      accent: "#111111",
      accentDeep: "#000000",
      accentSoft: "#f5f5f5",
      rule: "#e0e0e0",
      h1Size: sc(23),
      h2Size: sc(16),
      lineHeight: 1.84,
    },
  },
  {
    id: "minimal",
    name: "极简",
    mode: "minimal",
    defaults: {
      font: "sans",
      paper: "#ffffff",
      ink: "#333333",
      muted: "#666666",
      accent: "#111111",
      accentDeep: "#111111",
      accentSoft: "#f5f5f5",
      rule: "#eeeeee",
      h1Size: sc(22),
      h2Size: sc(15),
      lineHeight: 1.88,
    },
  },
  {
    id: "openai",
    name: "OpenAI",
    mode: "openai",
    defaults: {
      font: "sans",
      paper: "#ffffff",
      ink: "#000000",
      muted: "#4a4a4a",
      accent: "#000000",
      accentDeep: "#000000",
      accentSoft: "rgba(0,0,0,0.045)",
      rule: "#e5e7eb",
      paddingH: sc(36),
      contentWidth: sc(348),
      h1Size: sc(22),
      h2Size: sc(16),
      fontSize: sc(12.8),
      lineHeight: 1.72,
    },
  },
  {
    id: "cards-claude",
    name: "卡片 Claude",
    mode: "cards-claude",
    defaults: {
      font: "serif",
      paper: "#faf9f5",
      ink: "#141413",
      muted: "#706e68",
      accent: "#d97757",
      accentDeep: "#be5f42",
      accentSoft: "rgba(217,119,87,0.09)",
      rule: "#e8e6dc",
      h1Size: sc(22),
      h2Size: sc(15),
      lineHeight: 1.88,
    },
  },
];

function mergedDefaults(spec) {
  return {
    ...baseDefaults,
    ...spec.defaults,
    mode: spec.mode,
  };
}

function bodyCss(theme) {
  const headingAlign = theme.mode === "coral" ? "center" : "left";
  const paragraphAlign = theme.mode === "openai" || theme.mode === "minimal" ? "left" : "justify";
  const h1Weight = theme.mode === "openai" ? 500 : 700;
  const h2Weight = theme.mode === "openai" ? 500 : 700;
  const tableRule = theme.mode === "openai" || theme.mode === "minimal" ? "1px solid var(--rule)" : "1px dashed var(--rule)";

  let headingExtra = "";
  let blockquote = `border-left: ${sc(3)}px solid var(--accent); padding: ${sc(12)}px ${sc(16)}px; background: var(--accent-soft); color: var(--muted);`;
  let codeBlock = `background: var(--accent-soft); color: var(--ink); border-radius: ${sc(6)}px; padding: ${sc(11)}px ${sc(14)}px;`;
  let image = `border-radius: ${sc(8)}px;`;

  if (theme.mode === "claude") {
    headingExtra = `
  .md-body h1, .md-body h2 { color: var(--accent); }
  .md-body strong { color: var(--accent); background: var(--accent-soft); padding: 0 ${sc(3)}px; border-radius: ${sc(3)}px; }`;
    blockquote = `border-left: ${sc(4)}px solid var(--accent); padding: ${sc(12)}px ${sc(16)}px; background: rgba(183,92,61,0.045); color: var(--muted); border-radius: ${sc(4)}px;`;
    codeBlock = `background: #f0ece4; color: var(--accent); border-radius: ${sc(8)}px; padding: ${sc(12)}px ${sc(14)}px;`;
    image = `border-radius: ${sc(12)}px; padding: ${sc(5)}px; border: 1px solid rgba(15,23,42,0.1); box-shadow: 0 ${sc(10)}px ${sc(22)}px rgba(15,23,42,0.14);`;
  } else if (theme.mode === "medium") {
    blockquote = `border-left: ${sc(3)}px solid #d1d5db; padding: ${sc(12)}px ${sc(16)}px; background: #f5f5f5; color: #555; border-radius: ${sc(4)}px;`;
    codeBlock = `background: #f2f3f5; color: #333; border-radius: ${sc(5)}px; padding: ${sc(12)}px ${sc(14)}px;`;
    image = `border-radius: ${sc(6)}px; padding: ${sc(4)}px; border: 1px solid rgba(15,23,42,0.08); box-shadow: 0 ${sc(8)}px ${sc(18)}px rgba(15,23,42,0.1);`;
  } else if (theme.mode === "minimal") {
    blockquote = `border-left: ${sc(3)}px solid #cccccc; padding: ${sc(10)}px ${sc(14)}px; color: var(--muted); background: transparent;`;
    codeBlock = `background: #f5f5f5; color: #333; border-radius: ${sc(4)}px; padding: ${sc(10)}px ${sc(14)}px;`;
    image = `border-radius: ${sc(12)}px; padding: ${sc(5)}px; border: 1px solid rgba(15,23,42,0.08);`;
  } else if (theme.mode === "openai") {
    headingExtra = `
  .md-body strong { font-weight: 700; }
  .md-body a { color: #000; text-decoration-thickness: 1px; }`;
    blockquote = `border-left: ${sc(2)}px solid #d1d5db; padding: ${sc(10)}px ${sc(16)}px; background: transparent; color: #000; font-style: italic;`;
    codeBlock = `background: rgba(0,0,0,0.045); color: #000; border-radius: ${sc(5)}px; padding: ${sc(11)}px ${sc(14)}px;`;
    image = `border-radius: 0;`;
  } else if (theme.mode === "cards-claude") {
    headingExtra = `
  .md-body h2 { border-left: ${sc(4)}px solid var(--accent); padding-left: ${sc(10)}px; }
  .md-body strong { color: var(--accent); background: var(--accent-soft); padding: 0 ${sc(3)}px; border-radius: ${sc(3)}px; }`;
    blockquote = `border-left: ${sc(3)}px solid var(--accent); padding: ${sc(12)}px ${sc(16)}px; background: var(--accent-soft); color: var(--muted); border-radius: ${sc(8)}px; font-style: italic;`;
    codeBlock = `background: #1e1e1c; color: #e8e6dc; border-radius: ${sc(8)}px; padding: ${sc(12)}px ${sc(14)}px;`;
    image = `border-radius: ${sc(10)}px; padding: ${sc(4)}px; background: #f8f6f1; border: 1px solid var(--rule); box-shadow: 0 ${sc(8)}px ${sc(18)}px rgba(20,20,19,0.1);`;
  }

  return `
  .md-body { font-family: ${theme.mode === "openai" || theme.mode === "minimal" || theme.mode === "claude" ? "var(--sans-cn)" : "var(--serif-cn)"}; }
  .md-body h1 {
    font-size: ${theme.h1Size}px; line-height: 1.36; text-align: ${headingAlign};
    font-weight: ${h1Weight}; margin-bottom: ${theme.paraGap}px; color: var(--ink);
  }
  .md-body h2 {
    font-size: ${theme.h2Size}px; line-height: 1.42; text-align: ${headingAlign};
    font-weight: ${h2Weight}; margin-bottom: ${Math.round(theme.paraGap * 0.8)}px; color: var(--ink);
  }
  .md-body h3 { font-size: ${theme.h3Size}px; line-height: 1.45; font-weight: 600; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; color: var(--ink); }
  .md-body p { text-indent: 0; text-align: ${paragraphAlign}; color: var(--ink); }
  .md-body blockquote { ${blockquote} }
  .md-body pre { ${codeBlock} }
  .md-body code { background: var(--accent-soft); color: var(--accent-deep); padding: .08em .38em; border-radius: ${sc(3)}px; }
  .md-body table { border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }
  .md-body th { color: ${theme.mode === "openai" || theme.mode === "minimal" || theme.mode === "medium" ? "var(--ink)" : "var(--accent)"}; font-weight: 700; border-bottom: ${tableRule}; }
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
    return `<div id="theme-header" class="theme-header-gzh theme-header-quiet"><span data-chapter-label>${chapter}</span><span data-page-num>${pageNum}</span></div>`;
  }
  return `<div id="theme-header" class="theme-header-gzh"><span data-page-num>${pad2(pageNum)}</span><i></i><span data-chapter-label>${chapter}</span></div>`;
}

function footerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  if (theme.mode === "openai" || theme.mode === "minimal") {
    return `<div id="theme-footer" class="theme-footer-gzh theme-footer-quiet"><i></i><span><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></span></div>`;
  }
  return `<div id="theme-footer" class="theme-footer-gzh"><span>WECHAT STYLE</span><strong><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></strong></div>`;
}

function chromeCss(theme) {
  return `
  .theme-header-gzh {
    display: flex; align-items: center; gap: ${sc(10)}px;
    font-family: var(--sans-cn); font-size: ${sc(10)}px; color: var(--accent) !important;
    letter-spacing: .18em; font-weight: 700;
  }
  .theme-header-gzh i { flex: 1; height: 1px; background: var(--rule); }
  .theme-header-quiet { justify-content: space-between; color: var(--muted) !important; letter-spacing: .08em; font-weight: 500; }
  .theme-footer-gzh {
    display: flex; justify-content: space-between; align-items: baseline;
    font-family: ${theme.mode === "medium" || theme.mode === "cards-claude" ? "var(--serif-cn)" : "var(--sans-cn)"};
    color: var(--muted) !important; font-size: ${sc(10)}px;
  }
  .theme-footer-gzh > span:first-child { letter-spacing: .18em; }
  .theme-footer-gzh strong { color: var(--accent); font-size: ${sc(12)}px; }
  .theme-footer-quiet { flex-direction: column; gap: ${sc(7)}px; align-items: stretch; }
  .theme-footer-quiet i { height: 1px; background: var(--rule); }
  .theme-footer-quiet span { text-align: right; }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  const isQuiet = theme.mode === "openai" || theme.mode === "minimal" || theme.mode === "medium";
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute; inset:0; padding:${coverY(58)}px ${sc(42)}px ${coverY(44)}px; display:flex; flex-direction:column; font-family:${isQuiet ? "var(--sans-cn)" : "var(--serif-cn)"}; color:var(--ink);">
          <div style="display:flex;align-items:center;gap:${sc(12)}px;color:var(--accent);font-size:${sc(10)}px;letter-spacing:.32em;font-weight:${isQuiet ? 500 : 800};">
            <span>${chapter}</span><i style="flex:1;height:1px;background:var(--rule);"></i>
          </div>
          ${coverImageSrc ? `<div style="width:100%; aspect-ratio:4/3; margin-top:${coverY(24)}px; overflow:hidden; border:${isQuiet ? "1px solid var(--rule)" : "none"};">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div class="fit-box" style="flex:1;width:100%;display:flex;align-items:center;justify-content:${isQuiet ? "flex-start" : "center"};">
            <h1 class="fit-title" data-min="${sc(16)}" data-max="${coverImageSrc ? sc(24) : sc(34)}" style="line-height:${isQuiet ? 1.25 : 1.42};font-weight:${theme.mode === "openai" ? 500 : 800};text-align:${isQuiet ? "left" : "center"};color:var(--ink);">${safeTitle}</h1>
          </div>
          <div style="height:${isQuiet ? "1px" : sc(2) + "px"};width:${isQuiet ? "100%" : sc(70) + "px"};background:var(--accent);opacity:${isQuiet ? ".25" : "1"};"></div>
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
          ${coverImageSrc ? `<div style="margin-top:${coverY(24)}px;width:100%;aspect-ratio:1/1;overflow:hidden;">${coverImageHtml(coverImageSrc)}</div>` : `<div style="margin-top:${coverY(28)}px;flex:1;border:1px solid var(--rule);background:var(--accent-soft);display:flex;align-items:center;justify-content:center;color:var(--accent);font-size:${sc(52)}px;font-family:var(--serif-cn);">文</div>`}
          <div class="fit-box" style="height:${coverImageSrc ? coverY(116) : coverY(150)}px;margin-top:${coverY(24)}px;"><h1 class="fit-title" data-min="${sc(14)}" data-max="${coverImageSrc ? sc(20) : sc(26)}" style="line-height:1.32;font-weight:800;color:var(--ink);">${safeTitle}</h1></div>
        </div>
      </div>`, fontOpts);
}

function makeTemplate(spec) {
  return createThemedTemplate({
    id: spec.id,
    name: spec.name,
    defaults: mergedDefaults(spec),
    bodyCss,
    headerHtml,
    footerHtml,
    chromeCss,
    primaryCover,
    altCover,
  });
}

export const gongzhonghaoTemplates = themeSpecs.map(makeTemplate);
