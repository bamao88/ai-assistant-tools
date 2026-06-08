# Cold Review

## Verdict
REVISE

## Why The Self Review Was Too Generous

The article is structurally strong and uses the provided 14→21→24→28 baseline case well, but it adds teaching-scene details that were not in the provided material:

- "他有点慌，问我是不是该上 RAG，是不是该考虑微调。"
- "我说先别动技术栈。"

The user only provided a training-camp learner case with numbers and one bad case. They did not provide a live dialogue, emotion, or Zhang He's direct response. This is a subtle fabrication. It improves readability, but it violates the skill's core constraint: no invented Zhang He experience, learner behavior, dialogue, or teaching scene.

## Required Skill Fix

When a case is user-provided, the agent must preserve the boundary between:

- given facts,
- reasonable product interpretation,
- invented scene/dialogue/emotion.

Only the first two are allowed. The third is forbidden unless explicitly present in the source material.

## Article-Level Fix

Replace invented interaction with source-bounded phrasing:

- Instead of "他有点慌，问我是不是该上 RAG..."
- Use "如果这时马上去讨论 RAG 或微调，很容易把问题想偏。我的判断会是：先别动技术栈..."
