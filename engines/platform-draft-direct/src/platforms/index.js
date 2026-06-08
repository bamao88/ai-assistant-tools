import { ZhihuAdapter } from './zhihu.js'
import { JuejinAdapter } from './juejin.js'
import { CsdnAdapter } from './csdn.js'

export function createAdapter(platform, runtime, options = {}) {
  if (platform === 'zhihu') return new ZhihuAdapter(runtime, options)
  if (platform === 'juejin') return new JuejinAdapter(runtime, options)
  if (platform === 'csdn') return new CsdnAdapter(runtime, options)
  throw new Error(`不支持的平台: ${platform}`)
}
