import { DirectAdapter } from './base.js'

export class CnblogsAdapter extends DirectAdapter {
  id = 'cnblogs'
  name = '博客园'
  xsrfToken = null

  headerRules = [
    {
      urlFilter: '*://i.cnblogs.com/*',
      headers: {
        Origin: 'https://i.cnblogs.com',
        Referer: 'https://i.cnblogs.com/',
      },
    },
    {
      urlFilter: '*://upload.cnblogs.com/*',
      headers: {
        Origin: 'https://i.cnblogs.com',
        Referer: 'https://i.cnblogs.com/',
      },
    },
  ]

  async checkAuth() {
    try {
      const response = await this.runtime.fetch('https://home.cnblogs.com/user/CurrentUserInfo', {
        method: 'GET',
      })
      const html = await response.text()
      if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }

      const linkMatch = html.match(/href="\/u\/([^/]+)\/"/)
      if (!linkMatch) return { isAuthenticated: false, error: '未登录' }

      const avatarMatch = html.match(/<img[^>]+class="pfs"[^>]+src="([^"]+)"/)
      return {
        isAuthenticated: true,
        userId: linkMatch[1],
        username: linkMatch[1],
        avatar: avatarMatch?.[1],
      }
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async getXsrfToken() {
    if (this.xsrfToken) return this.xsrfToken

    await this.runtime.fetch('https://i.cnblogs.com/posts/edit', { method: 'GET' })
    for (const domain of ['i.cnblogs.com', '.cnblogs.com', 'cnblogs.com']) {
      const value = await this.runtime.getCookie?.(domain, 'XSRF-TOKEN')
      if (value) {
        this.xsrfToken = value
        return value
      }
    }

    throw new Error('获取 XSRF-TOKEN 失败，请重新登录博客园')
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        const xsrfToken = await this.getXsrfToken()
        let markdown = article.markdown || ''
        markdown = await this.processImages(markdown, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['cnblogs.com', 'img2024.cnblogs.com', 'img2023.cnblogs.com'],
        })

        const response = await this.runtime.fetch('https://i.cnblogs.com/api/posts', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-xsrf-token': xsrfToken,
          },
          body: JSON.stringify({
            id: null,
            postType: 2,
            accessPermission: 0,
            title: article.title,
            url: null,
            postBody: markdown,
            categoryIds: null,
            categories: null,
            collectionIds: [],
            inSiteCandidate: false,
            inSiteHome: false,
            siteCategoryId: null,
            blogTeamIds: null,
            isPublished: false,
            displayOnHomePage: false,
            isAllowComments: true,
            includeInMainSyndication: false,
            isPinned: false,
            showBodyWhenPinned: false,
            isOnlyForRegisterUser: false,
            isUpdateDateAdded: false,
            entryName: null,
            description: null,
            featuredImage: null,
            tags: null,
            password: null,
            publishAt: null,
            datePublished: new Date().toISOString(),
            dateUpdated: null,
            isMarkdown: true,
            isDraft: true,
            autoDesc: null,
            changePostType: false,
            blogId: 0,
            author: null,
            removeScript: false,
            clientInfo: null,
            changeCreatedTime: false,
            canChangeCreatedTime: false,
            isContributeToImpressiveBugActivity: false,
            usingEditorId: 5,
            sourceUrl: null,
          }),
        })
        const text = await response.text()
        if (!response.ok) throw new Error(`创建草稿失败: ${response.status} - ${text}`)

        const res = JSON.parse(text)
        if (!res.id) throw new Error(res.error || '创建草稿失败: 无效响应')

        const postId = String(res.id)
        return this.createResult(true, {
          postId,
          postUrl: `https://i.cnblogs.com/articles/edit;postId=${postId}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  async uploadImageByUrl(src) {
    const xsrfToken = await this.getXsrfToken()
    const { blob, filename } = await this.sourceToBlob(src)
    const formData = new FormData()
    formData.append('image', blob, filename || 'image.png')
    formData.append('app', 'blog')
    formData.append('uploadType', 'Select')

    const response = await this.runtime.fetch('https://upload.cnblogs.com/v2/images/cors-upload', {
      method: 'POST',
      headers: { 'x-xsrf-token': xsrfToken },
      body: formData,
    })
    const text = await response.text()
    if (!response.ok) throw new Error(`图片上传失败: ${response.status} - ${text}`)

    const res = JSON.parse(text)
    const imageUrl = res.data || res.url || res.imageUrl || res.src
    if (!imageUrl || typeof imageUrl !== 'string') {
      throw new Error(`图片上传失败: 无法获取图片 URL`)
    }
    return { url: imageUrl }
  }
}
