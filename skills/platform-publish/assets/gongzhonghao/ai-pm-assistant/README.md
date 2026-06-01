# AI PM 小助理公众号封面资产

这套资产只用于 `AI PM 小助理` 微信公众号横版封面。不要用于小红书、视频号，或其他公众号账号。

## 文件

| 文件 | 用途 |
|---|---|
| `covers/article-cover-base.png` | 普通文章封面底图 |
| `covers/daily-cover-base.png` | 日报封面底图 |
| `cover-kit.json` | 封面尺寸、用途、字段、文字区域和字体依赖 |
| `generate_cover.py` | 按 `cover-kit.json` 生成最终封面 PNG |
| `fonts/README.md` | 字体文件和来源说明 |

两张底图均为 `1283 x 383` PNG。文字渲染时按 `cover-kit.json` 的 `text_slots` 自动适配字号，在不溢出区域的前提下尽量填满当前模板区域，并保留配置里的对齐、颜色和旋转角度。

## 普通文章封面

普通文章封面是一张左右拼接图，服务两个微信展示场景：

| 区域 | 用途 | 字段 |
|---|---|---|
| 左侧长方形 | 公众号推荐页 / 消息列表封面标题 | `title_primary`、`title_secondary` |
| 右侧正方形 | 私聊、转发卡片、公众号主页等 1:1 场景关键词 | `keyword_top`、`keyword_bottom` |

字段规则：

| 字段 | 是否必填 | 内容规则 |
|---|---|---|
| `title` | 推荐传入 | 原始文章标题；脚本会自动拆成上下两段，并提取右侧关键词 |
| `title_primary` | 可选覆盖 | 左侧上方标题段，目标不超过 10 个中文等效字符 |
| `title_secondary` | 可选覆盖 | 左侧下方标题段，目标不超过 10 个中文等效字符，可做轻度语义压缩 |
| `keyword_top` | 可选覆盖 | 右侧上方关键词，单个英文词，或不超过 3 个中文字符 |
| `keyword_bottom` | 可选覆盖 | 右侧下方关键词，单个英文词，或不超过 3 个中文字符 |

自动处理规则：

- 标题优先按冒号、破折号、竖线等分隔符拆成上下两段。
- 英文专名按整词保留，不拆字母。
- 关键词优先提取标题里的英文专名；中文关键词优先取 AI、产品、技术相关名词。
- 用户显式传 `--title-primary`、`--title-secondary`、`--keyword-top`、`--keyword-bottom` 时，以用户传入为准。

普通文章封面字体为 `思源宋体粗体`，文件是 `fonts/SourceHanSerifCN-Heavy.otf`，文字颜色为黑色。

## 日报封面

日报封面只填日期，左右两个红色日期牌显示同一个值。

| 字段 | 是否必填 | 内容规则 |
|---|---|---|
| `date` | 可选 | 日报日期；格式为 `M月D日`，例如 `5月26日`、`11月23日`；也可传 `YYYY-MM-DD`，脚本会自动转换。不传时使用当天日期 |

日报日期字体为 `思源黑体超粗体`，文件是 `fonts/SourceHanSansSC-Heavy.otf`，文字颜色为白色。

## 裁剪

普通文章封面左侧 `900 x 383` 供微信 `2.35:1` 场景裁剪，右侧 `383 x 383` 供微信 `1:1` 场景裁剪。`gzh-publish` 创建草稿时会自动写入裁剪坐标，避免微信后台按整张长图居中裁剪。

如需手动覆盖，可在 Markdown frontmatter 写：

```yaml
pic_crop_235_1: 0_0_0.701481_1
pic_crop_1_1: 0.701481_0_1_1
```

## 生成命令

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/gongzhonghao/ai-pm-assistant/generate_cover.py article \
  --title "Harness 是什么：模型外面那一层到底在干什么" \
  --output /absolute/path/article-cover.png
```

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/gongzhonghao/ai-pm-assistant/generate_cover.py daily \
  --date 5月26日 \
  --output /absolute/path/daily-cover.png
```
