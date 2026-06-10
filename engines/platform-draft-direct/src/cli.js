#!/usr/bin/env node
import path from 'node:path'
import fs from 'node:fs/promises'
import { CookieJar, extractCookiesFromInput } from './cookies.js'
import { NodeRuntime } from './runtime.js'
import { parseArticleFile } from './content.js'
import { createAdapter } from './platforms/index.js'
import { credentialsDir, expectedAccountsPath, platformCookiePath } from './paths.js'
import {
  accountMatches,
  assertSupportedPlatform,
  ensureDir,
  formatAuthAccount,
  formatExpectedAccount,
  parseArgs,
  readJsonFile,
  splitPlatforms,
  SUPPORTED_PLATFORMS,
} from './util.js'

const RAW_COOKIE_DEFAULT_DOMAINS = {
  zhihu: '.zhihu.com',
  juejin: '.juejin.cn',
  csdn: '.csdn.net',
  baijiahao: '.baijiahao.baidu.com',
  '51cto': '.51cto.com',
  cnblogs: '.cnblogs.com',
  segmentfault: '.segmentfault.com',
  oschina: '.oschina.net',
  bilibili: '.bilibili.com',
  sohu: '.sohu.com',
}

function printUsage() {
  console.log(`draft-direct - 无 Chrome 插件草稿直传

用法:
  draft-direct import-cookies --platform zhihu --file /path/cookies.json
  draft-direct import-cookies --platform baijiahao --file /path/cookie-header.txt
  draft-direct import-cookies --platform baijiahao --file - < cookie-header.txt
  draft-direct auth --platform zhihu,juejin,csdn,baijiahao,51cto,cnblogs,segmentfault,oschina,bilibili,sohu
  draft-direct sync /path/article.md --platform zhihu,juejin,csdn,baijiahao,51cto,cnblogs,segmentfault,oschina,bilibili,sohu --title "标题" --dry-run
  draft-direct sync /path/article.md --platform zhihu,juejin,csdn,baijiahao,51cto,cnblogs,segmentfault,oschina,bilibili,sohu --title "标题"

知乎设置:
  --cover /path/cover.png
  --zhihu-creation-statement none|ai_creation|spoiler|medical_advice|fictional_creation|contain_finance
  --zhihu-reward true|false
  --zhihu-column <column-id|none>
  --zhihu-toc true|false

支持平台: ${SUPPORTED_PLATFORMS.join(', ')}`)
}

function platformListFromFlags(flags, defaultValue = '') {
  const value = flags.platform || flags.platforms || flags.p || defaultValue
  const platforms = splitPlatforms(value)
  if (platforms.length === 0) throw new Error('必须指定 --platform')
  for (const platform of platforms) assertSupportedPlatform(platform)
  return platforms
}

async function loadExpectedAccounts() {
  try {
    const json = await readJsonFile(expectedAccountsPath())
    return json.assistant_zh?.expectedAccounts || {}
  } catch {
    return {}
  }
}

async function loadRuntime(platform) {
  const cookiePath = platformCookiePath(platform)
  const cookieJar = await CookieJar.load(cookiePath)
  return new NodeRuntime({
    cookieJar,
    persistCookies: async (jar) => {
      await jar.save(cookiePath)
    },
  })
}

async function readStdin() {
  const chunks = []
  for await (const chunk of process.stdin) chunks.push(chunk)
  return Buffer.concat(chunks.map((chunk) => Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk))).toString('utf8')
}

async function checkPlatformAuth(platform, expectedAccounts) {
  const runtime = await loadRuntime(platform)
  const adapter = createAdapter(platform, runtime)
  const auth = await adapter.checkAuth()
  const expected = expectedAccounts[platform]
  const match = auth.isAuthenticated && accountMatches(auth, expected)
  return {
    platform,
    expected,
    ...auth,
    accountMatched: match,
  }
}

async function importCookies(flags) {
  const platform = flags.platform
  if (!platform) throw new Error('必须指定 --platform')
  assertSupportedPlatform(platform)
  if (!flags.file) throw new Error('必须指定 --file')

  const file = flags.file === '-' ? '-' : path.resolve(flags.file)
  const text = flags.file === '-' ? await readStdin() : await fs.readFile(file, 'utf8')
  const cookies = extractCookiesFromInput(text, {
    defaultDomain: flags.domain || RAW_COOKIE_DEFAULT_DOMAINS[platform],
  })
  const jar = new CookieJar(cookies)
  const out = platformCookiePath(platform)
  await ensureDir(credentialsDir())
  await jar.save(out)

  console.log(`已导入 ${cookies.length} 个 Cookie`)
  console.log(`平台: ${platform}`)
  console.log(`保存: ${out}`)
  console.log('提示: 未打印 Cookie 值；请运行 auth 校验账号。')
}

async function authCommand(flags) {
  const platforms = platformListFromFlags(flags, SUPPORTED_PLATFORMS.join(','))
  const expectedAccounts = await loadExpectedAccounts()
  const results = []

  for (const platform of platforms) {
    const result = await checkPlatformAuth(platform, expectedAccounts)
    results.push(result)
  }

  for (const result of results) {
    if (!result.isAuthenticated) {
      console.log(`✗ ${result.platform}: 未登录${result.error ? ` (${result.error})` : ''}`)
      continue
    }
    const accountStatus = result.accountMatched ? '账号匹配' : `账号不匹配，期望「${formatExpectedAccount(result.expected)}」`
    console.log(`✓ ${result.platform}: ${formatAuthAccount(result)} (${accountStatus})`)
  }

  if (results.some((result) => !result.isAuthenticated || !result.accountMatched)) {
    process.exitCode = 2
  }
}

async function dryRunSync(article, platforms) {
  console.log('Dry-run: 不访问平台 API，不写草稿')
  console.log(`文件: ${article.file}`)
  console.log(`标题: ${article.title}`)
  console.log(`格式: ${article.format}`)
  console.log(`平台: ${platforms.join(', ')}`)
  console.log(`图片: ${article.imageCount}`)
  if (article.cover) console.log(`封面: ${article.cover}`)
  if (article.platformOptions?.zhihu && platforms.includes('zhihu')) {
    const zhihu = article.platformOptions.zhihu
    const settings = Object.entries(zhihu)
      .filter(([, value]) => value !== undefined && value !== '')
      .map(([key, value]) => `${key}=${value}`)
    if (settings.length) console.log(`知乎设置: ${settings.join(', ')}`)
  }
}

function collectPlatformOptions(flags) {
  return {
    zhihu: {
      creationStatement: flags['zhihu-creation-statement'] || flags['zhihu-disclaimer'],
      reward: flags['zhihu-reward'],
      column: flags['zhihu-column'],
      toc: flags['zhihu-toc'],
    },
  }
}

async function syncCommand(positional, flags) {
  const file = positional[0]
  if (!file) throw new Error('sync 必须指定文章文件')
  const platforms = platformListFromFlags(flags)
  const article = await parseArticleFile(file, {
    title: flags.title,
    cover: flags.cover,
  })
  article.platformOptions = collectPlatformOptions(flags)
  if (!article.title) throw new Error('无法从文件提取标题，请用 --title 指定')

  if (flags['dry-run']) {
    await dryRunSync(article, platforms)
    return
  }

  const expectedAccounts = await loadExpectedAccounts()
  const authResults = []
  for (const platform of platforms) {
    const auth = await checkPlatformAuth(platform, expectedAccounts)
    authResults.push(auth)
    if (!auth.isAuthenticated) {
      throw new Error(`${platform} 未登录${auth.error ? `: ${auth.error}` : ''}`)
    }
    if (!auth.accountMatched) {
      throw new Error(`${platform} 账号不匹配: 当前「${formatAuthAccount(auth)}」，期望「${formatExpectedAccount(auth.expected)}」`)
    }
  }

  console.log('账号校验通过:')
  for (const auth of authResults) {
    console.log(`  ✓ ${auth.platform}: ${formatAuthAccount(auth)}`)
  }

  const results = []
  for (const platform of platforms) {
    const runtime = await loadRuntime(platform)
    const adapter = createAdapter(platform, runtime, { baseDir: article.baseDir })
    const result = await adapter.publish(article)
    results.push(result)
  }

  console.log('同步结果:')
  for (const result of results) {
    if (result.success) {
      console.log(`  ✓ ${result.platform}: ${result.postUrl}`)
    } else {
      console.log(`  ✗ ${result.platform}: ${result.error || '未知错误'}`)
    }
  }

  if (results.some((result) => !result.success)) {
    process.exitCode = 3
  }
}

async function main() {
  const [command, ...rest] = process.argv.slice(2)
  if (!command || command === '--help' || command === '-h') {
    printUsage()
    return
  }

  const { positional, flags } = parseArgs(rest)

  switch (command) {
    case 'import-cookies':
      await importCookies(flags)
      break
    case 'auth':
      await authCommand(flags)
      break
    case 'sync':
      await syncCommand(positional, flags)
      break
    default:
      throw new Error(`未知命令: ${command}`)
  }
}

main().catch(async (error) => {
  if (error.code === 'ENOENT') {
    console.error(`错误: 文件不存在: ${error.path || ''}`)
  } else if (error instanceof SyntaxError) {
    console.error(`错误: JSON 解析失败: ${error.message}`)
  } else {
    console.error(`错误: ${error.message}`)
  }
  if (process.env.DRAFT_DIRECT_DEBUG) {
    console.error(error.stack)
  }
  process.exit(1)
})
