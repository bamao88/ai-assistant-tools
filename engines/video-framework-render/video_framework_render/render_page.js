// 框架图页 HTML → 720x1280 PNG（白底，2x 清晰）
// usage: node render_page.js <in.html> <out.png>
const puppeteer = require('/Users/xpw/.npm/_npx/7d92d9a2d2ccc630/node_modules/puppeteer');
const path = require('path');
(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 720, height: 1280, deviceScaleFactor: 2 });
  await page.goto('file://' + path.resolve(process.argv[2]), { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 250));
  await page.screenshot({ path: path.resolve(process.argv[3]), type: 'png',
    clip: { x: 0, y: 0, width: 720, height: 1280 } });
  await browser.close();
  console.log('  rendered', path.basename(process.argv[3]));
})();
