import fs from 'node:fs/promises'
import path from 'node:path'
import { guessMimeType, guessExtFromMime } from '../util.js'

export class DirectAdapter {
  constructor(runtime, options = {}) {
    this.runtime = runtime
    this.baseDir = options.baseDir || process.cwd()
  }

  createResult(success, data = {}) {
    return {
      platform: this.id,
      success,
      timestamp: Date.now(),
      ...data,
    }
  }

  async withHeaderRules(rules, fn) {
    return this.runtime.withHeaderRules(rules, fn)
  }

  async processImages(content, uploadFn, options = {}) {
    const matches = []
    const htmlImgRegex = /<img[^>]+src="([^"]+)"[^>]*>/gi
    let htmlMatch
    while ((htmlMatch = htmlImgRegex.exec(content)) !== null) {
      matches.push({ full: htmlMatch[0], src: htmlMatch[1], type: 'html' })
    }

    const markdownImgRegex = /!\[([^\]]*)\]\(([^)\s]+)(?:\s+["'][^"']*["'])?\)/g
    let mdMatch
    while ((mdMatch = markdownImgRegex.exec(content)) !== null) {
      matches.push({ full: mdMatch[0], alt: mdMatch[1], src: mdMatch[2], type: 'markdown' })
    }

    let result = content
    const uploaded = new Map()
    const skipPatterns = options.skipPatterns || []

    for (const match of matches) {
      if (!match.src) continue
      if (!match.src.startsWith('data:') && skipPatterns.some((pattern) => match.src.includes(pattern))) {
        continue
      }

      let uploadResult = uploaded.get(match.src)
      if (!uploadResult) {
        uploadResult = await uploadFn(match.src)
        uploaded.set(match.src, uploadResult)
      }

      const replacement = match.type === 'html'
        ? `<img src="${uploadResult.url}" />`
        : `![${match.alt || ''}](${uploadResult.url})`
      result = result.replace(match.full, replacement)
    }

    return result
  }

  resolveLocalPath(src) {
    if (src.startsWith('file://')) return new URL(src)
    if (path.isAbsolute(src)) return src
    return path.resolve(this.baseDir, src)
  }

  async sourceToBlob(src) {
    if (src.startsWith('data:')) {
      const response = await fetch(src)
      const blob = await response.blob()
      return { blob, filename: `image.${guessExtFromMime(blob.type || '')}` }
    }

    if (/^https?:\/\//i.test(src)) {
      const response = await this.runtime.fetch(src, { method: 'GET' })
      if (!response.ok) throw new Error(`图片下载失败: ${response.status} ${src}`)
      const blob = await response.blob()
      const pathname = new URL(src).pathname
      const filename = path.basename(pathname) || `image.${guessExtFromMime(blob.type || '')}`
      return { blob, filename }
    }

    const filePath = this.resolveLocalPath(src)
    const buffer = await fs.readFile(filePath)
    return {
      blob: new Blob([buffer], { type: guessMimeType(filePath) }),
      filename: path.basename(filePath),
    }
  }
}
