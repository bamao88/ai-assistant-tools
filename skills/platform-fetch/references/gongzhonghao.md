# 微信公众号文章采集（gongzhonghao）

适用：搜公众号、列最近文章、下载单篇、监控、选题/竞品/爆款分析。

## 前置条件

1. wechat-article-exporter 服务跑在 `http://localhost:3000`
2. 已完成扫码登录并保存了 auth-key

服务不需要用户手动开。CLI 在需要 exporter 的命令前会自动后台启动并等待可用。

只有自动启动失败、或需要用户扫码/复制 auth-key 时才请求用户介入。

要单独检查/启动服务：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/gzh/exporter_service.py
```

## CLI 路径

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py <子命令>
```

每次触发后先 `check-auth`。未登录就 `login` 并提示用户扫码 + 保存 auth-key。

## 子命令

### 认证

```bash
# 检查登录
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py check-auth

# 浏览器扫码登录
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py login

# 保存 auth-key
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py set-auth-key --key <AUTH_KEY>
```

### 搜索 & 浏览

```bash
# 搜公众号
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py search-accounts --keyword "AI"

# 列文章
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py list-articles --fakeid <FAKEID> --size 10

# 按关键词搜文章
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py list-articles --fakeid <FAKEID> --keyword "大模型"

# 下载单篇
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py download-article --url <URL> --format md --account-name "某公众号"
```

### 监控

```bash
# 添加监控
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py add-watch \
  --fakeid <FAKEID> --name "某公众号" \
  --min-reads 10000 --min-likes 100 \
  --keywords "AI,大模型" --since-days 7

# 查看监控列表
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py list-watch

# 移除
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py remove-watch --fakeid <FAKEID>

# 跑一次采集
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py run-monitor

# 模拟（不下载）
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py run-monitor --dry-run
```

## 典型工作流

**选题参考：** `search-accounts` 找号 → `list-articles --size 20` 浏览 → 挑文章 `download-article --format md`

**竞品监控：** `search-accounts` → `add-watch` 设置筛选 → `run-monitor` 手动触发或等 cron

**爆款分析：** `list-articles --size 50` 拿大量数据 → 分析 JSON 里的阅读量、点赞 → 找高数据文章的共同特征（标题模式、发布时间）

**发布后回填自己号 note_url（不问用户要链接）：** `check-auth` →
`list-articles --fakeid <自己号fakeid> --size 15` → 按标题匹配刚发那篇，取 `link`（永久链接）回填到内容真源；`create_time` 顺带校验发布日期。
已接管自己号：**AI PM 小助理**（副号）fakeid = `Mzk3NTI5MzM5NQ==`。
> 微信官方 `freepublish/batchget` 对该号返回 48001 无权限，读已群发列表只能走这里的 `list-articles`。

## 输出

所有命令输出 JSON（`ensure_ascii=False`）：

```json
{
  "success": true/false,
  "error": "错误信息（仅失败时）",
  "...": "其他数据字段"
}
```

下载文章存放：

```
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/data/{公众号名称}/{YYYY-MM}/{文章标题}.html
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/data/{公众号名称}/{YYYY-MM}/{文章标题}.json  # 元数据
```

## 注意

- 微信限流严格，CLI 内置 3 秒请求间隔
- auth-key 默认 30 天有效
- 每次执行命令前先 `check-auth`
- 单次最多 100 篇
