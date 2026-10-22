# 小红书账号研究

负责公开主页、作品和评论的研究采集；现行命令、参数和输出说明见 [小红书采集 reference](../../platform-fetch/references/xiaohongshu.md)。先读它，再按本次问题选择命令。

## 执行路径

优先消费已有原文、截图或导出；需要补采时可用当前可用的只读浏览器、连接器，或本地 CLI。独立测试会话与运营号隔离；CLI 显式使用测试号：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account 测试号 --isolated-read user-profile \
  --user-id <USER_ID> --xsec-token <CURRENT_PROFILE_TOKEN>
```

主页 token 与每条笔记的 token 不通用。优先从当前页面/响应取对应值；不要复用测试文档的历史值。公开主页在当前工具支持时可用空主页 token；详情仍使用对应作品的有效 token。

需要核对正文、图片、评论或发布时间时再取详情：

```bash
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/.venv/bin/python \
  /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py \
  --account 测试号 --isolated-read get-feed-detail \
  --feed-id <FEED_ID> --xsec-token <CURRENT_FEED_TOKEN>
```

评论是问题需要时的补充证据；具体加载参数按采集 reference。不因为“深度研究”就默认全量加载评论。重要信息在图片或视频内时读对应内容，缺少媒体只报告已读部分。

## 字段核对

当前 CLI 的主页响应为 `basicInfo`、`interactions[]`、`feeds[]`。`interactions[]` 按 `type/name/count` 识别实际指标；不能假设存在顶层 `fans` 或 `total_liked`。

主页 `feeds[]` 当前使用 `id`、`xsecToken`、`displayTitle`、`type` 和 `interactInfo`；互动字段如 `likedCount`、`collectedCount`、`commentCount` 可能为空或缩写字符串。搜索/详情响应可能另有嵌套层，以真实输出为准。主页摘要没有日期或正文时补详情，不从标题猜。

用户要求完整公开主页时，在 `user-profile` 加 `--scroll-to-end` 并检查 `coverage`。单次默认列表不等于全量，`no_growth` 不单独证明结束。

## 研究输出

保留账号链接、作品 ID/链接、实际读取内容和数据时间。高互动与普通作品一起比较；只研究少数作品时交付相应范围结论。遇到会话失效、验证、权限或限流，按当前 reference 恢复测试环境或报告阻塞，不换运营号，不执行互动。
