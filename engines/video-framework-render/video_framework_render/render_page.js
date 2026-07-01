// 框架图页 HTML → PNG（白底，2x 清晰）。画幅由参数给，默认 720x1280（竖版）。
// usage: node render_page.js <in.html> <out.png> [width=720] [height=1280]
// 迁移阶段3：puppeteer 解析去硬编码——优先 PUPPETEER_PATH 环境变量，再引擎本地
// node_modules / 全局，最后回退旧 npx 缓存。任一可用即可（渲染输出与来源无关）。
const path = require('path');
function loadPuppeteer() {
  const candidates = [
    process.env.PUPPETEER_PATH,
    'puppeteer',                                  // 引擎本地 node_modules / NODE_PATH / 全局
    path.join(__dirname, 'node_modules', 'puppeteer'),
    '/Users/xpw/.npm/_npx/7d92d9a2d2ccc630/node_modules/puppeteer',  // 旧 npx 缓存兜底
  ].filter(Boolean);
  for (const c of candidates) { try { return require(c); } catch (_) {} }
  throw new Error('puppeteer 未找到：设 PUPPETEER_PATH 或在引擎内 npm i puppeteer（见 README）');
}
const puppeteer = loadPuppeteer();
(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  const W = parseInt(process.argv[4], 10) || 720;
  const H = parseInt(process.argv[5], 10) || 1280;
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 2 });
  await page.goto('file://' + path.resolve(process.argv[2]), { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  await new Promise(r => setTimeout(r, 250));
  // 自适应缩放：厚页内容超过安全内容区(.ppt 由 top/bottom 定高、overflow:hidden)时，
  // 整体等比缩小塞进框内——不裁字、不溢出到底部字幕/PIP 安全带。
  const scaled = await page.evaluate(() => {
    const el = document.querySelector('.ppt');
    if (!el) return 1;
    const avail = el.clientHeight, need = el.scrollHeight;
    if (avail > 0 && need > avail + 1) {
      const s = avail / need;
      el.style.transformOrigin = 'top left';
      el.style.transform = 'scale(' + s + ')';
      return s;
    }
    return 1;
  });
  if (scaled < 1) console.log('  fit-scale', path.basename(process.argv[2]), '×' + scaled.toFixed(3));
  await page.screenshot({ path: path.resolve(process.argv[3]), type: 'png',
    clip: { x: 0, y: 0, width: W, height: H } });
  await browser.close();
  console.log('  rendered', path.basename(process.argv[3]));
})();
