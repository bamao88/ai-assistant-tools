#!/usr/bin/env bun
/**
 * gzh-publish - 微信公众号自动排版发布工具
 *
 * Usage:
 *   bun src/index.ts article.md                     # Default theme, create draft
 *   bun src/index.ts article.md --theme claude      # Specify theme
 *   bun src/index.ts article.md --publish           # Create draft + publish
 *   bun src/index.ts article.md --dry-run           # Preview HTML output only
 *   bun src/index.ts --list-themes                  # List all available themes
 *   bun src/index.ts --check-auth                   # Test WeChat credentials
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import matter from 'gray-matter';
import { typeset } from './typeset';
import { THEME_GROUPS, THEMES } from './lib/themes/index';
import { getAccessToken, uploadImage, createDraft, publishDraft } from './wechat';

// ─── Config ──────────────────────────────────────────────────────────────────

interface Config {
  appId: string;
  appSecret: string;
}

function loadConfig(profile?: string): Config | null {
  // Priority: env vars > ~/.gzh-publish/config.json (profile or default) > .env
  const appId = process.env.WECHAT_APP_ID;
  const appSecret = process.env.WECHAT_APP_SECRET;

  if (!profile && appId && appSecret) {
    return { appId, appSecret };
  }

  // Try ~/.gzh-publish/config.json
  const configFile = path.join(os.homedir(), '.gzh-publish', 'config.json');
  if (fs.existsSync(configFile)) {
    try {
      const data = JSON.parse(fs.readFileSync(configFile, 'utf-8'));

      // New multi-profile format: { profiles: { mdx: {...}, wxp: {...} }, default: "mdx" }
      if (data.profiles && typeof data.profiles === 'object') {
        const profileName = profile || data.default || Object.keys(data.profiles)[0];
        const p = data.profiles[profileName];
        if (!p) {
          console.error(`错误：profile "${profileName}" 不存在。可用 profile：${Object.keys(data.profiles).join(', ')}`);
          return null;
        }
        if (p.WECHAT_APP_ID && p.WECHAT_APP_SECRET) {
          return { appId: p.WECHAT_APP_ID, appSecret: p.WECHAT_APP_SECRET };
        }
      }

      // Legacy flat format: { WECHAT_APP_ID: "...", WECHAT_APP_SECRET: "..." }
      if (!profile && data.WECHAT_APP_ID && data.WECHAT_APP_SECRET) {
        return { appId: data.WECHAT_APP_ID, appSecret: data.WECHAT_APP_SECRET };
      }
    } catch {
      // ignore
    }
  }

  // Try .env in current directory (only when no profile specified)
  if (!profile) {
    const envFile = path.join(process.cwd(), '.env');
    if (fs.existsSync(envFile)) {
      const lines = fs.readFileSync(envFile, 'utf-8').split('\n');
      const env: Record<string, string> = {};
      for (const line of lines) {
        const match = line.match(/^([A-Z_]+)\s*=\s*(.+)$/);
        if (match) env[match[1]] = match[2].trim().replace(/^["']|["']$/g, '');
      }
      if (env.WECHAT_APP_ID && env.WECHAT_APP_SECRET) {
        return { appId: env.WECHAT_APP_ID, appSecret: env.WECHAT_APP_SECRET };
      }
    }
  }

  return null;
}

// ─── Frontmatter ─────────────────────────────────────────────────────────────

interface Frontmatter {
  title?: string;
  theme?: string;
  cover?: string;
  author?: string;
  digest?: string;
  abstract?: string;
  published?: string | boolean;
}

function updateFrontmatter(filePath: string, updates: Partial<Frontmatter>): void {
  const content = fs.readFileSync(filePath, 'utf-8');
  const parsed = matter(content);
  const newData = { ...parsed.data, ...updates };
  const newContent = matter.stringify(parsed.content, newData);
  fs.writeFileSync(filePath, newContent, 'utf-8');
}

interface LeadingTitle {
  title: string;
  body: string;
}

function plainTitle(value: string): string {
  return value
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/[`*_~]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function stripLeadingBlankLines(content: string): string {
  return content.replace(/^(?:[ \t]*\r?\n)+/, '');
}

function extractLeadingTitle(content: string): LeadingTitle | null {
  const leadingBlankMatch = content.match(/^(?:[ \t]*\r?\n)*/);
  const leadingBlankLength = leadingBlankMatch?.[0].length ?? 0;
  const rest = content.slice(leadingBlankLength);

  const atxMatch = rest.match(/^[ \t]{0,3}#(?!#)[ \t]+(.+?)(?:[ \t]+#+[ \t]*)?(?:\r?\n|$)/);
  if (atxMatch) {
    return {
      title: atxMatch[1].trim(),
      body: stripLeadingBlankLines(rest.slice(atxMatch[0].length)),
    };
  }

  const setextMatch = rest.match(/^([^\r\n]+)\r?\n[ \t]{0,3}=+[ \t]*(?:\r?\n|$)/);
  if (setextMatch) {
    const title = setextMatch[1].trim();
    if (title) {
      return {
        title,
        body: stripLeadingBlankLines(rest.slice(setextMatch[0].length)),
      };
    }
  }

  return null;
}

function resolveTitleAndBody(frontmatter: Frontmatter, content: string, fallbackTitle: string): { title: string; body: string } {
  const leadingTitle = extractLeadingTitle(content);
  const title = frontmatter.title || (leadingTitle ? plainTitle(leadingTitle.title) : fallbackTitle);

  if (!leadingTitle) {
    return { title, body: content };
  }

  const shouldStripLeadingTitle = !frontmatter.title || plainTitle(leadingTitle.title) === plainTitle(title);
  return {
    title,
    body: shouldStripLeadingTitle ? leadingTitle.body : content,
  };
}

// ─── CLI ─────────────────────────────────────────────────────────────────────

function printThemes(): void {
  console.log('\n可用排版主题：\n');
  for (const group of THEME_GROUPS) {
    console.log(`  【${group.label}】`);
    for (const theme of group.themes) {
      console.log(`    ${theme.id.padEnd(14)} ${theme.name.padEnd(8)} ${theme.description}`);
    }
    console.log('');
  }
}

function parseArgs(args: string[]): {
  file?: string;
  theme: string;
  publish: boolean;
  dryRun: boolean;
  listThemes: boolean;
  checkAuth: boolean;
  forceRefresh: boolean;
  profile?: string;
} {
  const result = {
    file: undefined as string | undefined,
    theme: 'medium',
    publish: false,
    dryRun: false,
    listThemes: false,
    checkAuth: false,
    forceRefresh: false,
    profile: undefined as string | undefined,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--list-themes') {
      result.listThemes = true;
    } else if (arg === '--check-auth') {
      result.checkAuth = true;
    } else if (arg === '--publish') {
      result.publish = true;
    } else if (arg === '--dry-run') {
      result.dryRun = true;
    } else if (arg === '--refresh') {
      result.forceRefresh = true;
    } else if (arg === '--theme' && args[i + 1]) {
      result.theme = args[++i];
    } else if (arg === '--profile' && args[i + 1]) {
      result.profile = args[++i];
    } else if (!arg.startsWith('--') && !result.file) {
      result.file = arg;
    }
  }

  return result;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const opts = parseArgs(args);

  // --list-themes
  if (opts.listThemes) {
    printThemes();
    return;
  }

  // Load config for API operations
  const config = loadConfig(opts.profile);

  // --check-auth
  if (opts.checkAuth) {
    if (!config) {
      console.error('错误：未找到微信配置。请设置 WECHAT_APP_ID 和 WECHAT_APP_SECRET 环境变量。');
      process.exit(1);
    }
    console.log('正在验证微信凭证...');
    try {
      await getAccessToken(config.appId, config.appSecret, true);
      console.log('✓ 微信凭证有效，连接成功！');
    } catch (err) {
      console.error('✗ 验证失败：', err instanceof Error ? err.message : err);
      process.exit(1);
    }
    return;
  }

  // Require a file
  if (!opts.file) {
    console.log('用法：bun src/index.ts <file.md> [options]');
    console.log('');
    console.log('选项：');
    console.log('  --theme <id>       指定主题（默认：medium）');
    console.log('  --profile <name>   指定账号 profile（多账号时使用）');
    console.log('  --publish          发布草稿（默认仅创建草稿）');
    console.log('  --dry-run          预览 HTML，不上传');
    console.log('  --refresh          强制刷新 access_token');
    console.log('  --list-themes      列出所有可用主题');
    console.log('  --check-auth       验证微信凭证');
    process.exit(0);
  }

  // Resolve file path
  const filePath = path.isAbsolute(opts.file)
    ? opts.file
    : path.join(process.cwd(), opts.file);

  if (!fs.existsSync(filePath)) {
    console.error(`错误：文件不存在：${filePath}`);
    process.exit(1);
  }

  // Parse markdown + frontmatter
  const rawContent = fs.readFileSync(filePath, 'utf-8');
  const parsed = matter(rawContent);
  const frontmatter = parsed.data as Frontmatter;
  const { title, body: bodyContent } = resolveTitleAndBody(
    frontmatter,
    parsed.content,
    path.basename(filePath, '.md')
  );
  const fileDir = path.dirname(filePath);

  // --- 自动补全缺失字段 ---
  if (!frontmatter.digest && frontmatter.abstract) {
    frontmatter.digest = frontmatter.abstract.replace(/\n/g, ' ').slice(0, 120);
  }
  if (!frontmatter.digest) {
    frontmatter.digest = bodyContent.replace(/[#*>\-\n]/g, ' ').trim().slice(0, 120);
  }
  if (!frontmatter.cover) {
    const imgRegex = /!\[.*?\]\(<?(.+?)>?\)/g;
    let imgMatch: RegExpExecArray | null;
    while ((imgMatch = imgRegex.exec(bodyContent)) !== null) {
      if (!/\.svg$/i.test(imgMatch[1])) break;
      imgMatch = null;
    }
    if (imgMatch) {
      const imgSrc = imgMatch[1];
      frontmatter.cover = path.isAbsolute(imgSrc) ? imgSrc : path.join(fileDir, imgSrc);
    } else {
      frontmatter.cover = path.join(__dirname, '..', 'assets', 'default-cover.png');
    }
  }

  // Check published status
  if (frontmatter.published === true || frontmatter.published === 'true') {
    console.log(`跳过：文章已发布 (${filePath})`);
    return;
  }

  // Determine theme (frontmatter > CLI > default)
  const themeId = frontmatter.theme || opts.theme || 'medium';

  // Validate theme
  const validTheme = THEMES.find(t => t.id === themeId);
  if (!validTheme) {
    console.error(`错误：未知主题 "${themeId}"。使用 --list-themes 查看可用主题。`);
    process.exit(1);
  }

  console.log(`排版文章：${title}`);
  console.log(`主题：${validTheme.name} (${themeId})`);

  // --dry-run: generate HTML without token (local images → base64)
  if (opts.dryRun) {
    const html = await typeset(bodyContent, {
      theme: themeId,
      baseDir: fileDir,
      convertImages: true,
    });
    const outputPath = filePath.replace(/\.md$/, '.html');
    const fullHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
</head>
<body>
${html}
</body>
</html>`;
    fs.writeFileSync(outputPath, fullHtml, 'utf-8');
    console.log(`\n✓ HTML 预览已保存至：${outputPath}`);
    return;
  }

  // Require config for upload
  if (!config) {
    console.error('\n错误：未找到微信配置。');
    console.error('请设置环境变量：WECHAT_APP_ID 和 WECHAT_APP_SECRET');
    console.error('或创建配置文件：~/.gzh-publish/config.json');
    process.exit(1);
  }

  // Get access token first (needed for both image upload and draft creation)
  console.log('\n正在获取 access_token...');
  const token = await getAccessToken(config.appId, config.appSecret, opts.forceRefresh);
  console.log('✓ 已获取 access_token');

  // Generate HTML with token so local images are uploaded to WeChat CDN
  const html = await typeset(bodyContent, {
    theme: themeId,
    baseDir: fileDir,
    convertImages: true,
    accessToken: token,
  });

  // Upload cover image
  let thumbMediaId = '';
  if (frontmatter.cover) {
    const coverPath = path.isAbsolute(frontmatter.cover)
      ? frontmatter.cover
      : path.join(fileDir, frontmatter.cover);

    if (fs.existsSync(coverPath)) {
      console.log(`\n正在上传封面图：${frontmatter.cover}`);
      thumbMediaId = await uploadImage(coverPath, token);
      console.log(`✓ 封面图已上传，media_id: ${thumbMediaId}`);
    } else {
      console.warn(`警告：封面图不存在：${coverPath}`);
    }
  }

  if (!thumbMediaId) {
    console.error('\n错误：必须提供封面图（在 frontmatter 中设置 cover: your-image.jpg）');
    console.error('微信公众号草稿必须有封面图。');
    process.exit(1);
  }

  // Create draft
  console.log('\n正在创建草稿...');
  const draftMediaId = await createDraft({
    title,
    content: html,
    thumbMediaId,
    author: frontmatter.author,
    digest: frontmatter.digest,
  }, token);
  console.log(`✓ 草稿已创建，media_id: ${draftMediaId}`);

  // Update frontmatter
  updateFrontmatter(filePath, { published: 'draft' });
  console.log('✓ 已更新 frontmatter: published: draft');

  // Publish if requested
  if (opts.publish) {
    console.log('\n正在发布文章...');
    const publishId = await publishDraft(draftMediaId, token);
    console.log(`✓ 文章已发布，publish_id: ${publishId}`);
    updateFrontmatter(filePath, { published: 'true' });
    console.log('✓ 已更新 frontmatter: published: true');
  }

  console.log(`\n✓ 完成！请查看微信公众号后台草稿箱。`);
}

main().catch(err => {
  console.error('错误：', err instanceof Error ? err.message : err);
  process.exit(1);
});
