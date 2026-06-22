# 提示词改动账本（CHANGELOG）

> ②选片 5 条提示词的版本账本。**改一条提示词 = 升一版 = 记一行**，把版本和评测分数对上。
> 配套：`versions/<name>/vN.md`（每版原文归档）、`versions.json`（当前版本指针·机器读）。
> 升版用：`python3 _version.py bump <name> "改了啥"`（自动归档+改指针+在此追加一行）。

## 怎么读这份账本
- **name**：哪条提示词（`topic-select` / `body-edit` / `refine-deduct` / `hook` / `dedup-merge`）。
- **版本**：`vN`，原文存在 `versions/<name>/vN.md`。
- **分变化**：相对上一版，该阶段评分器（见 `eval/contracts/<阶段>.md`）的分怎么动。**没跑评测就写"未测"**——别凭感觉填。

---

## topic-select
- **v1**（2026-06-22 · 基线）：dbskill 选片灵魂(认知增量第一+五维富集度≥3+标题5铁律)+`hit_dims`输出。分变化：基线·未测。

## body-edit
- **v1**（2026-06-22 · 基线）：总编(全局取证+逻辑编排+精选合并)，出口过 `gates.merge_segments`。分变化：基线·未测。

## refine-deduct
- **v1**（2026-06-22 · 基线）：字级删除决策(删哪些字·带位置·可执行)+承接句保护红线。分变化：基线·未测。

## hook
- **v1**（2026-06-22 · 基线）：整句优先🥇/剪头尾🥈/拼接兜底🥉+dbs-hook 三要素。分变化：基线·未测。

## dedup-merge
- **v1**（2026-06-22 · 基线）：整批内容级去重(merge/drop/keep)。分变化：基线·未测。
