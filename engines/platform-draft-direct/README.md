# platform-draft-direct

无 Chrome 插件的草稿直传引擎。使用本地 Cookie 调平台 Web 编辑器草稿 API，只保存草稿，不正式发布。

当前 `assistant_zh` 默认可用平台（2026-06-10 实测）：知乎、掘金、CSDN、百家号、思否。51CTO、博客园、开源中国、B站专栏、搜狐号有适配器能力，但当前账号/登录态未验证为可默认发布。

## 用法

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/platform-draft-direct

# 导入浏览器导出的 Cookie JSON（Chrome extension export 或 Playwright storage_state 均可）
node src/cli.js import-cookies --platform zhihu --file /absolute/path/cookies.json

# 也支持导入原始 Cookie header 文本文件（name=value; name2=value2）
node src/cli.js import-cookies --platform baijiahao --file /absolute/path/baijiahao-cookie.txt
node src/cli.js import-cookies --platform baijiahao --file - < /absolute/path/baijiahao-cookie.txt

PLATFORMS=zhihu,juejin,csdn,baijiahao,segmentfault

# 检查登录态和账号白名单
node src/cli.js auth --platform "$PLATFORMS"

# 预览，不访问平台 API
node src/cli.js sync /absolute/path/article.md --platform "$PLATFORMS" --title "文章标题" --dry-run

# 写入草稿箱
node src/cli.js sync /absolute/path/article.md --platform "$PLATFORMS" --title "文章标题"

# 图片较多或图床较慢时调大超时
PLATFORM_DRAFT_DIRECT_TIMEOUT_MS=180000 \
node src/cli.js sync /absolute/path/article.md --platform "$PLATFORMS" --title "文章标题"

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

账号白名单支持字符串或稳定账号 ID。百家号显示名可能后续修改，拿到 `auth` 输出里的 `id:` 后，可以把 `vendor/wechatsync/config/project-platforms.json` 中的平台配置升级成：

```json
"baijiahao": {
  "username": "利幼枫0hK",
  "userId": "<auth 输出的 id>"
}
```

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

### assistant_zh 实测状态（2026-06-10）

| 平台 | 当前结论 | 备注 |
|------|----------|------|
| `zhihu` | 成功写入草稿 | HTML + 本地图片 |
| `juejin` | 成功写入草稿 | 账号需要已绑定手机号 |
| `csdn` | 成功写入草稿 | Markdown + 本地图片 |
| `baijiahao` | 成功写入草稿 | 大尺寸长图可能需要先压缩 |
| `segmentfault` | 成功写入草稿 | Markdown + 本地图片 |
| `cnblogs` | 当前账号不可用 | 用户尚未开通博客 |
| `sohu` | 当前账号不可用 | 用户不通过 |
| `51cto` | 当前 Cookie 未登录 | 需重新导入 Cookie 后验证 |
| `oschina` | 当前 Cookie 未登录 | 需重新导入 Cookie 后验证 |
| `bilibili` | 当前 Cookie 未登录 | 需重新导入 Cookie 后验证 |
| `toutiao` | 无 direct adapter | 当前走 Chrome 编辑器自动保存草稿 |

默认批量发布建议只使用：

```text
zhihu,juejin,csdn,baijiahao,segmentfault
```

百家号如果返回空响应或 JSON 解析失败，先检查是否有超大长图。已知大尺寸海报压缩后可重试成功。

### 适配器能力

- `zhihu`: HTML 草稿，返回 `https://zhuanlan.zhihu.com/p/<id>/edit`
- `juejin`: Markdown 草稿，返回 `https://juejin.cn/editor/drafts/<id>`
- `csdn`: Markdown 草稿，返回 `https://editor.csdn.net/md?articleId=<id>`
- `baijiahao`: HTML 草稿，返回 `https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=<id>`
- `51cto`: Markdown 草稿，返回 `https://blog.51cto.com/blogger/draft/<id>`
- `cnblogs`: Markdown 草稿，返回 `https://i.cnblogs.com/articles/edit;postId=<id>`
- `segmentfault`: Markdown 草稿，返回 `https://segmentfault.com/write?draftId=<id>`
- `oschina`: Markdown 草稿，返回 `https://my.oschina.net/u/<userId>/blog/write/draft/<id>`
- `bilibili`: B站专栏 HTML 草稿，返回 `https://member.bilibili.com/platform/upload/text/edit?aid=<id>`
- `sohu`: HTML 草稿，返回 `https://mp.sohu.com/mpfe/v4/contentManagement/news/addarticle?...&contentStatus=2&id=<id>`
- `toutiao`: 当前公开 Wechatsync 仓库没有 adapter 源码，本引擎未启用
