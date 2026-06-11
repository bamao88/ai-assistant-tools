import { CookieJar } from './cookies.js'
import { normalizeHeaderObject } from './util.js'

const DEFAULT_TIMEOUT_MS = Number(process.env.PLATFORM_DRAFT_DIRECT_TIMEOUT_MS || 30000)
const DEFAULT_USER_AGENT = [
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
  'AppleWebKit/537.36 (KHTML, like Gecko)',
  'Chrome/126.0.0.0 Safari/537.36',
].join(' ')

function globToRegex(glob) {
  const escaped = String(glob)
    .replace(/[.+?^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '.*')
  return new RegExp(`^${escaped}$`)
}

function matchesUrlFilter(url, filter) {
  return globToRegex(filter).test(url)
}

export class NodeRuntime {
  constructor(options = {}) {
    this.type = 'node'
    this.timeout = options.timeout || DEFAULT_TIMEOUT_MS
    this.userAgent = options.userAgent || DEFAULT_USER_AGENT
    this.cookieJar = options.cookieJar || new CookieJar()
    this.activeHeaderRules = []
    this.persistCookies = options.persistCookies || null

    this.storageMap = new Map()
    this.sessionMap = new Map()

    this.cookies = {
      get: async (domain) => this.cookieJar.getAll(domain),
      set: async (cookie) => {
        this.cookieJar.set(cookie)
        await this.saveCookies()
      },
      remove: async (name, domain) => {
        const normalizedDomain = String(domain || '').toLowerCase()
        this.cookieJar.cookies = this.cookieJar.cookies.filter((cookie) => {
          return !(cookie.name === name && cookie.domain === normalizedDomain)
        })
        await this.saveCookies()
      },
    }

    this.storage = {
      get: async (key) => this.storageMap.get(key) ?? null,
      set: async (key, value) => {
        this.storageMap.set(key, value)
      },
      remove: async (key) => {
        this.storageMap.delete(key)
      },
    }

    this.session = {
      get: async (key) => this.sessionMap.get(key) ?? null,
      set: async (key, value) => {
        this.sessionMap.set(key, value)
      },
    }

    this.headerRules = {
      add: async (rule) => {
        const id = `node_rule_${Date.now()}_${Math.random().toString(36).slice(2)}`
        this.activeHeaderRules.push({ id, ...rule })
        return id
      },
      remove: async (ruleId) => {
        this.activeHeaderRules = this.activeHeaderRules.filter((rule) => rule.id !== ruleId)
      },
      clear: async () => {
        this.activeHeaderRules = []
      },
    }

    this.dom = {
      parseHTML: async () => {
        throw new Error('NodeRuntime DOM parser is not implemented')
      },
      querySelector: () => null,
      querySelectorAll: () => [],
      getTextContent: () => '',
      getInnerHTML: () => '',
    }
  }

  async getCookie(domain, name) {
    return this.cookieJar.get(domain, name)
  }

  async saveCookies() {
    if (this.persistCookies) await this.persistCookies(this.cookieJar)
  }

  headersForUrl(url, headers) {
    const result = {
      accept: '*/*',
      'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
      'user-agent': this.userAgent,
      ...normalizeHeaderObject(headers),
    }

    for (const rule of this.activeHeaderRules) {
      if (!matchesUrlFilter(url, rule.urlFilter)) continue
      Object.assign(result, rule.headers)
    }

    const cookieHeader = this.cookieJar.headerFor(url)
    if (cookieHeader && !result.cookie && !result.Cookie) {
      result.cookie = cookieHeader
    }

    return result
  }

  async fetch(url, options = {}) {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || this.timeout)
    const headers = this.headersForUrl(url, options.headers)

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      })
      this.cookieJar.setFromResponseHeaders(url, response.headers)
      await this.saveCookies()
      return response
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error(`请求超时（${(options.timeout || this.timeout) / 1000}秒）: ${url}`)
      }
      throw error
    } finally {
      clearTimeout(timeoutId)
    }
  }

  async withHeaderRules(rules, fn) {
    const ids = []
    try {
      for (const rule of rules) ids.push(await this.headerRules.add(rule))
      return await fn()
    } finally {
      for (const id of ids.reverse()) await this.headerRules.remove(id)
    }
  }
}

export const __runtimeTest = {
  matchesUrlFilter,
  globToRegex,
}
