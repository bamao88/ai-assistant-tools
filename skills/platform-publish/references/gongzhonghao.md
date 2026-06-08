# Skill: gzh-publish

## 触发条件

当用户提到以下任意关键词时激活此 Skill：
- "发布公众号"、"发布到公众号"、"发布微信"、"微信公众号"
- "排版发布"、"公众号排版"、"gzh"
- "上传文章"、"创建草稿"（公众号相关语境）

## 工具路径

```
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts
```

运行命令格式：
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> [options]
```

## 可用主题

**经典系列：** claude(Claude，直觉机器漫谈 / MiaoDX 固定风格), medium(Medium), minimal(极简)

**更多风格：** openai(OpenAI), cards-claude(卡片 Claude), coral(粉红/珊瑚系，AI PM 小助理固定风格), monograph_all_both(黑白书页)

## 账号样式映射（按账号匹配 profile + 主题 + 封面）

每个公众号账号绑定一套固定的发布身份：发布用哪个 `--profile`、排版用哪个主题、封面用哪套 cover kit。做该账号的公众号发布时直接按这张表取，不要每次重新问。

| 账号 | 作者 / 发布身份 | `--profile` | 固定主题 | 封面 cover kit |
|---|---|---|---|---|
| AI PM 小助理 | AI PM超级小助理 | `wxp-ai` | `coral`（粉红/珊瑚系） | `assets/gongzhonghao/ai-pm-assistant/` |
| 直觉机器漫谈 | MiaoDX | `mdx` | `claude` | 使用文章 frontmatter 的 `cover`，不要套用 AI PM 封面 |

封面和模板按账号专属化。`coral`（粉红/珊瑚系）是 AI PM 小助理 / `wxp-ai` 的固定主题；`claude` 是 直觉机器漫谈 / MiaoDX / `mdx` 的固定主题。AI PM 小助理这套封面只用于 `wxp-ai`，不要混用到直觉机器漫谈或其他公众号账号。

config 里 `~/.gzh-publish/config.json` 现有 profile：`mdx`(default) / `wxp-ai` / `wxp-self`。其中 `mdx` = 直觉机器漫谈 / MiaoDX，`wxp-ai` = AI PM 小助理号。

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

## 执行流程

### 1. 检查文件

确认用户提供了 Markdown 文件路径，文件存在且有效。

### 2. 确认主题（如未指定）

先按账号样式映射取固定主题，不要把账号专属主题当成通用推荐：
- AI PM 小助理 / `wxp-ai` → 固定用 `coral`（粉红/珊瑚系）。
- 直觉机器漫谈 / MiaoDX / `mdx` → 固定用 `claude`。

如果用户明确要求非固定账号或实验主题，再询问主题。通用备选主题：
- 技术/开发文章 → `openai`
- 卡片感公众号长文 → `cards-claude`
- 黑白书页/专著感长文 → `monograph_all_both`
- 零干扰极简排版 → `minimal`

### 3. 检查 frontmatter

确认文件有：
- `title`：文章标题
- `cover`：封面图路径（**必填**，否则无法上传）
- `theme`（可选，frontmatter 中指定会覆盖 CLI 参数）

如果已确定公众号账号，frontmatter 里的 `theme` 必须与账号固定主题一致；不一致时先改 frontmatter，再 dry-run。`wxp-ai` 固定 `coral`，`mdx` 固定 `claude`。

### 4. 预览（可选）

运行 dry-run 先预览 HTML：
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --theme <id> --dry-run
```

### 5. 执行上传

**仅创建草稿（推荐）：**
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --theme <id>
```

**指定账号 profile 发布：**
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile mdx
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile wxp-ai
```

按账号固定主题发布示例：

```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile mdx --theme claude
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile wxp-ai --theme coral
```

**创建草稿并直接发布：**
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --theme <id> --publish
```

### 6. 报告结果

告知用户：
- ✓ 草稿已创建 + media_id
- ✓ frontmatter 已更新 `published: draft`
- 如果发布：✓ 已发布 + publish_id

## Markdown frontmatter 格式

```yaml
---
title: "文章标题"
theme: monograph_all_both # 可选，覆盖 CLI 参数；不填则使用工具默认主题
cover: cover.png        # 必填，相对于 .md 文件的路径
author: 作者名          # 可选
digest: 文章摘要描述    # 可选，最多120字
published: false        # false=未发布, draft=草稿, true=已发布
---
```

## 配置要求

需要设置微信公众号凭证（任选一种方式）：

1. **环境变量**：`WECHAT_APP_ID` + `WECHAT_APP_SECRET`
2. **配置文件（多账号）**：`~/.gzh-publish/config.json` 使用 profiles 格式：
   ```json
   {
     "profiles": {
       "mdx": { "WECHAT_APP_ID": "wx...", "WECHAT_APP_SECRET": "..." },
       "wxp-ai": { "WECHAT_APP_ID": "wx...", "WECHAT_APP_SECRET": "..." }
     },
     "default": "mdx"
   }
   ```
   使用时加 `--profile mdx` 或 `--profile wxp-ai`，不加则用 `default` 指定的账号。
3. **配置文件（单账号，兼容旧格式）**：`~/.gzh-publish/config.json` 包含 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`
4. **本地 .env 文件**：在文章所在目录创建 `.env` 文件

验证凭证：
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts --check-auth
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts --check-auth --profile mdx
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts --check-auth --profile wxp-ai
```

## 注意事项

- 已标记 `published: true` 的文章会被跳过
- 正文开头的同名一级标题会自动作为公众号标题处理，不会写入正文
- 封面图是微信草稿的必填项，没有封面图无法上传
- 草稿创建后需在微信公众号后台审核后手动发布（或使用 --publish 直接发布）
- `--dry-run` 模式生成 HTML 文件便于预览，不会调用微信 API
