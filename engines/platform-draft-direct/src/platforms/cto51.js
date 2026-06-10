import { DirectAdapter } from './base.js'
import { guessExtFromMime } from '../util.js'

export class Cto51Adapter extends DirectAdapter {
  id = '51cto'
  name = '51CTO'
  csrf = null

  headerRules = [
    {
      urlFilter: '*://blog.51cto.com/*',
      headers: {
        Origin: 'https://blog.51cto.com',
        Referer: 'https://blog.51cto.com/blogger/publish',
      },
    },
  ]

  async checkAuth() {
    try {
      return await this.withHeaderRules(this.headerRules, async () => {
        const response = await this.runtime.fetch('https://blog.51cto.com/blogger/publish', {
          method: 'GET',
        })
        const html = await response.text()
        if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }

        const imgMatch = html.match(/<li class="more user">\s*<a[^>]*href="([^"]+)"[^>]*>\s*<img[^>]*src="([^"]+)"/)
        if (!imgMatch) return { isAuthenticated: false, error: '未登录' }

        const csrfMatch = html.match(/<meta\s+name="csrf-token"\s+content="([^"]+)"/)
        if (csrfMatch) this.csrf = csrfMatch[1]

        const userLink = imgMatch[1]
        const uid = userLink.split('/').filter(Boolean).pop() || ''
        return {
          isAuthenticated: true,
          userId: uid,
          username: uid,
          avatar: imgMatch[2],
        }
      })
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        if (!this.csrf) {
          const auth = await this.checkAuth()
          if (!auth.isAuthenticated) throw new Error('请先登录 51CTO')
        }

        const hasMarkdown = Boolean(article.markdown)
        let content = article.markdown || article.html || ''
        content = await this.processImages(content, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['51cto.com', 's2.51cto.com'],
        })

        const response = await this.runtime.fetch('https://blog.51cto.com/blogger/draft', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            Accept: 'application/json, text/javascript, */*; q=0.01',
          },
          body: new URLSearchParams({
            title: article.title,
            content,
            pid: '',
            cate_id: '',
            custom_id: '0',
            tag: '',
            abstract: '',
            banner_type: '0',
            blog_type: '1',
            copy_code: '1',
            is_hide: '0',
            top_time: '0',
            is_comment: '0',
            is_old: hasMarkdown ? '0' : '2',
            blog_id: '',
            did: '',
            work_id: '',
            class_id: '',
            subjectId: '',
            import_type: '-1',
            invite_code: '',
            raffle: '',
            orig: '',
            _csrf: this.csrf || '',
          }).toString(),
        })
        const res = await response.json()
        if (res.status !== 1 || !res.data?.did) {
          throw new Error(res.msg || '保存草稿失败')
        }

        const postId = String(res.data.did)
        return this.createResult(true, {
          postId,
          postUrl: `https://blog.51cto.com/blogger/draft/${postId}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  async getUploadSign() {
    const response = await this.runtime.fetch('https://blog.51cto.com/getUploadSign', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: 'upload_type=image',
    })
    const res = await response.json()
    if (res.code !== 0 || !res.data?.sign) throw new Error(res.msg || '获取上传签名失败')
    return res.data
  }

  async getUploadConfig(uploadSign, mimeType, filename) {
    const response = await this.runtime.fetch('https://blog.51cto.com/getUploadConfig', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: new URLSearchParams({
        upload_type: 'image',
        upload_sign: uploadSign,
        ext: mimeType,
        name: filename,
      }).toString(),
    })
    const res = await response.json()
    if (res.code !== 0 || !res.data?.url || !res.data?.fields) {
      throw new Error(res.msg || '获取上传配置失败')
    }
    return res.data
  }

  async uploadImageByUrl(src) {
    const { blob, filename } = await this.sourceToBlob(src)
    const mimeType = blob.type || 'image/jpeg'
    const ext = guessExtFromMime(mimeType)
    const uploadName = filename || `${Date.now()}.${ext}`
    const signData = await this.getUploadSign()
    const configData = await this.getUploadConfig(signData.sign, mimeType, uploadName)

    const formData = new FormData()
    formData.append('key', configData.fields.key)
    formData.append('policy', configData.fields.policy)
    formData.append('x-amz-algorithm', configData.fields['x-amz-algorithm'])
    formData.append('x-amz-signature', configData.fields['x-amz-signature'])
    formData.append('x-amz-credential', configData.fields['x-amz-credential'])
    formData.append('X-Amz-Date', configData.fields['X-Amz-Date'])
    formData.append('Content-Type', mimeType)
    formData.append('file', blob, uploadName)

    const response = await this.runtime.fetch(configData.url, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) throw new Error(`上传到 COS 失败: ${response.status}`)

    return { url: `https://s2.51cto.com/${configData.fields.key}` }
  }
}
