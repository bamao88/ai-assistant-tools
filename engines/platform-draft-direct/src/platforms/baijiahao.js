import { DirectAdapter } from './base.js'

export class BaijiahaoAdapter extends DirectAdapter {
  id = 'baijiahao'
  name = '百家号'
  userInfo = null
  authToken = ''

  headerRules = [
    {
      urlFilter: '*://baijiahao.baidu.com/*',
      headers: {
        Origin: 'https://baijiahao.baidu.com',
        Referer: 'https://baijiahao.baidu.com/',
      },
    },
  ]

  async checkAuth() {
    try {
      return await this.withHeaderRules(this.headerRules, async () => {
        const response = await this.runtime.fetch(
          `https://baijiahao.baidu.com/builder/app/appinfo?_=${Date.now()}`,
          { method: 'GET' }
        )
        if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }

        const res = await response.json()
        const user = res.data?.user
        if ((res.errmsg === 'success' || res.errno === 0) && user?.userid) {
          this.userInfo = user
          return {
            isAuthenticated: true,
            userId: user.userid,
            username: user.name,
            avatar: user.avatar,
          }
        }

        return { isAuthenticated: false, error: res.errmsg }
      })
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async fetchAuthToken() {
    if (this.authToken) return this.authToken

    const response = await this.runtime.fetch('https://baijiahao.baidu.com/builder/rc/edit', {
      method: 'GET',
    })
    const html = await response.text()
    if (!response.ok) throw new Error(`获取百家号编辑器 token 失败: HTTP ${response.status}`)

    const match = html.match(/window\.__BJH__INIT__AUTH__\s*=\s*['"]([^'"]+)['"]/)
    if (!match) throw new Error('登录失效或编辑器 token 缺失，请重新登录百家号')

    this.authToken = match[1]
    return this.authToken
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        if (!this.userInfo) {
          const auth = await this.checkAuth()
          if (!auth.isAuthenticated) throw new Error('请先登录百家号')
        }

        const token = await this.fetchAuthToken()
        let content = article.html || ''
        content = await this.processImages(content, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['baijiahao.baidu.com', 'bdstatic.com', 'bcebos.com'],
        })

        const response = await this.runtime.fetch(
          'https://baijiahao.baidu.com/pcui/article/save?callback=bjhdraft',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
              token,
            },
            body: new URLSearchParams({
              title: article.title,
              content,
              feed_cat: '1',
              len: String(content.length),
              activity_list: JSON.stringify([{ id: 408, is_checked: 0 }]),
              source_reprinted_allow: '0',
              original_status: '0',
              original_handler_status: '1',
              isBeautify: 'false',
              subtitle: '',
              bjhtopic_id: '',
              bjhtopic_info: '',
              type: 'news',
            }),
          }
        )

        const text = await response.text()
        if (!response.ok) throw new Error(`保存草稿失败: ${response.status} - ${text}`)

        const res = this.parseDraftResponse(text)
        if (res.errmsg !== 'success' || !res.ret?.article_id) {
          throw new Error(res.errmsg || '保存草稿失败')
        }

        const postId = res.ret.article_id
        return this.createResult(true, {
          postId,
          postUrl: `https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=${postId}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  parseDraftResponse(text) {
    const trimmed = String(text || '').trim()
    const jsonText = trimmed
      .replace(/^bjhdraft\(/, '')
      .replace(/\);?$/, '')
    return JSON.parse(jsonText)
  }

  async uploadImageByUrl(src) {
    const { blob, filename } = await this.sourceToBlob(src)

    const formData = new FormData()
    formData.append('media', blob, filename || 'image.jpg')
    formData.append('type', 'image')
    formData.append('app_id', '1589639493090963')
    formData.append('is_waterlog', '1')
    formData.append('save_material', '1')
    formData.append('no_compress', '0')
    formData.append('is_events', '')
    formData.append('article_type', 'news')

    const response = await this.runtime.fetch('https://baijiahao.baidu.com/pcui/picture/uploadproxy', {
      method: 'POST',
      body: formData,
    })
    const res = await response.json()
    if (res.errmsg !== 'success' || !res.ret?.https_url) {
      throw new Error(res.errmsg || '图片上传失败')
    }

    return { url: res.ret.https_url }
  }
}
