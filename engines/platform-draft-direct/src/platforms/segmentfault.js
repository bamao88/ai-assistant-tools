import { DirectAdapter } from './base.js'

export class SegmentfaultAdapter extends DirectAdapter {
  id = 'segmentfault'
  name = '思否'
  sessionToken = null

  headerRules = [
    {
      urlFilter: '*://segmentfault.com/gateway/*',
      headers: {
        Origin: 'https://segmentfault.com',
        Referer: 'https://segmentfault.com/',
      },
    },
  ]

  async checkAuth() {
    try {
      const response = await this.runtime.fetch('https://segmentfault.com/user/settings', {
        method: 'GET',
      })
      const html = await response.text()
      if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }

      const userLinkMatch = html.match(/href="\/u\/([^"]+)"/)
      if (!userLinkMatch) return { isAuthenticated: false, error: '未登录' }

      const avatarMatch = html.match(/src="(https:\/\/avatar-static\.segmentfault\.com\/[^"]+)"/)
      return {
        isAuthenticated: true,
        userId: userLinkMatch[1],
        username: userLinkMatch[1],
        avatar: avatarMatch?.[1],
      }
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async getSessionToken() {
    if (this.sessionToken) return this.sessionToken

    const response = await this.runtime.fetch('https://segmentfault.com/write', { method: 'GET' })
    const html = await response.text()
    if (!response.ok) throw new Error(`获取思否 token 失败: HTTP ${response.status}`)

    const tokenMatch = html.match(/serverData":\s*\{\s*"Token"\s*:\s*"([^"]+)"/)
    if (tokenMatch) {
      this.sessionToken = tokenMatch[1]
      return this.sessionToken
    }

    const markStr = 'window.g_initialProps = '
    const start = html.indexOf(markStr)
    if (start === -1) throw new Error('获取思否 session token 失败')

    const end = html.indexOf(';\n\t</script>', start)
    if (end === -1) throw new Error('解析思否 session token 失败')

    const config = JSON.parse(html.substring(start + markStr.length, end))
    const token = config?.global?.sessionInfo?.key
    if (!token) throw new Error('思否 session token 为空')

    this.sessionToken = token
    return token
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        const token = await this.getSessionToken()
        let content = article.markdown || article.html || ''
        content = await this.processImages(content, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['segmentfault.com', 'image-static.segmentfault.com', 'avatar-static.segmentfault.com'],
        })

        const response = await this.runtime.fetch('https://segmentfault.com/gateway/draft', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            token,
            accept: '*/*',
          },
          body: JSON.stringify({
            title: article.title,
            tags: [],
            text: content,
            object_id: '',
            type: 'article',
          }),
        })
        const text = await response.text()
        this.throwIfBlocked(text)
        if (!response.ok) throw new Error(`保存草稿失败: ${response.status} - ${text}`)

        const res = JSON.parse(text)
        const postId = this.extractDraftId(res)
        if (!postId) {
          const errorMsg = res.message || res.msg || res.error || res.errMsg || JSON.stringify(res)
          throw new Error(errorMsg)
        }

        return this.createResult(true, {
          postId: String(postId),
          postUrl: `https://segmentfault.com/write?draftId=${postId}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  extractDraftId(res) {
    if (Array.isArray(res)) {
      if (res[0] === 1) throw new Error(res[1] || '保存草稿失败')
      return res[1]?.id
    }
    return res.id
  }

  throwIfBlocked(text) {
    if (text === 'Unauthorized') throw new Error('未授权')
    if (text.includes('禁言') || text.includes('锁定')) throw new Error(text)
  }

  async uploadImageByUrl(src) {
    const token = await this.getSessionToken()
    const { blob, filename } = await this.sourceToBlob(src)
    const formData = new FormData()
    formData.append('image', blob, filename || 'image.jpg')

    const response = await this.runtime.fetch('https://segmentfault.com/gateway/image', {
      method: 'POST',
      headers: { token },
      body: formData,
    })
    const text = await response.text()
    this.throwIfBlocked(text)
    if (!response.ok) throw new Error(`图片上传失败: ${response.status} - ${text}`)

    const res = JSON.parse(text)
    const imageUrl = res.result || (Array.isArray(res) ? (res[0] === 1 ? null : res[1] || `https://image-static.segmentfault.com/${res[2]}`) : null)
    if (!imageUrl) throw new Error(Array.isArray(res) ? (res[1] || '图片上传失败') : '图片上传失败')
    return { url: imageUrl }
  }
}
