const { chromium } = require('playwright');
(async () => {
  const [,, url, out] = process.argv;
  const b = await chromium.launch({ args:['--no-sandbox'] });
  const p = await (await b.newContext({ viewport:{width:1440,height:900}, deviceScaleFactor:2 })).newPage();
  await p.goto(url, { waitUntil:'load', timeout:60000 });
  await p.waitForTimeout(3500);
  for (const t of ['Okay','Accept all','Accept','Got it','I agree']) {
    try { const el = p.getByText(t, {exact:true}).first(); if (await el.count()) { await el.click({timeout:1500}); break; } } catch(e){}
  }
  await p.waitForTimeout(1200);
  await p.screenshot({ path: out });
  await b.close(); console.log('done', out);
})();
