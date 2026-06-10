import { DirectAdapter } from './base.js'

export class OschinaAdapter extends DirectAdapter {
  id = 'oschina'
  name = '开源中国'
  userId = null

  headerRules = [
    {
      urlFilter: '*://apiv1.oschina.net/oschinapi/*',
      headers: {
        Origin: 'https://my.oschina.net',
        Referer: 'https://my.oschina.net/',
      },
    },
  ]

  async checkAuth() {
    try {
      return await this.withHeaderRules(this.headerRules, async () => {
        const response = await this.runtime.fetch('https://apiv1.oschina.net/oschinapi/user/myDetails', {
          method: 'GET',
        })
        if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }

        const res = await response.json()
        if (!res.success || !res.result?.userId) {
          return { isAuthenticated: false, error: res.message || '未登录' }
        }

        this.userId = String(res.result.userId)
        return {
          isAuthenticated: true,
          userId: this.userId,
          username: res.result.userVo?.name || this.userId,
          avatar: res.result.userVo?.portraitUrl,
        }
      })
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        if (!this.userId) {
          const auth = await this.checkAuth()
          if (!auth.isAuthenticated) throw new Error('请先登录开源中国')
        }

        const rawMarkdown = article.markdown || ''
        const useMarkdown = rawMarkdown.trim().length > 0
        let content = useMarkdown ? rawMarkdown : (article.html || '')
        content = await this.processImages(content, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['oschina.net', 'static.oschina.net'],
        })

        const response = await this.runtime.fetch('https://apiv1.oschina.net/oschinapi/api/draft/save_draft', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: article.title,
            user: Number(this.userId),
            content,
            contentType: useMarkdown ? 1 : 2,
            catalog: 0,
            originUrl: '',
            privacy: true,
            disableComment: false,
          }),
        })
        const res = await response.json()
        if (!res.success || !res.result?.id) {
          throw new Error(res.message || '保存草稿失败')
        }

        const draftId = String(res.result.id)
        return this.createResult(true, {
          postId: draftId,
          postUrl: `https://my.oschina.net/u/${this.userId}/blog/write/draft/${draftId}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  async uploadImageByUrl(src) {
    if (!this.userId) await this.checkAuth()
    const { blob, filename } = await this.sourceToBlob(src)
    const formData = new FormData()
    formData.append('file', blob, filename || 'image.jpg')

    const response = await this.runtime.fetch('https://apiv1.oschina.net/oschinapi/ai/creation/project/uploadDetail', {
      method: 'POST',
      body: formData,
    })
    const res = await response.json()
    if (!res.success || !res.result) {
      throw new Error(res.message || '图片上传失败')
    }
    return { url: res.result }
  }
}
