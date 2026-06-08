import crypto from 'node:crypto'
import { hmacHex, sha256Hex } from './util.js'

function formatAmzDate(date) {
  return date.toISOString().replace(/[:-]|\.\d{3}/g, '')
}

function formatDateStamp(date) {
  return date.toISOString().slice(0, 10).replace(/-/g, '')
}

function hmacBuffer(key, message) {
  return crypto.createHmac('sha256', key).update(message).digest()
}

export function signAWS4(params) {
  const {
    method,
    url,
    accessKeyId,
    secretAccessKey,
    securityToken,
    region = 'cn-north-1',
    service = 'imagex',
    headers = {},
    body = '',
  } = params

  const parsedUrl = new URL(url)
  const now = new Date()
  const amzDate = formatAmzDate(now)
  const dateStamp = formatDateStamp(now)

  const queryParams = Array.from(parsedUrl.searchParams.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  const canonicalQueryString = queryParams
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&')

  const signedHeadersObj = {
    'x-amz-date': amzDate,
    ...headers,
  }
  if (securityToken) signedHeadersObj['x-amz-security-token'] = securityToken

  const signedHeaderNames = Object.keys(signedHeadersObj)
    .map((key) => key.toLowerCase())
    .sort()
    .join(';')

  const canonicalHeaders = Object.entries(signedHeadersObj)
    .map(([key, value]) => `${key.toLowerCase()}:${String(value).trim()}`)
    .sort()
    .join('\n') + '\n'

  const canonicalRequest = [
    method.toUpperCase(),
    parsedUrl.pathname || '/',
    canonicalQueryString,
    canonicalHeaders,
    signedHeaderNames,
    sha256Hex(body),
  ].join('\n')

  const algorithm = 'AWS4-HMAC-SHA256'
  const credentialScope = `${dateStamp}/${region}/${service}/aws4_request`
  const stringToSign = [
    algorithm,
    amzDate,
    credentialScope,
    sha256Hex(canonicalRequest),
  ].join('\n')

  const kDate = hmacBuffer(Buffer.from(`AWS4${secretAccessKey}`), dateStamp)
  const kRegion = hmacBuffer(kDate, region)
  const kService = hmacBuffer(kRegion, service)
  const kSigning = hmacBuffer(kService, 'aws4_request')
  const signature = hmacHex('sha256', kSigning, stringToSign)
  const authorization = `${algorithm} Credential=${accessKeyId}/${credentialScope}, SignedHeaders=${signedHeaderNames}, Signature=${signature}`

  const resultHeaders = {
    authorization,
    'x-amz-date': amzDate,
  }
  if (securityToken) resultHeaders['x-amz-security-token'] = securityToken

  return { authorization, amzDate, headers: resultHeaders }
}

let crc32Table = null

function getCrc32Table() {
  if (crc32Table) return crc32Table
  crc32Table = new Uint32Array(256)
  for (let i = 0; i < 256; i++) {
    let c = i
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1)
    }
    crc32Table[i] = c
  }
  return crc32Table
}

export function crc32(data) {
  let crc = 0xffffffff
  const table = getCrc32Table()
  for (let i = 0; i < data.length; i++) {
    crc = (crc >>> 8) ^ table[(crc ^ data[i]) & 0xff]
  }
  return ((crc ^ 0xffffffff) >>> 0).toString(16).padStart(8, '0')
}
