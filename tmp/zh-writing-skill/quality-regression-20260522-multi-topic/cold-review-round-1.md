# Cold Review Round 1

## Cases Reviewed

- `case-1-os-agent-ecosystem`
- `case-2-long-context-eval`
- `case-3-eval-dimension-design`

## Result

Self-reviews gave all three PASS scores around 90. Cold review does not accept them all as-is.

## Failure Pattern Found

The drafts sometimes create source-like immediacy that is not clearly supported by the cited material:

- `case-1`: "过去两周我被问最多的一句话是..." may be true in the original article context, but the current Dossier/Brief did not prove this exact time-bound reader interaction.
- `case-3`: "上周训练营答疑，一个学员把他的评测方案发给我..." is explicitly described by the generated review as a representative/composite scene, not a traceable event.

This is a form of soft fabrication. It is less severe than inventing a learner quote, but it still makes the article sound like a documented recent scene when the source only supports a repeated pattern.

## Required Skill Fix

Add a rule: representative patterns may be used, but must not be dressed as a specific recent event unless the source material provides the time, channel, person, or interaction.

Allowed:

- "这类问题我每期都会遇到。"
- "训练营里反复有人交这种九维表。"
- "最近围绕这个问题的讨论很多。"

Forbidden without source:

- "上周一个学员发给我..."
- "过去两周我被问最多..."
- "昨天有个客户..."
- "某个团队当场问我..."

## Impact

`case-2-long-context-eval` is acceptable pending source check for ExcelMaster; `case-1` and `case-3` require at least opening-line polish or rerun after the rule update.
