#!/usr/bin/env node
/**
 * Playwright 截图工具
 *
 * 用法:
 *   node screenshot.js <url> <output> [selector_or_text] [wait_ms]
 *
 * 参数:
 *   url            目标网页 URL
 *   output         输出图片路径 (.png)
 *   selector_or_text  可选，CSS selector 或 "text=..." 定位目标元素
 *   wait_ms        可选，额外等待毫秒数（默认 2000）
 *
 * 示例:
 *   # 全页截图
 *   node screenshot.js "https://openai.com/api/pricing/" /tmp/out.png
 *
 *   # 截特定文字所在区域
 *   node screenshot.js "https://openai.com/api/pricing/" /tmp/out.png "text=GPT-5.4 mini"
 *
 *   # 截 CSS selector 元素
 *   node screenshot.js "https://example.com" /tmp/out.png ".pricing-table"
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Credentials live in the shared runtime dir (tools/var/state), not in the engine code dir.
const STORAGE_STATE = path.resolve(__dirname, '../../var/state/storage_state.json');

async function main() {
  const [,, url, output, selectorOrText, waitMsStr] = process.argv;

  if (!url || !output) {
    console.error('用法: node screenshot.js <url> <output> [selector_or_text] [wait_ms]');
    process.exit(1);
  }

  const waitMs = parseInt(waitMsStr || '2000', 10);
  const storageState = fs.existsSync(STORAGE_STATE) ? STORAGE_STATE : undefined;

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    storageState,
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
  });

  const page = await context.newPage();

  try {
    console.log(`→ 打开: ${url}`);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1500); // 等 JS 初始渲染

    // 关闭 cookie 弹窗（如果有）
    const cookieDismiss = [
      'button:has-text("接受")', 'button:has-text("Accept")',
      'button:has-text("全部接受")', 'button:has-text("Accept all")',
      'button:has-text("拒绝必要")', 'button:has-text("同意")',
      '[aria-label="Close"]', '[aria-label="关闭"]'
    ];
    for (const sel of cookieDismiss) {
      try {
        const btn = page.locator(sel).first();
        if (await btn.isVisible({ timeout: 1000 })) {
          await btn.click();
          await page.waitForTimeout(500);
          console.log(`  → 关闭弹窗: ${sel}`);
          break;
        }
      } catch {}
    }

    await page.waitForTimeout(waitMs);

    if (selectorOrText) {
      // 定位到目标元素后截图
      let locator;
      if (selectorOrText.startsWith('text=')) {
        locator = page.locator(selectorOrText);
      } else if (selectorOrText.startsWith('/')) {
        // XPath
        locator = page.locator(`xpath=${selectorOrText}`);
      } else {
        // CSS selector
        locator = page.locator(selectorOrText);
      }

      // 等待元素出现
      await locator.first().waitFor({ timeout: 10000 });

      // 滚动到元素位置
      await locator.first().scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);

      // 获取元素及其周围区域
      const box = await locator.first().boundingBox();
      if (box) {
        // 上下各留 80px 边距，让截图有上下文
        const clip = {
          x: 0,
          y: Math.max(0, box.y - 80),
          width: 1440,
          height: Math.max(box.height + 400, 600)  // 元素下方留足够空间
        };
        await page.screenshot({ path: output, clip });
        console.log(`✓ 元素截图: ${output} (${Math.round(box.width)}×${Math.round(box.height)})`);
      } else {
        // 找不到 boundingBox，退化为全页截图
        await page.screenshot({ path: output, fullPage: false });
        console.log(`✓ 截图（元素未定位到 box）: ${output}`);
      }
    } else {
      // 全视口截图
      await page.screenshot({ path: output, fullPage: false });
      console.log(`✓ 全视口截图: ${output}`);
    }

    const stat = fs.statSync(output);
    console.log(`  文件大小: ${Math.round(stat.size / 1024)}KB`);

  } catch (err) {
    console.error(`✗ 失败: ${err.message}`);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
