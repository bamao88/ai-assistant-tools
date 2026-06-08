import { DirectAdapter } from './base.js'
import { crc32, signAWS4 } from '../aws4.js'

const IMAGEX_AID = '2608'
const IMAGEX_SERVICE_ID = '73owjymdk6'

function generateUuid() {
  return 'xxxxxxxxxxxxxxxx'.replace(/x/g, () => Math.floor(Math.random() * 16).toString(16)) + Date.now().toString()
}

export class JuejinAdapter extends DirectAdapter {
  id = 'juejin'
  name = '掘金'
  cachedCsrfToken = null
  cachedImageXToken = null
  imageXTokenExpiry = 0
  uuid = generateUuid()

  headerRules = [
    {
      urlFilter: '*://api.juejin.cn/*',
      headers: { Origin: 'https://juejin.cn', Referer: 'https://juejin.cn/' },
    },
    {
      urlFilter: '*://imagex.bytedanceapi.com/*',
      headers: { Origin: 'https://juejin.cn', Referer: 'https://juejin.cn/' },
    },
  ]

  async checkAuth() {
    try {
      return await this.withHeaderRules(this.headerRules, async () => {
        const response = await this.runtime.fetch('https://api.juejin.cn/user_api/v1/user/get', {
          method: 'GET',
        })
        if (!response.ok) return { isAuthenticated: false, error: `HTTP ${response.status}` }
        const data = await response.json()
        if (!data.data?.user_id) return { isAuthenticated: false }
        return {
          isAuthenticated: true,
          userId: data.data.user_id,
          username: data.data.user_name,
          avatar: data.data.avatar_large,
        }
      })
    } catch (error) {
      return { isAuthenticated: false, error: error.message }
    }
  }

  async getCsrfToken() {
    if (this.cachedCsrfToken) return this.cachedCsrfToken
    const response = await this.runtime.fetch('https://api.juejin.cn/user_api/v1/sys/token', {
      method: 'HEAD',
      headers: {
        'x-secsdk-csrf-request': '1',
        'x-secsdk-csrf-version': '1.2.10',
      },
    })
    const wareToken = response.headers.get('x-ware-csrf-token')
    if (!wareToken) throw new Error('获取掘金 CSRF token 失败')
    const parts = wareToken.split(',')
    if (parts.length < 2) throw new Error('掘金 CSRF token 格式异常')
    this.cachedCsrfToken = parts[1]
    return this.cachedCsrfToken
  }

  async publish(article) {
    return this.withHeaderRules(this.headerRules, async () => {
      try {
        const csrfToken = await this.getCsrfToken()
        let markdown = article.markdown || ''
        markdown = await this.processImages(markdown, (src) => this.uploadImageByUrl(src), {
          skipPatterns: ['juejin.cn', 'p1-juejin', 'p3-juejin', 'p6-juejin', 'p9-juejin', 'byteimg.com'],
        })

        const response = await this.runtime.fetch('https://api.juejin.cn/content_api/v1/article_draft/create', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-secsdk-csrf-token': csrfToken,
          },
          body: JSON.stringify({
            brief_content: '',
            category_id: '0',
            cover_image: '',
            edit_type: 10,
            html_content: 'deprecated',
            link_url: '',
            mark_content: markdown,
            tag_ids: [],
            title: article.title,
          }),
        })
        const text = await response.text()
        if (!response.ok) throw new Error(`创建草稿失败: ${response.status} - ${text}`)
        const data = JSON.parse(text)
        if (data.err_no && data.err_no !== 0) throw new Error(data.err_msg || `创建草稿失败: ${data.err_no}`)
        if (!data.data?.id) throw new Error(data.err_msg || '创建草稿失败: 无效响应')
        return this.createResult(true, {
          postId: data.data.id,
          postUrl: `https://juejin.cn/editor/drafts/${data.data.id}`,
          draftOnly: true,
        })
      } catch (error) {
        return this.createResult(false, { error: error.message })
      }
    })
  }

  async uploadImageByUrl(src) {
    const { blob } = await this.sourceToBlob(src)
    return { url: await this.uploadImageBinary(blob) }
  }

  async getImageXToken() {
    if (this.cachedImageXToken && Date.now() < this.imageXTokenExpiry - 60000) {
      return this.cachedImageXToken
    }
    const url = `https://api.juejin.cn/imagex/v2/gen_token?aid=${IMAGEX_AID}&uuid=${this.uuid}&client=web`
    const response = await this.runtime.fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    })
    const text = await response.text()
    const data = JSON.parse(text)
    if (data.err_no && data.err_no !== 0) throw new Error(data.err_msg || '获取掘金图片 token 失败')
    const token = data.data?.token
    if (!token?.AccessKeyId || !token?.SecretAccessKey) throw new Error('掘金图片 token 响应异常')

    this.cachedImageXToken = {
      AccessKeyId: token.AccessKeyId,
      SecretAccessKey: token.SecretAccessKey,
      SessionToken: token.SessionToken,
      ExpiredTime: new Date(token.ExpiredTime).getTime(),
    }
    this.imageXTokenExpiry = this.cachedImageXToken.ExpiredTime
    return this.cachedImageXToken
  }

  async applyImageUpload(token) {
    const url = `https://imagex.bytedanceapi.com/?Action=ApplyImageUpload&Version=2018-08-01&ServiceId=${IMAGEX_SERVICE_ID}`
    const signed = signAWS4({
      method: 'GET',
      url,
      accessKeyId: token.AccessKeyId,
      secretAccessKey: token.SecretAccessKey,
      securityToken: token.SessionToken,
      region: 'cn-north-1',
      service: 'imagex',
    })
    const response = await this.runtime.fetch(url, { method: 'GET', headers: signed.headers })
    const data = await response.json()
    if (!data.Result?.UploadAddress) throw new Error('申请掘金图片上传地址失败')
    return data.Result.UploadAddress
  }

  async uploadToTOS(uploadAddress, blob) {
    const storeInfo = uploadAddress.StoreInfos[0]
    const uploadHost = uploadAddress.UploadHosts[0]
    if (!storeInfo || !uploadHost) throw new Error('掘金图片上传地址异常')
    const uploadUrl = `https://${uploadHost}/${storeInfo.StoreUri}`
    const bytes = new Uint8Array(await blob.arrayBuffer())
    const response = await this.runtime.fetch(uploadUrl, {
      method: 'PUT',
      headers: {
        Authorization: storeInfo.Auth,
        'Content-Type': blob.type || 'application/octet-stream',
        'Content-CRC32': crc32(bytes),
      },
      body: blob,
    })
    if (!response.ok) throw new Error(`掘金 TOS 上传失败: ${response.status} - ${await response.text()}`)
  }

  async commitImageUpload(token, sessionKey) {
    const url = `https://imagex.bytedanceapi.com/?Action=CommitImageUpload&Version=2018-08-01&SessionKey=${encodeURIComponent(sessionKey)}&ServiceId=${IMAGEX_SERVICE_ID}`
    const signed = signAWS4({
      method: 'POST',
      url,
      accessKeyId: token.AccessKeyId,
      secretAccessKey: token.SecretAccessKey,
      securityToken: token.SessionToken,
      region: 'cn-north-1',
      service: 'imagex',
    })
    const response = await this.runtime.fetch(url, {
      method: 'POST',
      headers: signed.headers,
    })
    const data = await response.json()
    if (!data.Result) throw new Error('提交掘金图片上传失败')
    return data.Result
  }

  async getImageUrl(uri) {
    const url = `https://api.juejin.cn/imagex/v2/get_img_url?aid=${IMAGEX_AID}&uuid=${this.uuid}&uri=${encodeURIComponent(uri)}&img_type=private`
    const response = await this.runtime.fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    })
    const data = await response.json()
    if (data.err_no && data.err_no !== 0) throw new Error(data.err_msg || '获取掘金图片 URL 失败')
    const imageUrl = data.data?.main_url || data.data?.backup_url
    if (!imageUrl) throw new Error('掘金图片 URL 响应异常')
    return imageUrl
  }

  async uploadImageBinary(blob) {
    const token = await this.getImageXToken()
    const uploadAddress = await this.applyImageUpload(token)
    await this.uploadToTOS(uploadAddress, blob)
    await this.commitImageUpload(token, uploadAddress.SessionKey)
    const storeUri = uploadAddress.StoreInfos[0]?.StoreUri
    if (!storeUri) throw new Error('掘金图片 StoreUri 缺失')
    return this.getImageUrl(storeUri)
  }
}
