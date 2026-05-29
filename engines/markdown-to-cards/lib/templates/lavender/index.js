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

const defaults = {
  font: "serif",
  paper: "oklch(0.99 0.003 80)",
  ink: "oklch(0.18 0.01 260)",
  muted: "oklch(0.45 0.01 260)",
  accent: "oklch(0.55 0.14 290)",
  accentDeep: "oklch(0.55 0.14 290)",
  accentSoft: "color-mix(in oklab, oklch(0.78 0.08 290) 32%, var(--paper))",
  rule: "color-mix(in oklab, var(--accent) 35%, transparent)",
  cover: "oklch(0.78 0.08 290)",
  paddingH: sc(36),
  contentWidth: sc(348),
  contentTop: sc(68),
  maxContentHeight: sc(430 + EXTRA_BASE_HEIGHT),
  headerTop: sc(40),
  footerBottom: sc(32),
  fontSize: sc(12.5),
  h1Size: sc(22),
  h2Size: sc(15),
  h3Size: sc(13),
  codeSize: sc(11),
  tableSize: sc(11.5),
  paraGap: sc(10),
  lineHeight: 1.95,
};

function bodyCss(theme) {
  return `
  .md-body { font-family: var(--serif-cn); }
  .md-body h1 { color: var(--accent); font-size: ${theme.h1Size}px; text-align: center; line-height: 1.5; padding: ${sc(8)}px 0; margin-bottom: ${theme.paraGap}px; font-weight: 700; }
  .md-body h2 { color: var(--accent); font-size: ${theme.h2Size}px; line-height: 1.5; padding-bottom: ${sc(4)}px; border-bottom: 1px solid var(--accent); margin-bottom: ${theme.paraGap}px; font-weight: 700; }
  .md-body h3 { color: var(--accent); font-size: ${theme.h3Size}px; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; font-weight: 700; }
  .md-body h3::before { content: "※ "; }
  .md-body p { text-indent: 2em; text-align: justify; }
  .md-body blockquote { background: var(--accent-soft); color: var(--accent); border-radius: ${sc(10)}px; padding: ${sc(10)}px ${sc(14)}px; font-style: italic; }
  .md-body ul li::marker { content: "◆  "; }
  .md-body pre { background: var(--accent-soft); border: 1px solid var(--rule); border-radius: ${sc(10)}px; padding: ${sc(10)}px ${sc(14)}px; color: var(--accent-deep); }
  .md-body code { background: var(--accent-soft); color: var(--accent-deep); padding: .08em .38em; border-radius: 999px; }
  .md-body table { border: 1px solid var(--rule); border-radius: ${sc(10)}px; overflow: hidden; border-collapse: separate; border-spacing: 0; }
  .md-body th { background: var(--accent-soft); color: var(--accent); font-weight: 800; }
  .md-body tr:nth-child(even) td { background: color-mix(in oklab, oklch(0.78 0.08 290) 14%, transparent); }
  .md-body p:has(> img.md-image:only-child) { background: transparent; border-radius: ${sc(12)}px; box-shadow: 0 ${sc(6)}px ${sc(18)}px color-mix(in oklab, var(--accent) 25%, transparent); }
  .md-body img.md-image { border-radius: ${sc(12)}px; }
  .md-body hr { border-top: 1px solid var(--rule); }`;
}

function headerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-header" class="theme-header-lavender">
        <div><span class="lavender-rule"></span><span data-chapter-label>${chapter}</span></div>
        <div><span data-page-num data-page-num-pad>${pad2(pageNum)}</span> · <span data-page-total data-page-total-pad>${pad2(total)}</span></div>
      </div>`;
}

function footerHtml(_theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  return `<div id="theme-footer" class="theme-footer-lavender"><strong data-page-num>${pageNum}</strong></div>`;
}

function chromeCss() {
  return `
  .theme-header-lavender { display: flex; justify-content: space-between; align-items: center; font-family: var(--serif-cn); font-size: ${sc(10)}px; letter-spacing: .2em; color: var(--accent) !important; }
  .theme-header-lavender > div:first-child { display: flex; align-items: center; gap: ${sc(8)}px; }
  .lavender-rule { width: ${sc(18)}px; height: ${sc(2)}px; background: var(--accent); display: inline-block; }
  .theme-footer-lavender { display: flex; justify-content: flex-end; font-family: var(--serif-cn); font-size: ${sc(14)}px; font-weight: 700; color: var(--accent) !important; }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:${theme.cover || theme.accent}; color:white;">
        <div style="position:absolute; inset:0; padding:${coverY(44)}px ${sc(32)}px; display:flex; flex-direction:column; align-items:center; font-family:var(--serif-cn);">
          <div style="font-size:${sc(11)}px; letter-spacing:.5em; opacity:.88; margin-bottom:${coverY(14)}px;">${chapter}</div>
          <div style="width:${sc(36)}px;height:1px;background:rgba(255,255,255,.72);margin-bottom:${coverY(18)}px;"></div>
          ${coverImageSrc ? `<div style="width:100%; aspect-ratio:4/3; border-radius:${sc(10)}px; overflow:hidden; box-shadow:0 ${coverY(8)}px ${sc(24)}px rgba(0,0,0,.22); margin-bottom:${coverY(18)}px;">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div class="fit-box" style="flex:1; width:100%; display:flex; align-items:center; justify-content:center;">
            <h1 class="fit-title" data-min="${sc(16)}" data-max="${coverImageSrc ? sc(22) : sc(26)}" style="text-align:center; line-height:1.55; font-weight:500;">${safeTitle}</h1>
          </div>
          <div style="width:${sc(36)}px;height:1px;background:rgba(255,255,255,.72);margin-top:${coverY(18)}px;"></div>
          ${coverImageSrc ? "" : `<svg style="position:absolute;bottom:${coverY(36)}px;" width="${sc(22)}" height="${sc(22)}" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.2"><path d="M12 3l1.8 5.6H19l-4.6 3.4 1.8 5.6L12 14.2 7.8 17.6l1.8-5.6L5 8.6h5.2z"/></svg>`}
        </div>
      </div>`, fontOpts);
}

function altCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#1d3a8a;color:white;">
        <div style="position:absolute;inset:0;padding:${coverY(32)}px ${sc(32)}px ${coverY(28)}px;display:flex;flex-direction:column;font-family:var(--sans-cn);">
          <svg width="${sc(48)}" height="${sc(36)}" viewBox="0 0 48 36" fill="white"><path d="M0 22 c0-12 6-20 18-22 v6 c-7 2-11 8-11 14 h11 v16 H0z"/><path d="M26 22 c0-12 6-20 18-22 v6 c-7 2-11 8-11 14 h11 v16 H26z"/></svg>
          ${coverImageSrc ? `<div style="margin-top:${coverY(18)}px;width:100%;aspect-ratio:16/9;overflow:hidden;border-radius:${sc(4)}px;">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div style="flex:1;"></div><div class="fit-box" style="height:${coverImageSrc ? coverY(150) : coverY(260)}px;"><h1 class="fit-title" data-min="${sc(18)}" data-max="${coverImageSrc ? sc(22) : sc(28)}" style="line-height:1.5;font-weight:600;color:white;">${safeTitle}</h1></div>
          <div style="margin-top:${coverY(18)}px;font-size:${sc(13)}px;opacity:.88;">— ${chapter}</div>
          <div style="margin-top:${coverY(12)}px;display:flex;justify-content:flex-end;"><svg width="${sc(28)}" height="${sc(22)}" viewBox="0 0 48 36" fill="white" opacity=".85" style="transform:rotate(180deg);"><path d="M0 22 c0-12 6-20 18-22 v6 c-7 2-11 8-11 14 h11 v16 H0z"/><path d="M26 22 c0-12 6-20 18-22 v6 c-7 2-11 8-11 14 h11 v16 H26z"/></svg></div>
        </div>
      </div>`, fontOpts);
}

export default createThemedTemplate({
  id: "lavender",
  name: "薰衣草",
  defaults,
  bodyCss,
  headerHtml,
  footerHtml,
  chromeCss,
  primaryCover,
  altCover,
});
