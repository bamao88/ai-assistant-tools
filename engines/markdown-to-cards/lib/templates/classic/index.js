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
  font: "serif",
  paper: "oklch(0.97 0.012 75)",
  ink: "oklch(0.18 0.01 260)",
  muted: "color-mix(in oklab, var(--ink) 70%, transparent)",
  accent: "#25211b",
  accentDeep: "oklch(0.18 0.01 260)",
  accentSoft: "color-mix(in oklab, var(--ink) 4%, var(--paper))",
  rule: "color-mix(in oklab, var(--ink) 18%, transparent)",
  paddingH: sc(40),
  contentWidth: sc(340),
  contentTop: sc(68),
  maxContentHeight: sc(420 + EXTRA_BASE_HEIGHT),
  headerTop: sc(36),
  footerBottom: sc(30),
  fontSize: sc(12.5),
  h1Size: sc(22),
  h2Size: sc(14.5),
  h3Size: sc(12.5),
  codeSize: sc(11),
  tableSize: sc(11.5),
  paraGap: sc(10),
  lineHeight: 2,
};

function bodyCss(theme) {
  return `
  .md-body { font-family: var(--serif-cn); }
  .md-body h1 { font-size: ${theme.h1Size}px; line-height: 1.5; text-align: center; padding: ${sc(4)}px 0 ${sc(8)}px; font-weight: 700; margin-bottom: ${theme.paraGap}px; }
  .md-body h2 { font-size: ${theme.h2Size}px; line-height: 1.5; margin-top: ${sc(4)}px; margin-bottom: ${Math.round(theme.paraGap * 0.75)}px; font-weight: 700; }
  .md-body h3 { font-size: ${theme.h3Size}px; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; font-weight: 700; }
  .md-body p { text-indent: 0; text-align: justify; }
  .md-body blockquote { padding: 0 ${sc(18)}px; color: var(--muted); font-style: italic; text-align: justify; }
  .md-body pre { background: var(--accent-soft); border-top: 1px solid var(--accent); border-bottom: 1px solid var(--accent); padding: ${sc(10)}px ${sc(14)}px; color: var(--ink); }
  .md-body code { background: var(--accent-soft); color: var(--ink); padding: .08em .38em; border-radius: 3px; }
  .md-body table { border-top: ${sc(2)}px solid var(--accent); border-bottom: ${sc(2)}px solid var(--accent); font-family: var(--serif-cn); line-height: 1.6; }
  .md-body th { border-bottom: 1px solid var(--accent); font-style: italic; }
  .md-body p:has(> img.md-image:only-child) { border: 1px solid var(--accent); background: transparent; padding: ${sc(3)}px; }
  .md-body hr { border-top: 1px solid var(--accent); opacity: .35; }`;
}

function headerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-header" class="theme-header-classic">
        <div><span data-page-num>${pageNum}</span><span data-chapter-label>${chapter}</span></div><i></i>
      </div>`;
}

function footerHtml(_theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  return `<div id="theme-footer" class="theme-footer-classic"><i></i><div><span>— PAGE —</span><strong><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></strong></div></div>`;
}

function chromeCss() {
  return `
  .theme-header-classic { font-family: var(--serif-cn); color: var(--ink) !important; }
  .theme-header-classic div { display: flex; justify-content: space-between; font-size: ${sc(11)}px; letter-spacing: .3em; }
  .theme-header-classic div span:first-child { font-weight: 700; letter-spacing: 0; }
  .theme-header-classic i { display: block; height: 1px; background: var(--ink); opacity: .18; margin-top: ${sc(6)}px; }
  .theme-footer-classic { font-family: var(--serif-cn); color: var(--ink) !important; }
  .theme-footer-classic i { display: block; height: 1px; background: var(--ink); opacity: .18; margin-bottom: ${sc(6)}px; }
  .theme-footer-classic div { display: flex; justify-content: space-between; align-items: baseline; font-size: ${sc(10)}px; opacity: .75; }
  .theme-footer-classic div span { letter-spacing: .2em; }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute; inset:0; padding:${coverY(60)}px ${sc(44)}px ${coverY(44)}px; display:flex; flex-direction:column; align-items:center; font-family:var(--serif-cn);">
          <div style="font-size:${sc(11)}px;letter-spacing:.45em;font-style:italic;color:var(--muted);">a story of</div>
          <div style="width:${sc(50)}px;height:1px;background:var(--ink);opacity:.4;margin-top:${coverY(16)}px;"></div>
          ${coverImageSrc ? `<div style="width:100%; aspect-ratio:4/3; margin-top:${coverY(26)}px; border:1px solid var(--ink); padding:${sc(4)}px;">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div class="fit-box" style="flex:1;width:100%;display:flex;align-items:center;justify-content:center;">
            <h1 class="fit-title" data-min="${sc(16)}" data-max="${coverImageSrc ? sc(22) : sc(30)}" style="text-align:center;line-height:1.55;font-style:italic;font-weight:700;">${safeTitle}</h1>
          </div>
          <div style="font-size:${sc(12)}px;color:var(--muted);letter-spacing:.15em;">— ${chapter} —</div>
          <div style="width:${sc(50)}px;height:1px;background:var(--ink);opacity:.4;margin-top:${coverY(16)}px;"></div>
        </div>
      </div>`, fontOpts);
}

function altCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  const year = new Date().getFullYear();
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="height:26%;background:#bdb6a3;overflow:hidden;">${coverImageSrc ? coverImageHtml(coverImageSrc) : ""}</div>
        <div style="height:74%;background:${coverImageSrc ? "#e8d76b" : "#f0f0ec"};padding:${coverY(32)}px ${sc(30)}px ${coverY(26)}px;display:flex;flex-direction:column;font-family:var(--serif-cn);color:var(--ink);">
          <div style="font-size:${sc(10)}px;letter-spacing:.2em;opacity:.7;">地域文化のこと</div>
          <div class="fit-box" style="margin-top:${coverY(10)}px;height:${coverY(150)}px;"><h1 class="fit-title" data-min="${sc(16)}" data-max="${sc(24)}" style="line-height:1.45;font-weight:700;">${safeTitle}</h1></div>
          <div style="font-size:${sc(11)}px;opacity:.75;">${chapter} 編</div>
          <div style="flex:1;"></div><div style="columns:2;column-gap:${sc(18)}px;font-size:${sc(9.5)}px;line-height:1.9;color:var(--muted);"><div>I. 序</div><div>II. 工艺</div><div>III. 材料</div><div>IV. 风土</div><div>V. 工具</div><div>VI. 后记</div></div>
          <div style="margin-top:${coverY(12)}px;display:flex;justify-content:space-between;font-size:${sc(9)}px;opacity:.55;letter-spacing:.15em;"><span>NO. 01</span><span>${year} · ISSUE</span></div>
        </div>
      </div>`, fontOpts);
}

export default createThemedTemplate({
  id: "classic",
  name: "经典书页",
  defaults,
  bodyCss,
  headerHtml,
  footerHtml,
  chromeCss,
  primaryCover,
  altCover,
});
