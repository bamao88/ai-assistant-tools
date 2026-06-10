import test from 'node:test'
import assert from 'node:assert/strict'
import { Cto51Adapter } from '../src/platforms/cto51.js'
import { CnblogsAdapter } from '../src/platforms/cnblogs.js'
import { SegmentfaultAdapter } from '../src/platforms/segmentfault.js'
import { OschinaAdapter } from '../src/platforms/oschina.js'
import { BilibiliAdapter } from '../src/platforms/bilibili.js'
import { SohuAdapter } from '../src/platforms/sohu.js'

class FakeRuntime {
  constructor(cookies = {}) {
    this.calls = []
    this.cookies = cookies
  }

  async withHeaderRules(_rules, fn) {
    return fn()
  }

  async getCookie(domain, name) {
    return this.cookies[`${domain}:${name}`] || this.cookies[name] || null
  }

  async fetch(url, options = {}) {
    const href = String(url)
    this.calls.push({ url: href, options })

    if (href === 'https://blog.51cto.com/blogger/publish') {
      return new Response('<meta name="csrf-token" content="csrf-51"><li class="more user"><a href="https://blog.51cto.com/u_123"><img src="avatar.png"', { status: 200 })
    }
    if (href === 'https://blog.51cto.com/blogger/draft') {
      return Response.json({ status: 1, data: { did: '51draft' } })
    }

    if (href === 'https://home.cnblogs.com/user/CurrentUserInfo') {
      return new Response('<a href="/u/3798805/"><img class="pfs" src="avatar.png"></a>', { status: 200 })
    }
    if (href === 'https://i.cnblogs.com/posts/edit') return new Response('', { status: 200 })
    if (href === 'https://i.cnblogs.com/api/posts') return Response.json({ id: 12345 })

    if (href === 'https://segmentfault.com/write') {
      return new Response('<script>serverData":{"Token":"sf-token"}</script>', { status: 200 })
    }
    if (href === 'https://segmentfault.com/gateway/draft') return Response.json({ id: 'sf-draft' })

    if (href === 'https://apiv1.oschina.net/oschinapi/user/myDetails') {
      return Response.json({
        success: true,
        result: { userId: 2468, userVo: { name: 'osc-user', portraitUrl: 'avatar.png' } },
      })
    }
    if (href === 'https://apiv1.oschina.net/oschinapi/api/draft/save_draft') {
      return Response.json({ success: true, result: { id: 1357 } })
    }

    if (href === 'https://api.bilibili.com/x/web-interface/nav?build=0&mobi_app=web') {
      return Response.json({
        code: 0,
        data: { isLogin: true, mid: 1122, uname: '张和', face: 'avatar.png' },
      })
    }
    if (href === 'https://api.bilibili.com/x/article/creative/draft/addupdate') {
      return Response.json({ code: 0, data: { aid: 9988 } })
    }

    if (href.startsWith('https://mp.sohu.com/mpbp/bp/account/list')) {
      return Response.json({
        code: 2000000,
        data: { data: [{ accounts: [{ id: 'sohu-1', nickName: '小狐狸rXB420pXAq', avatar: 'avatar.png' }] }] },
      })
    }
    if (href.startsWith('https://mp.sohu.com/mpbp/bp/news/v4/news/draft/v2')) {
      return Response.json({ success: true, data: 'sohu-draft' })
    }

    throw new Error(`unexpected URL: ${href}`)
  }
}

const article = {
  title: '直传草稿测试',
  markdown: '正文',
  html: '<p>正文</p>',
}

test('51CTO adapter saves markdown draft', async () => {
  const runtime = new FakeRuntime()
  const result = await new Cto51Adapter(runtime).publish(article)

  assert.equal(result.success, true)
  assert.equal(result.postUrl, 'https://blog.51cto.com/blogger/draft/51draft')
  const saveCall = runtime.calls.find((call) => call.url === 'https://blog.51cto.com/blogger/draft')
  assert.match(String(saveCall.options.body), /_csrf=csrf-51/)
})

test('Cnblogs adapter saves markdown draft with XSRF token', async () => {
  const runtime = new FakeRuntime({ 'XSRF-TOKEN': 'xsrf-cnblogs' })
  const result = await new CnblogsAdapter(runtime).publish(article)

  assert.equal(result.success, true)
  assert.equal(result.postUrl, 'https://i.cnblogs.com/articles/edit;postId=12345')
  const saveCall = runtime.calls.find((call) => call.url === 'https://i.cnblogs.com/api/posts')
  assert.equal(saveCall.options.headers['x-xsrf-token'], 'xsrf-cnblogs')
})

test('Segmentfault adapter saves markdown draft', async () => {
  const runtime = new FakeRuntime()
  const result = await new SegmentfaultAdapter(runtime).publish(article)

  assert.equal(result.success, true)
  assert.equal(result.postUrl, 'https://segmentfault.com/write?draftId=sf-draft')
  const saveCall = runtime.calls.find((call) => call.url === 'https://segmentfault.com/gateway/draft')
  assert.equal(saveCall.options.headers.token, 'sf-token')
})

test('Oschina adapter saves markdown draft with user id', async () => {
  const runtime = new FakeRuntime()
  const result = await new OschinaAdapter(runtime).publish(article)

  assert.equal(result.success, true)
  assert.equal(result.postUrl, 'https://my.oschina.net/u/2468/blog/write/draft/1357')
})

test('Bilibili article adapter saves draft with csrf', async () => {
  const runtime = new FakeRuntime({ bili_jct: 'bili-csrf' })
  const result = await new BilibiliAdapter(runtime).publish(article)

  assert.equal(result.success, true)
  assert.equal(result.postUrl, 'https://member.bilibili.com/platform/upload/text/edit?aid=9988')
  const saveCall = runtime.calls.find((call) => call.url === 'https://api.bilibili.com/x/article/creative/draft/addupdate')
  assert.match(String(saveCall.options.body), /csrf=bili-csrf/)
})

test('Sohu adapter saves html draft for first sub-account', async () => {
  const runtime = new FakeRuntime({ 'mp-cv': 'sp-cm-cookie' })
  const result = await new SohuAdapter(runtime).publish(article)

  assert.equal(result.success, true)
  assert.equal(result.postUrl, 'https://mp.sohu.com/mpfe/v4/contentManagement/news/addarticle?spm=smmp.articlelist.0.0&contentStatus=2&id=sohu-draft')
  const saveCall = runtime.calls.find((call) => call.url.startsWith('https://mp.sohu.com/mpbp/bp/news/v4/news/draft/v2'))
  assert.equal(saveCall.options.headers['sp-cm'], 'sp-cm-cookie')
})
