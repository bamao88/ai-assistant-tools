import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import { JSDOM } from 'jsdom';
import { THEMES } from './themes/index';

export const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: false,
  highlight: function (str, lang) {
    let codeContent = '';
    if (lang && hljs.getLanguage(lang)) {
      try {
        codeContent = hljs.highlight(str, { language: lang }).value;
      } catch (__) {
        codeContent = md.utils.escapeHtml(str);
      }
    } else {
      codeContent = md.utils.escapeHtml(str);
    }

    const dots = `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ff5f56;margin-right:5px;"></span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ffbd2e;margin-right:5px;"></span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#27c93f;"></span>`;

    return `<pre><div class="code-dots" style="padding:8px 16px 4px;margin-bottom:4px;">${dots}</div><code class="hljs language-${lang}">${codeContent}</code></pre>`;
  }
});

export function preprocessMarkdown(content: string): string {
  // Fix fragmented bold/hr patterns from rich-text paste
  content = content.replace(/^[ ]{0,3}(\*[ ]*\*[ ]*\*[* ]*)\s*$/gm, '***');
  content = content.replace(/^[ ]{0,3}(-[ ]*-[ ]*-[- ]*)\s*$/gm, '---');
  content = content.replace(/^[ ]{0,3}(_[ ]*_[ ]*_[_ ]*)\s*$/gm, '___');
  content = content.replace(/\*\*[ \t]+\*\*/g, ' ');
  content = content.replace(/\*{4,}/g, '');

  // markdown-it may fail to open bold when content starts with punctuation/symbol
  // and `**` is attached directly to preceding text (e.g. `至**-5%**。`).
  // Insert a zero-width separator only inside opening `**...` for these cases.
  content = content.replace(
    /([^\s])\*\*([+\-＋－%％~～!！?？,，.。:：;；、\\/|@#￥$^&*_=（）()【】\[\]《》〈〉「」『』"""'`…·][^\n*]*?)\*\*/g,
    '$1**\u200B$2**'
  );

  return content;
}

export function renderMarkdown(content: string): string {
  const preprocessed = preprocessMarkdown(content);
  return md.render(preprocessed);
}

const NUMBER_FONT_STYLE = [
  'font-family: "Avenir Next", "DIN Alternate", "Helvetica Neue", Arial, sans-serif !important',
  'font-variant-numeric: lining-nums proportional-nums',
  'font-weight: 500',
  'letter-spacing: 0.01em',
].join('; ');

const NUMBER_RUN_RE = /[+\-−]?\d+(?:[.,:/-]\d+)*(?:%|％)?/g;

function wrapNumberRuns(doc: Document): void {
  const walker = doc.createTreeWalker(doc.body, doc.defaultView?.NodeFilter.SHOW_TEXT ?? 4);
  const textNodes: Text[] = [];
  while (walker.nextNode()) {
    textNodes.push(walker.currentNode as Text);
  }

  textNodes.forEach(node => {
    const parent = node.parentElement;
    const text = node.textContent || '';
    if (!parent || !NUMBER_RUN_RE.test(text)) {
      NUMBER_RUN_RE.lastIndex = 0;
      return;
    }
    NUMBER_RUN_RE.lastIndex = 0;
    if (parent.closest('pre, code, script, style, a, [data-number-font]')) return;

    const fragment = doc.createDocumentFragment();
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = NUMBER_RUN_RE.exec(text)) !== null) {
      if (match.index > lastIndex) {
        fragment.appendChild(doc.createTextNode(text.slice(lastIndex, match.index)));
      }
      const span = doc.createElement('span');
      span.setAttribute('data-number-font', 'true');
      span.setAttribute('style', NUMBER_FONT_STYLE);
      span.textContent = match[0];
      fragment.appendChild(span);
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < text.length) {
      fragment.appendChild(doc.createTextNode(text.slice(lastIndex)));
    }
    node.parentNode?.replaceChild(fragment, node);
  });
}

export function applyTheme(html: string, themeId: string): string {
  const theme = THEMES.find(t => t.id === themeId) || THEMES[0];
  const style = theme.styles;

  const dom = new JSDOM(`<!DOCTYPE html><html><body>${html}</body></html>`);
  const doc = dom.window.document;
  const TEXT_NODE = 3;

  // Specific inline overrides to prevent headings from uninheriting styles
  const headingInlineOverrides: Record<string, string> = {
    strong: 'font-weight: 700; color: inherit !important; background-color: transparent !important;',
    em: 'font-style: italic; color: inherit !important; background-color: transparent !important;',
    a: 'color: inherit !important; text-decoration: none !important; border-bottom: 1px solid currentColor !important; background-color: transparent !important;',
    code: 'color: inherit !important; background-color: transparent !important; border: none !important; padding: 0 !important;',
  };

  const getSingleImageNode = (p: Element): Element | null => {
    const children = Array.from(p.childNodes).filter(n =>
      !(n.nodeType === TEXT_NODE && !(n.textContent || '').trim()) &&
      !(n.nodeType === 1 && (n as Element).tagName === 'BR')
    );
    if (children.length !== 1) return null;
    const onlyChild = children[0];
    if ((onlyChild as Element).nodeName === 'IMG') return onlyChild as Element;
    if (
      (onlyChild as Element).nodeName === 'A' &&
      onlyChild.childNodes.length === 1 &&
      (onlyChild.childNodes[0] as Element).nodeName === 'IMG'
    ) {
      return onlyChild as Element;
    }
    return null;
  };

  // Merge consecutive single-image paragraphs into pair-wise side-by-side grids
  const paragraphSnapshot = Array.from(doc.querySelectorAll('p'));
  for (const paragraph of paragraphSnapshot) {
    if (!paragraph.isConnected) continue;
    const parent = paragraph.parentElement;
    if (!parent) continue;
    if (!getSingleImageNode(paragraph)) continue;

    const run: Element[] = [paragraph];
    let cursor = paragraph.nextElementSibling;
    while (cursor && cursor.tagName === 'P') {
      const p = cursor as Element;
      if (!getSingleImageNode(p)) break;
      run.push(p);
      cursor = p.nextElementSibling;
    }
    if (run.length < 2) continue;

    for (let i = 0; i + 1 < run.length; i += 2) {
      const first = run[i];
      const second = run[i + 1];
      if (!first.isConnected || !second.isConnected) continue;
      const firstImageNode = getSingleImageNode(first);
      const secondImageNode = getSingleImageNode(second);
      if (!firstImageNode || !secondImageNode) continue;

      const gridParagraph = doc.createElement('p');
      gridParagraph.classList.add('image-grid');
      gridParagraph.setAttribute('style', 'display: flex; justify-content: center; gap: 8px; margin: 24px 0; align-items: flex-start;');
      gridParagraph.appendChild(firstImageNode);
      gridParagraph.appendChild(secondImageNode);
      first.before(gridParagraph);
      first.remove();
      second.remove();
    }
  }

  // Process multi-image paragraphs
  const paragraphs = doc.querySelectorAll('p');
  paragraphs.forEach(p => {
    const children = Array.from(p.childNodes).filter(n =>
      !(n.nodeType === TEXT_NODE && !(n.textContent || '').trim())
    );
    const isAllImages = children.length > 1 && children.every(n =>
      (n as Element).nodeName === 'IMG' ||
      ((n as Element).nodeName === 'A' && n.childNodes.length === 1 && (n.childNodes[0] as Element).nodeName === 'IMG')
    );
    if (isAllImages) {
      p.classList.add('image-grid');
      p.setAttribute('style', 'display: flex; justify-content: center; gap: 8px; margin: 24px 0; align-items: flex-start;');
      p.querySelectorAll('img').forEach(img => {
        const w = 100 / children.length;
        img.setAttribute('style', `width: calc(${w}% - ${8 * (children.length - 1) / children.length}px); margin: 0; height: auto;`);
      });
    }
  });

  // Non-CSS keys used as flags, skip in querySelectorAll
  const nonCssKeys = new Set([
    'codeDots',
    'codeHighlight',
    'ulMarker',
    'olMarker',
    'videoLink',
    'videoLinkText',
  ]);

  // Apply theme styles to each element type
  Object.keys(style).forEach((selector) => {
    if (selector === 'pre code' || nonCssKeys.has(selector)) return;
    const elements = doc.querySelectorAll(selector);
    elements.forEach(el => {
      if (selector === 'code' && el.parentElement?.tagName === 'PRE') return;
      if (el.tagName === 'IMG' && el.closest('.image-grid')) return;
      const currentStyle = el.getAttribute('style') || '';
      el.setAttribute('style', currentStyle + '; ' + style[selector as keyof typeof style]);
    });
  });

  // WeChat forces indentation on <ul>/<ol> that CSS cannot override.
  // Convert lists to plain rows with manual bullet/number characters.
  const liStyle = style.li || '';
  const ulStyle = style.ul || '';
  const olStyle = style.ol || '';
  const ulMarkerStyle = style.ulMarker || '';
  const olMarkerStyle = style.olMarker || '';

  const appendListContent = (target: Element, li: Element): Element[] => {
    const trailingBlocks: Element[] = [];
    Array.from(li.childNodes).forEach(node => {
      if (node.nodeType === 1) {
        const el = node as Element;
        if (['UL', 'OL', 'BLOCKQUOTE'].includes(el.tagName)) {
          trailingBlocks.push(el.cloneNode(true) as Element);
          return;
        }
        if (el.tagName === 'P') {
          Array.from(el.childNodes).forEach(child => target.appendChild(child.cloneNode(true)));
          return;
        }
      }
      target.appendChild(node.cloneNode(true));
    });
    return trailingBlocks;
  };

  // Process ordered lists first (before ul, since ol can contain nested ul)
  doc.querySelectorAll('ol').forEach(ol => {
    const wrapper = doc.createElement('section');
    wrapper.setAttribute('style', olStyle.replace(/list-style[^;]*(;|$)/g, '') + '; padding: 0 !important; margin-left: 0 !important;');
    const items = Array.from(ol.querySelectorAll(':scope > li'));
    items.forEach((li, idx) => {
      const row = doc.createElement('p');
      row.setAttribute('style', `${liStyle}; margin: 8px 0 !important;`);
      const marker = doc.createElement('span');
      marker.setAttribute('data-number-font', 'skip');
      marker.setAttribute('style', `margin-right: 6px; ${olMarkerStyle}`);
      marker.textContent = `${idx + 1}.`;
      row.appendChild(marker);
      const trailingBlocks = appendListContent(row, li);
      wrapper.appendChild(row);
      trailingBlocks.forEach(block => wrapper.appendChild(block));
    });
    ol.replaceWith(wrapper);
  });

  doc.querySelectorAll('ul').forEach(ul => {
    const depth = (() => {
      let d = 0, node = ul.parentElement;
      while (node) { if (node.tagName === 'UL') d++; node = node.parentElement; }
      return d;
    })();
    const bullets = ['•', '◦', '▪'];
    const bullet = bullets[Math.min(depth, bullets.length - 1)];

    const wrapper = doc.createElement('section');
    wrapper.setAttribute('style', ulStyle.replace(/list-style[^;]*(;|$)/g, '') + '; padding: 0 !important; margin-left: 0 !important;');
    const items = Array.from(ul.querySelectorAll(':scope > li'));
    items.forEach(li => {
      const row = doc.createElement('p');
      row.setAttribute('style', `${liStyle}; margin: 8px 0 !important;`);
      const marker = doc.createElement('span');
      marker.setAttribute('style', `margin-right: 6px; ${ulMarkerStyle}`);
      marker.textContent = bullet;
      row.appendChild(marker);
      const trailingBlocks = appendListContent(row, li);
      wrapper.appendChild(row);
      trailingBlocks.forEach(block => wrapper.appendChild(block));
    });
    ul.replaceWith(wrapper);
  });

  // Remove inner margin of paragraphs inside blockquotes
  doc.querySelectorAll('blockquote p').forEach(p => {
    const currentStyle = p.getAttribute('style') || '';
    p.setAttribute('style', `${currentStyle}; margin: 0 !important;`);
  });

  // Video links are source references, not body text. Let themes make them quiet
  // while keeping ordinary blockquotes available for editorial callouts.
  const videoLinkStyle = style.videoLink || '';
  const videoLinkTextStyle = style.videoLinkText || '';
  if (videoLinkStyle || videoLinkTextStyle) {
    doc.querySelectorAll('blockquote, p').forEach(node => {
      if (node.tagName === 'P' && node.closest('blockquote')) return;
      const text = (node.textContent || '').trim();
      if (!/^(?:视频链接|链接)[：:]/.test(text)) return;
      if (videoLinkStyle) {
        const currentStyle = node.getAttribute('style') || '';
        node.setAttribute('style', `${currentStyle}; ${videoLinkStyle}`);
      }
      if (videoLinkTextStyle) {
        const textNodes = node.tagName === 'P'
          ? [node, ...Array.from(node.querySelectorAll('span, a'))]
          : Array.from(node.querySelectorAll('p, span, a'));
        textNodes.forEach(child => {
          const currentStyle = child.getAttribute('style') || '';
          child.setAttribute('style', `${currentStyle}; ${videoLinkTextStyle}`);
        });
      }
    });
  }

  // Remove empty <li> elements (caused by blank lines in source markdown)
  doc.querySelectorAll('li').forEach(li => {
    if (!(li.textContent || '').trim()) {
      li.remove();
    }
  });

  // Syntax highlighting color schemes
  const hljsSchemes: Record<string, Record<string, string>> = {
    github: {
      'hljs-comment': 'color: #6a737d; font-style: normal;',
      'hljs-quote': 'color: #6a737d; font-style: normal;',
      'hljs-keyword': 'color: #d73a49; font-weight: 600;',
      'hljs-selector-tag': 'color: #d73a49; font-weight: 600;',
      'hljs-string': 'color: #032f62;',
      'hljs-title': 'color: #6f42c1; font-weight: 600;',
      'hljs-section': 'color: #6f42c1; font-weight: 600;',
      'hljs-type': 'color: #005cc5; font-weight: 600;',
      'hljs-number': 'color: #005cc5;',
      'hljs-literal': 'color: #005cc5;',
      'hljs-built_in': 'color: #005cc5;',
      'hljs-variable': 'color: #e36209;',
      'hljs-template-variable': 'color: #e36209;',
      'hljs-tag': 'color: #22863a;',
      'hljs-name': 'color: #22863a;',
      'hljs-attr': 'color: #6f42c1;',
    },
    mono: {
      'hljs-comment': 'color: #888888; font-style: normal;',
      'hljs-quote': 'color: #888888; font-style: normal;',
      'hljs-keyword': 'color: #333333; font-weight: 600;',
      'hljs-selector-tag': 'color: #333333; font-weight: 600;',
      'hljs-string': 'color: #555555;',
      'hljs-title': 'color: #333333; font-weight: 600;',
      'hljs-section': 'color: #333333; font-weight: 600;',
      'hljs-type': 'color: #333333; font-weight: 600;',
      'hljs-number': 'color: #555555;',
      'hljs-literal': 'color: #555555;',
      'hljs-built_in': 'color: #333333;',
      'hljs-variable': 'color: #555555;',
      'hljs-template-variable': 'color: #555555;',
      'hljs-tag': 'color: #333333;',
      'hljs-name': 'color: #333333;',
      'hljs-attr': 'color: #555555;',
    },
  };

  const schemeName = style.codeHighlight || 'github';
  const hljsColors = hljsSchemes[schemeName] || hljsSchemes.github;

  const codeTokens = doc.querySelectorAll('.hljs span');
  codeTokens.forEach(span => {
    let inlineStyle = span.getAttribute('style') || '';
    if (inlineStyle && !inlineStyle.endsWith(';')) inlineStyle += '; ';
    span.classList.forEach(cls => {
      if (hljsColors[cls]) {
        inlineStyle += hljsColors[cls] + '; ';
      }
    });
    if (inlineStyle) {
      span.setAttribute('style', inlineStyle);
    }
  });

  doc.querySelectorAll('pre').forEach(pre => {
    const currentStyle = pre.getAttribute('style') || '';
    pre.setAttribute('style', `${currentStyle}; font-variant-ligatures: none; tab-size: 2; overflow-x: auto !important; -webkit-overflow-scrolling: touch;`);
  });

  doc.querySelectorAll('pre code, pre .hljs, .hljs').forEach(codeNode => {
    const currentStyle = codeNode.getAttribute('style') || '';
    codeNode.setAttribute(
      'style',
      `${currentStyle}; display: block; font-size: inherit !important; line-height: inherit !important; font-style: normal !important; white-space: nowrap; word-break: normal; overflow-wrap: normal;`
    );

    // WeChat strips white-space:pre — wrap each line in a nowrap block span
    // and convert spaces to &nbsp; in text nodes only (preserve HTML tag attributes)
    const rawHtml = codeNode.innerHTML;
    const lines = rawHtml.split('\n');
    const lineStyle = 'display:block;white-space:nowrap;min-height:1.5em;';
    const wrappedLines = lines.map(line => {
      // Replace spaces in text content only (outside HTML tags)
      const safeLineHtml = line.replace(/([^<]*)(<[^>]*>)?/g, (_, text, tag) => {
        const safeText = text ? text.replace(/ /g, '\u00A0') : '';
        return safeText + (tag || '');
      });
      return `<span style="${lineStyle}">${safeLineHtml || '\u00A0'}</span>`;
    });
    codeNode.innerHTML = wrappedLines.join('');
  });

  // Code block dots: hide if theme sets codeDots to 'none'
  if (style.codeDots === 'none') {
    doc.querySelectorAll('.code-dots').forEach(el => el.remove());
  }

  // Heading inline overrides
  const headings = doc.querySelectorAll('h1, h2, h3, h4, h5, h6');
  headings.forEach(heading => {
    Object.keys(headingInlineOverrides).forEach(tag => {
      heading.querySelectorAll(tag).forEach(node => {
        const override = headingInlineOverrides[tag];
        node.setAttribute('style', `${node.getAttribute('style') || ''}; ${override}`);
      });
    });
  });

  wrapNumberRuns(doc);

  doc.querySelectorAll('h1 [data-number-font], h2 [data-number-font], h3 [data-number-font], h4 [data-number-font], h5 [data-number-font], h6 [data-number-font]').forEach(node => {
    const currentStyle = node.getAttribute('style') || '';
    node.setAttribute('style', `${currentStyle}; color: inherit !important; font-size: inherit !important; font-weight: inherit !important; line-height: inherit !important;`);
  });

  // Apply image styling: use theme img style, fallback to default decorated style
  const themeImgStyle = style.img || '';
  const hasThemeImg = Boolean(themeImgStyle);
  const defaultImgSingle = 'display:block; width:100%; max-width:100%; height:auto; margin:30px auto !important; padding:8px !important; box-sizing:border-box; border-radius:14px !important; box-shadow:0 16px 34px rgba(15,23,42,0.22), 0 4px 10px rgba(15,23,42,0.12); border:1px solid rgba(15,23,42,0.12);';
  const defaultImgGrid = 'display:block; max-width:100%; height:auto; margin:0 !important; padding:8px !important; box-sizing:border-box; border-radius:14px !important; box-shadow:0 12px 28px rgba(15,23,42,0.18), 0 2px 8px rgba(15,23,42,0.12); border:1px solid rgba(255,255,255,0.75);';

  doc.querySelectorAll('img').forEach(img => {
    const inGrid = Boolean(img.closest('.image-grid'));
    const currentStyle = img.getAttribute('style') || '';
    if (hasThemeImg) {
      // Theme controls image style entirely
      const base = inGrid
        ? 'display:block; max-width:100%; height:auto; margin:0 !important; box-sizing:border-box;'
        : 'display:block; width:100%; max-width:100%; height:auto; box-sizing:border-box;';
      img.setAttribute('style', `${currentStyle}; ${base}`);
    } else {
      // Fallback: decorated style with shadow + rounded corners
      img.setAttribute('style', `${currentStyle}; ${inGrid ? defaultImgGrid : defaultImgSingle}`);
    }
  });

  const container = doc.createElement('div');
  container.setAttribute('style', style.container);
  container.innerHTML = doc.body.innerHTML;
  return container.outerHTML;
}
