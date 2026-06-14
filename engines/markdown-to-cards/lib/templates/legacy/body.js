export function renderBodyPage(cfg, pageHtml = "") {
  const {
    cssWidth,
    cssHeight,
    paddingH,
    paddingV,
    fontSize,
    lineHeight,
    fontFamily,
    headingFontFamily = fontFamily,
    fontCss = "",
    bodyBg,
    textColor,
    accent,
    accentTint,
    subtleBg,
    inlineCodeBg,
    inlineCodeText,
    codeBg,
    codeText,
    blockquoteText,
    blockquoteBorder,
    ruleColor,
    tableHeadBg,
    tableHeadBorder,
    tableCellBorder,
    tableAltBg,
  } = cfg;
  const h2Size = Math.round(fontSize * 1.32);
  const h3Size = Math.round(fontSize * 1.12);
  const codeSize = Math.round(fontSize * 0.84);
  const tableFs = Math.round(fontSize * 0.88);
  const paraGap = Math.round(fontSize * 0.88);
  const imagePad = Math.round(fontSize * 0.35);
  const maxImageHeight = Math.round((cssHeight - paddingV * 2) * 0.48);
  const maxImageWidth = cssWidth - paddingH * 2 - imagePad * 2;

  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  ${fontCss}
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { width: ${cssWidth}px; background: ${bodyBg}; color: ${textColor};
         font-size: ${fontSize}px; line-height: ${lineHeight}; font-family: ${fontFamily};
         -webkit-font-smoothing: antialiased; }
  #measure-wrap { width: ${cssWidth - paddingH * 2}px; position: absolute; top: -9999px;
                  left: 0; visibility: hidden; overflow: hidden;
                  font-size: ${fontSize}px; line-height: ${lineHeight}; font-family: ${fontFamily}; }
  #capture-page { width: ${cssWidth}px; height: ${cssHeight}px; overflow: hidden;
                  background: ${bodyBg}; padding: ${paddingV}px ${paddingH}px; }
  .md-body h2 { font-family: ${headingFontFamily}; font-size: ${h2Size}px; font-weight: 700; line-height: 1.35; color: ${accent};
                border-left: 5px solid ${accent}; padding-left: 16px;
                margin-top: ${Math.round(paraGap * 0.5)}px; margin-bottom: ${Math.round(paraGap * 0.8)}px; }
  .md-body h3 { font-family: ${headingFontFamily}; font-size: ${h3Size}px; font-weight: 600; line-height: 1.4; color: ${textColor};
                margin-top: ${Math.round(paraGap * 0.3)}px; margin-bottom: ${Math.round(paraGap * 0.6)}px; }
  .md-body p { margin-bottom: ${paraGap}px; word-break: normal; overflow-wrap: anywhere; }
  .md-body p[data-split-part="start"], .md-body p[data-split-part="middle"] { margin-bottom: 0; }
  .md-body p:has(> img.md-image:only-child) {
    display: flex; align-items: center; justify-content: center;
    width: fit-content; max-width: 100%;
    padding: ${imagePad}px; margin: ${Math.round(paraGap * 0.35)}px auto ${paraGap}px;
    background: ${subtleBg}; border-radius: 8px; overflow: hidden;
  }
  .md-body img.md-image {
    display: block; max-width: ${maxImageWidth}px; max-height: var(--image-max-height, ${maxImageHeight}px);
    width: auto; height: auto; object-fit: contain; border-radius: 7px;
  }
  .md-body ul { margin-bottom: ${paraGap}px; padding-left: ${Math.round(fontSize * 1.3)}px; list-style-type: disc; }
  .md-body ol { margin-bottom: ${paraGap}px; padding-left: ${Math.round(fontSize * 1.6)}px; list-style-type: decimal; }
  .md-body li { margin-bottom: ${Math.round(fontSize * 0.35)}px; line-height: ${lineHeight}; }
  .md-body li[data-split-part="start"], .md-body li[data-split-part="middle"] { margin-bottom: 0; }
  .md-body li > ul, .md-body li > ol { margin-top: ${Math.round(fontSize * 0.2)}px; margin-bottom: 0; }
  .md-body strong { font-weight: 700; color: ${accent}; }
  .md-body em { font-style: italic; }
  .md-body code { font-family: 'SF Mono','Fira Code','Consolas',monospace; font-size: ${codeSize}px;
                  background: ${inlineCodeBg}; padding: 0.12em 0.4em; border-radius: 4px; color: ${inlineCodeText};
                  white-space: nowrap; word-break: keep-all; overflow-wrap: normal; }
  .md-body pre { background: ${codeBg}; color: ${codeText};
                 padding: ${Math.round(fontSize * 0.9)}px ${Math.round(fontSize)}px;
                 border-radius: 10px; margin-bottom: ${paraGap}px; overflow: hidden; }
  .md-body pre code { background: none; padding: 0; color: inherit; font-size: ${codeSize}px; line-height: 1.6;
                      white-space: pre; word-break: normal; overflow-wrap: normal; }
  .md-body blockquote { background: ${accentTint}; border-left: ${blockquoteBorder};
                        padding: ${Math.round(fontSize * 0.5)}px ${Math.round(fontSize * 0.85)}px;
                        border-radius: 8px; margin-bottom: ${paraGap}px; color: ${blockquoteText}; font-style: italic; }
  .md-body blockquote p { margin-bottom: 0; }
  .md-body hr { border: none; border-top: 1.5px solid ${ruleColor}; margin: ${Math.round(paraGap * 0.7)}px 0; }
  .md-body table { width: 100%; border-collapse: collapse; margin-bottom: ${paraGap}px; font-size: ${tableFs}px; line-height: 1.5; }
  .md-body th { background: ${tableHeadBg}; color: ${textColor}; font-weight: 700;
                padding: ${Math.round(fontSize * 0.4)}px ${Math.round(fontSize * 0.5)}px;
                border: 1.5px solid ${tableHeadBorder}; text-align: left; }
  .md-body td { padding: ${Math.round(fontSize * 0.38)}px ${Math.round(fontSize * 0.5)}px;
                border: 1.5px solid ${tableCellBorder}; vertical-align: top; }
  .md-body tr:nth-child(even) td { background: ${tableAltBg}; }
  .md-body a { color: ${accent}; text-decoration: underline; text-underline-offset: 3px; }
</style></head>
<body>
  <div id="measure-wrap"><div id="measure-content"></div></div>
  <div id="capture-page"><div class="md-body" id="capture-body">${pageHtml}</div></div>
</body></html>`;
}
