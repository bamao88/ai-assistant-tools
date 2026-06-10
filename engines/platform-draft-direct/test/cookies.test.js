import test from 'node:test'
import assert from 'node:assert/strict'
import { CookieJar, extractCookiesFromJson, extractCookiesFromInput, extractCookiesFromText, __cookieTest } from '../src/cookies.js'

test('extractCookiesFromJson accepts array and storage_state shape', () => {
  const arrayCookies = extractCookiesFromJson([
    { name: 'a', value: '1', domain: '.example.com', path: '/', secure: true },
  ])
  assert.equal(arrayCookies.length, 1)
  assert.equal(arrayCookies[0].domain, '.example.com')

  const storageCookies = extractCookiesFromJson({
    cookies: [{ name: 'b', value: '2', domain: 'example.com', path: '/' }],
  })
  assert.equal(storageCookies.length, 1)
  assert.equal(storageCookies[0].name, 'b')
})

test('CookieJar matches domains, paths, secure cookies, and expiration', () => {
  const jar = new CookieJar([
    { name: 'root', value: '1', domain: '.example.com', path: '/', secure: true },
    { name: 'sub', value: '2', domain: 'api.example.com', path: '/v1', secure: false },
    { name: 'old', value: '3', domain: '.example.com', path: '/', expirationDate: 1 },
  ])

  assert.equal(jar.headerFor('https://api.example.com/v1/posts'), 'sub=2; root=1')
  assert.equal(jar.headerFor('http://api.example.com/v1/posts'), 'sub=2')
  assert.equal(jar.get('.example.com', 'old'), null)
})

test('CookieJar updates from Set-Cookie headers', () => {
  const jar = new CookieJar()
  const headers = new Headers()
  headers.append('set-cookie', 'sid=abc; Domain=.example.com; Path=/; HttpOnly, theme=dark; Path=/ui')

  jar.setFromResponseHeaders('https://www.example.com/ui/page', headers)

  assert.equal(jar.get('.example.com', 'sid'), 'abc')
  assert.equal(jar.headerFor('https://www.example.com/ui/page'), 'theme=dark; sid=abc')
})

test('Set-Cookie splitter keeps Expires comma intact', () => {
  const split = __cookieTest.splitSetCookieHeader('a=1; Expires=Wed, 21 Oct 2030 07:28:00 GMT; Path=/, b=2; Path=/')
  assert.deepEqual(split, [
    'a=1; Expires=Wed, 21 Oct 2030 07:28:00 GMT; Path=/',
    'b=2; Path=/',
  ])
})

test('extractCookiesFromText accepts raw Cookie header strings', () => {
  const cookies = extractCookiesFromText('Cookie: sid=abc; token=a=b=c', '.example.com')

  assert.equal(cookies.length, 2)
  assert.equal(cookies[0].name, 'sid')
  assert.equal(cookies[0].domain, '.example.com')
  assert.equal(cookies[1].value, 'a=b=c')
})

test('extractCookiesFromInput falls back to raw Cookie text', () => {
  const cookies = extractCookiesFromInput('sid=abc; theme=dark', {
    defaultDomain: '.example.com',
  })

  assert.equal(cookies.length, 2)
  assert.equal(cookies[0].secure, true)
})
