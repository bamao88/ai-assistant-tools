#!/usr/bin/env node
/**
 * 视频字幕金句卡（拼图）：一张代表性视频帧 + 下方双语字幕条若干，合成一张可分享的「金句卡」。
 *
 * find-images skill「方式四：视频字幕金句卡」配套工具。机械活（取帧 → 渲染字幕条 → 合成）交给它，
 * 选哪个时间点的帧、挑哪几句金句、中文怎么译，仍由 AI/人定。
 *
 * 位置：tools/engines/screenshot/subtitle_card.js
 *
 * 用法：
 *   node subtitle_card.js --frame <顶图.jpg> --lines <quotes.json> --out <composite.jpg> [--width 1280]
 *   node subtitle_card.js --frame f.jpg --out c.jpg --lines '[{"en":"...","zh":"..."}]'   # 也可内联 JSON
 *
 * quotes.json 格式（每条 = 一句英文 + 一句中文译文，按顺序从上到下排）：
 *   [
 *     {"en": "Two years ago, the model was actually just a set of weights.",
 *      "zh": "两年前，所谓「模型」就是字面意义上的一组权重。"},
 *     {"en": "Now it's not just the weights.", "zh": "但今天，它早就不只是那组权重了。"}
 *   ]
 *
 * 顶图来源：用 video_frame.py grab 从视频抠帧（不裁子区域，即整帧画面），或任意现成截图。
 * 风格：深色底 + 英文白字加粗 + 中文浅灰 + 细分隔线，复刻烧录双语字幕的观感。手机竖屏可读。
 *
 * 依赖：playwright（engine 已装）。中文用系统 PingFang SC，英文用 Helvetica Neue。
 */
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

function parseArgs(argv) {
  const a = { width: 1280 };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--frame") a.frame = argv[++i];
    else if (k === "--lines") a.lines = argv[++i];
    else if (k === "--out") a.out = argv[++i];
    else if (k === "--width") a.width = parseInt(argv[++i], 10);
    else if (k === "--bg") a.bg = argv[++i];
  }
  return a;
}

function loadLines(spec) {
  // spec 既可是 JSON 文件路径，也可是内联 JSON 字符串
  let raw = spec;
  if (fs.existsSync(spec)) raw = fs.readFileSync(spec, "utf8");
  let arr;
  try {
    arr = JSON.parse(raw);
  } catch (e) {
    console.error("无法解析 --lines（既不是有效 JSON 文件也不是 JSON 字符串）：", e.message);
    process.exit(1);
  }
  if (!Array.isArray(arr) || !arr.length) {
    console.error("--lines 必须是非空数组 [{en, zh}, ...]");
    process.exit(1);
  }
  return arr;
}

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function buildHtml({ frameDataUri, lines, width, bg }) {
  const blocks = lines.map((l) => `
      <div class="block">
        ${l.en ? `<div class="en">${esc(l.en)}</div>` : ""}
        ${l.zh ? `<div class="zh">${esc(l.zh)}</div>` : ""}
      </div>`).join(`<div class="divider"></div>`);
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { width: ${width}px; background: ${bg}; }
    .frame { display: block; width: ${width}px; }
    .panel { background: ${bg}; padding: 40px 64px 48px; }
    .block { padding: 18px 0; text-align: center; }
    .en {
      font-family: "Helvetica Neue", Arial, sans-serif;
      font-size: 38px; font-weight: 600; color: #fff;
      line-height: 1.32; letter-spacing: .2px;
    }
    .zh {
      font-family: "PingFang SC", "Heiti SC", sans-serif;
      font-size: 30px; font-weight: 400; color: #c9d2dc;
      line-height: 1.5; letter-spacing: 1px; margin-top: 10px;
    }
    .divider { height: 1px; background: rgba(120,160,150,.35); margin: 0 8px; }
  </style></head><body>
    <img class="frame" src="${frameDataUri}">
    <div class="panel">${blocks}</div>
  </body></html>`;
}

(async () => {
  const a = parseArgs(process.argv);
  if (!a.frame || !a.lines || !a.out) {
    console.error("用法：node subtitle_card.js --frame <顶图> --lines <quotes.json|内联JSON> --out <composite.jpg> [--width 1280]");
    process.exit(1);
  }
  if (!fs.existsSync(a.frame)) {
    console.error("顶图不存在：", a.frame);
    process.exit(1);
  }
  const bg = a.bg || "#161a23";
  const ext = path.extname(a.frame).slice(1).toLowerCase();
  const mime = ext === "png" ? "image/png" : "image/jpeg";
  const frameDataUri = `data:${mime};base64,${fs.readFileSync(a.frame).toString("base64")}`;
  const lines = loadLines(a.lines);
  const html = buildHtml({ frameDataUri, lines, width: a.width, bg });

  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 2 });
  await page.setViewportSize({ width: a.width, height: 800 });
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.waitForTimeout(150);
  const outIsPng = path.extname(a.out).toLowerCase() === ".png";
  await page.screenshot({
    path: a.out,
    fullPage: true,
    type: outIsPng ? "png" : "jpeg",
    quality: outIsPng ? undefined : 92,
  });
  await browser.close();
  const dim = await (async () => {
    try { const sz = fs.statSync(a.out).size; return `${(sz / 1024).toFixed(0)}KB`; }
    catch { return "?"; }
  })();
  console.log(`✓ 金句卡已生成：${a.out}（${lines.length} 句，${dim}）`);
})();
