# 公众号博主调研（抓取部分）

目标：把一个微信公众号最近的文章拉全，供上层做选题/爆款/节奏分析。

## CLI 路径

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py <子命令>
```

依赖 wechat-article-exporter 服务（`http://localhost:3000`）。CLI 在需要时自动后台启动；只有自动启动失败或需扫码/auth-key 时才请求用户介入。

## 前置：认证

```bash
python3 .../engines/gzh-scraper/scripts/cli.py check-auth
# 未登录：
python3 .../engines/gzh-scraper/scripts/cli.py login          # 浏览器扫码
python3 .../engines/gzh-scraper/scripts/cli.py set-auth-key --key <AUTH_KEY>
```

## 抓取流程

### 1. 定位公众号（拿 fakeid）

```bash
python3 .../engines/gzh-scraper/scripts/cli.py search-accounts --keyword "<公众号名>"
```

从结果里确认目标号，记下其 `fakeid`。

### 2. 列最近文章

```bash
python3 .../engines/gzh-scraper/scripts/cli.py list-articles --fakeid <FAKEID> --size 20
```

输出每篇：标题、链接、发布时间、（可得时）阅读/在看/点赞。默认拉最近 10–20 篇；用户要"全量历史"再加大 `--size` 或翻页。

### 3. 下载代表性正文

挑高互动或主题代表性的若干篇下载正文，做内容结构/选题分析：

```bash
python3 .../engines/gzh-scraper/scripts/cli.py download-article \
  --url <ARTICLE_URL> --format md --account-name "<公众号名>"
```

### 4. 结构化落盘

汇总：标题 / 发布时间 / 阅读·在看·点赞 / 主题分类 / 篇幅 / 头条 vs 次条，供上层分析选题矩阵、爆款规律、发布频率与时段。

## 失败处理

- exporter 未起来 / auth 失效 → 按提示扫码、保存 auth-key；自动启动失败再请用户介入。
- 文章 404 / 被删 → 跳过并记录。
- 限流 → 降速、加 sleep；大批量下载提示用户输出目录占用。
