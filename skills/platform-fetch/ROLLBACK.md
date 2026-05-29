# 回滚记录

如需恢复被删除的下层 skill 入口，执行：

```bash
# xhs-fetch（整个目录是符号链接）
ln -s /Volumes/ExtSSD2601/AI_Assistant/tools/engines/xiaohongshu/skills/xhs-fetch \
      /Users/xpw/.claude/skills/xhs-fetch

# gzh-scraper（目录里只有一个符号链接 SKILL.md）
mkdir -p /Users/xpw/.claude/skills/gzh-scraper
ln -s /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper/SKILL.md \
      /Users/xpw/.claude/skills/gzh-scraper/SKILL.md

# tencent-meeting-downloader
mkdir -p /Users/xpw/.claude/skills/tencent-meeting-downloader
ln -s /Volumes/ExtSSD2601/AI_Assistant/tools/engines/tencent-meeting/SKILL.md \
      /Users/xpw/.claude/skills/tencent-meeting-downloader/SKILL.md

# content-research-hub
mkdir -p /Users/xpw/.claude/skills/content-research-hub
ln -s /Volumes/ExtSSD2601/AI_Assistant/tools/content_research_hub/SKILL.md \
      /Users/xpw/.claude/skills/content-research-hub/SKILL.md
```

底层 Python 实现都在 `/Volumes/ExtSSD2601/AI_Assistant/tools/` 没动过，删除符号链接只影响 Claude 是否把它们当独立 skill 触发。
