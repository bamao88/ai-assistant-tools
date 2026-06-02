#!/usr/bin/env node
/**
 * 飞书登录态截图（headed + 持久化 profile）
 *
 * 用法:
 *   node feishu_capture.js <url> <output.png> [wait_selector_text]
 *
 * 第一次运行会弹出可见的 Chromium 窗口，请用飞书 App 扫码登录；
 * 登录态保存在持久化 profile，后续运行免登录。
 */
const { chromium } = require('playwright');
const path = require('path');

const PROFILE_DIR = path.resolve(__dirname, '../../var/state/feishu_chrome_profile');

async function main() {
  const [, , url, output, waitText] = process.argv;
  if (!url || !output) {
    console.error('用法: node feishu_capture.js <url> <output.png> [wait_selector_text]');
    process.exit(1);
  }

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1512, height: 950 },
    deviceScaleFactor: 2,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = context.pages()[0] || (await context.newPage());
  try { await page.bringToFront(); } catch {}

  console.log(`→ 打开: ${url}`);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  try { await page.bringToFront(); } catch {}
  await page.waitForTimeout(2500);

  // 检测是否在登录页（出现“扫码登录”）
  const loginMarker = page.locator('text=扫码登录').first();
  let needLogin = false;
  try { needLogin = await loginMarker.isVisible({ timeout: 2000 }); } catch {}

  if (needLogin) {
    console.log('⏳ 需要登录：请在弹出的窗口里用飞书 App 扫码。最多等待 180 秒…');
    // 轮询直到登录页消失（最多 180s）
    const deadline = Date.now() + 180000;
    while (Date.now() < deadline) {
      await page.waitForTimeout(3000);
      let still = false;
      try { still = await page.locator('text=扫码登录').first().isVisible({ timeout: 1000 }); } catch {}
      if (!still) { console.log('✓ 登录页已消失，等待文档加载…'); break; }
    }
    // 登录后可能跳到首页，重新打开目标 URL
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
  }

  // 等目标内容出现
  if (waitText) {
    try {
      await page.locator(`text=${waitText}`).first().waitFor({ timeout: 30000 });
      console.log(`✓ 命中等待文本: ${waitText}`);
    } catch { console.log(`⚠ 未等到文本「${waitText}」，仍然截图`); }
  }
  await page.waitForTimeout(2500);

  await page.screenshot({ path: output, fullPage: false });
  console.log(`✓ 截图: ${output}`);

  await context.close();
}

main().catch((e) => { console.error('✗ 失败:', e.message); process.exit(1); });
