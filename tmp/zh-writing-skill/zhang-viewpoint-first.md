# Zhang Viewpoint First

大选题文章不要从外部资料或写作结构开始。先找张和已经怎么判断这件事，再用 deep research 把这个判断做深。

目标不是把张和已有内容机械复述出来，而是把它当作观点原点：如果张和已有内容只有 50% 深度，可以通过研究补机制、证据、案例、反例和边界，把文章推到 80 分；但不能杜撰经历，不能把外部研究结论伪装成张和原话，也不能让最终观点偏离张和的基本立场。

## 适用场景

内容/分析文章只要满足任一条件，就先执行本文件，再进入 `topic-preflight.md`：

- 用户只给了一个大选题：Agent、AI PM、Skill、Evals、产品化、作品集、训练营、某个行业事件。
- 文章需要代表张和主账号发表，而不是普通资料整理。
- 需要先判断“张和怎么看”，再决定是否研究和怎么写。
- 基于单篇外部资料或新闻写解读，但用户期待张和观点。

运营通知、活动介绍、嘉宾宣传等事务文可以不执行本文件。

## 检索顺序

先找张和观点，再做外部研究。按这个顺序查：

1. `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/wiki/expertise/`
   - 优先找已经沉淀过的主题判断、概念框架和边界。
2. `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/raw/works/`
   - 找张和已公开文章、草稿、历史表达。
3. `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/raw/meeting/`
   - 找会议、课程、答疑里对同一问题的判断。
4. `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/raw/course/`
   - 找训练营教材、作业点评、方法定义。
5. `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/raw/chat/`
   - 只在前面找不到时补查；聊天内容通常置信度较低。
6. `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/profile/voice-brief.md`
   和 `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/profile/boss-profile.md`
   - 只用于人设、表达边界和口吻，不把 profile 当事实来源。
7. `../../../.agents/skills/content-writing-guide/refer/`
   - 只用于找已认可文章的高层质量原则，不用于推断张和没说过的观点。

## 必须先输出的 Dossier

在 Article Brief 之前，先输出：

```markdown
# Zhang Viewpoint Dossier

## Topic
大选题是什么，边界收在哪里。

## Search Terms Used
实际检索过的关键词。

## Confirmed Zhang Views
- [观点] 来源：[文件路径或用户给定素材]；置信度 HIGH / MEDIUM / LOW；证据类型：原文 / 会议 / 课程 / 聊天 / 用户输入。

## Viewpoint Core
用 1-2 句话概括张和对这个题的原始立场。

## Boundaries
张和没有说过什么；哪些结论不能直接归到张和名下。

## Depth Gap
现有张和材料缺什么：机制、数据、案例、反例、产品细节、行业对照、读者动作。

## Research Questions
接下来 deep research 要解决哪些问题，才能把 50% 深度推到 80% 文章。

## Research Source Ledger
- [研究延展判断或数字] 来源：[URL 或文件路径]；原文支持到什么程度：直接支持 / 间接支持 / 只支持方向不支持数字；可否写进正文：YES / DOWNGRADE / NO。

## Allowed Extensions
哪些延展是允许的：可以由外部研究支撑，但必须标成研究后的判断或本文推演，不能写成张和原话。

## Forbidden Moves
哪些写法会导致观点偏移或杜撰。

## Decision Before Research
WRITE-RESEARCH / SUPPLEMENT-ZHANG-VIEW / DOWNGRADE / KILL
```

## 置信度

- `HIGH`：张和公开文章、原始作品、明确 boss_take、知识库 expertise 中的稳定判断。
- `MEDIUM`：会议/课程/多处材料一致的转述，能看出稳定立场但不是完整文章。
- `LOW`：从 profile、相关主题、零散聊天推断出来的倾向。

第一人称张和文章至少需要 `MEDIUM` 观点置信度，或用户在本轮明确给出张和的观点。只有 `LOW` 时，不能写成“我一直认为”“我在训练营里看到”，只能补素材、降级成研究备忘，或请用户补张和判断。

## Deep Research 的作用

deep research 是为了加深张和观点，不是替换张和观点。

研究可以补：

- 原始事实、发布时间、产品功能边界、实验条件。
- 行业案例、竞品对照、官方文档、论文、代码仓库。
- 机制解释：为什么这个现象发生，为什么张和的判断成立或需要收窄。
- 反例和边界：在哪些条件下张和的判断不成立。
- 可执行产物：填好的表格、评估口径、检查清单、bad case 对照。

研究不能做：

- 把外部资料里的观点直接改写成“张和认为”。
- 用研究结论反向覆盖张和已有立场，却不说明冲突。
- 编造张和项目、学员数据、客户案例、内部经历或实测。
- 为了文章更尖锐，把张和谨慎判断写成绝对断言。
- 把无法核查的外部数字、比例、排名、实验结论写成事实。外部研究中的精确数字必须进入 `Research Source Ledger`；如果来源只支持方向，不支持数字，正文只能写成定性机制。

## 观点偏移检查

写作前和审稿时都要问：

1. 最终核心判断是否仍然从 `Viewpoint Core` 生长出来？
2. 外部研究是在补证据和机制，还是已经换了一个主张？
3. 哪些句子把“研究后的延展判断”写成了张和原始观点？
4. 如果删掉所有外部研究，文章是否还能看出张和原来的判断？
5. 如果删掉张和来源，文章是否变成普通研究综述？

命中第 2、3、5 条时，不能直接写正文或不能 `PASS`。

## 决策

- `WRITE-RESEARCH`：张和观点至少 MEDIUM，且有明确 research questions；先研究，再进入 Article Brief。
- `SUPPLEMENT-ZHANG-VIEW`：题值得写，但没有足够张和立场；先补张和原话、boss_take、会议材料或用户口述。
- `DOWNGRADE`：可以写成资料卡、研究备忘、轻量推文，但不适合张和第一人称主账号文章。
- `KILL`：题本身只是在追热点、复述新闻、服务招生，或外部研究会把张和观点带偏。
