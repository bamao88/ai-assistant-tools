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
  font: "sans",
  paper: "oklch(0.99 0.003 80)",
  ink: "oklch(0.18 0.01 260)",
  muted: "oklch(0.45 0.01 260)",
  accent: "oklch(0.52 0.13 152)",
  accentDeep: "oklch(0.52 0.13 152)",
  accentSoft: "color-mix(in oklab, oklch(0.78 0.09 150) 22%, var(--paper))",
  rule: "oklch(0.52 0.13 152)",
  paddingH: sc(36),
  contentWidth: sc(348),
  contentTop: sc(77),
  maxContentHeight: sc(410 + EXTRA_BASE_HEIGHT),
  headerTop: sc(36),
  footerBottom: sc(30),
  fontSize: sc(12.5),
  h1Size: sc(26),
  h2Size: sc(16),
  h3Size: sc(13),
  codeSize: sc(11),
  tableSize: sc(11.5),
  paraGap: sc(10),
  lineHeight: 1.9,
};

function bodyCss(theme) {
  return `
  .md-body { font-family: var(--sans-cn); }
  .md-body h1 { color: var(--accent); font-size: ${theme.h1Size}px; line-height: 1.3; margin-bottom: ${theme.paraGap}px; font-weight: 900; }
  .md-body h2 { color: var(--accent); font-size: ${theme.h2Size}px; line-height: 1.4; margin-bottom: ${Math.round(theme.paraGap * 0.75)}px; font-weight: 800; }
  .md-body h3 { font-size: ${theme.h3Size}px; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; font-weight: 800; }
  .md-body p { text-align: justify; }
  .md-body blockquote { border-left: ${sc(3)}px solid var(--accent); padding-left: ${sc(14)}px; color: var(--accent); font-style: italic; font-weight: 700; }
  .md-body blockquote::before { content: "“"; }
  .md-body blockquote::after { content: "”"; }
  .md-body pre { background: var(--ink); color: #e6efe8; border: ${sc(2)}px solid var(--ink); padding: ${sc(12)}px ${sc(14)}px; }
  .md-body code { background: var(--accent-soft); color: var(--accent-deep); padding: .08em .38em; border-radius: 4px; }
  .md-body table { border: ${sc(2)}px solid var(--accent); }
  .md-body th { background: var(--accent); color: #fff; font-weight: 800; letter-spacing: .05em; }
  .md-body td { border-top: 1px solid color-mix(in oklab, var(--accent) 25%, transparent); }
  .md-body li::marker { content: "■ "; font-size: .8em; }
  .md-body p:has(> img.md-image:only-child) { border: ${sc(3)}px solid var(--accent); padding: ${sc(4)}px; }
  .md-body hr { border-top: ${sc(2)}px solid var(--accent); }`;
}

function headerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-header" class="theme-header-prologue">
        <span>PROLOGUE · <span data-chapter-label>${chapter}</span></span><span><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></span>
        <i></i>
      </div>`;
}

function footerHtml(_theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  return `<div id="theme-footer" class="theme-footer-prologue"><strong data-page-num data-page-num-pad>${pad2(pageNum)}</strong></div>`;
}

function chromeCss() {
  return `
  .theme-header-prologue { font-family: var(--sans-cn); font-size: ${sc(10)}px; letter-spacing: .4em; font-weight: 800; display: flex; justify-content: space-between; align-items: baseline; color: var(--accent) !important; }
  .theme-header-prologue i { position: absolute; left: 0; top: ${sc(22)}px; width: ${sc(60)}px; height: ${sc(3)}px; background: var(--accent); display: block; }
  .theme-footer-prologue strong { display: block; font-family: var(--sans-cn); font-size: ${sc(28)}px; line-height: 1; font-weight: 900; color: var(--accent) !important; }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute; inset:0; padding:${coverY(40)}px ${sc(36)}px ${coverY(32)}px; display:flex; flex-direction:column; font-family:var(--sans-cn); color:var(--accent);">
          <div style="font-size:${sc(10)}px;letter-spacing:.5em;font-weight:900;">PROLOGUE</div>
          <div style="width:${sc(80)}px;height:${sc(4)}px;background:var(--accent);margin-top:${coverY(10)}px;"></div>
          ${coverImageSrc ? `<div style="margin-top:${coverY(22)}px;aspect-ratio:16/10;border:${sc(3)}px solid var(--accent);padding:${sc(4)}px;background:var(--paper);">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div style="flex:1;"></div>
          <div class="fit-box" style="width:100%;max-height:${coverImageSrc ? coverY(180) : coverY(300)}px;">
            <h1 class="fit-title" data-min="${sc(18)}" data-max="${coverImageSrc ? sc(28) : sc(40)}" style="line-height:1.2;font-weight:900;color:var(--accent);">${safeTitle}</h1>
          </div>
          <div style="margin-top:${coverY(16)}px;font-size:${sc(11)}px;letter-spacing:.3em;font-weight:700;">— ${chapter} —</div>
          <div style="margin-top:${coverY(18)}px;border-top:${sc(2)}px solid var(--accent);padding-top:${coverY(8)}px;text-align:center;font-size:${sc(10)}px;letter-spacing:.3em;font-weight:800;">FIRST EDITION</div>
        </div>
      </div>`, fontOpts);
}

function altCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#ece7da;">
        <div style="position:absolute;inset:0;padding:${coverY(36)}px ${sc(30)}px ${coverY(30)}px;color:#1a1a1a;font-family:var(--serif-cn);display:flex;flex-direction:column;">
          <div class="fit-box" style="height:${coverY(120)}px;"><h1 class="fit-title" data-min="${sc(18)}" data-max="${sc(30)}" style="line-height:1.05;text-align:center;font-weight:800;">${safeTitle}</h1></div>
          <div style="margin-top:${coverY(18)}px;border:1.5px solid #1a1a1a;aspect-ratio:16/10;display:flex;align-items:center;justify-content:center;overflow:hidden;">${coverImageSrc ? coverImageHtml(coverImageSrc) : `<div style="padding:0 ${sc(18)}px;text-align:center;font-size:${sc(14)}px;line-height:1.5;font-style:italic;">"an honest account, written for those who have known the same."</div>`}</div>
          <p style="margin-top:${coverY(18)}px;font-size:${sc(11.5)}px;line-height:1.65;text-align:justify;">A short prologue, written quietly. ${chapter} — these notes were collected over many evenings, then arranged into the smallest order possible, so that they might find their reader.</p>
          <div style="flex:1;"></div><div style="font-size:${sc(9.5)}px;letter-spacing:.3em;text-align:right;opacity:.6;font-weight:700;">DREX.DSGN</div>
        </div>
      </div>`, fontOpts);
}

export default createThemedTemplate({
  id: "prologue",
  name: "序章手记",
  defaults,
  bodyCss,
  headerHtml,
  footerHtml,
  chromeCss,
  primaryCover,
  altCover,
});
