import { DirectAdapter } from './base.js'

function generateDeviceId() {
  const chars = '0123456789abcdef'
  let result = ''
  for (let i = 0; i < 32; i++) result += chars[Math.floor(Math.random() * chars.length)]
  return result
}

export class SohuAdapter extends DirectAdapter {
  id = 'sohu'
  name = '搜狐号'
  accountInfo = null
  deviceId = generateDeviceId()
  spCm = ''

  headerRules = [
    {
      urlFilter: '*://mp.sohu.com/*',
      headers: {
        Origin: 'https://mp.sohu.com',
        Referer: 'https://mp.sohu.com/',
      },
    },
  ]

  async checkAuth() {
    try {
      return await this.withHeaderRules(this.headerRules, async () => {
        const response = await this.runtime.fetch(`https://mp.sohu.com/mpbp/bp/account/list?_=${Date.now()}`, {
          method: 'GET',
        })
        if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }

        const res = await response.json()
        if (res.code !== 2000000 || !res.data?.data?.length) {
          return { isAuthenticated: false, error: res.msg || '未登录' }
        }

        const allAccounts = []
        for (const group of res.data.data) {
          if (Array.isArray(group.accounts)) allAccounts.push(...group.accounts)
        }
        if (!allAccounts.length) return { isAuthenticated: false, error: '未找到搜狐号子账号' }

        this.accountInfo = allAccounts[0]
        await this.fetchSpCm()
        return {
          isAuthenticated: true,
          userId: String(this.accountInfo.id),
          username: allAccounts.length > 1
            ? `${this.accountInfo.nickName} (共${allAccounts.length}个子账号)`
            : this.accountInfo.nickName,
          avatar: this.accountInfo.avatar,
        }
      })
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async fetchSpCm() {
    const cookieValue = await this.runtime.getCookie?.('.sohu.com', 'mp-cv')
    this.spCm = cookieValue || `100-${Date.now()}-${generateDeviceId()}`
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        if (!this.accountInfo) {
          const auth = await this.checkAuth()
          if (!auth.isAuthenticated) throw new Error('请先登录搜狐号')
        }

        let content = article.html || ''
        content = await this.processImages(content, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['sohu.com'],
        })

        const accountId = String(this.accountInfo.id)
        const response = await this.runtime.fetch(
          `https://mp.sohu.com/mpbp/bp/news/v4/news/draft/v2?accountId=${accountId}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest',
              'dv-id': this.deviceId,
              'sp-cm': this.spCm,
            },
            body: JSON.stringify({
              title: article.title,
              brief: '',
              content,
              channelId: 24,
              categoryId: -1,
              id: 0,
              userColumnId: 0,
              columnNewsIds: [],
              businessCode: 0,
              declareOriginal: false,
              cover: '',
              topicIds: [],
              isAd: 0,
              userLabels: '[]',
              reprint: false,
              customTags: '',
              infoResource: 0,
              sourceUrl: '',
              visibleToLoginedUsers: 0,
              attrIds: [],
              auto: true,
              accountId: Number(accountId),
            }),
          }
        )
        const res = await response.json()
        if (!res.success || !res.data) throw new Error(res.msg || '保存草稿失败')

        const postId = String(res.data)
        return this.createResult(true, {
          postId,
          postUrl: `https://mp.sohu.com/mpfe/v4/contentManagement/news/addarticle?spm=smmp.articlelist.0.0&contentStatus=2&id=${postId}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  async uploadImageByUrl(src) {
    if (!this.accountInfo) throw new Error('请先登录搜狐号')
    const { blob, filename } = await this.sourceToBlob(src)
    const formData = new FormData()
    formData.append('file', blob, filename || 'image.jpg')
    formData.append('accountId', String(this.accountInfo.id))

    const response = await this.runtime.fetch(
      `https://mp.sohu.com/commons/front/outerUpload/image/file?accountId=${this.accountInfo.id}`,
      {
        method: 'POST',
        body: formData,
      }
    )
    const res = await response.json()
    if (!res.url) throw new Error(`图片上传失败: ${res.msg || '无图片 URL'}`)
    return { url: res.url }
  }
}
