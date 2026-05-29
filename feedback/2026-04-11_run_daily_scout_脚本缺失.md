# Bug: run_daily_scout.sh 脚本不存在

**日期**: 2026-04-11  
**模块**: hot_topics_monitor  
**影响**: 每日 8:00 cron 无法执行热点扫描

## 复现步骤

```bash
bash /Volumes/ExtSSD2601/AI_Assistant/shared/ai_topic_scout/hot_topics_monitor/run_daily_scout.sh
# 报错：bash: run_daily_scout.sh: No such file or directory
```

## 期望行为

脚本存在，可执行：
1. 拉取各 RSS/Twitter 源最新内容到 `hot_topics/`
2. 用 LLM 整理生成 `daily_recommend_YYYY-MM-DD.md` 和 `.json`
3. 触发日报追加飞书文档流程

## 实际行为

`hot_topics_monitor/` 目录下只有产出文件（`daily_recommend_*.md` 等），无任何可执行脚本或 Python 文件。

## 目录现状

```
hot_topics_monitor/
├── daily_recommend_2026-04-10.json
├── daily_recommend_2026-04-10.md
├── daily_recommend_2026-04-10_short.txt
├── hot_topics/        ← 原始数据（上次 15:05 采集）
└── logs/
```

## 临时处理

用 4/10 15:05 数据手动生成了 4/11 日报（数据时效约 17 小时）。

## 建议修复

在 `hot_topics_monitor/` 下创建 `run_daily_scout.sh`，功能：
1. 调用抓取脚本拉取新数据到 `hot_topics/`
2. 调用 AI 摘要脚本生成 `daily_recommend_YYYY-MM-DD.md/.json/_short.txt`
3. 退出码 0 = 成功
