# 契约 · ④ 钩子（4_hook）

| | |
|---|---|
| 提示词 | `prompts/hook.md` |
| 代码 | `video_select/generate.py::gen_hook_options` |
| 调用次数 | N（每条 clip 1 次） |
| 上游 | ①选题 + ②总编金标准 |

## 输入 schema（`input.json` · 别改）
```json
{
  "clips": [{
    "idx": 1,
    "title": "...", "one_argument": "...", "audience": "...",
    "candidate_pool": [{"sid": 140, "text": "候选原话句"}]   // 正文覆盖句±3 ∪ 原选段±2
  }]
}
```

## 输出金标准 schema（`golden.json` 的 `items` · 待 owner 填）
> ⚠ 钩子是开放生成，**没有唯一答案**。金标准不做"标准钩子"，而是「可接受集合 + 人工首选」：
```json
{"items": [{
  "idx": 1,
  "acceptable": [{
    "stitched": "可接受的钩子句",
    "fragments": [{"sid": 1890, "text": "原话子串"}],
    "strategy": "整句直用|整句剪头尾|短句拼接"
  }],
  "best_stitched": "人工心中最佳那条",
  "must_keep_terms": ["95%以上","3个月"]   // 这条题不许丢的限定词/数字（评分硬约束）
}]}
```

## 评分口径
- **硬规则（代码·自动）**：每个片段是原话子串；`must_keep_terms` 一个不丢；`stitched` 字数 ≤ 片段和×1.2；整条 ≤~30 字；`strategy` 已标。
- **打分卡 rubric（LLM 评委）**：戳点 / 中目标受众 / 露答案 三要素各打分；优先级是否「整句直用 > 剪头尾 > 拼接」。
- **人工**：最终从候选里挑哪条；候选是否落在 `acceptable` 近邻。

## 血缘
input ← ①选题（标题/论点/受众）+ ②总编金标准（正文决定候选池 `_hook_view`）。未填时种子兜底。
