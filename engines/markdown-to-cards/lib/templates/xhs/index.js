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

const DEFAULT_EXCERPT = "测试小红书长文排版模板，优化封面设计与标题层级，提升内容呈现效果。";

const baseDefaults = {
  font: "xhsSans",
  sansFont: "'PingFang SC', 'Hiragino Sans GB', 'Noto Sans SC', sans-serif",
  serifFont: "'Songti SC', 'STSong', 'Noto Serif SC', serif",
  paper: "#fbfaf7",
  ink: "#202124",
  muted: "#6b7280",
  accent: "#e33b33",
  accentDeep: "#b91c1c",
  accentSoft: "rgba(227,59,51,0.08)",
  rule: "rgba(17,24,39,0.12)",
  paddingH: sc(36),
  contentWidth: sc(348),
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

const specs = [
  { id: "xhs-rational-modern", name: "理性现代", mode: "rational", accent: "#d61f1f", accent2: "#111827", paper: "#ffffff", ink: "#1f2937" },
  { id: "xhs-logic-structure", name: "逻辑结构", mode: "logic", accent: "#d11b1b", accent2: "#f9e4e3", paper: "#fffafa", ink: "#242424" },
  { id: "xhs-plain-texture", name: "素雅底纹", mode: "texture", accent: "#1aa76d", accent2: "#dcefe7", paper: "#fbfdfa", ink: "#24342d" },
  { id: "xhs-magazine-vanguard", name: "杂志先锋", mode: "magazine", accent: "#18c978", accent2: "#ff7b2f", paper: "#ffffff", ink: "#222222" },
  { id: "xhs-cross-topology", name: "交叉拓扑", mode: "topology", accent: "#38bdf8", accent2: "#d6f75b", paper: "#ffffff", ink: "#2d2f35" },
  { id: "xhs-mono-minimal", name: "黑白极简", mode: "mono", accent: "#a15d2d", accent2: "#e5d8c9", paper: "#fffaf4", ink: "#3a2a21" },
  { id: "xhs-clear-bright", name: "清晰明朗", mode: "clear", accent: "#111827", accent2: "#e8ece6", paper: "#ffffff", ink: "#1f2937" },
  { id: "xhs-dusty-notes", name: "札记集尘", mode: "notes", accent: "#ffffff", accent2: "#b8121d", paper: "#b8121d", ink: "#ffffff" },
  { id: "xhs-simple-basic", name: "简约基础", mode: "basic", accent: "#222222", accent2: "#efede8", paper: "#ffffff", ink: "#222222" },
  { id: "xhs-elegant-geometry", name: "优雅几何", mode: "geometry", accent: "#5ef089", accent2: "#1d372d", paper: "#ffffff", ink: "#1f2937" },
  { id: "xhs-inspiration-memo", name: "灵感备忘", mode: "memo", accent: "#f3b316", accent2: "#fffbeb", paper: "#fffdf6", ink: "#374151" },
  { id: "xhs-plain-narrative", name: "平实叙事", mode: "narrative", accent: "#26c6e7", accent2: "#1f2937", paper: "#f5f5f5", ink: "#1f2937" },
  { id: "xhs-dusk-manuscript", name: "黄昏手稿", mode: "dusk", accent: "#2d2a25", accent2: "#eadcc3", paper: "#f3ead8", ink: "#2d2a25" },
  { id: "xhs-literary-fresh", name: "文艺清新", mode: "literary", accent: "#8c5a2e", accent2: "#f7f5f2", paper: "#fffdfb", ink: "#3f3127" },
  { id: "xhs-handbook", name: "手帐书写", mode: "handbook", accent: "#b39a79", accent2: "#eaf5ee", paper: "#f9f4eb", ink: "#2d2a26" },
  { id: "xhs-retro-lines", name: "线条复古", mode: "retro", accent: "#d9ed46", accent2: "#d8d8d8", paper: "#f5f6f2", ink: "#111827" },
  { id: "xhs-color-block", name: "拼接色块", mode: "block", accent: "#efe7c7", accent2: "#f5e58b", paper: "#fffdf4", ink: "#111827" },
  { id: "xhs-light-bright", name: "轻感明快", mode: "quote", accent: "#ff7a2f", accent2: "#fff58a", paper: "#fffefa", ink: "#8a4a1f" },
  { id: "xhs-photo-feature", name: "大图纯享", mode: "photo", accent: "#ffffff", accent2: "#f7c0b6", paper: "#f8fafc", ink: "#ffffff" },
  { id: "xhs-doodle-marker", name: "涂鸦马克", mode: "doodle", accent: "#d93b9f", accent2: "#f8b7df", paper: "#fff4fb", ink: "#5b1741" },
];

function defaultsFor(spec) {
  return {
    ...baseDefaults,
    paper: spec.paper,
    ink: spec.ink,
    accent: spec.accent,
    accentDeep: spec.accent,
    accentSoft: `color-mix(in oklab, ${spec.accent} 10%, ${spec.paper})`,
    rule: `color-mix(in oklab, ${spec.ink} 15%, transparent)`,
    xhsMode: spec.mode,
    xhsAccent2: spec.accent2,
  };
}

function bodyCss(theme) {
  return `
  .md-body { font-family: var(--sans-cn); }
  .md-body h1 {
    font-size: ${theme.h1Size}px; line-height: 1.35; font-weight: 800;
    margin-bottom: ${theme.paraGap}px; color: var(--ink);
  }
  .md-body h1::after { content: ""; display: block; width: ${sc(42)}px; height: ${sc(3)}px; background: var(--accent); margin-top: ${sc(10)}px; }
  .md-body h2 { color: var(--accent); font-size: ${theme.h2Size}px; line-height: 1.45; margin-bottom: ${Math.round(theme.paraGap * 0.8)}px; font-weight: 800; }
  .md-body h3 { font-size: ${theme.h3Size}px; line-height: 1.45; margin-bottom: ${Math.round(theme.paraGap * 0.55)}px; font-weight: 700; }
  .md-body p { text-align: justify; }
  .md-body blockquote { border-left: ${sc(4)}px solid var(--accent); padding: ${sc(10)}px ${sc(14)}px; background: var(--accent-soft); color: var(--muted); }
  .md-body pre { background: color-mix(in oklab, var(--ink) 92%, #000); color: #f8fafc; border-radius: ${sc(6)}px; padding: ${sc(12)}px ${sc(14)}px; }
  .md-body code { background: var(--accent-soft); color: var(--accent-deep); padding: .08em .38em; border-radius: ${sc(3)}px; }
  .md-body table { border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }
  .md-body th { color: var(--ink); font-weight: 800; border-bottom: 1px solid var(--rule); }
  .md-body td { border-bottom: 1px dashed var(--rule); }
  .md-body p:has(> img.md-image:only-child) { padding: ${sc(5)}px; border: 1px solid var(--rule); border-radius: ${sc(8)}px; }
  .md-body img.md-image { border-radius: ${sc(7)}px; }`;
}

function headerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const chapter = escapeHtml(meta.chapterLabel || theme.chapterLabel || DEFAULT_CHAPTER_LABEL);
  return `<div id="theme-header" class="theme-header-xhs"><span data-chapter-label>${chapter}</span><i></i><span data-page-num>${pad2(pageNum)}</span></div>`;
}

function footerHtml(theme, meta) {
  const pageNum = meta.pageNum ?? 1;
  const total = meta.totalPages ?? 1;
  return `<div id="theme-footer" class="theme-footer-xhs"><span>${escapeHtml(theme.name)}</span><strong><span data-page-num>${pageNum}</span> / <span data-page-total>${total}</span></strong></div>`;
}

function chromeCss() {
  return `
  .theme-header-xhs {
    display: flex; align-items: center; gap: ${sc(10)}px; color: var(--accent) !important;
    font-family: var(--sans-cn); font-size: ${sc(10)}px; letter-spacing: .14em; font-weight: 800;
  }
  .theme-header-xhs i { flex: 1; height: 1px; background: var(--rule); }
  .theme-footer-xhs {
    display: flex; justify-content: space-between; align-items: baseline; color: var(--muted) !important;
    font-family: var(--sans-cn); font-size: ${sc(10)}px; letter-spacing: .12em;
  }
  .theme-footer-xhs strong { color: var(--accent); letter-spacing: 0; font-size: ${sc(12)}px; }`;
}

function commonCoverCss() {
  return `
  #cover-page { border: 1px solid rgba(17,24,39,.12); }
  .xhs-title { letter-spacing: 0; word-break: normal; overflow-wrap: anywhere; }
  .xhs-summary {
    font-family: var(--sans-cn); font-size: ${sc(13)}px; line-height: 1.72;
    font-weight: 500; letter-spacing: 0; word-break: normal; overflow-wrap: anywhere;
  }
  .xhs-kicker { font-family: var(--sans-cn); font-size: ${sc(9)}px; letter-spacing: .08em; font-weight: 700; }
  .xhs-art, .xhs-photo { overflow: hidden; }
  .xhs-art svg { display: block; width: 100%; height: 100%; }
  .xhs-lines i { display:block; height:1px; background: currentColor; opacity:.25; margin-bottom:${coverY(9)}px; }
  .xhs-dots {
    background-image: radial-gradient(rgba(245,158,11,.2) 1px, transparent 1px);
    background-size: ${sc(18)}px ${coverY(18)}px;
  }
  .xhs-paper {
    background-image:
      linear-gradient(90deg, rgba(0,0,0,.025) 1px, transparent 1px),
      linear-gradient(rgba(0,0,0,.02) 1px, transparent 1px);
    background-size: ${sc(28)}px ${coverY(28)}px;
  }`;
}

function withCss(fontOpts = {}, css = "") {
  return { ...fontOpts, css: `${fontOpts.css || ""}${commonCoverCss()}${css}` };
}

function cleanTitle(title) {
  return String(title || "").trim() || "小红书长文";
}

function brokenTitleHtml(title) {
  const raw = cleanTitle(title).replace(/\s+/g, "");
  const chars = Array.from(raw);
  const cjkCount = chars.filter((char) => /[\u3400-\u9fff]/u.test(char)).length;
  if (chars.length < 7 || cjkCount < chars.length * 0.65) return escapeHtml(cleanTitle(title));

  let lineSizes;
  if (chars.length <= 12) lineSizes = [5, chars.length - 5];
  else if (chars.length <= 18) lineSizes = [6, 6, chars.length - 12];
  else lineSizes = [6, 6, 6, chars.length - 18];

  const lines = [];
  let offset = 0;
  for (const size of lineSizes) {
    if (size <= 0) continue;
    const line = chars.slice(offset, offset + size).join("");
    if (line) lines.push(line);
    offset += size;
  }
  if (offset < chars.length) lines.push(chars.slice(offset).join(""));
  return lines.map(escapeHtml).join("<br>");
}

function cleanExcerpt(value, maxLength = 128) {
  const text = String(value || DEFAULT_EXCERPT).replace(/\s+/g, " ").trim();
  const finalText = text || DEFAULT_EXCERPT;
  return finalText.length > maxLength ? `${finalText.slice(0, maxLength - 1)}…` : finalText;
}

function titleHtml(title, min, max, style = "") {
  return `<h1 class="fit-title xhs-title" data-min="${sc(min)}" data-max="${sc(max)}" style="margin:0;${style}">${brokenTitleHtml(title)}</h1>`;
}

function summaryHtml(excerpt, style = "", maxLength = 128) {
  return `<p class="xhs-summary" style="margin:0;${style}">${escapeHtml(cleanExcerpt(excerpt, maxLength))}</p>`;
}

function lineStack(widths, color = "currentColor") {
  return `<div class="xhs-lines" style="color:${color};">${widths.map((w) => `<i style="width:${sc(w)}px;"></i>`).join("")}</div>`;
}

function photoOr(src, fallbackClass = "") {
  if (src) return coverImageHtml(src);
  return `<div class="xhs-photo ${fallbackClass}" style="width:100%;height:100%;"></div>`;
}

function studyArt() {
  return `<svg viewBox="0 0 320 260" role="img" aria-hidden="true">
    <rect x="18" y="178" width="100" height="64" rx="22" fill="#38c66b"/>
    <path d="M34 60h66l10 66H44z" fill="#fff" stroke="#111" stroke-width="3"/>
    <path d="M52 86h36M52 106h42M52 126h28" stroke="#111" stroke-width="3"/>
    <circle cx="65" cy="107" r="5" fill="#f59e0b"/>
    <path d="M212 54h72l-8 76h-76z" fill="#fff" stroke="#111" stroke-width="3"/>
    <path d="M222 82h36M220 103h42M218 124h31" stroke="#111" stroke-width="3"/>
    <rect x="238" y="44" width="38" height="14" fill="#ffcc3d"/>
    <circle cx="154" cy="110" r="32" fill="#fff" stroke="#111" stroke-width="4"/>
    <path d="M126 107c11-26 45-28 61-8" fill="none" stroke="#111" stroke-width="5"/>
    <path d="M139 116c14 12 31 13 45 0" fill="none" stroke="#111" stroke-width="4"/>
    <path d="M116 229c12-58 32-88 58-88s47 30 62 88" fill="#fff" stroke="#111" stroke-width="4"/>
    <path d="M122 178l58 26 42-48" fill="none" stroke="#111" stroke-width="5"/>
    <path d="M172 173l43-24 18 44-54 25z" fill="#ffcd45" stroke="#111" stroke-width="3"/>
    <rect x="228" y="166" width="66" height="58" rx="5" fill="#f5f5f5" stroke="#111" stroke-width="4"/>
    <path d="M241 201h40" stroke="#111" stroke-width="4"/>
  </svg>`;
}

function phoneArt() {
  return `<svg viewBox="0 0 340 220" role="img" aria-hidden="true">
    <defs>
      <linearGradient id="xhs-phone-bg" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#d9a46d"/><stop offset="1" stop-color="#214033"/></linearGradient>
    </defs>
    <rect width="340" height="220" fill="url(#xhs-phone-bg)"/>
    <path d="M172 60c44 18 78 56 84 102" fill="none" stroke="#2b201a" stroke-width="18" opacity=".35"/>
    <path d="M112 118c52-48 110-50 174-16" fill="none" stroke="#f0c08a" stroke-width="30" stroke-linecap="round"/>
    <rect x="113" y="44" width="82" height="140" rx="13" fill="#f7f0e3" stroke="#1f2937" stroke-width="5" transform="rotate(-12 154 114)"/>
    <path d="M130 78h45M128 100h38M126 122h45M124 144h32" stroke="#1f2937" stroke-width="4" opacity=".7"/>
    <circle cx="175" cy="157" r="6" fill="#ef4444"/>
    <path d="M222 58c28 23 39 55 28 94" fill="none" stroke="#201b16" stroke-width="10" opacity=".42"/>
  </svg>`;
}

function openBookArt() {
  return `<svg viewBox="0 0 320 220" role="img" aria-hidden="true">
    <path d="M34 74c54-27 91-16 126 12v96c-38-28-79-35-126-9z" fill="#fff" stroke="#111827" stroke-width="5"/>
    <path d="M160 86c39-28 78-39 126-12v99c-46-26-87-19-126 9z" fill="#fff" stroke="#111827" stroke-width="5"/>
    <path d="M160 86v96" stroke="#111827" stroke-width="5"/>
    <path d="M61 101h62M60 123h70M60 145h55M191 101h56M189 123h68M188 145h48" stroke="#9ca3af" stroke-width="5"/>
    <path d="M72 132h45M198 133h48" stroke="#f5b82e" stroke-width="6"/>
    <rect x="60" y="118" width="54" height="76" rx="8" fill="#3b82f6" stroke="#111827" stroke-width="5"/>
    <rect x="70" y="131" width="34" height="42" fill="#e9f4ff"/>
    <circle cx="87" cy="152" r="11" fill="#f6c29f"/>
    <path d="M73 187h28" stroke="#fff" stroke-width="4"/>
  </svg>`;
}

function handbookArt(src) {
  if (src) return coverImageHtml(src);
  return `<div style="position:relative;width:100%;height:100%;background:#e6efe8;border:${sc(2)}px solid #d5dfd8;">
    <div style="position:absolute;left:${sc(18)}px;top:${coverY(18)}px;right:${sc(18)}px;height:${coverY(154)}px;background:linear-gradient(145deg,#96b5bb,#f9fafb);box-shadow:0 ${coverY(4)}px ${coverY(10)}px rgba(0,0,0,.14);"></div>
    <div style="position:absolute;left:${sc(44)}px;right:${sc(44)}px;bottom:${coverY(30)}px;height:${coverY(58)}px;background:#d8edf0;border:1px solid #b7cfd2;"></div>
    <div style="position:absolute;right:${sc(18)}px;top:${coverY(124)}px;width:${sc(44)}px;height:${coverY(44)}px;border-radius:999px;background:#f1c74b;color:white;display:flex;align-items:center;justify-content:center;font-weight:900;">Y</div>
  </div>`;
}

function deskArt(src) {
  if (src) return coverImageHtml(src);
  return `<div style="position:relative;width:100%;height:100%;background:#f1f1ed;">
    <div style="position:absolute;left:${sc(35)}px;top:${coverY(70)}px;width:${sc(165)}px;height:${coverY(110)}px;background:#fff;box-shadow:0 ${coverY(8)}px ${coverY(16)}px rgba(0,0,0,.14);transform:rotate(-8deg);"></div>
    <div style="position:absolute;left:${sc(120)}px;top:${coverY(52)}px;width:${sc(155)}px;height:${coverY(104)}px;background:#f9fafb;box-shadow:0 ${coverY(8)}px ${coverY(16)}px rgba(0,0,0,.12);transform:rotate(8deg);"></div>
    <div style="position:absolute;right:${sc(34)}px;bottom:${coverY(28)}px;width:${sc(86)}px;height:${coverY(86)}px;border-radius:999px;background:#dccb92;"></div>
  </div>`;
}

function softScene(src) {
  if (src) return coverImageHtml(src);
  return `<svg viewBox="0 0 360 520" role="img" aria-hidden="true">
    <defs>
      <linearGradient id="xhs-scene" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#ffd7ce"/><stop offset=".62" stop-color="#f5b7aa"/><stop offset="1" stop-color="#916f61"/></linearGradient>
    </defs>
    <rect width="360" height="520" fill="url(#xhs-scene)"/>
    <circle cx="70" cy="420" r="58" fill="#e87991" opacity=".45"/>
    <circle cx="308" cy="410" r="64" fill="#f7a8a8" opacity=".48"/>
    <path d="M0 380c92-54 167-42 360-74v214H0z" fill="#70564b" opacity=".65"/>
    <path d="M146 260c17-34 51-35 67 0v96h-67z" fill="#7c4a3b"/>
    <circle cx="179" cy="231" r="29" fill="#2f2b2a"/>
    <path d="M214 281c22 32 39 55 61 74" stroke="#4d4038" stroke-width="12" stroke-linecap="round"/>
    <path d="M146 280c-22 33-41 58-69 84" stroke="#4d4038" stroke-width="12" stroke-linecap="round"/>
  </svg>`;
}

function bookPhoto(src) {
  if (src) return coverImageHtml(src);
  return `<div style="position:relative;width:100%;height:100%;background:linear-gradient(135deg,#e8e1d0,#f7f6f1 52%,#cbbd9d);">
    <div style="position:absolute;left:${sc(30)}px;right:${sc(35)}px;top:${coverY(36)}px;height:${coverY(150)}px;background:#efe7d3;box-shadow:${sc(26)}px ${coverY(20)}px ${coverY(32)}px rgba(0,0,0,.22);"></div>
    <div style="position:absolute;left:${sc(72)}px;top:${coverY(48)}px;width:${sc(95)}px;height:${coverY(126)}px;background:#f9f6e9;border-left:1px solid #cbbd9d;"></div>
    <div style="position:absolute;left:${sc(172)}px;top:${coverY(48)}px;width:${sc(95)}px;height:${coverY(126)}px;background:#fffaf0;border-left:1px solid #cbbd9d;"></div>
    <div style="position:absolute;left:${sc(82)}px;right:${sc(76)}px;bottom:${coverY(36)}px;height:${coverY(80)}px;background:rgba(255,255,255,.55);"></div>
  </div>`;
}

function rationalCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fff;">
    <div style="position:absolute;left:${sc(34)}px;right:${sc(34)}px;top:${coverY(92)}px;height:${coverY(180)}px;" class="fit-box">
      ${titleHtml(title, 30, 44, "font-weight:900;line-height:1.18;color:#202124;")}
    </div>
    <div class="xhs-art" style="position:absolute;left:${sc(36)}px;right:${sc(28)}px;bottom:${coverY(58)}px;height:${coverY(430)}px;">${studyArt()}</div>
  </div>`, withCss(fontOpts));
}

function logicCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fff;border-top:${coverY(18)}px solid #fde9e9;">
    <div style="position:absolute;left:${sc(36)}px;right:${sc(36)}px;top:${coverY(112)}px;">
      <div style="height:${coverY(136)}px;background:#fde9e9;position:relative;padding:${coverY(16)}px ${sc(10)}px;">
        <i style="position:absolute;left:0;top:${coverY(12)}px;bottom:${coverY(12)}px;width:${sc(3)}px;background:#d61f1f;"></i>
        <i style="position:absolute;right:0;top:${coverY(12)}px;bottom:${coverY(12)}px;width:${sc(3)}px;background:#d61f1f;"></i>
        <div class="fit-box" style="height:${coverY(104)}px;">${titleHtml(title, 24, 36, "font-weight:900;line-height:1.12;color:#202124;")}</div>
      </div>
      <div style="margin-top:${coverY(44)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(12) + "px;line-height:1.75;color:#333;", 220)}</div>
    </div>
  </div>`, withCss(fontOpts));
}

function textureCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" class="xhs-paper" style="background:#fbfdfa;">
    <div style="position:absolute;inset:${coverY(32)}px ${sc(20)}px;border:1px solid rgba(35,120,78,.12);"></div>
    <div style="position:absolute;left:${sc(38)}px;right:${sc(38)}px;top:${coverY(112)}px;">
      <div class="fit-box" style="height:${coverY(154)}px;">${titleHtml(title, 28, 42, "font-family:var(--serif-cn);font-weight:700;line-height:1.2;color:#16a66a;")}</div>
      <div style="height:${coverY(2)}px;background:#73cfa6;margin:${coverY(20)}px 0 ${coverY(30)}px;width:72%;"></div>
      ${summaryHtml(contentExcerpt, "font-family:var(--serif-cn);font-size:" + sc(12) + "px;line-height:1.85;color:#33443d;", 220)}
    </div>
  </div>`, withCss(fontOpts, `
    #cover-page::before { content:""; position:absolute; inset:0; opacity:.32; background:
      radial-gradient(circle at 12% 8%, rgba(26,167,109,.12), transparent 18%),
      radial-gradient(circle at 82% 20%, rgba(26,167,109,.10), transparent 20%),
      radial-gradient(circle at 62% 74%, rgba(26,167,109,.08), transparent 24%); }`));
}

function magazineCover({ title, cfg, theme, contentExcerpt, coverImageSrc, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fff;">
    <div style="position:absolute;right:${sc(18)}px;top:${coverY(14)}px;width:${sc(26)}px;height:${coverY(56)}px;background:#ff7b2f;"></div>
    <div style="position:absolute;left:${sc(38)}px;right:${sc(38)}px;top:${coverY(100)}px;">
      <div class="fit-box" style="height:${coverY(142)}px;">${titleHtml(title, 28, 41, "font-weight:900;line-height:1.13;color:#202124;")}</div>
      <div style="margin-top:${coverY(24)}px;background:#18c978;color:#05351f;padding:${coverY(16)}px ${sc(18)}px;font-size:${sc(12)}px;line-height:1.55;font-weight:800;">${escapeHtml(cleanExcerpt(contentExcerpt, 72))}</div>
    </div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:${coverY(390)}px;">${coverImageSrc ? coverImageHtml(coverImageSrc) : phoneArt()}</div>
  </div>`, withCss(fontOpts));
}

function topologyCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fff;">
    <div style="height:${coverY(72)}px;background:linear-gradient(90deg,#38bdf8 0 92%,#d6f75b 92%);"></div>
    <div style="position:absolute;left:${sc(44)}px;right:${sc(38)}px;top:${coverY(178)}px;">
      <div style="height:${coverY(3)}px;background:#bbb;margin-bottom:${coverY(28)}px;width:${sc(132)}px;"></div>
      <div class="fit-box" style="height:${coverY(142)}px;">${titleHtml(title, 27, 40, "font-weight:900;line-height:1.15;color:#3a3a3a;")}</div>
      <div style="margin-top:${coverY(32)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(12) + "px;line-height:1.75;color:#3d3d3d;", 220)}</div>
    </div>
  </div>`, withCss(fontOpts));
}

function monoCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fffaf4;">
    <div style="position:absolute;left:${sc(34)}px;right:${sc(34)}px;top:${coverY(132)}px;height:1px;background:#dfcfc0;"></div>
    <div style="position:absolute;left:${sc(36)}px;right:${sc(36)}px;top:${coverY(174)}px;">
      <div class="fit-box" style="height:${coverY(150)}px;">${titleHtml(title, 28, 41, "font-weight:900;line-height:1.14;color:#9b5b2c;")}</div>
      <div style="margin-top:${coverY(36)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(12) + "px;line-height:1.78;color:#6d4328;", 220)}</div>
    </div>
  </div>`, withCss(fontOpts));
}

function clearCover({ title, cfg, theme, contentExcerpt, coverImageSrc, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fff;">
    <div style="position:absolute;left:0;right:0;top:${coverY(72)}px;height:${coverY(345)}px;">${coverImageSrc ? coverImageHtml(coverImageSrc) : bookPhoto(null)}</div>
    <div style="position:absolute;left:${sc(38)}px;right:${sc(38)}px;top:${coverY(452)}px;">
      <div class="fit-box" style="height:${coverY(140)}px;">${titleHtml(title, 28, 41, "font-weight:900;line-height:1.14;color:#222;")}</div>
      <div style="margin-top:${coverY(12)}px;height:${coverY(82)}px;border-left:${sc(4)}px solid #808080;padding-left:${sc(16)}px;overflow:hidden;">${summaryHtml(contentExcerpt, "font-size:" + sc(11) + "px;line-height:1.55;color:#4b5563;", 82)}</div>
      <div style="height:1px;background:#b7b7b7;margin-top:${coverY(46)}px;"></div>
    </div>
  </div>`, withCss(fontOpts));
}

function notesCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#b8121d;color:#fff;">
    <div style="position:absolute;left:${sc(78)}px;top:${coverY(166)}px;width:${sc(3)}px;height:${coverY(390)}px;background:#fff;transform:rotate(-8deg);opacity:.9;"></div>
    <div style="position:absolute;left:${sc(160)}px;right:${sc(36)}px;top:${coverY(120)}px;height:${coverY(360)}px;" class="fit-box">
      ${titleHtml(title, 25, 38, "font-family:var(--serif-cn);font-weight:800;line-height:1.06;color:#fff;text-align:right;")}
    </div>
    <div style="position:absolute;left:${sc(42)}px;right:${sc(48)}px;bottom:${coverY(76)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(11) + "px;line-height:1.75;color:#fff;", 220)}</div>
  </div>`, withCss(fontOpts));
}

function basicCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" class="xhs-paper" style="background:#fff;">
    <div style="position:absolute;inset:${coverY(12)}px ${sc(12)}px;border:1px solid rgba(17,24,39,.12);border-radius:${sc(10)}px;"></div>
    <div style="position:absolute;left:${sc(42)}px;right:${sc(42)}px;top:${coverY(152)}px;">
      <div class="fit-box" style="height:${coverY(148)}px;">${titleHtml(title, 29, 43, "font-family:var(--serif-cn);font-weight:800;line-height:1.16;color:#222;")}</div>
      <div style="margin-top:${coverY(38)}px;">${summaryHtml(contentExcerpt, "font-family:var(--serif-cn);font-size:" + sc(12) + "px;line-height:1.85;color:#303030;", 220)}</div>
    </div>
  </div>`, withCss(fontOpts, `
    #cover-page::before { content:""; position:absolute; inset:0; opacity:.26; background:repeating-linear-gradient(45deg, rgba(0,0,0,.025) 0 ${sc(2)}px, transparent ${sc(2)}px ${sc(9)}px); }`));
}

function geometryCover({ title, cfg, theme, contentExcerpt, coverImageSrc, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fff;">
    <div style="position:absolute;left:0;right:0;top:0;height:${coverY(548)}px;">${coverImageSrc ? coverImageHtml(coverImageSrc) : bookPhoto(null)}</div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:${coverY(430)}px;background:#1c372e;color:#fff;padding:${coverY(64)}px ${sc(42)}px;">
      <div class="fit-box" style="height:${coverY(154)}px;">${titleHtml(title, 27, 40, "font-weight:900;line-height:1.13;color:#5ef089;")}</div>
      <div style="margin-top:${coverY(34)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(11) + "px;line-height:1.7;color:#cadbd2;", 92)}</div>
    </div>
  </div>`, withCss(fontOpts));
}

function memoCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fffdf6;">
    <div style="position:absolute;left:${sc(30)}px;right:${sc(30)}px;top:${coverY(36)}px;height:${coverY(44)}px;color:#f3b316;font-size:${sc(18)}px;font-weight:700;display:flex;justify-content:space-between;">
      <span>&lt; 备忘录</span><span>□ ○</span>
    </div>
    <div style="position:absolute;left:${sc(44)}px;right:${sc(44)}px;top:${coverY(140)}px;">
      <div class="fit-box" style="height:${coverY(150)}px;">${titleHtml(title, 28, 41, "font-weight:850;line-height:1.17;color:#4b5563;")}</div>
      <div style="margin-top:${coverY(42)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(12) + "px;line-height:1.75;color:#555;", 220)}</div>
    </div>
  </div>`, withCss(fontOpts));
}

function narrativeCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#f5f5f5;">
    <div style="position:absolute;left:0;right:0;top:0;height:${coverY(230)}px;background:#15191d;display:flex;align-items:center;padding:0 ${sc(42)}px;">
      <div class="fit-box" style="height:${coverY(150)}px;width:100%;">${titleHtml(title, 26, 39, "font-weight:900;line-height:1.16;color:#27c8eb;")}</div>
    </div>
    <div style="position:absolute;left:${sc(44)}px;right:${sc(44)}px;top:${coverY(284)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(12) + "px;line-height:1.78;color:#4a4a4a;", 220)}</div>
  </div>`, withCss(fontOpts));
}

function duskCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#f3ead8;">
    <div style="position:absolute;inset:0;opacity:.22;background:radial-gradient(circle at 30% 18%,#b59769,transparent 24%),radial-gradient(circle at 78% 76%,#c9b486,transparent 26%);"></div>
    <div style="position:absolute;left:${sc(54)}px;right:${sc(54)}px;top:${coverY(132)}px;text-align:center;">
      <div class="fit-box" style="height:${coverY(146)}px;">${titleHtml(title, 26, 38, "font-family:var(--serif-cn);font-weight:700;line-height:1.25;color:#2d2a25;text-align:center;")}</div>
      <div style="margin-top:${coverY(120)}px;">${summaryHtml(contentExcerpt, "font-family:var(--serif-cn);font-size:" + sc(12) + "px;line-height:1.85;color:#4f4537;text-align:left;", 220)}</div>
    </div>
  </div>`, withCss(fontOpts));
}

function literaryCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fffdfb;">
    <div style="position:absolute;left:${sc(42)}px;right:${sc(42)}px;top:${coverY(130)}px;">
      <div class="fit-box" style="height:${coverY(130)}px;">${titleHtml(title, 28, 40, "font-family:var(--serif-cn);font-weight:800;line-height:1.15;color:#8c5a2e;")}</div>
    </div>
    <div class="xhs-art" style="position:absolute;left:${sc(64)}px;right:${sc(58)}px;top:${coverY(315)}px;height:${coverY(310)}px;">${openBookArt()}</div>
    <div style="position:absolute;left:${sc(42)}px;right:${sc(42)}px;bottom:${coverY(80)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(11) + "px;line-height:1.7;color:#3f3127;", 72)}</div>
  </div>`, withCss(fontOpts, `
    #cover-page::before { content:""; position:absolute; inset:0; opacity:.23; background:linear-gradient(120deg, transparent 0 70%, rgba(196,139,93,.13) 70% 71%, transparent 71%); }`));
}

function handbookCover({ title, cfg, theme, contentExcerpt, coverImageSrc, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#f9f4eb;">
    <div style="position:absolute;inset:${coverY(36)}px ${sc(28)}px;background:#eaf5ee;border:1px solid #cbd9cd;box-shadow:0 ${coverY(14)}px ${coverY(24)}px rgba(73,53,28,.16);">
      <div style="position:absolute;left:${sc(22)}px;right:${sc(22)}px;top:${coverY(42)}px;height:${coverY(154)}px;background:#eef7f0;border:1px solid #cfd9cf;padding:${coverY(22)}px ${sc(22)}px;">
        <div class="fit-box" style="height:${coverY(108)}px;">${titleHtml(title, 23, 34, "font-family:var(--serif-cn);font-weight:650;line-height:1.22;color:#2d2a26;")}</div>
      </div>
      <div style="position:absolute;left:${sc(44)}px;right:${sc(44)}px;top:${coverY(248)}px;height:${coverY(300)}px;background:#fff;">${handbookArt(coverImageSrc)}</div>
      <div style="position:absolute;left:${sc(38)}px;right:${sc(38)}px;bottom:${coverY(48)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(10.5) + "px;line-height:1.6;color:#5c4b35;", 72)}</div>
    </div>
  </div>`, withCss(fontOpts, `
    #cover-page::before { content:"The Post to The World"; position:absolute; left:${sc(70)}px; top:${coverY(20)}px; color:#a99a87; font-size:${sc(11)}px; }`));
}

function retroCover({ title, cfg, theme, contentExcerpt, coverImageSrc, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#f5f6f2;">
    <div style="height:${coverY(96)}px;background:#d8d8d8;"></div>
    <div style="position:absolute;left:${sc(38)}px;right:${sc(38)}px;top:${coverY(156)}px;">
      <div class="fit-box" style="height:${coverY(126)}px;background:linear-gradient(transparent 48%,#d9ed46 48% 82%,transparent 82%);padding:0 ${sc(4)}px;">
        ${titleHtml(title, 27, 40, "font-weight:900;line-height:1.12;color:#111827;")}
      </div>
      <div style="margin-top:${coverY(30)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(11) + "px;line-height:1.65;color:#111827;font-weight:700;", 92)}</div>
    </div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:${coverY(360)}px;">${deskArt(coverImageSrc)}</div>
    <div style="position:absolute;left:${sc(42)}px;bottom:${coverY(16)}px;width:${sc(420)}px;height:${coverY(10)}px;background:#d9ed46;"></div>
  </div>`, withCss(fontOpts));
}

function blockCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fffdf4;">
    <div style="height:${coverY(118)}px;background:#efe7c7;"></div>
    <div style="position:absolute;left:${sc(44)}px;right:${sc(44)}px;top:${coverY(178)}px;">
      <div class="fit-box" style="height:${coverY(132)}px;background:linear-gradient(transparent 18%,#f5e58b 18% 74%,transparent 74%);padding:0 ${sc(6)}px;">
        ${titleHtml(title, 27, 40, "font-weight:900;line-height:1.13;color:#111827;")}
      </div>
      <div style="margin-top:${coverY(40)}px;">${summaryHtml(contentExcerpt, "font-size:" + sc(12) + "px;line-height:1.75;color:#222;", 220)}</div>
    </div>
  </div>`, withCss(fontOpts));
}

function quoteCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" class="xhs-dots" style="background:#fffefa;">
    <div style="position:absolute;left:${sc(50)}px;top:${coverY(106)}px;font-size:${sc(76)}px;line-height:1;color:#ffe68c;font-weight:900;">“</div>
    <div style="position:absolute;left:${sc(54)}px;right:${sc(54)}px;top:${coverY(388)}px;">
      <div class="fit-box" style="height:${coverY(170)}px;">${titleHtml(title, 27, 41, "font-weight:900;line-height:1.14;color:#ff7a2f;")}</div>
    </div>
    <div style="position:absolute;left:${sc(54)}px;right:${sc(54)}px;bottom:${coverY(108)}px;display:flex;align-items:center;color:#ffb357;">
      <span style="font-size:${sc(10)}px;font-weight:700;">右划查看全文</span><span style="height:1px;background:#ffcf73;flex:1;margin-left:${sc(28)}px;"></span><span style="font-size:${sc(30)}px;margin-left:${sc(8)}px;">→</span>
    </div>
  </div>`, withCss(fontOpts));
}

function photoCover({ title, cfg, theme, contentExcerpt, coverImageSrc, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#f7c0b6;">
    <div style="position:absolute;inset:0;">${softScene(coverImageSrc)}</div>
    <div style="position:absolute;left:0;right:0;bottom:${coverY(60)}px;height:${coverY(192)}px;background:linear-gradient(90deg,rgba(0,0,0,.52),rgba(0,0,0,.22));padding:${coverY(28)}px ${sc(42)}px;color:#fff;">
      <div class="fit-box" style="height:${coverY(104)}px;">${titleHtml(title, 24, 36, "font-weight:900;line-height:1.14;color:#fff;")}</div>
      <div style="height:1px;background:rgba(255,255,255,.75);margin-top:${coverY(18)}px;"></div>
    </div>
  </div>`, withCss(fontOpts));
}

function doodleCover({ title, cfg, theme, contentExcerpt, fontOpts }) {
  return coverDoc(cfg, theme, `<div id="cover-page" style="background:#fff4fb;">
    <div style="position:absolute;left:${sc(38)}px;top:${coverY(112)}px;color:#ffc83d;font-size:${sc(58)}px;font-weight:900;transform:rotate(-18deg);">⌒</div>
    <div style="position:absolute;left:${sc(222)}px;top:${coverY(102)}px;color:#f58bd4;font-size:${sc(48)}px;font-weight:900;">＊</div>
    <div style="position:absolute;right:${sc(74)}px;top:${coverY(116)}px;color:#ffc83d;font-size:${sc(54)}px;font-weight:900;transform:rotate(28deg);">×</div>
    <div style="position:absolute;right:${sc(40)}px;top:${coverY(250)}px;width:${sc(78)}px;height:${coverY(18)}px;background:#86dff7;transform:rotate(42deg);"></div>
    <div style="position:absolute;left:${sc(70)}px;right:${sc(70)}px;top:${coverY(414)}px;text-align:center;">
      <div class="fit-box" style="height:${coverY(170)}px;background:linear-gradient(transparent 42%,#f6a8dd 42% 78%,transparent 78%);transform:rotate(-2deg);padding:${coverY(8)}px ${sc(8)}px;">
        <div style="transform:rotate(2deg);">${titleHtml(title, 28, 42, "font-weight:900;line-height:1.14;color:#5b1741;text-align:center;")}</div>
      </div>
    </div>
    <div style="position:absolute;left:${sc(78)}px;right:${sc(78)}px;bottom:${coverY(150)}px;text-align:center;">${summaryHtml(contentExcerpt, "font-size:" + sc(12) + "px;line-height:1.6;color:#d93b9f;font-weight:700;text-align:center;", 64)}</div>
    <div style="position:absolute;left:${sc(86)}px;bottom:${coverY(128)}px;width:${sc(5)}px;height:${coverY(90)}px;background:#f58bd4;"></div>
    <div style="position:absolute;right:${sc(86)}px;bottom:${coverY(128)}px;width:${sc(5)}px;height:${coverY(90)}px;background:#f58bd4;"></div>
  </div>`, withCss(fontOpts, `
    #cover-page::before { content:""; position:absolute; inset:0; opacity:.28; background:
      radial-gradient(circle at 22% 58%, #62d8f4 0 ${sc(6)}px, transparent ${sc(7)}px),
      radial-gradient(circle at 72% 90%, #f58bd4 0 ${sc(7)}px, transparent ${sc(8)}px),
      radial-gradient(circle at 55% 22%, #ffca45 0 ${sc(3)}px, transparent ${sc(4)}px); }`));
}

const coverByMode = {
  rational: rationalCover,
  logic: logicCover,
  texture: textureCover,
  magazine: magazineCover,
  topology: topologyCover,
  mono: monoCover,
  clear: clearCover,
  notes: notesCover,
  basic: basicCover,
  geometry: geometryCover,
  memo: memoCover,
  narrative: narrativeCover,
  dusk: duskCover,
  literary: literaryCover,
  handbook: handbookCover,
  retro: retroCover,
  block: blockCover,
  quote: quoteCover,
  photo: photoCover,
  doodle: doodleCover,
};

function createXhsTemplate(spec) {
  const cover = coverByMode[spec.mode];
  return createThemedTemplate({
    id: spec.id,
    name: spec.name,
    defaults: defaultsFor(spec),
    bodyCss,
    headerHtml,
    footerHtml,
    chromeCss,
    primaryCover(args) {
      return cover(args);
    },
  });
}

export const xhsTemplates = specs.map(createXhsTemplate);
