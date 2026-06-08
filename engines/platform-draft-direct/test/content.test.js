import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { markdownToHtml, parseArticleFile, parseFrontmatter } from '../src/content.js'

test('parseFrontmatter extracts simple key values', () => {
  const parsed = parseFrontmatter('---\ntitle: Hello\ncover: /tmp/a.png\n---\n# Body\n')
  assert.equal(parsed.data.title, 'Hello')
  assert.equal(parsed.data.cover, '/tmp/a.png')
  assert.equal(parsed.body, '# Body\n')
})

test('markdownToHtml handles headings, images, links, and code fences', () => {
  const html = markdownToHtml('# T\n\nHello [site](https://example.com)\n\n![alt](a.png)\n\n```js\nconst a = 1\n```')
  assert.match(html, /<h1>T<\/h1>/)
  assert.match(html, /<a href="https:\/\/example.com">site<\/a>/)
  assert.match(html, /<img alt="alt" src="a.png" \/>/)
  assert.match(html, /<pre><code class="language-js">/)
})

test('parseArticleFile extracts title and removes leading h1 from markdown body', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'draft-direct-'))
  const file = path.join(dir, 'article.md')
  await fs.writeFile(file, '# My Title\n\nBody\n\n![x](img.png)\n')

  const article = await parseArticleFile(file)

  assert.equal(article.title, 'My Title')
  assert.equal(article.markdown.startsWith('# My Title'), false)
  assert.deepEqual(article.metadata, {})
  assert.equal(article.imageCount, 1)
  assert.match(article.html, /<p>Body<\/p>/)
})
