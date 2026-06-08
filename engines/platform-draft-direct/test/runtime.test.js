import test from 'node:test'
import assert from 'node:assert/strict'
import { CookieJar } from '../src/cookies.js'
import { NodeRuntime, __runtimeTest } from '../src/runtime.js'

test('matchesUrlFilter supports extension-style wildcard filters', () => {
  assert.equal(__runtimeTest.matchesUrlFilter('https://api.juejin.cn/foo', '*://api.juejin.cn/*'), true)
  assert.equal(__runtimeTest.matchesUrlFilter('https://www.juejin.cn/foo', '*://api.juejin.cn/*'), false)
})

test('headersForUrl merges cookies and active header rules', async () => {
  const runtime = new NodeRuntime({
    cookieJar: new CookieJar([
      { name: 'session', value: 'abc', domain: '.juejin.cn', path: '/', secure: true },
    ]),
  })
  const ruleId = await runtime.headerRules.add({
    urlFilter: '*://api.juejin.cn/*',
    headers: {
      Origin: 'https://juejin.cn',
      Referer: 'https://juejin.cn/',
    },
  })

  const headers = runtime.headersForUrl('https://api.juejin.cn/user_api/v1/user/get', {
    accept: 'application/json',
  })

  assert.equal(headers.cookie, 'session=abc')
  assert.equal(headers.Origin, 'https://juejin.cn')
  assert.equal(headers.Referer, 'https://juejin.cn/')
  assert.equal(headers.accept, 'application/json')

  await runtime.headerRules.remove(ruleId)
  const withoutRule = runtime.headersForUrl('https://api.juejin.cn/user_api/v1/user/get')
  assert.equal(withoutRule.Origin, undefined)
})
