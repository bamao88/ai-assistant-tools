# Multi-Topic Regression Set

Goal: test whether `zh-writing-skill` works beyond a single favorable topic.

Each case must run the current skill flow:

1. `Zhang Viewpoint Dossier`
2. `Article Brief`
3. deep research only when it deepens Zhang He's viewpoint
4. article only when `Decision=WRITE`
5. `zh-editor-review.md` review

## Cases

### case-1-os-agent-ecosystem

Prompt: 写一篇张和主账号文章：OS Agent 为什么不是一个功能，而是一次生态位重排。要求先找张和已有观点，再决定是否写。

Expected: should find strong Zhang He GUI Agent / OS Agent viewpoints. If writing, must avoid turning into generic ByteDance/Doubao news recap.

### case-2-long-context-eval

Prompt: 写一篇张和主账号文章：长上下文工程为什么会把 AI PM 推向“定义失败”的角色。

Expected: likely WRITE if Zhang He article/source exists. Must explain mechanism and not become long-context literature summary.

### case-3-eval-dimension-design

Prompt: 写一篇张和主账号文章：做 AI 产品评测集，为什么维度越多越可能错。

Expected: should use Zhang He's eval dimension principle. Needs a concrete case spine or downgrade if not enough.

### case-4-thin-model-news

Prompt: OpenAI 刚发了一个新模型，帮我写一篇张和主账号文章。

Expected: SUPPLEMENT / KILL, unless a Zhang viewpoint and original facts are found. Must not write generic news commentary.

### case-5-single-source-skill-baseline

Prompt: 基于 Google Agent Skills 官方博客，写一篇张和主账号文章，重点讲它对细分 Agent 产品 baseline 的意义。

Expected: should only write if Zhang viewpoint + source ledger + product judgment are strong. Must not repeat the old rev80 weakness.

### case-6-proactive-ai-product

Prompt: 写一篇张和主账号文章：为什么主动式 AI 产品最难的不是提醒用户，而是判断什么时候不该打扰。

Expected: should first find Zhang He proactive AI product views. If no concrete case, should SUPPLEMENT or write a narrow article with clear boundaries.

## Pass Criteria

- Positive cases: article `PASS >= 80` after cold review, not only self-review.
- Negative cases: correct `SUPPLEMENT / KILL`, no weak article.
- No fabricated Zhang He experiences, learner dialogue, user data, customer case, or unsupported external numbers.
- Every external numeric/research claim must appear in `Research Source Ledger`.
