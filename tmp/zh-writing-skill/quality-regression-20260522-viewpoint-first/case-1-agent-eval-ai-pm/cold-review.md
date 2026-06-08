# Cold Review

## Verdict
REVISE

## Why The Self Review Was Too Generous

The generated article is directionally strong and aligns with Zhang He's viewpoint, but it cannot be accepted as PASS because one external research extension became an unsupported numeric claim:

- Article claim: "只看输出的评测，通过率会比看完整轨迹的评测虚高两到四成。"
- Dossier claim: this came from Anthropic / LangChain engineering sources.
- Cold verification: Anthropic and LangChain sources support the qualitative point that output-only eval misses trajectory/tool failures, but I did not verify a 20-40% agent-eval uplift/overestimate statistic in those sources.

This is exactly the new failure mode the skill needs to block: deep research is allowed to deepen Zhang He's view, but numeric research extensions must remain source-verifiable. "不暴露调研痕迹" cannot become a license to hide unverified numbers.

## Required Skill Fix

Add a source ledger for deep research claims:

- Every external numeric claim must have source URL/path and source-supported wording.
- If a statistic cannot be verified, the draft must downgrade it to a qualitative mechanism claim.
- The editor review must veto exact external numbers that are not traceable in the Dossier or Article Brief.

## Article-Level Fix

Replace the unsupported sentence with a qualitative claim:

"只看最终输出，会漏掉工具调用、检索路径、重复尝试和成本这些隐藏失败。一个结果看起来对的 Agent，轨迹里可能已经暴露出下一次崩掉的原因。"
