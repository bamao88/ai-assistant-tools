import fs from 'node:fs/promises'
import path from 'node:path'
import crypto from 'node:crypto'

export const SUPPORTED_PLATFORMS = [
  'zhihu',
  'juejin',
  'csdn',
  'baijiahao',
  '51cto',
  'cnblogs',
  'segmentfault',
  'oschina',
  'bilibili',
  'sohu',
]

export function splitPlatforms(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean)
}

export function assertSupportedPlatform(platform) {
  if (!SUPPORTED_PLATFORMS.includes(platform)) {
    throw new Error(`不支持的平台: ${platform}. 当前支持: ${SUPPORTED_PLATFORMS.join(', ')}`)
  }
}

export function parseArgs(argv) {
  const positional = []
  const flags = {}
  const booleanFlags = new Set(['dry-run', 'json'])

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    if (!arg.startsWith('--')) {
      positional.push(arg)
      continue
    }

    const key = arg.slice(2)
    if (booleanFlags.has(key)) {
      flags[key] = true
      continue
    }

    const next = argv[i + 1]
    if (!next || next.startsWith('--')) {
      throw new Error(`参数缺少值: ${arg}`)
    }
    flags[key] = next
    i++
  }

  return { positional, flags }
}

export function parseBoolean(value, fieldName = 'value') {
  if (typeof value === 'boolean') return value
  if (value === undefined || value === null || value === '') return undefined
  const normalized = String(value).trim().toLowerCase()
  if (['1', 'true', 'yes', 'y', 'on', 'open', 'enable', 'enabled', '开启', '是'].includes(normalized)) return true
  if (['0', 'false', 'no', 'n', 'off', 'close', 'closed', 'disable', 'disabled', '关闭', '否'].includes(normalized)) return false
  throw new Error(`${fieldName} 必须是 true/false`)
}

export function redact(value) {
  if (!value) return ''
  return `${String(value).slice(0, 4)}...`
}

function nameMatches(actual, expected) {
  if (!expected) return true
  if (!actual) return false
  return actual === expected || actual.includes(expected) || expected.includes(actual)
}

export function accountMatches(actualOrAuth, expected) {
  if (!expected) return true

  const auth = typeof actualOrAuth === 'object' && actualOrAuth !== null
    ? actualOrAuth
    : { username: actualOrAuth }

  if (typeof expected === 'string') {
    return nameMatches(auth.username, expected) || String(auth.userId || '') === expected
  }

  const expectedUserId = expected.userId || expected.userid || expected.id
  if (expectedUserId) {
    return Boolean(auth.userId) && String(auth.userId) === String(expectedUserId)
  }

  const names = [
    expected.username,
    expected.name,
    expected.account,
    ...(Array.isArray(expected.aliases) ? expected.aliases : []),
  ].filter(Boolean)

  return names.some((name) => nameMatches(auth.username, String(name)))
}

export function formatExpectedAccount(expected) {
  if (!expected) return '未配置'
  if (typeof expected === 'string') return expected
  const parts = []
  const userId = expected.userId || expected.userid || expected.id
  const username = expected.username || expected.name || expected.account
  if (username) parts.push(String(username))
  if (userId) parts.push(`id:${userId}`)
  if (parts.length === 0) return JSON.stringify(expected)
  return parts.join(' / ')
}

export function formatAuthAccount(auth) {
  if (!auth) return 'unknown'
  const parts = []
  if (auth.username) parts.push(auth.username)
  if (auth.userId) parts.push(`id:${auth.userId}`)
  return parts.join(' / ') || 'unknown'
}

export async function readJsonFile(file) {
  const text = await fs.readFile(file, 'utf8')
  return JSON.parse(text)
}

export async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true })
}

export function md5Hex(buffer) {
  return crypto.createHash('md5').update(Buffer.from(buffer)).digest('hex')
}

export function hmacBase64(algorithm, key, message) {
  return crypto.createHmac(algorithm, key).update(message).digest('base64')
}

export function hmacHex(algorithm, key, message) {
  return crypto.createHmac(algorithm, key).update(message).digest('hex')
}

export function sha256Hex(message) {
  return crypto.createHash('sha256').update(message).digest('hex')
}

export function toBase64(buffer) {
  return Buffer.from(buffer).toString('base64')
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function guessMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase()
  if (ext === '.png') return 'image/png'
  if (ext === '.jpg' || ext === '.jpeg') return 'image/jpeg'
  if (ext === '.gif') return 'image/gif'
  if (ext === '.webp') return 'image/webp'
  if (ext === '.svg') return 'image/svg+xml'
  return 'application/octet-stream'
}

export function guessExtFromMime(mimeType) {
  if (mimeType.includes('png')) return 'png'
  if (mimeType.includes('jpeg') || mimeType.includes('jpg')) return 'jpg'
  if (mimeType.includes('gif')) return 'gif'
  if (mimeType.includes('webp')) return 'webp'
  return 'jpg'
}

export function normalizeHeaderObject(headers) {
  if (!headers) return {}
  if (headers instanceof Headers) return Object.fromEntries(headers.entries())
  if (Array.isArray(headers)) return Object.fromEntries(headers)
  return { ...headers }
}
