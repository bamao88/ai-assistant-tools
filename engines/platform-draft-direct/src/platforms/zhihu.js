import { DirectAdapter } from './base.js'
import { hmacBase64, md5Hex, parseBoolean } from '../util.js'

const CREATION_STATEMENTS = new Set([
  'none',
  'ai_creation',
  'spoiler',
  'medical_advice',
  'fictional_creation',
  'contain_finance',
])

export class ZhihuAdapter extends DirectAdapter {
  id = 'zhihu'
  name = '知乎'

  headerRules = [
    {
      urlFilter: '*://www.zhihu.com/api/*',
      headers: { 'x-requested-with': 'fetch' },
    },
    {
      urlFilter: '*://zhuanlan.zhihu.com/api/*',
      headers: { 'x-requested-with': 'fetch' },
    },
    {
      urlFilter: '*://api.zhihu.com/*',
      headers: { 'x-requested-with': 'fetch' },
    },
  ]

  async checkAuth() {
    try {
      return await this.withHeaderRules(this.headerRules, async () => {
        const response = await this.runtime.fetch('https://www.zhihu.com/api/v4/me', {
          method: 'GET',
          headers: { 'x-requested-with': 'fetch' },
        })
        if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }
        const data = await response.json()
        if (!data.id) return { isAuthenticated: false }
        return {
          isAuthenticated: true,
          userId: data.id,
          username: data.name,
          avatar: data.avatar_url,
        }
      })
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        const createResponse = await this.runtime.fetch('https://zhuanlan.zhihu.com/api/articles/drafts', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-requested-with': 'fetch',
          },
          body: JSON.stringify({
            title: article.title,
            content: '',
            delta_time: 0,
          }),
        })
        const createText = await createResponse.text()
        if (!createResponse.ok) {
          throw new Error(`创建草稿失败: ${createResponse.status} - ${createText}`)
        }
        const createData = JSON.parse(createText)
        if (!createData.id) throw new Error('创建草稿失败: 无效响应')

        let content = article.html || ''
        content = await this.processImages(content, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['zhimg.com', 'pic1.zhimg.com', 'pic2.zhimg.com', 'pic3.zhimg.com', 'pic4.zhimg.com'],
        })
        content = this.transformContent(content)

        const payload = await this.buildUpdatePayload(article, content)
        const updateResponse = await this.runtime.fetch(
          `https://zhuanlan.zhihu.com/api/articles/${createData.id}/draft`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'x-requested-with': 'fetch',
            },
            body: JSON.stringify(payload),
          }
        )
        if (!updateResponse.ok) {
          throw new Error(`更新草稿失败: ${updateResponse.status} - ${await updateResponse.text()}`)
        }

        return this.createResult(true, {
          postId: createData.id,
          postUrl: `https://zhuanlan.zhihu.com/p/${createData.id}/edit`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  async buildUpdatePayload(article, content) {
    const payload = {
      title: article.title,
      content,
    }

    Object.assign(payload, this.buildDraftSettings(article))

    if (article.cover) {
      const cover = await this.uploadImageByUrl(article.cover)
      payload.titleImage = cover.url
      payload.isTitleImageFullScreen = false
    }

    return payload
  }

  buildDraftSettings(article) {
    const settings = {}

    const creationStatement = this.readOption(article, [
      'creationStatement',
      'creation_statement',
      'disclaimer',
      'zhihu_creation_statement',
      'zhihu_disclaimer',
    ])
    if (creationStatement !== undefined && creationStatement !== '') {
      const type = String(creationStatement).trim()
      if (!CREATION_STATEMENTS.has(type)) {
        throw new Error(`知乎创作声明不支持: ${type}`)
      }
      settings.disclaimer_type = type
      settings.disclaimer_status = type === 'none' ? 'close' : 'open'
    }

    const reward = this.readOption(article, ['reward', 'canReward', 'zhihu_reward', 'zhihu_can_reward'])
    if (reward !== undefined && reward !== '') {
      settings.canReward = parseBoolean(reward, 'zhihu_reward')
    }

    const column = this.readOption(article, ['column', 'zhihu_column'])
    if (column !== undefined && column !== '') {
      const value = String(column).trim()
      settings.column = ['none', 'null', 'false', '0', ''].includes(value.toLowerCase()) ? [] : [value]
    }

    const toc = this.readOption(article, ['toc', 'table_of_contents', 'zhihu_toc', 'zhihu_table_of_contents'])
    if (toc !== undefined && toc !== '') {
      settings.table_of_contents = parseBoolean(toc, 'zhihu_toc')
    }

    return settings
  }

  readOption(article, names) {
    const platformOptions = article.platformOptions?.zhihu || {}
    const metadata = article.metadata || {}
    for (const name of names) {
      if (platformOptions[name] !== undefined) return platformOptions[name]
    }
    for (const name of names) {
      if (metadata[name] !== undefined) return metadata[name]
    }
    return undefined
  }

  transformContent(content) {
    let result = this.transformTables(content)
    result = result.replace(/<img([^>]+)src="([^"]+)"([^>]*)>/gi, '<figure><img$1src="$2"$3></figure>')
    result = result.replace(/<pre><code class="language-(\w+)">/gi, '<pre lang="$1"><code>')
    result = result.replace(/\s*data-(?!draft)[a-z-]+="[^"]*"/gi, '')
    result = result.replace(/\s*style="[^"]*"/gi, '')
    result = this.removeEmptyBlocks(result)
    return this.compactHtml(result)
  }

  removeEmptyBlocks(html) {
    return html.replace(/<(p|div)(?:\s[^>]*)?>\s*(?:<br\s*\/?>)?\s*<\/\1>/gi, '')
  }

  compactHtml(html) {
    return html
      .replace(/>\s+</g, '><')
      .trim()
  }

  transformTables(html) {
    return html.replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (_match, tableContent) => {
      const thead = tableContent.match(/<thead[^>]*>([\s\S]*?)<\/thead>/i)?.[1] || ''
      let body = tableContent.match(/<tbody[^>]*>([\s\S]*?)<\/tbody>/i)?.[1]
      if (!body) body = tableContent.replace(/<thead[^>]*>[\s\S]*?<\/thead>/gi, '')
      const headerRows = thead.replace(/<td([^>]*)>/gi, '<th$1>').replace(/<\/td>/gi, '</th>')
      return `<table data-draft-node="block" data-draft-type="table" data-size="normal" data-row-style="normal"><tbody>${headerRows}${body}</tbody></table>`
    })
  }

  async uploadImageByUrl(src) {
    if (/^https?:\/\//i.test(src)) {
      const response = await this.runtime.fetch('https://zhuanlan.zhihu.com/api/uploaded_images', {
        method: 'POST',
        headers: {
          'x-requested-with': 'fetch',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ url: src, source: 'article' }),
      })
      const data = await response.json()
      if (data.src) return { url: data.src }
      throw new Error('知乎图片上传失败')
    }

    const { blob } = await this.sourceToBlob(src)
    return { url: await this.uploadImageBinary(blob) }
  }

  async uploadImageBinary(blob) {
    const buffer = await blob.arrayBuffer()
    const imageHash = md5Hex(buffer)
    const tokenResponse = await this.runtime.fetch('https://api.zhihu.com/images', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_hash: imageHash, source: 'article' }),
    })
    const tokenData = await tokenResponse.json()
    const uploadFile = tokenData.upload_file
    if (!uploadFile?.image_id) throw new Error('知乎图片上传凭证获取失败')

    if (uploadFile.state === 1) {
      const detail = await this.waitForImageReady(uploadFile.image_id)
      return `https://pic4.zhimg.com/${detail.original_hash}`
    }

    await this.ossUpload('https://zhihu-pics-upload.zhimg.com', uploadFile.object_key, blob, tokenData.upload_token)
    const suffix = blob.type === 'image/gif' ? '.gif' : ''
    return `https://pic4.zhimg.com/${uploadFile.object_key}${suffix}`
  }

  async waitForImageReady(imageId) {
    for (let i = 0; i < 10; i++) {
      const response = await this.runtime.fetch(`https://api.zhihu.com/images/${imageId}`)
      const data = await response.json()
      if (data.status === 'completed' || data.original_hash) return data
      await new Promise((resolve) => setTimeout(resolve, 1000))
    }
    throw new Error('知乎图片处理超时')
  }

  async ossUpload(endpoint, objectKey, blob, token) {
    const contentType = blob.type || 'application/octet-stream'
    const url = `${endpoint}/${objectKey}`
    const ossDate = new Date().toUTCString()
    const ossHeaders = {
      'x-oss-date': ossDate,
      'x-oss-security-token': token.access_token,
      'x-oss-user-agent': 'aliyun-sdk-js/6.8.0',
    }
    const canonicalizedOSSHeaders = Object.keys(ossHeaders)
      .sort()
      .map((key) => `${key}:${ossHeaders[key]}`)
      .join('\n')
    const stringToSign = [
      'PUT',
      '',
      contentType,
      ossDate,
      `${canonicalizedOSSHeaders}`,
      `/zhihu-pics/${objectKey}`,
    ].join('\n')
    const signature = hmacBase64('sha1', token.access_key, stringToSign)
    const response = await this.runtime.fetch(url, {
      method: 'PUT',
      headers: {
        'Origin': 'https://zhuanlan.zhihu.com',
        'Referer': 'https://zhuanlan.zhihu.com/',
        'Content-Type': contentType,
        'Authorization': `OSS ${token.access_id}:${signature}`,
        'x-oss-date': ossDate,
        'x-oss-security-token': token.access_token,
        'x-oss-user-agent': 'aliyun-sdk-js/6.8.0',
      },
      body: blob,
    })
    if (!response.ok) {
      throw new Error(`知乎 OSS 上传失败: ${response.status} - ${await response.text()}`)
    }
  }
}
