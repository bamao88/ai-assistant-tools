import fs from 'node:fs/promises'
import path from 'node:path'
import { ensureDir } from './util.js'

function normalizeDomain(domain) {
  return String(domain || '').trim().toLowerCase()
}

function normalizeCookie(raw) {
  if (!raw || !raw.name || raw.value === undefined) {
    throw new Error('Cookie 缺少 name/value')
  }

  const domain = normalizeDomain(raw.domain || raw.host || raw.urlHost)
  if (!domain) {
    throw new Error(`Cookie ${raw.name} 缺少 domain`)
  }

  let expirationDate = raw.expirationDate ?? raw.expires ?? raw.expiry
  if (typeof expirationDate === 'string') {
    const parsed = Number(expirationDate)
    expirationDate = Number.isFinite(parsed) ? parsed : undefined
  }
  if (typeof expirationDate === 'number' && expirationDate > 100000000000) {
    expirationDate = Math.floor(expirationDate / 1000)
  }

  return {
    name: String(raw.name),
    value: String(raw.value),
    domain,
    path: raw.path || '/',
    secure: Boolean(raw.secure),
    httpOnly: Boolean(raw.httpOnly),
    sameSite: raw.sameSite,
    expirationDate,
  }
}

export function extractCookiesFromJson(json) {
  const source = Array.isArray(json) ? json : json.cookies
  if (!Array.isArray(source)) {
    throw new Error('Cookie 文件必须是数组，或包含 cookies 数组')
  }
  return source.map(normalizeCookie)
}

export function extractCookiesFromText(text, domain) {
  const normalizedDomain = normalizeDomain(domain)
  if (!normalizedDomain) throw new Error('原始 Cookie 文本导入必须指定 domain')

  const cookieHeader = String(text || '')
    .trim()
    .replace(/^Cookie:\s*/i, '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .join('; ')

  if (!cookieHeader) return []

  return cookieHeader
    .split(/;\s*/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const eq = part.indexOf('=')
      if (eq <= 0) throw new Error(`Cookie 文本格式异常: ${part.slice(0, 24)}`)
      return normalizeCookie({
        name: part.slice(0, eq).trim(),
        value: part.slice(eq + 1),
        domain: normalizedDomain,
        path: '/',
        secure: true,
      })
    })
}

export function extractCookiesFromInput(text, options = {}) {
  try {
    return extractCookiesFromJson(JSON.parse(text))
  } catch (error) {
    if (error instanceof SyntaxError) {
      return extractCookiesFromText(text, options.defaultDomain)
    }
    throw error
  }
}

function domainMatches(hostname, cookieDomain) {
  const host = hostname.toLowerCase()
  const domain = normalizeDomain(cookieDomain).replace(/^\./, '')
  return host === domain || host.endsWith(`.${domain}`)
}

function pathMatches(requestPath, cookiePath) {
  return requestPath.startsWith(cookiePath || '/')
}

function isExpired(cookie, now = Date.now()) {
  return typeof cookie.expirationDate === 'number' && cookie.expirationDate * 1000 <= now
}

function splitSetCookieHeader(header) {
  if (!header) return []
  const parts = []
  let start = 0
  let inExpires = false

  for (let i = 0; i < header.length; i++) {
    const slice = header.slice(i, i + 8).toLowerCase()
    if (slice === 'expires=') {
      inExpires = true
      i += 7
      continue
    }
    if (inExpires && header[i] === ';') {
      inExpires = false
      continue
    }
    if (!inExpires && header[i] === ',') {
      const next = header.slice(i + 1).trimStart()
      if (/^[^=;,\s]+=/.test(next)) {
        parts.push(header.slice(start, i).trim())
        start = i + 1
      }
    }
  }
  parts.push(header.slice(start).trim())
  return parts.filter(Boolean)
}

function parseSetCookie(setCookie, requestUrl) {
  const url = new URL(requestUrl)
  const pieces = setCookie.split(';').map((part) => part.trim())
  const [nameValue, ...attrs] = pieces
  const eq = nameValue.indexOf('=')
  if (eq <= 0) return null

  const cookie = {
    name: nameValue.slice(0, eq),
    value: nameValue.slice(eq + 1),
    domain: url.hostname,
    path: '/',
    secure: false,
    httpOnly: false,
  }

  for (const attr of attrs) {
    const [rawKey, ...rawValue] = attr.split('=')
    const key = rawKey.toLowerCase()
    const value = rawValue.join('=')
    if (key === 'domain' && value) cookie.domain = normalizeDomain(value)
    if (key === 'path' && value) cookie.path = value
    if (key === 'secure') cookie.secure = true
    if (key === 'httponly') cookie.httpOnly = true
    if (key === 'expires' && value) {
      const timestamp = Date.parse(value)
      if (Number.isFinite(timestamp)) cookie.expirationDate = Math.floor(timestamp / 1000)
    }
    if (key === 'max-age' && value) {
      const seconds = Number(value)
      if (Number.isFinite(seconds)) cookie.expirationDate = Math.floor(Date.now() / 1000) + seconds
    }
  }

  return normalizeCookie(cookie)
}

export class CookieJar {
  constructor(cookies = []) {
    this.cookies = []
    for (const cookie of cookies) this.set(cookie)
  }

  static async load(file) {
    try {
      const text = await fs.readFile(file, 'utf8')
      const json = JSON.parse(text)
      return new CookieJar(extractCookiesFromJson(json))
    } catch (error) {
      if (error.code === 'ENOENT') return new CookieJar()
      throw error
    }
  }

  async save(file) {
    await ensureDir(path.dirname(file))
    await fs.writeFile(file, `${JSON.stringify({ cookies: this.cookies }, null, 2)}\n`, {
      mode: 0o600,
    })
    await fs.chmod(file, 0o600).catch(() => {})
  }

  set(rawCookie) {
    const cookie = normalizeCookie(rawCookie)
    this.cookies = this.cookies.filter((item) => {
      return !(
        item.name === cookie.name &&
        item.domain === cookie.domain &&
        item.path === cookie.path
      )
    })
    if (!isExpired(cookie)) this.cookies.push(cookie)
  }

  get(domain, name) {
    const host = normalizeDomain(domain)
    const found = this.cookies.find((cookie) => {
      return cookie.name === name && domainMatches(host, cookie.domain) && !isExpired(cookie)
    })
    return found?.value || null
  }

  getAll(domain) {
    const host = normalizeDomain(domain)
    return this.cookies.filter((cookie) => domainMatches(host, cookie.domain) && !isExpired(cookie))
  }

  headerFor(urlValue) {
    const url = new URL(urlValue)
    const matching = this.cookies
      .filter((cookie) => !isExpired(cookie))
      .filter((cookie) => domainMatches(url.hostname, cookie.domain))
      .filter((cookie) => pathMatches(url.pathname || '/', cookie.path || '/'))
      .filter((cookie) => !cookie.secure || url.protocol === 'https:')
      .sort((a, b) => (b.path || '/').length - (a.path || '/').length)

    return matching.map((cookie) => `${cookie.name}=${cookie.value}`).join('; ')
  }

  setFromResponseHeaders(url, headers) {
    const values = typeof headers.getSetCookie === 'function'
      ? headers.getSetCookie().flatMap((value) => splitSetCookieHeader(value))
      : splitSetCookieHeader(headers.get('set-cookie'))

    for (const value of values) {
      const cookie = parseSetCookie(value, url)
      if (cookie) this.set(cookie)
    }
  }
}

export const __cookieTest = {
  splitSetCookieHeader,
  domainMatches,
  parseSetCookie,
  isExpired,
}
