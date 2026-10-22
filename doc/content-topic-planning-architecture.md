# 内容选题与平台巡看

内容选题只保留 content-topic-planning 入口。它负责研究、比较、深化与反馈；用户要刷平台找题时，按需读取 references/platform-scout.md，把平台证据带回同一判断流程。图文、视频和文章按目标选择，不把“可拍视频”作为所有题目的门槛。

来源采集、账号研究和选题判断各负其责：platform-fetch 取得指定来源；content-creator-research 研究账号/赛道；选题 Skill 综合项目定位、现有作品和这些证据，决定值得做什么与还缺什么。采集的排序分数不替代判断，固定篇数、点赞比率和爆款率均非通用准入条件。

原 daily-topic-scout 的平台命令保存在选题 Skill 的平台巡看 reference；platform-scout 与 xiaohongshu 引擎未迁移。当前真实命令能力仍以各引擎和本次账号会话为准，不因合并入口宣称新平台接入。

通用源位于 tools/skills/content-topic-planning，registry 将同一份源同步给 Claude 与 Codex。旧巡看源在 archive/skills/2026-10-21，入口文件改为 SKILL.retired.md；原始模板可追溯，不再自动触发。

本轮验证为 Skill 结构、路由与逻辑契约；没有为这次整理重跑平台真实采集，也未执行内容生产或发布 E2E。
