# 微信公众号账号研究

支持定位公众号、列公开文章、读取代表正文并分析选题与表达；完整命令和服务说明见 [公众号采集 reference](../../platform-fetch/references/gongzhonghao.md)。先读它。

## 采集顺序

1. 先用已有文章、项目导出或研究资料；需要补采时检查授权会话。
2. 按准确名称或已知链接定位公众号并确认 `fakeid`，不要仅靠同名昵称混合资料。
3. 按研究时间窗列文章；选择不同主题、栏目及表现的代表正文。
4. 核对全文是否实际可读，图文信息是否已覆盖，记录列表与正文缺项。

本地已知入口：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py check-auth
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py search-accounts --keyword "<公众号名>"
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py list-articles --fakeid <FAKEID> --size <本轮列表数量>
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/scripts/cli.py download-article --url <ARTICLE_URL> --format md --account-name "<公众号名>"
```

依赖的 exporter 服务由 CLI 按需启动。只有登录确已失效、平台要求本人验证或服务自动启动失败时，按具体问题请求介入；不要求用户手动启动一切依赖。

## 可分析的证据

账号自述、文章标题、主题、正文结构、原创/转载标识、栏目、发布时间、头条/次条关系，以及平台实际提供的阅读/在看/点赞等。未返回的数据标“未取得”，不猜阅读量或账号平均表现。

标题/摘要列表只能支持列表层结论；正文结构与作者表达需要读正文。未见某类文章不代表该号历史上从未做过。读者需求可从文章问题和公开反馈归纳；不能推断完整粉丝画像或商业转化。

这里执行一次研究采集；长期监控列表、定时任务和发布都需要用户另行授权。文章不可访问时保留链接与错误，说明对当前结论的影响，不绕权限。
