# 字体准备

这套公众号封面需要以下字体。当前目录已放入实际渲染需要的字体文件，并在 `cover-kit.json` 里记录来源。

## 需要的字体

| 字体 | 用途 | 已放入文件 | 来源/限制 |
|---|---|---|
| 可画文黑-简 | 普通文章封面：标题、右侧关键词 | `HYWenHei-85W.otf` | 当前只是汉仪文黑 85W fallback；不是精确的可画文黑-简 |
| 思源黑体超粗体 | 日报封面：左右日期牌 | `SourceHanSansSC-Heavy.otf` | Adobe Source Han Sans，SIL Open Font License 1.1 |
| 阿里巴巴普惠体 | 备用中文字体 | `AlibabaPuHuiTi-3-85-Bold.ttf` | 阿里巴巴字体官网，免费商用 |

## 来源记录

- 思源黑体：<https://github.com/adobe-fonts/source-han-sans/releases/tag/2.005R>
  - 使用文件：<https://raw.githubusercontent.com/adobe-fonts/source-han-sans/2.005R/OTF/SimplifiedChinese/SourceHanSansSC-Heavy.otf>
- 阿里巴巴普惠体：<https://www.alibabafonts.com/>
  - 使用文件：<https://fonts.alibabadesign.com/AlibabaPuHuiTi-3/AlibabaPuHuiTi-3-85-Bold/AlibabaPuHuiTi-3-85-Bold.ttf>
- 可画文黑-简：当前目录里的 `HYWenHei-85W.otf` 真实字体名是 `汉仪文黑 85W / HYWenHei 85W`，只能作为 fallback；不是已经确认的精确可画文黑-简文件。
  - 汉仪官网页：<https://www.hanyi.com.cn/productdetail?id=986>
  - 使用文件：<https://hellofonts.oss-cn-beijing.aliyuncs.com/%E6%B1%89%E4%BB%AA%E6%96%87%E9%BB%91/9.00.00/HYWenHei-85W.otf>
  - 限制：仅按个人/非商业使用；如果后续公众号封面用于商业投放或品牌商业素材，应补汉仪商用授权或换成可商用字体。
  - 如果拿到真正的 `可画文黑-简` 字体文件，应替换 `cover-kit.json` 中普通文章 4 个槽位的 `font_file`，并更新本文件来源记录。

## 本机候选

```text
/Volumes/ExtSSD2601/JianyingPro/User Data/Cache/AITextTemplate/Resource/13179570373606979275/SourceHanSansCN-Heavy.ttf
```

## 放置规则

生成封面时应优先加载本目录字体，找不到时再 fallback 到系统字体。当前 Figma 设计上下文里普通文章 4 个文字节点仍显示为 `Inter Regular`，本机字体索引也找不到 `可画文黑-简`；`HYWenHei-85W.otf` 的真实字体名是 `汉仪文黑 85W`，不是 `可画文黑-简`。
