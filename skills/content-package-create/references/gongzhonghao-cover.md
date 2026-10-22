# 公众号封面制作

本说明供 `content-package-create` 在本地制作公众号封面使用；不访问公众号后台。

## 公众号封面选择逻辑（先判断用哪种封面）

AI PM 小助理号的文章按类型选封面，不要默认套同一套：

| 文章类型 | 封面形式 | 怎么做 |
|---|---|---|
| 普通原创文章（概念拆解 / 知识笔记 / 解读） | 文章封面 kit | `generate_cover.py article --title ...`，title 拆左标题 + 右关键词 |
| AI 日报 | 日报封面 kit | `generate_cover.py daily --date ...` |
| **视频 / 外部源转写类**（YouTube / 播客 / 访谈转写成文章） | **直接用数据源封面图** | 不套 kit、不跑 `generate_cover.py`；直接拿数据源自带的封面当公众号封面（如 YouTube 视频封面 `https://i.ytimg.com/vi/<id>/maxresdefault.jpg`），存进 item assets 后写进 frontmatter `cover` |

为什么转写类单独走数据源封面：这类文章的「主角」是那条视频 / 那场访谈本身，原封面（人物、品牌、节目画面）比自制标题卡更有辨识度和点击欲；现有两套 kit（标题卡、日报卡）都不适配这种「指向一个外部内容」的形态。数据源封面常是 16:9，`gzh-publish` 会按默认裁剪写 `pic_crop_235_1` / `pic_crop_1_1`，需要时在 frontmatter 显式覆盖裁剪坐标。

首例：Legora YC 访谈转写（ZHC20260608_201637_001，副号），封面 = 该 YouTube 视频封面。

## 公众号封面资产

公众号横版封面与小红书竖版卡片封面分开管理。不要把小红书 `markdown-to-cards` 封面直接当公众号封面使用。

AI PM 小助理号的公众号封面资产目录：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/gongzhonghao/ai-pm-assistant/
```

| 文件 | 用途 |
|---|---|
| `covers/article-cover-base.png` | AI PM 小助理普通文章封面底图 |
| `covers/daily-cover-base.png` | AI PM 小助理日报封面底图 |
| `generate_cover.py` | 生成最终封面 PNG |
| `cover-kit.json` | 封面用途、字段、文字区域、字体和裁剪配置 |
| `fonts/README.md` | 字体文件和来源说明 |

当前底图尺寸均为 `1283x383`。生成最终封面时，应按 `cover-kit.json` 的文字区域自动适配字号：在不溢出区域的前提下尽量填满当前模板区域，并保留配置里的对齐和旋转角度。导出为新的文章本地封面文件，再写入 Markdown frontmatter 的 `cover` 字段。

字体约定：
- 普通文章封面动态文字：使用 `思源宋体粗体`，本地文件 `fonts/SourceHanSerifCN-Heavy.otf`，默认黑色。
- 日报封面日期：`思源黑体超粗体`，本地文件 `fonts/SourceHanSansSC-Heavy.otf`。

普通文章封面是一张图拆两个场景使用：
- 注意：这里的短句规则只约束封面文字 `title_primary` / `title_secondary`，不约束 Markdown frontmatter 里的公众号文章 `title`。AI PM 小助理的公众号长文标题应保留来源、人物/公司、数字、问题或冲突，按公众号规则控制在 64 字以内；不要因为封面要短句，把文章标题也压成短标签。
- 左侧长方形区域：公众号推荐页 / 消息列表封面标题。字段为 `title_primary`、`title_secondary`，由 `title` 自动拆分，目标每段不超过 10 个中文等效字符；英文专名按整词保留。
- 右侧正方形区域：私聊、转发卡片、公众号主页等 1:1 场景关键词。字段为 `keyword_top`、`keyword_bottom`，每个关键词是单个英文词，或不超过 3 个中文字符。
- 上传草稿时，`gzh-publish` 会自动识别这类 `2.35:1 + 1:1` 左右拼接长图，并写入微信草稿接口的 `pic_crop_235_1` 与 `pic_crop_1_1`：左侧用于 2.35:1（消息列表），右侧用于 1:1（转发卡片/公众号主页）。不要手动把整张长图居中裁剪。
- 如需微调，可在 Markdown frontmatter 显式写 `pic_crop_235_1` / `pic_crop_1_1`（格式：`X1_Y1_X2_Y2`，坐标为原图左上角 0,0 到右下角 1,1 的归一化值），工具会优先使用 frontmatter。

普通文章封面字段：

| 字段 | 是否必填 | 内容 |
|---|---|---|
| `title` | 推荐传入 | 原始文章标题；脚本会自动拆成上下两段，并提取右侧关键词 |
| `title_primary` | 可选覆盖 | 左侧上方标题段 |
| `title_secondary` | 可选覆盖 | 左侧下方标题段 |
| `keyword_top` | 可选覆盖 | 右侧上方关键词 |
| `keyword_bottom` | 可选覆盖 | 右侧下方关键词 |

日报封面只填 `date`。格式为 `M月D日`，例如 `5月26日`、`11月23日`；也可传 `YYYY-MM-DD`，脚本会自动转换。不传时使用当天日期。

生成命令：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/gongzhonghao/ai-pm-assistant/generate_cover.py article \
  --title "<文章标题>" \
  --output "/absolute/path/cover.png"

python3 /Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/gongzhonghao/ai-pm-assistant/generate_cover.py daily \
  --date "5月26日" \
  --output "/absolute/path/daily-cover.png"
```

