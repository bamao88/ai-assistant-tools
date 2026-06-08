import test from 'node:test'
import assert from 'node:assert/strict'
import { NodeRuntime } from '../src/runtime.js'
import { ZhihuAdapter } from '../src/platforms/zhihu.js'

test('Zhihu transform compacts inter-tag whitespace to avoid editor blank lines', () => {
  const adapter = new ZhihuAdapter(new NodeRuntime())
  const html = [
    '<p>第一段</p>',
    '<p>第二段</p>',
    '<p><br /></p>',
    '<ul>',
    '<li>第一项</li>',
    '<li>第二项</li>',
    '</ul>',
  ].join('\n')

  assert.equal(
    adapter.transformContent(html),
    '<p>第一段</p><p>第二段</p><ul><li>第一项</li><li>第二项</li></ul>'
  )
})

test('Zhihu transform keeps code block text while normalizing code wrapper', () => {
  const adapter = new ZhihuAdapter(new NodeRuntime())
  const html = '<pre><code class="language-js">const a = 1\nconsole.log(a)</code></pre>\n<p>正文</p>'

  assert.equal(
    adapter.transformContent(html),
    '<pre lang="js"><code>const a = 1\nconsole.log(a)</code></pre><p>正文</p>'
  )
})

test('Zhihu draft settings map frontmatter and CLI options to PATCH payload fields', () => {
  const adapter = new ZhihuAdapter(new NodeRuntime())
  const settings = adapter.buildDraftSettings({
    metadata: {
      zhihu_creation_statement: 'ai_creation',
      zhihu_reward: 'false',
      zhihu_column: '12345',
    },
    platformOptions: {
      zhihu: {
        toc: 'true',
      },
    },
  })

  assert.deepEqual(settings, {
    disclaimer_type: 'ai_creation',
    disclaimer_status: 'open',
    canReward: false,
    column: ['12345'],
    table_of_contents: true,
  })
})

test('Zhihu draft settings can explicitly keep article out of columns', () => {
  const adapter = new ZhihuAdapter(new NodeRuntime())
  assert.deepEqual(adapter.buildDraftSettings({
    metadata: { zhihu_column: 'none', zhihu_creation_statement: 'none' },
  }), {
    column: [],
    disclaimer_type: 'none',
    disclaimer_status: 'close',
  })
})

test('Zhihu draft settings reject unsupported creation statement values', () => {
  const adapter = new ZhihuAdapter(new NodeRuntime())
  assert.throws(() => adapter.buildDraftSettings({
    metadata: { zhihu_creation_statement: 'original' },
  }), /知乎创作声明不支持/)
})
