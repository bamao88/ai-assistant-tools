# 契约 · ② 总编（2_body_edit）

| | |
|---|---|
| 提示词 | `prompts/body-edit.md` |
| 代码 | `video_select/generate.py::select_body` |
| 调用次数 | N（每条选题 1 次） |
| 上游 | ①选题金标准 |

## 输入 schema（`input.json` · 别改）
```json
{
  "shared_full_transcript": "../../words.json",   // 全场编号句，所有选题共享
  "topics": [{
    "idx": 1,
    "title": "...", "one_argument": "...", "hook_line": "...",
    "audience": "...", "mainstream": "高|中|低"
  }]
}
```
> 每条选题独立喂总编：给这 5 个字段 + 全场编号句。逐条循环。

## 输出金标准 schema（`golden.json` 的 `items` · 待 owner 填）
```json
{"items": [{
  "idx": 1,
  "segments": [{
    "role": "argument|evidence|closing",
    "sids": [起句号, 止句号],          // 连续闭区间；多段=跳接
    "reason": "为什么选这段"
  }]
}]}
```
> 金标准只需 `sids`（选了哪些句、什么顺序）+ role。时间区间由 `sids` 经 `words.json` 换算，不用手填。

## 评分口径
- **精确匹配（代码·自动·现成）**：`video_select/score.py` 已实现——
  - 句号 F1：金标准选的句子被候选覆盖多少（召回）+ 候选有没有注水（精确）。
  - 时间 IoU：两版选段在时间轴上的重合比例。
- **硬门（gates.py 已有）**：段间无重叠；相邻段 gap≤2 必合并；正文 ≥60s。

## 血缘
input ← ①选题金标准（`stages/1_topic_select/golden.json`）。金标准未填时由种子 `golden.json` 兜底派生。
