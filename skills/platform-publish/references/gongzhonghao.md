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
