---
name: gzh-scraper
description: |
  微信公众号/公号文章抓取、拉取、采集与监控。支持搜索公众号、列出最近文章、下载文章、公众号数据获取、管理监控列表、自动采集、选题参考、竞品观察和爆款分析。
  当用户说"公众号抓取"、"抓公众号"、"拉取公众号文章"、"读取公众号文章"、"找某公众号最近文章"、"搜索公众号"、"采集文章"、"微信文章下载"、"监控公众号"、"公众号数据"、"爆款分析"、"选题参考"时触发。
---

# 微信公众号文章采集

## 前置条件

1. wechat-article-exporter 服务需要运行在 `http://localhost:3000`
2. 已完成扫码登录并保存了 auth-key

服务不需要用户手动打开。CLI 会在需要 exporter 的命令前自动后台启动服务并等待可用。

如果要单独检查或启动服务，运行：
```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/gzh/exporter_service.py
```

只有在自动启动失败，或需要用户扫码/复制 auth-key 时，才请求用户介入。

## CLI 路径

所有命令前缀：
```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py
```

每次触发本 skill 后，先运行 `check-auth`。如果未登录，再运行 `login` 并提示用户扫码登录和保存 auth-key。

## 可用子命令

### 认证管理

```bash
# 检查登录状态
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py check-auth

# 打开浏览器扫码登录
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py login

# 保存 auth-key（从浏览器 Cookie 获取）
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py set-auth-key --key <AUTH_KEY>
```

### 搜索与浏览

```bash
# 搜索公众号
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py search-accounts --keyword "AI"

# 列出文章
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py list-articles --fakeid <FAKEID> --size 10

# 按关键词搜索文章
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py list-articles --fakeid <FAKEID> --keyword "大模型"

# 下载单篇文章
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py download-article --url <URL> --format md --account-name "某公众号"
```

### 监控管理

```bash
# 添加监控
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py add-watch \
  --fakeid <FAKEID> --name "某公众号" \
  --min-reads 10000 --min-likes 100 \
  --keywords "AI,大模型" --since-days 7

# 查看监控列表
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py list-watch

# 移除监控
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py remove-watch --fakeid <FAKEID>

# 执行一次监控采集
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py run-monitor

# 模拟运行（不下载）
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py run-monitor --dry-run
```

## 典型工作流

### 选题参考流程

1. `search-accounts --keyword "AI"` 找到目标公众号，记下 `fakeid`
2. `list-articles --fakeid xxx --size 20` 浏览最新文章
3. 选择感兴趣的文章，`download-article --url xxx --format md` 下载

### 竞品监控流程

1. `search-accounts` 找到竞品公众号
2. `add-watch` 添加到监控列表，设置筛选条件
3. `run-monitor` 手动触发一次，或等 cron 自动执行

### 爆款分析

1. `list-articles --fakeid xxx --size 50` 获取大量文章数据
2. 分析返回的 JSON 数据中的阅读量、点赞等指标
3. 识别高数据文章的共同特征（标题模式、发布时间等）

## 输出格式

所有命令输出 JSON（`ensure_ascii=False`），结构统一：
```json
{
  "success": true/false,
  "error": "错误信息（仅失败时）",
  "...": "其他数据字段"
}
```

## 文章存储位置

下载的文章保存在：
```
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/data/{公众号名称}/{YYYY-MM}/{文章标题}.html
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/data/{公众号名称}/{YYYY-MM}/{文章标题}.json  # 元数据
```

## 注意事项

- 微信限流较严格，CLI 内置 3 秒请求间隔
- auth-key 默认 30 天有效（已修改 exporter 源码 TTL）
- 每次执行命令前建议先 `check-auth` 确认登录状态
- 单次最多采集 100 篇文章
