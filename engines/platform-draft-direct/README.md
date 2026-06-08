# platform-draft-direct

无 Chrome 插件的草稿直传引擎。首批支持知乎、掘金、CSDN：使用本地 Cookie 调平台 Web 编辑器草稿 API，只保存草稿，不正式发布。

## 用法

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/platform-draft-direct

# 导入浏览器导出的 Cookie JSON（Chrome extension export 或 Playwright storage_state 均可）
node src/cli.js import-cookies --platform zhihu --file /absolute/path/cookies.json

# 检查登录态和账号白名单
node src/cli.js auth --platform zhihu,juejin,csdn

# 预览，不访问平台 API
node src/cli.js sync /absolute/path/article.md --platform zhihu,juejin,csdn --title "文章标题" --dry-run

# 写入草稿箱
node src/cli.js sync /absolute/path/article.md --platform zhihu,juejin,csdn --title "文章标题"

# 写入知乎草稿时预设发布设置
node src/cli.js sync /absolute/path/article.md \
  --platform zhihu \
  --title "文章标题" \
  --cover /absolute/path/cover.png \
  --zhihu-creation-statement ai_creation \
  --zhihu-reward false \
  --zhihu-column none \
  --zhihu-toc false
```

Cookie 存储在 `/Volumes/ExtSSD2601/AI_Assistant/tools/var/credentials/platform-draft-direct/<platform>.json`，不会进入 git。命令不会打印 Cookie 值。

## 文章 Frontmatter

CLI 参数会覆盖 frontmatter。知乎当前支持的草稿设置：

```markdown
---
title: 文章标题
cover: /absolute/path/cover.png
zhihu_creation_statement: ai_creation
zhihu_reward: false
zhihu_column: none
zhihu_toc: false
---
```

- `zhihu_creation_statement`: `none`、`ai_creation`、`spoiler`、`medical_advice`、`fictional_creation`、`contain_finance`
- `zhihu_reward`: 是否开启送礼物
- `zhihu_column`: 专栏 ID；`none` 表示不发布到专栏
- `zhihu_toc`: 是否开启目录

## 平台状态

- `zhihu`: HTML 草稿，返回 `https://zhuanlan.zhihu.com/p/<id>/edit`
- `juejin`: Markdown 草稿，返回 `https://juejin.cn/editor/drafts/<id>`
- `csdn`: Markdown 草稿，返回 `https://editor.csdn.net/md?articleId=<id>`
- `toutiao`: 当前公开 Wechatsync 仓库没有 adapter 源码，本引擎未启用
