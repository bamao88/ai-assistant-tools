const puppeteer = require('/Users/xpw/.npm/_npx/7d92d9a2d2ccc630/node_modules/puppeteer');
const path = require('path');
(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 720, height: 1280, deviceScaleFactor: 1 });
  const file = path.resolve(__dirname, process.argv[2]);
  const out  = path.resolve(__dirname, process.argv[3]);
  await page.goto('file://' + file, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 300));
  await page.screenshot({ path: out, type: 'png', omitBackground: true });
  await browser.close();
  console.log('done:', out);
})();
