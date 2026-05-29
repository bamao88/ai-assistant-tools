# Bug：daily_digest.sh dedup 输出路径硬编码到 WXP_agent 目录

**日期**：2026-04-15
**工具**：`/Volumes/ExtSSD2601/AI_Assistant_manage/tools/ai_topic_scout/hot_topics_monitor/daily_digest.sh`

## 复现步骤

运行 `bash daily_digest.sh`，Step 1（dedup_and_rank.py）执行成功，但输出文件写入了错误路径。

## 期望行为

dedup 产物写入：
`/Volumes/ExtSSD2601/AI_Assistant_manage/tools/ai_topic_scout/hot_topics_monitor/daily_digest_YYYY-MM-DD.json`

## 实际行为

dedup 产物写入：
`/Volumes/ExtSSD2601/WXP_agent/topic_extractor/hot_topics_monitor/daily_digest_YYYY-MM-DD.json`

随后 Step 2 检查原路径，发现文件不存在，直接退出，daily_recommend 无法生成。

## 日志片段

```
Output: /Volumes/ExtSSD2601/WXP_agent/topic_extractor/hot_topics_monitor/daily_digest_2026-04-15.json (30 candidates)
[2026-04-15 11:51:07] Step 1: Dedup OK — /Volumes/ExtSSD2601/AI_Assistant_manage/.../daily_digest_2026-04-15.json
[2026-04-15 11:51:07] Digest file not found: ...daily_digest_2026-04-15.json, exiting
```

另外 Step 2 调用 `claude -p` 会因 `CLAUDECODE` 环境变量存在而失败（不能嵌套 Claude Code 会话），建议改为 `env -u CLAUDECODE claude -p`。

## 临时绕过

手动 `cp` 文件后可继续，但 daily_recommend 的 AI 精选步骤仍因嵌套限制无法运行。
