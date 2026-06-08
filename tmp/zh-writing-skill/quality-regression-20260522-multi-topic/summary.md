# Multi-Topic Regression Summary

## Scope

This round tests whether `zh-writing-skill` works across multiple topic types, not just one favorable sample.

Test set:

1. OS Agent / ecosystem judgment
2. Long-context eval / AI PM role
3. Eval dimension design / training-method article
4. Thin model-news input that should be blocked
5. Google Agent Skills single-source event + Zhang baseline method
6. Proactive AI product judgment

## Final Results

| Case | Outcome | Final Article / Artifact | Cold Review Note |
|---|---|---|---|
| `case-1-os-agent-ecosystem` | PASS after polish | `case-1-os-agent-ecosystem/article.md` | Self-review PASS 90. Cold review flagged an unsupported time-bound opening; final article now removes "past two weeks" immediacy and avoids unsupported precision. |
| `case-2-long-context-eval` | PASS | `case-2-long-context-eval/article.md` | Self-review PASS 90. Strong Zhang-source alignment; caveat: this is a refocus of an existing Zhang topic, not a wholly new topic. |
| `case-3-eval-dimension-design` | PASS after rerun/polish | `case-3-eval-dimension-design-rerun/article.md` | First draft used a representative pattern as a specific recent scene. Skill was patched; rerun avoids the time anchor. Final article also removes false-precision "ten groups/seven groups" wording. |
| `case-4-thin-model-news` | Correct SUPPLEMENT / KILL | `case-4-thin-model-news/brief.md` | No article generated. The flow correctly refused an unspecified "new OpenAI model" news prompt because model name, source facts, and Zhang judgment were missing. |
| `case-5-single-source-skill-baseline` | PASS after polish | `case-5-single-source-skill-baseline/article.md` | External facts verified against source ledger. Final polish removed unsupported illustrative precision ("90% / 5%") and kept it as qualitative increment logic. |
| `case-6-proactive-ai-product` | PASS | `case-6-proactive-ai-product/article.md` | PASS 93. Strong one-case spine from ExcelMaster + bounded Apple Intelligence reference. External Apple news-summary point remains qualitative. |

## Skill Fixes From This Round

- Representative patterns cannot be dressed as recent specific events unless the source provides time, person, channel, or interaction record.
- Case data cannot be expanded into invented dialogue, learner emotion, customer reaction, or live scene detail.
- External numeric claims must appear in `Research Source Ledger`.
- Illustrative / hypothetical numbers now also need source or calculation support. Without support, use ranges or qualitative wording.

## Source Checks

- Google Developers Blog confirms the Agent Skills article date, authors, 117-prompt eval harness, failure rule for old SDKs, 6.8% / 28% low baseline, 95% SDK Usage category pass rate, and Vercel caveat.
- Vercel confirms the AGENTS.md vs skills eval direction and concrete pass-rate comparison.
- AP confirms Apple temporarily disabled error-prone AI-generated summaries for news and entertainment in iOS 18.3 beta after false-news-summary complaints.

## Current Assessment

The revised skill is not merely producing one acceptable article. In this 6-case regression:

- 5 publishable / near-publishable positive articles cleared 80 after cold review and small polish where needed.
- 1 underspecified hot-news topic was correctly blocked before drafting.
- The main remaining weakness is not article structure; it is source discipline around immediacy, case specificity, and false-precision numbers. Those are now encoded as review gates.
