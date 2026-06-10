import test from 'node:test'
import assert from 'node:assert/strict'
import { BaijiahaoAdapter } from '../src/platforms/baijiahao.js'

class FakeRuntime {
  constructor() {
    this.calls = []
  }

  async withHeaderRules(rules, fn) {
    this.rules = rules
    return fn()
  }

  async fetch(url, options = {}) {
    this.calls.push({ url: String(url), options })

    if (String(url).includes('/builder/app/appinfo')) {
      return Response.json({
        errno: 0,
        errmsg: 'success',
        data: {
          user: {
            userid: 'bjh-123',
            name: '利幼枫0hK',
            avatar: 'https://example.com/avatar.png',
          },
        },
      })
    }

    if (String(url).includes('/builder/rc/edit')) {
      return new Response('<script>window.__BJH__INIT__AUTH__ = "token-abc"</script>', {
        status: 200,
        headers: { 'content-type': 'text/html' },
      })
    }

    if (String(url).includes('/pcui/article/save')) {
      return new Response('bjhdraft({"errno":0,"errmsg":"success","ret":{"article_id":"987"}})', {
        status: 200,
        headers: { 'content-type': 'application/javascript' },
      })
    }

    throw new Error(`unexpected URL: ${url}`)
  }
}

test('Baijiahao checkAuth returns stable user id and display name', async () => {
  const adapter = new BaijiahaoAdapter(new FakeRuntime())

  const auth = await adapter.checkAuth()

  assert.equal(auth.isAuthenticated, true)
  assert.equal(auth.userId, 'bjh-123')
  assert.equal(auth.username, '利幼枫0hK')
})

test('Baijiahao publish saves article as draft with editor URL', async () => {
  const runtime = new FakeRuntime()
  const adapter = new BaijiahaoAdapter(runtime)

  const result = await adapter.publish({
    title: '百家号草稿测试',
    html: '<p>正文</p>',
    markdown: '正文',
  })

  assert.equal(result.success, true)
  assert.equal(result.postId, '987')
  assert.equal(result.postUrl, 'https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=987')

  const saveCall = runtime.calls.find((call) => call.url.includes('/pcui/article/save'))
  assert.equal(saveCall.options.headers.token, 'token-abc')
  assert.equal(saveCall.options.body.get('title'), '百家号草稿测试')
  assert.equal(saveCall.options.body.get('content'), '<p>正文</p>')
  assert.equal(saveCall.options.body.get('original_status'), '0')
})
