# xhs-search-note Skill 文档路径过时

## 复现
运行 `Skill(xhs-search-note)`，skill 文档里写死的命令是：
```
/Volumes/ExtSSD2601/AI_Assistant_manage/tools/engines/xiaohongshu/.venv/bin/python /Volumes/ExtSSD2601/AI_Assistant_manage/tools/engines/xiaohongshu/scripts/cli.py ...
```

## 期望
命令能直接跑通。

## 实际
`AI_Assistant_manage/tools/engines/xiaohongshu/` 这个目录不存在。真实路径是 `AI_Assistant/tools/engines/xiaohongshu/`（少一个 `_manage`）。`ls` 确认：

```
$ ls /Volumes/ExtSSD2601/AI_Assistant_manage/tools/
feedback
```

只有 `feedback`，没有 `xiaohongshu_skills`。真实路径：
```
$ ls /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py
/Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/scripts/cli.py
```

## 参数位置问题
Skill 文档示例写的是：
```
cli.py search-feeds --keyword "春招"
```
但 `--account` 参数位置错了。文档里隐含可以放在子命令后，实际 argparse 要求放在子命令**前**：
```
cli.py --account 测试号_小红书 search-feeds --keyword "xxx"  # 正确
cli.py search-feeds --account 测试号_小红书 --keyword "xxx"  # 报错 unrecognized arguments
```

## 建议
1. 把 SKILL.md 里所有路径从 `AI_Assistant_manage/tools/engines/xiaohongshu` 改成 `AI_Assistant/tools/engines/xiaohongshu`
2. 在文档里明确 `--account` 的位置是在子命令之前（作为全局参数）
3. 可以考虑把路径抽成变量 `$XHS_CLI`，避免散落在每条示例里

## 影响范围
- xhs-search-note
- xhs-fetch-note
- xhs-fetch-user
- xhs-publish-*
- xhs-auth
- xhs-comment
- xhs-like

所有 xhs-* skill 文档可能都有这个路径问题，建议批量统一检查。
