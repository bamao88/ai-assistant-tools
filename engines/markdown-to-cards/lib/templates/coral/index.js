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
  accent: "oklch(0.68 0.21 22)",
  accentDeep: "oklch(0.58 0.21 22)",
  accentSoft: "color-mix(in oklab, var(--accent) 6%, var(--paper))",
  rule: "color-mix(in oklab, var(--accent) 35%, transparent)",
  paddingH: sc(36),
  contentWidth: sc(348),
  contentTop: sc(78),
  maxContentHeight: sc(432 + EXTRA_BASE_HEIGHT),
  headerTop: sc(40),
  footerBottom: sc(32),
  fontSize: sc(12.5),
  h1Size: sc(24),
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
  .md-body h1 { color: var(--accent); font-size: ${theme.h1Size}px; line-height: 1.45; text-align: center; padding: ${sc(6)}px 0; margin-bottom: ${theme.paraGap}px; font-weight: 700; }
  .md-body h1::before, .md-body h1::after { content: ""; display: block; width: ${sc(24)}px; height: 1px; background: var(--accent); margin: 0 auto ${sc(14)}px; }
  .md-body h1::after { margin: ${sc(14)}px auto 0; }
  .md-body h2 { color: var(--accent); font-size: ${theme.h2Size}px; line-height: 1.45; text-align: center; margin: ${sc(4)}px 0 ${Math.round(theme.paraGap * 0.8)}px; font-weight: 700; }
  .md-body h2::after { content: ""; display: block; width: ${sc(18)}px; height: 1px; background: var(--accent); margin: ${sc(6)}px auto 0; opacity: .5; }
  .md-body h3 { color: var(--accent); font-size: ${theme.h3Size}px; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; font-weight: 700; }
  .md-body p { text-indent: 2em; text-align: justify; color: color-mix(in oklab, var(--ink) 88%, transparent); }
  .md-body blockquote { color: var(--accent); text-align: center; font-style: italic; padding: 0 ${sc(18)}px; }
  .md-body blockquote::before { content: "“"; }
  .md-body blockquote::after { content: "”"; }
  .md-body ul li::marker { content: "•  "; }
  .md-body pre { background: var(--accent-soft); border-top: 1px solid var(--accent); border-bottom: 1px solid var(--accent); padding: ${sc(10)}px ${sc(14)}px; color: color-mix(in oklab, var(--ink) 90%, transparent); }
  .md-body code { background: var(--accent-soft); color: var(--accent-deep); padding: .08em .38em; border-radius: ${sc(3)}px; }
  .md-body table { border-collapse: collapse; font-size: ${theme.tableSize}px; line-height: 1.55; }
  .md-body thead tr, .md-body table { border-top: 1px solid var(--accent); }
  .md-body th { color: var(--accent); font-weight: 700; border-bottom: 1px solid var(--accent); letter-spacing: .15em; font-size: ${sc(10.5)}px; }
  .md-body td { border-bottom: 1px dashed var(--rule); }
  .md-body p:has(> img.md-image:only-child) { border-top: 1px solid var(--accent); border-bottom: 1px solid var(--accent); padding-top: ${sc(10)}px; padding-bottom: ${sc(10)}px; }
  .md-body img.md-image { border-radius: ${sc(4)}px; }
  .md-body hr { border-top: 1px solid var(--rule); }`;
}

function headerHtml(_theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  return `<div id="theme-header" class="theme-header-coral">
        <div class="coral-page" data-page-num>${pad2(pageNum)}</div><div class="coral-rule"></div>
      </div>`;
}

function footerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-footer" class="theme-footer-coral"><span data-chapter-label>${chapter}</span><strong><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></strong></div>`;
}

function chromeCss() {
  return `
  .theme-header-coral { display: flex; flex-direction: column; align-items: center; gap: ${sc(8)}px; font-family: var(--serif-cn); color: var(--accent) !important; }
  .coral-page { font-size: ${sc(10)}px; letter-spacing: .4em; font-weight: 700; }
  .coral-rule { width: ${sc(22)}px; height: 1px; background: var(--accent); opacity: .5; }
  .theme-footer-coral { display: flex; justify-content: space-between; align-items: end; font-family: var(--serif-cn); font-size: ${sc(10)}px; color: var(--accent) !important; }
  .theme-footer-coral span:first-child { letter-spacing: .2em; }
  .theme-footer-coral strong { font-size: ${sc(13)}px; letter-spacing: 0; }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute; inset:0; padding:${coverY(60)}px ${sc(44)}px ${coverY(48)}px; display:flex; flex-direction:column; align-items:center; font-family:var(--serif-cn); color:var(--accent);">
          <div style="font-size:${sc(10)}px; letter-spacing:.5em; font-weight:700;">${chapter}</div>
          <div style="width:${sc(30)}px;height:1px;background:var(--accent);margin-top:${coverY(14)}px;margin-bottom:${coverY(22)}px;"></div>
          ${coverImageSrc ? `<div style="width:100%; border-top:1px solid var(--accent); border-bottom:1px solid var(--accent); padding:${coverY(10)}px 0; margin-bottom:${coverY(26)}px; aspect-ratio:4/3;">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div class="fit-box" style="flex:1; width:100%; display:flex; align-items:center; justify-content:center;">
            <h1 class="fit-title" data-min="${sc(16)}" data-max="${coverImageSrc ? sc(22) : sc(30)}" style="text-align:center; line-height:${coverImageSrc ? "1.5" : "1.45"}; color:var(--ink); font-weight:700;">${safeTitle}</h1>
          </div>
          <div style="width:${sc(30)}px;height:1px;background:var(--accent);"></div>
        </div>
      </div>`, fontOpts);
}

function altCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  const titleTag = escapeHtml((title.match(/[\u4e00-\u9fa5A-Za-z0-9]+/)?.[0] || "card").toUpperCase());
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="height:${coverImageSrc ? "58%" : "62%"}; background:var(--accent); position:relative; overflow:hidden;">
          ${coverImageSrc ? coverImageHtml(coverImageSrc) : `<div style="position:absolute;inset:0;background:radial-gradient(120% 90% at 50% 100%, #ffb5a9 0%, var(--accent) 68%);"></div>`}
          <div style="position:absolute;top:${coverY(22)}px;left:${sc(22)}px;color:white;font-size:${sc(10)}px;letter-spacing:.4em;font-weight:700;">№ ${chapter}</div>
        </div>
        <div style="height:${coverImageSrc ? "42%" : "38%"}; padding:${coverY(26)}px ${sc(28)}px ${coverY(24)}px; display:flex; flex-direction:column; font-family:var(--serif-cn);">
          <div class="fit-box" style="height:${coverY(132)}px;"><h1 class="fit-title" data-min="${sc(16)}" data-max="${sc(22)}" style="line-height:1.45;font-weight:700;color:var(--ink);">${safeTitle}</h1></div>
          <div style="margin-top:${coverY(8)}px;color:var(--accent);font-size:${sc(11)}px;font-weight:700;letter-spacing:.05em;">#${titleTag}</div>
          <div style="flex:1;"></div><div style="display:flex;justify-content:space-between;align-items:end;font-size:${sc(10)}px;color:var(--muted);letter-spacing:.2em;"><span>${chapter} · CARDS</span><span style="width:${sc(22)}px;height:${sc(22)}px;border:1px solid var(--accent);border-radius:999px;color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:${sc(10)}px;font-weight:800;">※</span></div>
        </div>
      </div>`, fontOpts);
}

export default createThemedTemplate({
  id: "coral",
  name: "珊瑚极简",
  defaults,
  bodyCss,
  headerHtml,
  footerHtml,
  chromeCss,
  primaryCover,
  altCover,
});
