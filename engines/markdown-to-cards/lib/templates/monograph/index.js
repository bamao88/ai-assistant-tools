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
  paper: "#ffffff",
  ink: "#111111",
  muted: "#555555",
  accent: "#111111",
  accentDeep: "#000000",
  accentSoft: "#f1f1f1",
  rule: "#111111",
  paddingH: sc(44),
  contentWidth: sc(332),
  contentTop: sc(94),
  maxContentHeight: sc(360 + EXTRA_BASE_HEIGHT),
  headerTop: sc(44),
  footerBottom: sc(32),
  fontSize: sc(12.5),
  h1Size: sc(20),
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
  #capture-body.md-body { display: flex; flex-direction: column; justify-content: flex-end; }
  .md-body h1 { font-size: ${theme.h1Size}px; line-height: 1.55; text-align: center; letter-spacing: .04em; font-weight: 500; padding: ${sc(8)}px 0 ${sc(6)}px; margin-bottom: ${theme.paraGap}px; }
  .md-body h2 { font-size: ${theme.h2Size}px; line-height: 1.55; letter-spacing: .03em; margin-top: ${sc(4)}px; margin-bottom: ${Math.round(theme.paraGap * 0.75)}px; font-weight: 600; }
  .md-body h3 { font-size: ${theme.h3Size}px; letter-spacing: .02em; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; font-weight: 600; }
  .md-body p { text-indent: 2em; text-align: justify; color: #111; }
  .md-body blockquote { padding: 0 ${sc(22)}px; color: #333; font-style: italic; text-align: justify; }
  .md-body ul li::marker { content: "·  "; }
  .md-body pre { border-top: 1px solid #111; border-bottom: 1px solid #111; padding: ${sc(10)}px 0; color: #111; background: transparent; }
  .md-body code { background: #f1f1f1; color: #111; padding: .08em .38em; border-radius: 2px; }
  .md-body table { border-top: 1.5px solid #111; border-bottom: 1.5px solid #111; font-family: var(--serif-cn); line-height: 1.6; }
  .md-body th { border-bottom: .5px solid #111; font-weight: 600; }
  .md-body p:has(> img.md-image:only-child) { padding: 0; background: transparent; }
  .md-body img.md-image { filter: grayscale(1); }
  .md-body hr { border-top: .5px solid #111; }`;
}

function headerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-header" class="theme-header-monograph">
        <span data-page-num>${pageNum}</span><span data-chapter-label>${chapter}</span>
      </div>`;
}

function footerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-footer" class="theme-footer-monograph"><i></i><div><span data-chapter-label>${chapter}</span><strong><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></strong></div></div>`;
}

function chromeCss() {
  return `
  .theme-header-monograph {
    font-family: var(--serif-cn); color: #111 !important;
    display: flex; justify-content: space-between; align-items: baseline;
  }
  .theme-header-monograph span:first-child {
    font-size: ${sc(22)}px; font-weight: 500; line-height: 1; letter-spacing: .05em;
  }
  .theme-header-monograph span:last-child {
    font-size: ${sc(12)}px; font-weight: 500; letter-spacing: .08em;
  }
  .theme-footer-monograph { font-family: var(--serif-cn); color: #222 !important; }
  .theme-footer-monograph i {
    display: block; height: 1px; background: #111; opacity: .45; margin-bottom: ${sc(8)}px;
  }
  .theme-footer-monograph div {
    display: flex; justify-content: space-between; align-items: baseline;
    font-size: ${sc(10)}px;
  }
  .theme-footer-monograph div > span { letter-spacing: .08em; }
  .theme-footer-monograph strong { font-weight: 600; }`;
}

function primaryCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  return coverDoc(cfg, theme, `<div id="cover-page">
        <div style="position:absolute; inset:0; padding:${coverImageSrc ? `${coverY(44)}px ${sc(36)}px ${coverY(40)}px` : `${coverY(70)}px ${sc(36)}px ${coverY(40)}px`}; display:flex; flex-direction:column; align-items:center; font-family:var(--serif-cn); color:#111;">
          <div style="width:1px;height:${coverY(38)}px;background:#111;"></div>
          ${coverImageSrc ? `<div style="width:100%; aspect-ratio:4/3; margin-top:${coverY(28)}px; filter:grayscale(1);">${coverImageHtml(coverImageSrc)}</div>` : ""}
          <div class="fit-box" style="width:100%;${coverImageSrc ? `margin-top:${coverY(24)}px;` : `margin-top:${coverY(38)}px;`}flex:1;display:flex;align-items:${coverImageSrc ? "start" : "center"};justify-content:center;">
            <h1 class="fit-title" data-min="${sc(15)}" data-max="${coverImageSrc ? sc(19) : sc(22)}" style="text-align:center;line-height:1.55;font-weight:500;letter-spacing:.05em;">${safeTitle}</h1>
          </div>
          <div style="width:100%;border-top:.5px solid #111;padding-top:${coverY(8)}px;display:flex;flex-direction:column;align-items:center;gap:${coverY(4)}px;">
            <span style="font-size:${sc(13)}px;font-weight:600;">—</span>
            <span style="font-size:${sc(10.5)}px;color:#333;letter-spacing:.05em;">${chapter}</span>
          </div>
        </div>
      </div>`, fontOpts);
}

function altCover({ title, cfg, theme, coverImageSrc, fontOpts }) {
  const chapter = escapeHtml(theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  const safeTitle = escapeHtml(title);
  const year = new Date().getFullYear();
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#f3f0e6;color:#111;">
        <div style="height:32%;"></div>
        <div style="display:flex;justify-content:space-between;padding:0 ${sc(22)}px;font-family:var(--mono);font-size:${sc(9.5)}px;line-height:1.45;letter-spacing:.05em;">
          <div>NIKON F3 HP<br>NIKKOR 50MM<br>ILFORD HP5</div><div style="background:#111;color:#f3f0e6;padding:${sc(3)}px ${sc(7)}px;font-weight:700;">MONO<br>CHROME</div><div style="text-align:right;">${chapter.toUpperCase()}<br>SHANGHAI, CN<br>${year}</div>
        </div>
        <div style="position:absolute;left:0;right:0;bottom:0;height:56%;background:${coverImageSrc ? "#222" : "#dcd6c5"};overflow:hidden;">${coverImageSrc ? coverImageHtml(coverImageSrc) : ""}
          ${coverImageSrc ? `<div style="position:absolute;left:0;right:0;bottom:0;height:45%;background:linear-gradient(to top, rgba(0,0,0,.72), rgba(0,0,0,0));"></div>` : ""}
          <div class="fit-box" style="position:absolute;left:${sc(22)}px;bottom:${coverY(18)}px;width:76%;height:${coverY(128)}px;"><h1 class="fit-title" data-min="${sc(14)}" data-max="${sc(17)}" style="line-height:1.4;font-family:var(--serif-cn);font-weight:500;color:${coverImageSrc ? "white" : "#111"};text-shadow:${coverImageSrc ? "0 2px 10px rgba(0,0,0,.35)" : "none"};">${safeTitle}</h1></div>
        </div>
      </div>`, fontOpts);
}

export default createThemedTemplate({
  id: "monograph",
  name: "黑白书页",
  defaults,
  bodyCss,
  headerHtml,
  footerHtml,
  chromeCss,
  primaryCover,
  altCover,
});
