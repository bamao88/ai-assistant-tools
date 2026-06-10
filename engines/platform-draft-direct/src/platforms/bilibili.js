import { DirectAdapter } from './base.js'

export class BilibiliAdapter extends DirectAdapter {
  id = 'bilibili'
  name = 'B站专栏'
  userInfo = null
  csrf = ''

  headerRules = [
    {
      urlFilter: '*://api.bilibili.com/*',
      headers: {
        Origin: 'https://member.bilibili.com',
        Referer: 'https://member.bilibili.com/',
      },
    },
  ]

  async checkAuth() {
    try {
      return await this.withHeaderRules(this.headerRules, async () => {
        const response = await this.runtime.fetch('https://api.bilibili.com/x/web-interface/nav?build=0&mobi_app=web', {
          method: 'GET',
        })
        if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }
        const res = await response.json()
        if (res.code === 0 && res.data?.isLogin) {
          this.userInfo = res.data
          this.csrf = await this.runtime.getCookie?.('.bilibili.com', 'bili_jct') || ''
          return {
            isAuthenticated: true,
            userId: String(res.data.mid),
            username: res.data.uname,
            avatar: res.data.face,
          }
        }
        return { isAuthenticated: false, error: res.message }
      })
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        if (!this.userInfo) {
          const auth = await this.checkAuth()
          if (!auth.isAuthenticated) throw new Error('请先登录 B站')
        }
        if (!this.csrf) throw new Error('获取 B站 CSRF token 失败，请重新登录')

        let content = article.html || ''
        content = await this.processImages(content, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['hdslb.com', 'bilibili.com', 'biliimg.com'],
        })

        const response = await this.runtime.fetch('https://api.bilibili.com/x/article/creative/draft/addupdate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            tid: '4',
            title: article.title,
            content,
            csrf: this.csrf,
            save: '0',
            pgc_id: '0',
          }).toString(),
        })
        const res = await response.json()
        if (res.code !== 0 || !res.data?.aid) {
          throw new Error(res.message || '保存草稿失败')
        }

        const postId = String(res.data.aid)
        return this.createResult(true, {
          postId,
          postUrl: `https://member.bilibili.com/platform/upload/text/edit?aid=${postId}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  async uploadImageByUrl(src) {
    if (!this.csrf) throw new Error('B站 CSRF token 未获取')
    const { blob, filename } = await this.sourceToBlob(src)
    const formData = new FormData()
    formData.append('binary', blob, filename || 'image.jpg')
    formData.append('csrf', this.csrf)

    const response = await this.runtime.fetch('https://api.bilibili.com/x/article/creative/article/upcover', {
      method: 'POST',
      body: formData,
    })
    const res = await response.json()
    if (res.code !== 0 || !res.data?.url) {
      throw new Error(res.message || '图片上传失败')
    }
    return { url: res.data.url }
  }
}
