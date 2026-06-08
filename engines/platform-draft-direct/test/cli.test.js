import test from 'node:test'
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const cwd = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const cli = path.join(cwd, 'src', 'cli.js')

test('sync --dry-run does not require credentials and reports image count', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'draft-direct-cli-'))
  const article = path.join(dir, 'article.md')
  await fs.writeFile(article, '# Dry Run\n\nText\n\n![img](./a.png)\n')

  const result = spawnSync(process.execPath, [cli, 'sync', article, '--platform', 'zhihu,juejin', '--dry-run'], {
    cwd,
    encoding: 'utf8',
    env: {
      ...process.env,
      DRAFT_DIRECT_CREDENTIAL_DIR: path.join(dir, 'creds'),
    },
  })

  assert.equal(result.status, 0, result.stderr)
  assert.match(result.stdout, /Dry-run/)
  assert.match(result.stdout, /平台: zhihu, juejin/)
  assert.match(result.stdout, /图片: 1/)
})

test('sync --dry-run reports Zhihu draft settings', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'draft-direct-cli-'))
  const article = path.join(dir, 'article.md')
  await fs.writeFile(article, '# Dry Run\n\nText\n')

  const result = spawnSync(process.execPath, [
    cli,
    'sync',
    article,
    '--platform',
    'zhihu',
    '--dry-run',
    '--zhihu-creation-statement',
    'ai_creation',
    '--zhihu-reward',
    'false',
    '--zhihu-column',
    'none',
    '--zhihu-toc',
    'true',
  ], {
    cwd,
    encoding: 'utf8',
    env: {
      ...process.env,
      DRAFT_DIRECT_CREDENTIAL_DIR: path.join(dir, 'creds'),
    },
  })

  assert.equal(result.status, 0, result.stderr)
  assert.match(result.stdout, /知乎设置:/)
  assert.match(result.stdout, /creationStatement=ai_creation/)
  assert.match(result.stdout, /reward=false/)
  assert.match(result.stdout, /column=none/)
  assert.match(result.stdout, /toc=true/)
})

test('import-cookies stores cookies without printing values', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'draft-direct-cli-'))
  const cookiesFile = path.join(dir, 'cookies.json')
  await fs.writeFile(cookiesFile, JSON.stringify([
    { name: 'sid', value: 'secret-cookie-value', domain: '.zhihu.com', path: '/', secure: true },
  ]))

  const result = spawnSync(process.execPath, [cli, 'import-cookies', '--platform', 'zhihu', '--file', cookiesFile], {
    cwd,
    encoding: 'utf8',
    env: {
      ...process.env,
      DRAFT_DIRECT_CREDENTIAL_DIR: path.join(dir, 'creds'),
    },
  })

  assert.equal(result.status, 0, result.stderr)
  assert.match(result.stdout, /已导入 1 个 Cookie/)
  assert.doesNotMatch(result.stdout, /secret-cookie-value/)

  const saved = await fs.readFile(path.join(dir, 'creds', 'zhihu.json'), 'utf8')
  assert.match(saved, /secret-cookie-value/)
})
