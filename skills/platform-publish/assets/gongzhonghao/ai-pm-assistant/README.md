# AI PM 小助理公众号封面资产

这套资产只用于微信公众号横版封面，不与小红书长图文封面共用。

## 文件

- `covers/article-cover-base.png`：普通文章封面底图，来自原始文件 `23.png`
- `covers/daily-cover-base.png`：日报封面底图，来自原始文件 `AI PM 日报.png`
- `cover-kit.json`：封面用途、尺寸、文字区域和字体依赖的机器可读清单
- `generate_cover.py`：按 `cover-kit.json` 生成封面 PNG
- `fonts/README.md`：字体准备说明

## 尺寸

两张底图均为 `1283 x 383` PNG，适配微信公众号横版封面场景。

普通文章底图是左右拼接复合封面：左侧 `900 x 383` 供微信 `2.35:1` 场景裁剪，右侧 `383 x 383` 供微信 `1:1` 场景裁剪。`gzh-publish` 会在创建草稿时自动写入对应裁剪坐标，避免微信后台按整张长图居中裁剪。

## 使用约束

- 公众号封面：使用本目录资产。
- 小红书封面：继续使用 `markdown-to-cards` 的竖版卡片封面模板，不要复用本目录的公众号横版底图。
- 文字渲染时按 `cover-kit.json` 中的 `text_slots` 区域做最大字号适配：在不溢出区域的前提下尽量填满区域，并保留 Figma 里的左对齐、右对齐、居中和旋转角度。
- 普通文章封面的目标字体是 `可画文黑-简`；当前目录里的 `fonts/HYWenHei-85W.otf` 只是 `汉仪文黑 85W` fallback，不是精确字体。
- 日报封面的日期使用 `思源黑体超粗体`，本地文件为 `fonts/SourceHanSansSC-Heavy.otf`。

## 生成命令

普通文章封面：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/gongzhonghao/ai-pm-assistant/generate_cover.py article \
  --title "Harness 是什么：模型外面那一层到底在干什么" \
  --output /absolute/path/cover.png
```

日报封面：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/gongzhonghao/ai-pm-assistant/generate_cover.py daily \
  --date 5月26日 \
  --output /absolute/path/daily-cover.png
```

## 输入处理规则

普通文章封面是一张图拆成两个场景：

- 左侧长方形区域：公众号推荐页封面标题。标题拆成上下两段，每段目标不超过 10 个中文等效字符；英文专名按整词保留，不拆字母。每段文字在各自 Figma 区域里自动放到最大。
- 右侧正方形区域：私聊/聊天场景封面关键词。展示两个关键词；每个关键词只能是单个英文词，或不超过 3 个中文字符。关键词在各自 Figma 区域里自动放到最大。

如果原始标题含冒号、破折号或竖线，优先按这些分隔符切标题。否则脚本会按长度和语义做保守切分。用户显式传 `--title-primary`、`--title-secondary`、`--keyword-top`、`--keyword-bottom` 时，以用户传入为准。

日报封面只填日期。日期格式统一为 `M月D日`，例如 `5月26日`、`11月23日`；输入 `YYYY-MM-DD` 会自动转换。

如遇特殊构图，可在文章 Markdown frontmatter 覆盖裁剪坐标：

```yaml
pic_crop_235_1: 0_0_0.701481_1
pic_crop_1_1: 0.701481_0_1_1
```
