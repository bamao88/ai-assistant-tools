import fs from 'node:fs/promises'
import path from 'node:path'
import { escapeHtml } from './util.js'

export function parseFrontmatter(markdown) {
  if (!markdown.startsWith('---\n')) return { data: {}, body: markdown }
  const end = markdown.indexOf('\n---', 4)
  if (end === -1) return { data: {}, body: markdown }

  const yaml = markdown.slice(4, end)
  const data = {}
  for (const line of yaml.split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/)
    if (!match) continue
    data[match[1]] = match[2].replace(/^["']|["']$/g, '').trim()
  }

  return { data, body: markdown.slice(end + 5).replace(/^\r?\n/, '') }
}

export function extractMarkdownTitle(markdown) {
  const match = markdown.match(/^\s*#\s+(.+)$/m)
  return match?.[1]?.trim() || ''
}

export function removeLeadingH1(markdown) {
  return markdown.replace(/^\s*#\s+.+\r?\n+/, '')
}

function inlineMarkdown(text) {
  let value = escapeHtml(text)
  value = value.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img alt="$1" src="$2" />')
  value = value.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
  value = value.replace(/`([^`]+)`/g, '<code>$1</code>')
  value = value.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  value = value.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  return value
}

export function markdownToHtml(markdown) {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const out = []
  let paragraph = []
  let inCode = false
  let codeLang = ''
  let code = []
  let listType = null

  const flushParagraph = () => {
    if (paragraph.length === 0) return
    out.push(`<p>${inlineMarkdown(paragraph.join(' '))}</p>`)
    paragraph = []
  }
  const closeList = () => {
    if (!listType) return
    out.push(`</${listType}>`)
    listType = null
  }

  for (const line of lines) {
    const fence = line.match(/^```([A-Za-z0-9_-]*)\s*$/)
    if (fence) {
      if (inCode) {
        out.push(`<pre><code${codeLang ? ` class="language-${codeLang}"` : ''}>${escapeHtml(code.join('\n'))}</code></pre>`)
        inCode = false
        codeLang = ''
        code = []
      } else {
        flushParagraph()
        closeList()
        inCode = true
        codeLang = fence[1] || ''
      }
      continue
    }

    if (inCode) {
      code.push(line)
      continue
    }

    if (!line.trim()) {
      flushParagraph()
      closeList()
      continue
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      flushParagraph()
      closeList()
      const level = heading[1].length
      out.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`)
      continue
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/)
    if (unordered) {
      flushParagraph()
      if (listType !== 'ul') {
        closeList()
        listType = 'ul'
        out.push('<ul>')
      }
      out.push(`<li>${inlineMarkdown(unordered[1])}</li>`)
      continue
    }

    const ordered = line.match(/^\s*\d+\.\s+(.+)$/)
    if (ordered) {
      flushParagraph()
      if (listType !== 'ol') {
        closeList()
        listType = 'ol'
        out.push('<ol>')
      }
      out.push(`<li>${inlineMarkdown(ordered[1])}</li>`)
      continue
    }

    const quote = line.match(/^>\s*(.+)$/)
    if (quote) {
      flushParagraph()
      closeList()
      out.push(`<blockquote>${inlineMarkdown(quote[1])}</blockquote>`)
      continue
    }

    paragraph.push(line.trim())
  }

  if (inCode) {
    out.push(`<pre><code${codeLang ? ` class="language-${codeLang}"` : ''}>${escapeHtml(code.join('\n'))}</code></pre>`)
  }
  flushParagraph()
  closeList()
  return out.join('\n')
}

export function countImages(markdownOrHtml) {
  const markdownMatches = markdownOrHtml.match(/!\[[^\]]*\]\([^)]+\)/g) || []
  const htmlMatches = markdownOrHtml.match(/<img\b[^>]*\bsrc=/gi) || []
  return markdownMatches.length + htmlMatches.length
}

export async function parseArticleFile(file, options = {}) {
  const absolutePath = path.resolve(file)
  const raw = await fs.readFile(absolutePath, 'utf8')
  const baseDir = path.dirname(absolutePath)
  const ext = path.extname(absolutePath).toLowerCase()

  if (ext === '.html' || ext === '.htm') {
    const title =
      options.title ||
      raw.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]?.trim() ||
      raw.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)?.[1]?.replace(/<[^>]+>/g, '').trim() ||
      ''
    return {
      file: absolutePath,
      baseDir,
      title,
      markdown: raw.replace(/<[^>]+>/g, ''),
      html: raw,
      metadata: {},
      cover: options.cover || '',
      imageCount: countImages(raw),
      format: 'html',
    }
  }

  const { data, body } = parseFrontmatter(raw)
  const extractedTitle = extractMarkdownTitle(body)
  const title = options.title || data.title || extractedTitle
  const markdown = extractedTitle ? removeLeadingH1(body) : body

  return {
    file: absolutePath,
    baseDir,
    title,
    markdown,
    html: markdownToHtml(markdown),
    metadata: data,
    cover: options.cover || data.cover || '',
    imageCount: countImages(markdown),
    format: 'markdown',
  }
}
