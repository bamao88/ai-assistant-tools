import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';
import { THEMES } from '../../engines/gzh-publish/src/lib/themes/index';
import { typeset } from '../../engines/gzh-publish/src/typeset';

const outDir = path.resolve('tmp/gzh-theme-overview');
const htmlPath = path.join(outDir, 'gzh-theme-overview.html');

const sample = `# Agent 产品的下一步

很多团队做 Agent，第一反应是继续堆模型、堆工具、堆上下文。但真正决定体验的，往往不是模型有没有更聪明，而是产品有没有把失败路径设计清楚。

> 一个可靠的 Agent 产品，必须先能解释自己为什么失败，再谈自动化。

## 我会看三个信号

- 是否有稳定的 baseline，而不是只展示一次惊艳 demo
- 是否能把人工判断沉淀成评估标准
- 是否能在异常状态下给用户一个可恢复的出口

| 维度 | 好的状态 | 风险信号 |
|---|---|---|
| 任务定义 | 边界清楚 | 需求无限扩张 |
| 评估 | 可复现 | 只靠主观感觉 |
| 交互 | 可恢复 | 失败后沉默 |

这也是为什么我更关心 **产品结构**，而不是单次调用的模型分数。

\`\`\`ts
const baseline = run(task);
expect(baseline.recoverable).toBe(true);
\`\`\`
`;

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function main() {
  const cards = await Promise.all(THEMES.map(async (theme) => {
    const body = await typeset(sample, {
      theme: theme.id,
      convertImages: false,
    });
    return `
      <article class="theme-card">
        <div class="theme-meta">
          <div>
            <h2>${escapeHtml(theme.name)}</h2>
            <code>${escapeHtml(theme.id)}</code>
          </div>
          <p>${escapeHtml(theme.description)}</p>
        </div>
        <div class="phone-frame">
          <div class="phone-scroll">${body}</div>
        </div>
      </article>
    `;
  }));

  const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>公众号排版主题总览</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; background: #f3f4f6; color: #111827; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; }
  body { padding: 34px; }
  #overview { width: 1372px; margin: 0 auto; }
  .header { display: flex; align-items: end; justify-content: space-between; margin-bottom: 20px; }
  .header h1 { margin: 0; font-size: 34px; line-height: 1.15; letter-spacing: 0; }
  .header p { margin: 8px 0 0; color: #6b7280; font-size: 15px; }
  .badge { color: #374151; background: #fff; border: 1px solid #e5e7eb; border-radius: 999px; padding: 8px 12px; font-size: 13px; }
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; align-items: start; }
  .theme-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08); }
  .theme-meta { min-height: 116px; display: flex; flex-direction: column; justify-content: space-between; gap: 8px; padding: 4px 2px 10px; }
  .theme-meta h2 { margin: 0 0 4px; font-size: 18px; line-height: 1.25; letter-spacing: 0; }
  .theme-meta code { font-size: 12px; color: #4b5563; background: #f3f4f6; border-radius: 4px; padding: 2px 6px; }
  .theme-meta p { margin: 0; color: #6b7280; font-size: 12px; line-height: 1.45; }
  .phone-frame { height: 560px; overflow: hidden; border-radius: 8px; border: 1px solid #d1d5db; background: #fff; }
  .phone-scroll { width: 100%; height: 100%; overflow: hidden; background: #fff; }
  .phone-scroll > section, .phone-scroll > div { min-height: 100%; }
  @media print {
    body { padding: 0; }
  }
</style>
</head>
<body>
  <main id="overview">
    <header class="header">
      <div>
        <h1>公众号排版主题总览</h1>
        <p>同一段示例内容套用当前 gzh-publish 注册主题生成</p>
      </div>
      <div class="badge">${THEMES.length} themes · generated from current code</div>
    </header>
    <section class="grid">
      ${cards.join('\n')}
    </section>
  </main>
</body>
</html>`;

  fs.writeFileSync(htmlPath, html);
  console.log(pathToFileURL(htmlPath).href);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
