# 小红书内容获取（xiaohongshu）

适用：搜笔记、首页推荐、笔记详情、用户主页。

## 强制约束

- **唯一执行方式**：只运行本项目的 Python CLI，不要用 MCP 工具、Go 命令行工具或其他实现。
- **完成即止**：拿到结果直接呈现，等待用户下一步。

CLI 路径（每次完整使用，不要省略）：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py <子命令>
```

## 子命令清单

| 子命令 | 用途 |
|--------|------|
| `list-accounts` | 列出已登录账号（每次开始先调） |
| `search-feeds` | 关键词搜索笔记 |
| `list-feeds` | 获取首页推荐 Feed |
| `get-feed-detail` | 获取笔记完整内容和评论 |
| `user-profile` | 获取用户主页信息 |

## 账号选择（强制锁定）

**本 skill 锁定使用 `--account 测试号`，不接受用户选择其他账号。**

所有 CLI 调用必须显式加 `--account 测试号`：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account 测试号 <subcommand> ...
```

**Why**：抓取/搜索/调研操作不应该污染真实账号（每个请求都会在该账号的浏览记录、推荐种子里留下痕迹）。

**禁止**：跳过 `--account` 用默认值、询问用户用哪个账号、临时切其他账号试。

## 输入意图判断

按优先级：

1. "搜索笔记 / 找内容 / 搜关键词" → 搜索流程
2. "首页推荐 / 浏览首页" → 首页 Feed
3. "查看笔记详情 / 看这篇 / 获取笔记内容" → 笔记详情
4. "查看用户主页 / 看看这个博主 / 用户资料" → 用户主页

## 工作流

### 搜索笔记

```bash
# 基础搜索
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py search-feeds \
  --keyword "春招"

# 带筛选
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py search-feeds \
  --keyword "春招" \
  --sort-by 最新 \
  --note-type 图文 \
  --publish-time 一周内 \
  --search-scope 未看过
```

筛选参数：

| 参数 | 可选值 |
|------|--------|
| `--sort-by` | 综合、最新、最多点赞、最多评论、最多收藏 |
| `--note-type` | 不限、视频、图文 |
| `--publish-time` | 不限、一天内、一周内、半年内 |
| `--search-scope` | 不限、已看过、未看过、已关注 |
| `--location` | 不限、同城、附近 |

输出 JSON 含 `feeds` 数组和 `count`，每项含 `id`、`xsec_token`、`note_card`（标题、封面、互动数据）。

### 首页 Feed

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py list-feeds
```

### 笔记详情

`feed_id` 和 `xsec_token` 必须配对使用，从搜索结果或首页 Feed 拿。

```bash
# 基础详情
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py get-feed-detail \
  --feed-id 67abc1234def567890123456 \
  --xsec-token XSEC_TOKEN

# 加载全部评论（含子评论展开）
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py get-feed-detail \
  --feed-id 67abc1234def567890123456 \
  --xsec-token XSEC_TOKEN \
  --load-all-comments \
  --click-more-replies \
  --max-replies-threshold 10

# 限制评论数量
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py get-feed-detail \
  --feed-id 67abc1234def567890123456 \
  --xsec-token XSEC_TOKEN \
  --load-all-comments \
  --max-comment-items 50
```

输出含：笔记完整内容、图片列表、互动数据、评论列表。

### 用户主页

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py user-profile \
  --user-id USER_ID \
  --xsec-token XSEC_TOKEN
```

输出含：用户基本信息、粉丝/关注数、笔记列表（`feeds`，每项 `id` + `xsecToken` + `noteCard.displayTitle`）。

### 发布后抓自己号笔记永久链接（不问用户要链接）

发布完成后回填 `note_url` 用这个——抓发布账号自己主页的 `feeds`，取刚发那条拼永久链接：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account <发布账号> user-profile --user-id <本号user_id> --xsec-token ""
```

- **本号 `user_id` 稳定不变**，首次取一次后复用。取法：登录态下访问 explore，取第一个 `/user/profile/<id>` 且 href **不带** `xsec_token` 的链接（= 导航栏「我」；feed 里作者链接都带 token）。已验证：测试号 `GG` = `577cb1836a6a693421551711`。
- 自己主页用**空** `xsec_token` 即可读 `feeds`（已验证）。
- 取 `feeds[0]`（最新一条；**有置顶**会顶到最前，按 `displayTitle` 核对刚发那条），拼：
  `https://www.xiaohongshu.com/explore/{id}?xsec_token={xsecToken}&xsec_source=pc_feed`
- 坑：`xsecToken` 返回空 = 会话 tab 陈旧，重跑一次（或先访问 explore 暖一下）即可。
- 本 skill 默认锁 `--account 测试号`；**回填自己号链接是例外**，必须 `--account <真实发布账号>` 抓该号自己的主页。

## 失败处理

- **未登录** → 提示用户先做 xhs-auth 登录（CLI 会显式报错）
- **搜索无结果** → 建议换关键词或调整筛选
- **笔记不可访问** → 私密或已删除，告知用户
- **用户主页不可访问** → 用户已注销或设置隐私
