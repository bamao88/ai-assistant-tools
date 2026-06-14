import {
  DEFAULT_CHAPTER_LABEL,
  EXTRA_BASE_HEIGHT,
  coverDoc,
  coverImageHtml,
  coverY,
  createThemedTemplate,
  escapeHtml,
  sc,
} from "../shared/themed.js";

const defaults = {
  font: "sans",
  paper: "oklch(0.99 0.003 80)",
  ink: "oklch(0.18 0.01 260)",
  muted: "oklch(0.45 0.01 260)",
  accent: "oklch(0.52 0.13 152)",
  accentDeep: "oklch(0.52 0.13 152)",
  accentSoft: "color-mix(in oklab, oklch(0.78 0.09 150) 22%, var(--paper))",
  rule: "color-mix(in oklab, var(--accent) 35%, transparent)",
  paddingH: sc(36),
  contentWidth: sc(348),
  contentTop: sc(104),
  maxContentHeight: sc(380 + EXTRA_BASE_HEIGHT),
  headerTop: sc(32),
  footerBottom: sc(28),
  fontSize: sc(12.5),
  h1Size: sc(22),
  h2Size: sc(14.5),
  h3Size: sc(13),
  codeSize: sc(11),
  tableSize: sc(11.5),
  paraGap: sc(10),
  lineHeight: 1.95,
};

function bodyCss(theme) {
  return `
  .md-body { font-family: var(--sans-cn); }
  .md-body h1 { font-size: ${theme.h1Size}px; line-height: 1.5; text-align: center; padding: ${sc(4)}px 0; margin-bottom: ${theme.paraGap}px; font-weight: 700; }
  .md-body h2 { color: var(--accent); font-size: ${theme.h2Size}px; line-height: 1.5; margin-bottom: ${Math.round(theme.paraGap * 0.75)}px; font-weight: 700; }
  .md-body h2::before { content: "▸ "; }
  .md-body h3 { font-size: ${theme.h3Size}px; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; font-weight: 700; }
  .md-body p { text-indent: 0; text-align: justify; }
  .md-body blockquote { background: var(--accent-soft); border-left: ${sc(3)}px solid var(--accent); border-radius: 0 ${sc(8)}px ${sc(8)}px 0; color: var(--accent); padding: ${sc(10)}px ${sc(14)}px; }
  .md-body ul li::marker { content: "▸  "; }
  .md-body pre { background: var(--accent-soft); border-left: ${sc(3)}px solid var(--accent); border-radius: 0 ${sc(8)}px ${sc(8)}px 0; padding: ${sc(10)}px ${sc(14)}px; color: color-mix(in oklab, var(--accent) 90%, var(--ink)); }
  .md-body code { background: var(--accent-soft); color: var(--accent-deep); padding: .08em .38em; border-radius: 5px; }
  .md-body table { border: 1px solid var(--rule); border-radius: ${sc(10)}px; overflow: hidden; border-collapse: separate; border-spacing: 0; }
  .md-body th { background: var(--accent); color: #fff; font-weight: 700; }
  .md-body tr:nth-child(even) td { background: color-mix(in oklab, oklch(0.78 0.09 150) 18%, transparent); }
  .md-body p:has(> img.md-image:only-child) { border: 1px solid color-mix(in oklab, var(--accent) 30%, transparent); background: transparent; border-radius: ${sc(14)}px; }
  .md-body img.md-image { border-radius: ${sc(14)}px; }
  .md-body hr { border-top: 1px dashed var(--accent); }`;
}

function headerHtml(_theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  return `<div id="theme-header" class="theme-header-sage">
        <span data-page-num>${pageNum}</span><i></i>
      </div>`;
}

function footerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-footer" class="theme-footer-sage"><span data-chapter-label>${chapter}</span> · <span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></div>`;
}

function chromeCss() {
  return `
  .theme-header-sage { display: flex; flex-direction: column; align-items: center; font-family: var(--sans-cn); color: var(--accent) !important; }
  .theme-header-sage span { width: ${sc(38)}px; height: ${sc(38)}px; border-radius: 999px; background: var(--accent); color: white; display: flex; align-items: center; justify-content: center; font-size: ${sc(16)}px; font-weight: 800; }
  .theme-header-sage i { width: 1px; height: ${sc(16)}px; background: var(--accent); opacity: .4; margin-top: ${sc(6)}px; display: block; }
  .theme-footer-sage { text-align: center; font-family: var(--sans-cn); font-size: ${sc(10)}px; letter-spacing: .2em; color: var(--accent) !important; }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute; inset:0; padding:${coverY(56)}px ${sc(40)}px ${coverY(40)}px; display:flex; flex-direction:column; align-items:center; font-family:var(--sans-cn);">
          <svg width="${sc(32)}" height="${sc(32)}" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.4"><path d="M12 2C8 6 6 9 6 13a6 6 0 0 0 12 0c0-4-2-7-6-11z"/></svg>
          <div style="font-size:${sc(11)}px;letter-spacing:.4em;color:var(--accent);margin-top:${coverY(14)}px;">${chapter}</div>
          ${coverImageSrc ? `<div style="width:100%; aspect-ratio:4/3; margin-top:${coverY(22)}px; border-radius:${sc(16)}px; overflow:hidden; border:1px solid var(--rule);">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div class="fit-box" style="flex:1;width:100%;display:flex;align-items:center;justify-content:center;">
            <h1 class="fit-title" data-min="${sc(16)}" data-max="${coverImageSrc ? sc(22) : sc(28)}" style="text-align:center;line-height:1.5;font-weight:700;color:var(--ink);">${safeTitle}</h1>
          </div>
          <div style="display:flex;align-items:center;gap:${sc(8)}px;color:var(--accent);font-size:${sc(10)}px;letter-spacing:.3em;"><i style="width:${sc(18)}px;height:1px;background:var(--accent);"></i>SLOW LIVING<i style="width:${sc(18)}px;height:1px;background:var(--accent);"></i></div>
        </div>
      </div>`, fontOpts);
}

function altCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#f4efde;">
        <div style="position:absolute;inset:0;padding:${coverY(70)}px ${sc(40)}px ${coverY(50)}px;display:flex;flex-direction:column;align-items:center;color:#5a5a3f;font-family:var(--serif-cn);">
          <div style="font-size:${sc(13)}px;letter-spacing:.6em;">SUTO</div>
          <div style="margin-top:${coverY(30)}px;width:${sc(160)}px;aspect-ratio:4/5;border:1px solid var(--rule);padding:${sc(5)}px;background:var(--accent-soft);">${coverImageSrc ? coverImageHtml(coverImageSrc) : `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#5a5a3f;font-size:${sc(36)}px;opacity:.45;">☉</div>`}</div>
          <div style="flex:1;"></div>
          <svg width="${sc(60)}" height="${sc(22)}" viewBox="0 0 60 22" fill="#5a5a3f" opacity=".72"><circle cx="6" cy="14" r="3.5"/><circle cx="14" cy="14" r="3.5"/><path d="M30 8 h12 a4 4 0 0 1 4 4 v3 a4 4 0 0 1 -4 4 h-12 a4 4 0 0 1 -4 -4 v-3 a4 4 0 0 1 4 -4 z"/><path d="M46 11 q5 1 5 5" stroke="#5a5a3f" stroke-width="1.2" fill="none"/><rect x="33" y="5" width="4" height="3"/></svg>
          <div class="fit-box" style="margin-top:${coverY(16)}px;height:${coverY(110)}px;width:100%;"><h1 class="fit-title" data-min="${sc(9)}" data-max="${sc(11)}" style="text-align:center;line-height:1.6;font-style:italic;font-weight:500;">${safeTitle}</h1></div>
        </div>
      </div>`, fontOpts);
}

export default createThemedTemplate({
  id: "sage",
  name: "清新晨光",
  defaults,
  bodyCss,
  headerHtml,
  footerHtml,
  chromeCss,
  primaryCover,
  altCover,
});
