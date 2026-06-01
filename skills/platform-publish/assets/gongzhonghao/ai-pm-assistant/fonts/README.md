# 字体

生成封面时优先加载本目录字体，找不到时再 fallback 到系统字体或备用字体。字体用途以 `cover-kit.json` 为准。

| 字体 | 用途 | 已放入文件 | 来源/限制 |
|---|---|---|---|
| 思源宋体粗体 | 普通文章封面：标题、右侧关键词 | `SourceHanSerifCN-Heavy.otf` | 本机剪映缓存字体，仅用于个人封面生成 |
| 思源黑体超粗体 | 日报封面：左右日期牌 | `SourceHanSansSC-Heavy.otf` | Adobe Source Han Sans，SIL Open Font License 1.1 |
| 阿里巴巴普惠体 | 备用中文字体 | `AlibabaPuHuiTi-3-85-Bold.ttf` | 阿里巴巴字体官网，免费商用 |

## 来源

- 思源宋体粗体：
  - 使用文件：`SourceHanSerifCN-Heavy.otf`
  - 原始文件：`/Volumes/ExtSSD2601/JianyingPro/User Data/Cache/AITextTemplate/Resource/9396968699109282531/SourceHanSerifCN-Heavy.otf`
  - 验证结果：`family=Source Han Serif CN,思源宋体 CN`，`fullname=Source Han Serif CN Heavy,思源宋体 CN Heavy`
  - 用途限制：本机缓存字体，仅用于个人封面生成。
- 思源黑体：<https://github.com/adobe-fonts/source-han-sans/releases/tag/2.005R>
  - 使用文件：<https://raw.githubusercontent.com/adobe-fonts/source-han-sans/2.005R/OTF/SimplifiedChinese/SourceHanSansSC-Heavy.otf>
- 阿里巴巴普惠体：<https://www.alibabafonts.com/>
  - 使用文件：<https://fonts.alibabadesign.com/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf>
