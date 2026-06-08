# Viewpoint-First Smoke Check

Purpose: verify the new workflow can find real Zhang He viewpoint anchors before writing, instead of inventing a stance from external research.

## Test Prompt

写一篇张和主账号文章，主题是 Agent 评估为什么会变成 AI PM 的基本功。

## Expected Workflow

1. Output `Zhang Viewpoint Dossier`.
2. Search Zhang He sources before external research.
3. Use external research only to deepen the confirmed viewpoint.
4. Do not write a first-person article if viewpoint confidence is below MEDIUM.

## Real Source Anchors Found

- `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/wiki/expertise/topic-ai-pm-profile-eval-driven.md`
  - Core: AI PM should have eval-driven product methodology, frontier insight, and technical communication ability.
  - Confidence: HIGH, because it is an expertise page with source meeting reference.

- `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/wiki/expertise/topic-eval-dimension-principles.md`
  - Core: eval dimensions should only include variables that truly affect model/product performance.
  - Confidence: HIGH, because it includes course and AMA sources.

- `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/wiki/expertise/topic-agent-cc-plus-skill-benchmark.md`
  - Core: a vertical Agent must beat Claude Code + generic Skill; otherwise its architecture or Agent concept may be outdated.
  - Confidence: HIGH, because it cites Zhang He's meeting discussion.

- `/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/knowledge_base/client/raw/works/2026-04_长上下文工程AI产品经理的新战场.md`
  - Core: AI PM responsibility is shifting from defining features to defining failures and building eval systems around those failures.
  - Confidence: HIGH, because it is an existing Zhang He article.

## Smoke Result

This prompt should be `WRITE-RESEARCH`, not direct drafting. The research questions should deepen these Zhang He views:

- What kinds of Agent failures should AI PMs define first?
- How should baseline and eval sets be constructed before optimization?
- What external cases prove eval-driven iteration is becoming a product competency?
- Where does Zhang He's view need boundaries, such as benchmark overfitting or eval metrics that do not map to user value?

The article should not drift into a generic "AI PM must learn tools" or "career anxiety" piece.
