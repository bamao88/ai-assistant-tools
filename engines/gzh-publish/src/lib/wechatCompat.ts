import { JSDOM } from 'jsdom';
import * as fs from 'fs';
import * as path from 'path';
import * as https from 'https';
import * as http from 'http';
import { THEMES } from './themes/index';
import { uploadContentImage } from '../wechat';

/**
 * Fetch a remote image as base64 data URL (Node.js implementation).
 */
function fetchImageAsBase64(imgUrl: string): Promise<string> {
  return new Promise((resolve) => {
    if (imgUrl.startsWith('data:')) return resolve(imgUrl);

    const protocol = imgUrl.startsWith('https://') ? https : http;
    const req = protocol.get(imgUrl, { timeout: 5000 }, (res) => {
      const chunks: Buffer[] = [];
      res.on('data', (chunk: Buffer) => chunks.push(chunk));
      res.on('end', () => {
        const buffer = Buffer.concat(chunks);
        const contentType = res.headers['content-type'] || 'image/jpeg';
        const base64 = buffer.toString('base64');
        resolve(`data:${contentType};base64,${base64}`);
      });
      res.on('error', () => resolve(imgUrl));
    });
    req.on('error', () => resolve(imgUrl));
    req.on('timeout', () => { req.destroy(); resolve(imgUrl); });
  });
}

/**
 * Convert a local image path to base64 data URL.
 */
function localImageToBase64(imgPath: string): string | null {
  try {
    if (!fs.existsSync(imgPath)) return null;
    const data = fs.readFileSync(imgPath);
    const ext = path.extname(imgPath).toLowerCase().replace('.', '');
    const mimeType = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg'
      : ext === 'png' ? 'image/png'
      : ext === 'gif' ? 'image/gif'
      : ext === 'webp' ? 'image/webp'
      : 'image/png';
    return `data:${mimeType};base64,${data.toString('base64')}`;
  } catch {
    return null;
  }
}

/**
 * Apply WeChat compatibility transformations to HTML content.
 * Ported from raphael-publish's makeWeChatCompatible() for Node.js/JSDOM.
 */
export async function applyWechatCompat(html: string, options: {
  themeId?: string;
  baseDir?: string;
  convertImages?: boolean;
  accessToken?: string;  // If provided, upload local images to WeChat CDN
} = {}): Promise<string> {
  const dom = new JSDOM(`<!DOCTYPE html><html><body>${html}</body></html>`);
  const doc = dom.window.document;
  const TEXT_NODE = 3;

  const theme = THEMES.find(t => t.id === options.themeId) || THEMES[0];
  const containerStyle = theme.styles.container || '';

  // 1. Wrap in <section> (WeChat prefers section as root wrapper)
  const rootNodes = Array.from(doc.body.children);
  const section = doc.createElement('section');
  section.setAttribute('style', containerStyle);
  rootNodes.forEach(node => {
    if (node.tagName === 'DIV' && rootNodes.length === 1) {
      Array.from(node.childNodes).forEach(child => section.appendChild(child));
    } else {
      section.appendChild(node);
    }
  });

  // 2. Flex → Table conversion (WeChat ignores flex in many scenarios)
  const flexLikeNodes = section.querySelectorAll('div, p.image-grid');
  flexLikeNodes.forEach(node => {
    if (node.closest('pre, code')) return;
    const nodeStyle = node.getAttribute('style') || '';
    const isFlexNode = nodeStyle.includes('display: flex') || nodeStyle.includes('display:flex');
    const isImageGrid = node.classList.contains('image-grid');
    if (!isFlexNode && !isImageGrid) return;

    const flexChildren = Array.from(node.children);
    if (flexChildren.every(child => child.tagName === 'IMG' || child.querySelector('img'))) {
      const table = doc.createElement('table');
      table.setAttribute('style', 'width: 100%; border-collapse: collapse; margin: 16px 0; border: none !important;');
      const tbody = doc.createElement('tbody');
      const tr = doc.createElement('tr');
      tr.setAttribute('style', 'border: none !important; background: transparent !important;');

      flexChildren.forEach(child => {
        const td = doc.createElement('td');
        td.setAttribute('style', 'padding: 4px; vertical-align: top; border: none !important; background: transparent !important;');
        td.appendChild(child);
        if (child.tagName === 'IMG') {
          const currentStyle = child.getAttribute('style') || '';
          child.setAttribute('style',
            currentStyle.replace(/(?<![-a-z])width:\s*[^;]+;?/gi, '') +
            ' width: 100% !important; display: block; margin: 0 auto;' +
            ' box-shadow: 0 12px 28px rgba(15,23,42,0.18), 0 2px 8px rgba(15,23,42,0.12);'
          );
        }
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
      table.appendChild(tbody);
      node.parentNode?.replaceChild(table, node);
    } else if (isFlexNode) {
      node.setAttribute('style', nodeStyle.replace(/display:\s*flex;?/g, 'display: block;'));
    }
  });

  // 3. Convert <ul>/<ol> to <p> paragraphs with manual bullet characters.
  // WeChat's rendering engine has a known bug: <li> with margin creates extra empty
  // bullet points. The reliable fix is to avoid <ul>/<li> entirely and use <p> + bullet chars.
  const BULLETS = ['•', '◦', '▪'];
  function convertList(listEl: Element, depth: number): Element[] {
    const isOrdered = listEl.tagName === 'OL';
    const out: Element[] = [];
    let counter = 0;
    Array.from(listEl.children).forEach(li => {
      if (li.tagName !== 'LI') return;
      counter++;
      const bulletChar = isOrdered ? `${counter}.` : (BULLETS[depth] || '•');

      // Separate nested lists from inline content
      const nestedLists: Element[] = [];
      const inlineNodes: Node[] = [];
      Array.from(li.childNodes).forEach(n => {
        const tag = (n as Element).tagName;
        if (tag === 'UL' || tag === 'OL') nestedLists.push(n as Element);
        else inlineNodes.push(n);
      });

      // Copy li's color/font styles, strip margin/padding
      const liStyle = (li.getAttribute('style') || '')
        .replace(/\bmargin[^:]*\s*:[^;]+;?/gi, '')
        .replace(/\bpadding[^:]*\s*:[^;]+;?/gi, '')
        .replace(/\blist-style[^:]*\s*:[^;]+;?/gi, '');
      const indentPx = 24 + depth * 16;

      const p = doc.createElement('p');
      p.setAttribute('style', `${liStyle}; margin: 4px 0 !important; padding-left: ${indentPx}px;`);
      // Bullet + non-breaking space, then inline content
      p.appendChild(doc.createTextNode(`${bulletChar}\u00A0`));
      inlineNodes.forEach(n => p.appendChild(n.cloneNode(true)));
      out.push(p);

      // Recurse into nested lists
      nestedLists.forEach(nested => convertList(nested, depth + 1).forEach(r => out.push(r)));
    });
    return out;
  }

  // Process top-level lists only (nested are handled recursively)
  Array.from(section.querySelectorAll('ul, ol'))
    .filter(list => !list.closest('li'))
    .forEach(list => {
      convertList(list as Element, 0).forEach(p => list.before(p));
      list.remove();
    });

  // 4. Force font inheritance — WeChat overrides inherited styles on text nodes
  const fontMatch = containerStyle.match(/font-family:\s*([^;]+);/);
  const sizeMatch = containerStyle.match(/font-size:\s*([^;]+);/);
  const colorMatch = containerStyle.match(/color:\s*([^;]+);/);
  const lineHeightMatch = containerStyle.match(/line-height:\s*([^;]+);/);

  const textNodes = section.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, blockquote, span');
  textNodes.forEach(node => {
    if (node.tagName === 'SPAN' && node.closest('pre, code')) return;
    let currentStyle = node.getAttribute('style') || '';
    if (fontMatch && !currentStyle.includes('font-family:')) {
      currentStyle += ` font-family: ${fontMatch[1]};`;
    }
    if (lineHeightMatch && !currentStyle.includes('line-height:')) {
      currentStyle += ` line-height: ${lineHeightMatch[1]};`;
    }
    if (sizeMatch && !currentStyle.includes('font-size:') && ['P', 'LI', 'BLOCKQUOTE', 'SPAN'].includes(node.tagName)) {
      currentStyle += ` font-size: ${sizeMatch[1]};`;
    }
    if (colorMatch && !currentStyle.includes('color:')) {
      currentStyle += ` color: ${colorMatch[1]};`;
    }
    node.setAttribute('style', currentStyle.trim());
  });

  // 4b. Force inline display on strong/em/a/code to prevent WeChat block rendering.
  // For <strong>/<b> inside <li>: replace with <span font-weight:bold> entirely —
  // WeChat's rendering engine treats <strong> specially and creates empty bullets
  // even when all decorative styles are stripped.
  section.querySelectorAll('strong, b, em, a, code').forEach(node => {
    if (node.closest('pre')) return;
    let currentStyle = node.getAttribute('style') || '';
    if (!currentStyle.includes('display:') && !currentStyle.includes('display :')) {
      currentStyle += ' display: inline !important;';
    }
    // Inside <li>: replace <strong>/<b> with <span> to avoid WeChat empty-bullet bug.
    if ((node.tagName === 'STRONG' || node.tagName === 'B') && node.closest('li')) {
      const span = doc.createElement('span');
      span.setAttribute('style', 'font-weight: bold;');
      span.innerHTML = node.innerHTML;
      node.parentNode?.replaceChild(span, node);
      return;
    }
    node.setAttribute('style', currentStyle);
  });

  // 5. CJK punctuation attachment — keep punctuation with preceding inline element
  const inlineNodes = section.querySelectorAll('strong, b, em, span, a, code');
  inlineNodes.forEach(node => {
    const next = node.nextSibling;
    if (!next || next.nodeType !== TEXT_NODE) return;
    const text = next.textContent || '';
    const match = text.match(/^\s*([：；，。！？、:])(.*)/s);
    if (!match) return;
    const punct = match[1];
    const rest = match[2] || '';
    node.appendChild(doc.createTextNode(punct));
    if (rest) {
      (next as Text).data = rest;
    } else {
      next.parentNode?.removeChild(next);
    }
  });

  // 6. Convert images: upload local images to WeChat CDN (preferred) or fall back to base64
  if (options.convertImages !== false) {
    const imgs = Array.from(section.querySelectorAll('img'));
    await Promise.all(imgs.map(async img => {
      const src = img.getAttribute('src');
      if (!src || src.startsWith('data:') || src.startsWith('http://') || src.startsWith('https://')) return;

      // Local image path (decode URL-encoding from markdown-it)
      const decodedSrc = decodeURIComponent(src);
      const imgPath = path.isAbsolute(decodedSrc) ? decodedSrc : (options.baseDir ? path.join(options.baseDir, decodedSrc) : decodedSrc);
      if (!fs.existsSync(imgPath)) return;

      if (options.accessToken) {
        // Upload to WeChat CDN — returns permanent URL usable in articles
        try {
          const url = await uploadContentImage(imgPath, options.accessToken);
          img.setAttribute('src', url);
          console.log(`  ✓ 图片已上传：${path.basename(imgPath)} → ${url}`);
        } catch (e) {
          console.warn(`  ⚠ 图片上传失败：${path.basename(imgPath)}`, e instanceof Error ? e.message : e);
          // Fall back to base64 if upload fails
          const base64 = localImageToBase64(imgPath);
          if (base64) img.setAttribute('src', base64);
        }
      } else {
        // No token: use base64 (works for dry-run previews)
        const base64 = localImageToBase64(imgPath);
        if (base64) img.setAttribute('src', base64);
      }
    }));
  }

  doc.body.innerHTML = '';
  doc.body.appendChild(section);

  // Final CJK punctuation zero-width join after closing tags
  let outputHtml = doc.body.innerHTML;
  outputHtml = outputHtml.replace(/(<\/(?:strong|b|em|span|a|code)>)\s*([：；，。！？、])/g, '$1\u2060$2');
  return outputHtml;
}
