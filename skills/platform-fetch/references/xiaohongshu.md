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
| `download-note-images` | 下载详情结果中的配图，供阅读图中文字 |
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

笔记里重要信息写在图片中时，可以在 `get-feed-detail` 加 `--download-images --image-dir <本地目录>`，返回 `downloadedImages` 本地路径。若详情已取得但再次读取失败，可以把上次 `imageList[].urlDefault` 交给 `download-note-images --image-dir <本地目录> --url '<图片 URL>'`；`--url` 可重复。下载器会把小红书图床的 `http` 链接改为 `https`，并使用平台来源页，避免仅因图片直链方式不对而误判图片不可访问。

### 用户主页

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py user-profile \
  --user-id USER_ID \
  --xsec-token XSEC_TOKEN
```

输出含：用户基本信息、粉丝/关注数、笔记列表（`feeds`，每项 `id` + `xsecToken` + `noteCard.displayTitle`）。

全量公开主页枚举：在 `user-profile` 后增加 `--scroll-to-end`。以 3 秒间隔滚动，按笔记 ID 去重，返回 `coverage`（停止原因、页面末尾文字、结束标记）。`no_growth` 只代表多次滚动无新增，不保证全历史完整；有明确结束标记才可说明已到当前公开主页末尾。最多滚动 60 次。

### 发布后抓运营号笔记永久链接（不问用户要链接；**只用测试号**）

发布完成后回填 `note_url`、以及后续 D+1/D+3/D+7 拉数，**一律用测试号抓运营号的公开主页**，绝不登录/操作运营号——这条链路要反复跑，用运营号自己抓有封号风险，用测试号当普通访客读公开内容没有。运营号已发布笔记是公开的，测试号能直接读。

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account 测试号 user-profile --user-id <运营号public_user_id> --xsec-token ""
```

- `--account 测试号` **固定不变**（符合本 skill「一切抓取锁测试号」）；`--user-id` 填**运营号的公开 user_id**，不是用运营号登录。
- 用**空** `xsec_token` 即可读对方公开主页 `feeds`（已验证：测试号读他人公开主页，空 token 返回完整 feeds + 每条 note 的 xsecToken）。
- **运营号 public user_id 稳定不变**，取一次复用；取法也走测试号/公开链接、不登录运营号：测试号 `search-feeds` 找该号笔记看作者 uid，或从该号任一公开分享链接里的 `/user/profile/<uid>` 取。（测试号自身 uid=`577cb1836a6a693421551711`，仅自测。）
- 取 `feeds[0]`（最新一条；**有置顶**会顶到最前，按 `displayTitle` 核对刚发那条），拼：
  `https://www.xiaohongshu.com/explore/{id}?xsec_token={xsecToken}&xsec_source=pc_feed`
- 坑：`xsecToken` 返回空 = 会话 tab 陈旧，重跑一次（或先访问 explore 暖一下）即可。
- 兜底：profile 抓不到时，测试号 `search-feeds --keyword "<笔记标题>"` 按标题+作者匹配刚发那条拿链接。

## 失败处理

- **未登录** → 提示用户先做 xhs-auth 登录（CLI 会显式报错）
- **搜索无结果** → 建议换关键词或调整筛选
- **笔记不可访问** → 私密或已删除，告知用户
- **用户主页不可访问** → 用户已注销或设置隐私

## 隔离只读标签页与覆盖证据

批量公开资料读取可在全局参数中增加 `--isolated-read`。仍显式使用 `--account 测试号`；每次命令创建并关闭自己拥有的标签页，不修改共享会话指针，避免其它读取任务切页或收尾时干扰本次抓取。该参数仅支持 `user-profile`、`get-feed-detail`、`search-feeds` 和 `list-feeds`。

`coverage` 记录页面滚动位置和笔记分页状态。连续无新增只在页面到底、页面高度稳定后停止；`no_growth` 本身仍不证明全历史。当前公开笔记查询的 `hasMore=false` 可作为当次公开分页结束证据，应同时核对查询对应目标账号和公开笔记列表、无加载错误以及枚举数量。已删除、私密和未展示内容不在覆盖声明中。详情的 `video` 字段保留页面实际返回的媒体流资料，供内部研究下载，不代表转载许可。
