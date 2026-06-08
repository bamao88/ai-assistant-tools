import { DirectAdapter } from './base.js'
import { guessExtFromMime, hmacBase64 } from '../util.js'

export class CsdnAdapter extends DirectAdapter {
  id = 'csdn'
  name = 'CSDN'
  userInfo = null
  apiKey = '203803574'
  apiSecret = '9znpamsyl2c7cdrr9sas0le9vbc3r6ba'

  headerRules = [
    {
      urlFilter: '*://bizapi.csdn.net/*',
      headers: { Origin: 'https://editor.csdn.net', Referer: 'https://editor.csdn.net/' },
    },
    {
      urlFilter: '*://imgservice.csdn.net/*',
      headers: { Origin: 'https://editor.csdn.net', Referer: 'https://editor.csdn.net/' },
    },
    {
      urlFilter: '*://csdn-img-blog.obs.cn-north-4.myhuaweicloud.com/*',
      headers: { Origin: 'https://editor.csdn.net', Referer: 'https://editor.csdn.net/' },
    },
  ]

  createUuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
      const r = Math.random() * 16 | 0
      const v = char === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }

  signRequest(apiPath, method = 'POST') {
    const nonce = this.createUuid()
    const signStr = method === 'GET'
      ? `GET\n*/*\n\n\n\nx-ca-key:${this.apiKey}\nx-ca-nonce:${nonce}\n${apiPath}`
      : `POST\n*/*\n\napplication/json\n\nx-ca-key:${this.apiKey}\nx-ca-nonce:${nonce}\n${apiPath}`

    const headers = {
      accept: '*/*',
      'x-ca-key': this.apiKey,
      'x-ca-nonce': nonce,
      'x-ca-signature': hmacBase64('sha256', this.apiSecret, signStr),
      'x-ca-signature-headers': 'x-ca-key,x-ca-nonce',
    }
    if (method === 'POST') headers['content-type'] = 'application/json'
    return headers
  }

  async checkAuth() {
    try {
      return await this.withHeaderRules(this.headerRules, async () => {
        const apiPath = '/blog-console-api/v3/editor/getBaseInfo'
        const response = await this.runtime.fetch(`https://bizapi.csdn.net${apiPath}`, {
          method: 'GET',
          headers: this.signRequest(apiPath, 'GET'),
        })
        if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }
        const res = await response.json()
        if (res.code === 200 && res.data?.name) {
          this.userInfo = {
            csdnid: res.data.name,
            username: res.data.nickname || res.data.name,
            avatarurl: res.data.avatar,
          }
          return {
            isAuthenticated: true,
            userId: res.data.name,
            username: res.data.nickname || res.data.name,
            avatar: res.data.avatar,
          }
        }
        return { isAuthenticated: false }
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
          if (!auth.isAuthenticated) throw new Error('请先登录 CSDN')
        }

        let markdown = article.markdown || ''
        markdown = await this.processImages(markdown, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['csdnimg.cn', 'csdn.net'],
        })

        const apiPath = '/blog-console-api/v3/mdeditor/saveArticle'
        const response = await this.runtime.fetch(`https://bizapi.csdn.net${apiPath}`, {
          method: 'POST',
          headers: this.signRequest(apiPath, 'POST'),
          body: JSON.stringify({
            title: article.title,
            markdowncontent: markdown,
            content: article.html || '',
            readType: 'public',
            level: 0,
            tags: '',
            status: 2,
            categories: '',
            type: 'original',
            original_link: '',
            authorized_status: false,
            not_auto_saved: '1',
            source: 'pc_mdeditor',
            cover_images: [],
            cover_type: 1,
            is_new: 1,
            vote_id: 0,
            resource_id: '',
            pubStatus: 'draft',
            creator_activity_id: '',
          }),
        })
        const res = await response.json()
        if (res.code !== 200 || !res.data?.id) {
          throw new Error(res.msg || res.message || '保存草稿失败')
        }
        return this.createResult(true, {
          postId: res.data.id,
          postUrl: `https://editor.csdn.net/md?articleId=${res.data.id}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  async uploadImageByUrl(src) {
    const { blob } = await this.sourceToBlob(src)
    const ext = guessExtFromMime(blob.type || '')
    const apiPath = '/resource-api/v1/image/direct/upload/signature'
    const signatureResponse = await this.runtime.fetch(`https://bizapi.csdn.net${apiPath}`, {
      method: 'POST',
      headers: this.signRequest(apiPath, 'POST'),
      body: JSON.stringify({
        imageTemplate: '',
        appName: 'direct_blog_markdown',
        imageSuffix: ext,
      }),
    })
    const signatureData = await signatureResponse.json()
    if (signatureData.code !== 200 || !signatureData.data) {
      throw new Error(signatureData.msg || signatureData.message || '获取 CSDN 图片上传签名失败')
    }

    const uploadData = signatureData.data
    const custom = uploadData.customParam
    const formData = new FormData()
    formData.append('key', uploadData.filePath)
    formData.append('policy', uploadData.policy)
    formData.append('signature', uploadData.signature)
    formData.append('callbackBody', uploadData.callbackBody)
    formData.append('callbackBodyType', uploadData.callbackBodyType)
    formData.append('callbackUrl', uploadData.callbackUrl)
    formData.append('AccessKeyId', uploadData.accessId)
    formData.append('x:rtype', custom.rtype)
    formData.append('x:filePath', custom.filePath)
    formData.append('x:isAudit', String(custom.isAudit))
    formData.append('x:x-image-app', custom['x-image-app'])
    formData.append('x:type', custom.type)
    formData.append('x:x-image-suffix', custom['x-image-suffix'])
    formData.append('x:username', custom.username)
    formData.append('file', blob, `image.${ext}`)

    const obsResponse = await this.runtime.fetch(uploadData.host, {
      method: 'POST',
      body: formData,
    })
    const obsData = await obsResponse.json()
    if (obsData.code !== 200 || !obsData.data?.imageUrl) {
      throw new Error(obsData.msg || obsData.message || 'CSDN 图片上传失败')
    }
    return { url: obsData.data.imageUrl }
  }
}
