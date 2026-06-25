# wechat-channels-fetch

视频号公开账号和作品列表抓取 engine。

实现思路：

- 复用 `engines/tencent-video-publish` 的账号 slot 和 `storage_state.json`。
- 打开视频号页面后，在页面上下文中调用视频号前端初始化出来的 `WXU` API。
- 支持账号搜索、账号作品列表分页、单条作品详情、评论列表。
- 默认使用 Windows 微信内置浏览器 UA；普通 Chrome UA 会被 `web/pages/*` 入口导到升级页。

当前约定：

- 默认账号为 `aipm`，也是测试号。
- `zhanghe` 是真实账号，只在用户明确指定时使用。
- 只读取公开可访问数据；遇到登录失效、页面 API 未初始化、限流或私密内容直接返回结构化错误。

常用命令：

```bash
engines/tencent-video-publish/.venv/bin/python \
  engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm diagnose

engines/tencent-video-publish/.venv/bin/python \
  engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm search-accounts --keyword "张和"

engines/tencent-video-publish/.venv/bin/python \
  engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm list-feeds --username "<finder_username>" --max-pages 3

engines/tencent-video-publish/.venv/bin/python \
  engines/wechat-channels-fetch/scripts/cli.py \
  --account aipm get-feed-detail --object-id "<object_id>" --nonce-id "<nonce_id>"
```

如果要排查视频号助手登录页，可加 `--chrome-ua`；如果 `diagnose` 返回 `api_unavailable`，先看 `diagnostics.pages` 里是 `login_url`、`support_update_url`，还是 `finder_*` 方法缺失。

`list-feeds` 默认把结果写到：

```text
var/data/wechat-channels-fetch/<username>_<timestamp>/
```

其中：

- `feeds.json`：标准化后的作品列表。
- `feeds.jsonl`：一行一个标准化作品，便于后续分析。
- `raw_pages/page_*.json`：原始分页响应，方便排查字段变化。
