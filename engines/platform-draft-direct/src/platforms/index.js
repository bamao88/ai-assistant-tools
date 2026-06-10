import { ZhihuAdapter } from './zhihu.js'
import { JuejinAdapter } from './juejin.js'
import { CsdnAdapter } from './csdn.js'
import { BaijiahaoAdapter } from './baijiahao.js'
import { Cto51Adapter } from './cto51.js'
import { CnblogsAdapter } from './cnblogs.js'
import { SegmentfaultAdapter } from './segmentfault.js'
import { OschinaAdapter } from './oschina.js'
import { BilibiliAdapter } from './bilibili.js'
import { SohuAdapter } from './sohu.js'

export function createAdapter(platform, runtime, options = {}) {
  if (platform === 'zhihu') return new ZhihuAdapter(runtime, options)
  if (platform === 'juejin') return new JuejinAdapter(runtime, options)
  if (platform === 'csdn') return new CsdnAdapter(runtime, options)
  if (platform === 'baijiahao') return new BaijiahaoAdapter(runtime, options)
  if (platform === '51cto') return new Cto51Adapter(runtime, options)
  if (platform === 'cnblogs') return new CnblogsAdapter(runtime, options)
  if (platform === 'segmentfault') return new SegmentfaultAdapter(runtime, options)
  if (platform === 'oschina') return new OschinaAdapter(runtime, options)
  if (platform === 'bilibili') return new BilibiliAdapter(runtime, options)
  if (platform === 'sohu') return new SohuAdapter(runtime, options)
  throw new Error(`不支持的平台: ${platform}`)
}
