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
  accentSoft: "color-mix(in oklab, var(--accent) 8%, var(--paper))",
  rule: "var(--ink)",
  paddingH: sc(36),
  contentWidth: sc(348),
  contentTop: sc(84),
  maxContentHeight: sc(408 + EXTRA_BASE_HEIGHT),
  headerTop: sc(36),
  footerBottom: sc(28),
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
  .md-body h1 { font-size: ${theme.h1Size}px; line-height: 1.4; font-weight: 700; margin-bottom: ${theme.paraGap}px; }
  .md-body h1::after { content: ""; display: block; width: ${sc(60)}px; height: ${sc(2)}px; background: var(--accent); margin-top: ${sc(10)}px; }
  .md-body h2 { color: var(--accent); font-size: ${theme.h2Size}px; line-height: 1.5; margin-bottom: ${Math.round(theme.paraGap * 0.8)}px; font-weight: 700; }
  .md-body h3 { font-size: ${theme.h3Size}px; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; font-weight: 700; }
  .md-body p { text-indent: 0; text-align: justify; }
  .md-body blockquote { border-left: ${sc(3)}px solid var(--accent); padding-left: ${sc(14)}px; color: var(--accent); font-style: italic; font-weight: 600; }
  .md-body ul li::marker { content: "—  "; }
  .md-body ol { list-style: decimal-leading-zero; }
  .md-body pre { background: var(--ink); color: #f5f5f0; padding: ${sc(12)}px ${sc(14)}px; border-radius: 0; position: relative; }
  .md-body code { background: #f2e9df; color: var(--ink); padding: .08em .38em; border-radius: 3px; }
  .md-body table { border-top: ${sc(2)}px solid var(--ink); border-bottom: ${sc(2)}px solid var(--ink); }
  .md-body th { border-bottom: ${sc(2)}px solid var(--accent); font-weight: 800; }
  .md-body td { border-bottom: 1px solid color-mix(in oklab, var(--ink) 15%, transparent); }
  .md-body p:has(> img.md-image:only-child) { background: var(--paper); border: 1px solid var(--ink); box-shadow: ${sc(4)}px ${sc(4)}px 0 var(--accent); padding: ${sc(8)}px; }
  .md-body img.md-image { filter: contrast(1.03); }
  .md-body hr { border-top: ${sc(2)}px solid var(--accent); }`;
}

function headerHtml(_theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  return `<div id="theme-header" class="theme-header-editorial">
        <span data-page-num>${pageNum}</span><span class="editorial-line"></span><span>/ <span data-page-total data-page-total-pad>${pad2(total)}</span></span>
      </div>`;
}

function footerHtml(theme, meta) {
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-footer" class="theme-footer-editorial"><span data-chapter-label>${chapter}</span><i></i></div>`;
}

function chromeCss() {
  return `
  .theme-header-editorial { display: flex; align-items: center; gap: ${sc(12)}px; font-family: var(--serif-cn); font-weight: 800; color: var(--accent) !important; }
  .theme-header-editorial > span:first-child { font-size: ${sc(30)}px; font-style: italic; line-height: 1; }
  .editorial-line { flex: 1; height: ${sc(2)}px; background: var(--accent); }
  .theme-header-editorial > span:last-child { font-size: ${sc(10)}px; letter-spacing: .3em; }
  .theme-footer-editorial { display: flex; align-items: center; justify-content: space-between; font-family: var(--serif-cn); font-size: ${sc(10)}px; letter-spacing: .25em; font-weight: 700; color: var(--accent) !important; }
  .theme-footer-editorial i { display: block; width: ${sc(30)}px; height: ${sc(2)}px; background: var(--accent); }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute; inset:0; padding:${coverY(36)}px ${sc(36)}px ${coverY(28)}px; display:flex; flex-direction:column; font-family:var(--serif-cn);">
          <div style="display:flex; align-items:center; gap:${sc(12)}px;"><span style="color:var(--accent); font-weight:900; font-style:italic; font-size:${sc(18)}px; letter-spacing:.2em;">FEATURE</span><i style="flex:1;height:${sc(3)}px;background:var(--accent);"></i></div>
          ${coverImageSrc ? `<div style="margin-top:${coverY(22)}px; aspect-ratio:16/10; border:1px solid var(--ink); box-shadow:${sc(5)}px ${coverY(5)}px 0 var(--accent);">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div style="flex:1;"></div>
          <div class="fit-box" style="width:100%; max-height:${coverImageSrc ? coverY(130) : coverY(250)}px;">
            <h1 class="fit-title" data-min="${sc(18)}" data-max="${coverImageSrc ? sc(26) : sc(40)}" style="line-height:1.15; font-weight:900; color:var(--ink);">${safeTitle}</h1>
          </div>
          <div style="width:${sc(60)}px;height:${sc(3)}px;background:var(--accent);margin-top:${coverY(14)}px;"></div>
          <div style="margin-top:${coverY(10)}px;font-size:${sc(10)}px;letter-spacing:.3em;font-weight:800;">${chapter}</div>
        </div>
      </div>`, fontOpts);
}

function altCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#f3c61f;">
        <div style="position:absolute;inset:0;padding:${coverY(24)}px ${sc(26)}px ${coverY(26)}px;color:var(--ink);font-family:var(--serif-cn);display:flex;flex-direction:column;">
          <div style="display:flex;justify-content:space-between;align-items:start;"><div><div style="font-size:${sc(26)}px;font-weight:900;line-height:1;">${chapter.slice(0, 10).toUpperCase()}</div><div style="margin-top:${coverY(6)}px;font-size:${sc(9)}px;line-height:1.4;max-width:${sc(180)}px;">Magazine for notes, systems and slow reading</div></div><div style="font-family:var(--mono);font-size:${sc(7)}px;text-align:right;">|||| ||| ||||<br>9 771234 567890</div></div>
          <div style="flex:1;"></div>
          ${coverImageSrc ? `<div style="width:70%;aspect-ratio:4/5;margin-left:10%;margin-bottom:${coverY(6)}px;background:#ddd;">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div class="fit-box" style="height:${coverImageSrc ? coverY(76) : coverY(210)}px;"><h1 class="fit-title" data-min="${coverImageSrc ? sc(10) : sc(18)}" data-max="${coverImageSrc ? sc(13) : sc(36)}" style="line-height:1.05;font-weight:900;letter-spacing:0;">${safeTitle}</h1></div>
        </div>
      </div>`, fontOpts);
}

export default createThemedTemplate({
  id: "editorial",
  name: "编辑部",
  defaults,
  bodyCss,
  headerHtml,
  footerHtml,
  chromeCss,
  primaryCover,
  altCover,
});
