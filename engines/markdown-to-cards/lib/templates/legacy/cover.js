import { escapeCssUrl, escapeHtml } from "../shared/themed.js";

export function renderTemplateCover(title, cfg, coverBgSrc, fontOpts = {}) {
  const { cssWidth, cssHeight, fontFamily, coverBg } = cfg;
  const titleFamily = fontOpts.family || "'Songti SC', serif";
  const titleWeight = fontOpts.weight || 900;
  const extraCss = fontOpts.css || "";

  const boxLeft = Math.round(cssWidth * 0.10);
  const boxTop = Math.round(cssHeight * 0.265);
  const boxWidth = Math.round(cssWidth * 0.80);
  const boxHeight = Math.round(cssHeight * 0.465);

  const bgStyle = coverBgSrc
    ? `background: url('${escapeCssUrl(coverBgSrc)}') center center / cover no-repeat;`
    : `background-color: ${coverBg};
       background-image: radial-gradient(circle, rgba(160,120,48,0.13) 1.5px, transparent 1.5px);
       background-size: 26px 26px;`;

  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  ${extraCss}
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { width: ${cssWidth}px; font-family: ${fontFamily}; -webkit-font-smoothing: antialiased; }
  #cover-page {
    width: ${cssWidth}px; height: ${cssHeight}px;
    ${bgStyle} overflow: hidden; position: relative;
  }
  #text-box {
    position: absolute; left: ${boxLeft}px; top: ${boxTop}px;
    width: ${boxWidth}px; height: ${boxHeight}px;
    display: flex; align-items: center; justify-content: flex-start;
  }
  #cover-title {
    font-family: ${titleFamily}; font-weight: ${titleWeight};
    color: #836034; -webkit-text-stroke: 1px #836034;
    line-height: 1.2; letter-spacing: 0.04em;
    word-break: normal; overflow-wrap: break-word;
    text-align: left; width: 100%; font-size: 72px;
  }
</style></head>
<body>
  <div id="cover-page">
    <div id="text-box"><div id="cover-title">${escapeHtml(title)}</div></div>
  </div>
  <script>
    document.fonts.ready.then(() => {
      const el = document.getElementById('cover-title');
      const BOX_H = ${boxHeight};
      let lo = 20, hi = 80, best = 20;
      while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        el.style.fontSize = mid + 'px';
        if (el.scrollHeight <= BOX_H) { best = mid; lo = mid + 1; } else { hi = mid - 1; }
      }
      el.style.fontSize = best + 'px';
    });
  </script>
</body></html>`;
}

export function renderImageCover(title, wordCount, cfg, coverImageSrc, fontOpts = {}) {
  const { cssWidth, cssHeight, fontFamily, coverBg, accent } = cfg;
  const titleFamily = fontOpts.family || "'Songti SC', serif";
  const titleWeight = fontOpts.weight || 900;
  const extraCss = fontOpts.css || "";
  const heroHeight = Math.round(cssHeight * 0.58);
  const panelX = Math.round(cssWidth * 0.075);
  const panelBottom = Math.round(cssHeight * 0.075);
  const panelHeight = Math.round(cssHeight * 0.34);
  const readMins = Math.max(1, Math.ceil(wordCount / 300));

  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  ${extraCss}
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { width: ${cssWidth}px; font-family: ${fontFamily}; -webkit-font-smoothing: antialiased; }
  #cover-page {
    width: ${cssWidth}px; height: ${cssHeight}px; overflow: hidden; position: relative;
    background: ${coverBg};
  }
  #cover-hero {
    position: absolute; left: 0; top: 0; width: 100%; height: ${heroHeight}px;
    background: url('${escapeCssUrl(coverImageSrc)}') center center / cover no-repeat;
  }
  #cover-hero::after {
    content: ""; position: absolute; left: 0; right: 0; bottom: -1px; height: 34%;
    background: linear-gradient(to bottom, rgba(253,250,244,0), ${coverBg});
  }
  #cover-panel {
    position: absolute; left: ${panelX}px; right: ${panelX}px; bottom: ${panelBottom}px;
    min-height: ${panelHeight}px; display: flex; flex-direction: column; justify-content: center;
    padding: 34px 38px 38px; background: rgba(253,250,244,0.94);
    border: 2px solid rgba(160,120,48,0.25); border-radius: 8px;
    box-shadow: 0 18px 44px rgba(70, 52, 26, 0.14);
  }
  #cover-kicker {
    color: ${accent}; font-size: 22px; font-weight: 700; line-height: 1.2;
    margin-bottom: 18px;
  }
  #cover-title {
    font-family: ${titleFamily}; font-weight: ${titleWeight};
    color: #2b2419; line-height: 1.18; letter-spacing: 0;
    word-break: normal; overflow-wrap: break-word; width: 100%; font-size: 62px;
  }
  #cover-meta {
    margin-top: 22px; color: rgba(43,36,25,0.62); font-size: 20px; line-height: 1.4;
  }
</style></head>
<body>
  <div id="cover-page">
    <div id="cover-hero"></div>
    <div id="cover-panel">
      <div id="cover-kicker">精选长图文</div>
      <div id="cover-title">${escapeHtml(title)}</div>
      <div id="cover-meta">约 ${readMins} 分钟阅读</div>
    </div>
  </div>
  <script>
    document.fonts.ready.then(() => {
      const el = document.getElementById('cover-title');
      const panel = document.getElementById('cover-panel');
      let lo = 26, hi = 68, best = 26;
      while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        el.style.fontSize = mid + 'px';
        if (panel.scrollHeight <= ${panelHeight + 46}) { best = mid; lo = mid + 1; } else { hi = mid - 1; }
      }
      el.style.fontSize = best + 'px';
    });
  </script>
</body></html>`;
}
