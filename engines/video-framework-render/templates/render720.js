const puppeteer = require('/Users/xpw/.npm/_npx/7d92d9a2d2ccc630/node_modules/puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 720, height: 1280, deviceScaleFactor: 2 });
  const query = process.argv[3] ? ('?' + process.argv[3]) : '';
  const file = path.resolve(__dirname, 'layout.html');
  const out  = path.resolve(__dirname, process.argv[2] || 'layout_mockup.png');
  await page.goto('file://' + file + query, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 400));
  const stage = await page.$('.stage');
  await stage.screenshot({ path: out, type: 'png' });
  await browser.close();
  console.log('done:', out);
})();
