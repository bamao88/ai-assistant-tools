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

**经典系列：** claude(Claude), medium(Medium), minimal(极简)

**更多风格：** openai(OpenAI), cards-claude(卡片 Claude), coral(珊瑚极简), monograph_all_both(黑白书页)

## 账号样式映射（按账号匹配 profile + 主题 + 封面）

每个公众号账号绑定一套固定的发布身份：发布用哪个 `--profile`、排版用哪个主题、封面用哪套 cover kit。做该账号的公众号发布时直接按这张表取，不要每次重新问。

| 账号 | `--profile` | 固定主题 | 封面 cover kit |
|---|---|---|---|
| AI PM 超级小助理（副号） | `wxp-ai` | `coral`（珊瑚极简，唯一粉红/珊瑚系） | `assets/gongzhonghao/ai-pm-assistant/`（粉紫渐变 #ff67c0→#9521b5） |

约定来源：用户 2026-05-31 指定。后续每接入一个新公众号账号，就往这张表加一行（profile、专属主题、专属封面 kit）。封面和模板都按账号专属化——当前 AI PM 小助理这套封面样式与 coral 主题就是该账号专属，不要混用到别的账号。

config 里 `~/.gzh-publish/config.json` 现有 profile：`mdx`(default) / `wxp-ai` / `wxp-self`。其中 `wxp-ai` = AI PM 小助理号。

## 公众号封面资产

公众号横版封面与小红书竖版卡片封面分开管理。不要把小红书 `markdown-to-cards` 封面直接当公众号封面使用。

AI PM 小助理号的公众号封面资产：

```text
/Volumes/ExtSSD2601/AI_Assistant/tools/skills/platform-publish/assets/gongzhonghao/ai-pm-assistant/
```

- 普通文章底图：`covers/article-cover-base.png`
- 日报底图：`covers/daily-cover-base.png`
- 封面生成脚本：`generate_cover.py`
- 字体和文字区域清单：`cover-kit.json`
- 字体准备说明：`fonts/README.md`

当前底图尺寸均为 `1283x383`。生成最终封面时，应按 `cover-kit.json` 的文字区域自动适配字号：在不溢出区域的前提下尽量填满区域，并保留 Figma 里的左对齐、右对齐、居中和旋转角度。导出为新的文章本地封面文件，再写入 Markdown frontmatter 的 `cover` 字段。

字体约定：
- 普通文章封面动态文字：目标字体是 `可画文黑-简`。当前本地 `fonts/HYWenHei-85W.otf` 的真实字体名是 `汉仪文黑 85W`，只是 fallback；如果用户提供真正的可画文黑字体文件，应替换普通文章 4 个槽位的 `font_file`。
- 日报封面日期：`思源黑体超粗体`，本地文件 `fonts/SourceHanSansSC-Heavy.otf`。

普通文章封面是一张图拆两个场景使用：
- 左侧长方形区域：公众号推荐页封面标题。把原始标题拆成上下两段，每段目标不超过 10 个中文等效字符；英文专名按整词保留；每段文字在各自 Figma 区域里自动放到最大。
- 右侧正方形区域：私聊/聊天场景封面关键词。提取 2 个关键词；每个关键词是单个英文词，或不超过 3 个中文字符；关键词在各自 Figma 区域里自动放到最大。

日报封面只填日期，统一格式为 `M月D日`，例如 `5月26日`、`11月23日`。

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

询问用户想用哪种主题，或使用工具当前默认主题 `medium`。推荐主题：
- 技术/开发文章 → `openai`
- 人文/生活内容 → `claude`、`medium`
- 卡片感公众号长文 → `cards-claude`
- 精致视觉长文 → `coral`
- 黑白书页/专著感长文 → `monograph_all_both`
- 零干扰极简排版 → `minimal`

### 3. 检查 frontmatter

确认文件有：
- `title`：文章标题
- `cover`：封面图路径（**必填**，否则无法上传）
- `theme`（可选，frontmatter 中指定会覆盖 CLI 参数）

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
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <file.md> --profile wxp
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
       "wxp": { "WECHAT_APP_ID": "wx...", "WECHAT_APP_SECRET": "..." }
     },
     "default": "mdx"
   }
   ```
   使用时加 `--profile mdx` 或 `--profile wxp`，不加则用 `default` 指定的账号。
3. **配置文件（单账号，兼容旧格式）**：`~/.gzh-publish/config.json` 包含 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`
4. **本地 .env 文件**：在文章所在目录创建 `.env` 文件

验证凭证：
```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts --check-auth
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts --check-auth --profile mdx
```

## 注意事项

- 已标记 `published: true` 的文章会被跳过
- 正文开头的同名一级标题会自动作为公众号标题处理，不会写入正文
- 封面图是微信草稿的必填项，没有封面图无法上传
- 草稿创建后需在微信公众号后台审核后手动发布（或使用 --publish 直接发布）
- `--dry-run` 模式生成 HTML 文件便于预览，不会调用微信 API
