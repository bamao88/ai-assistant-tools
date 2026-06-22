# 契约 · ⑤ 批量去重（5_dedup_merge）

| | |
|---|---|
| 提示词 | `prompts/dedup-merge.md` |
| 代码 | `video_select/dedup.py` |
| 调用次数 | 1（整批一次性） |
| 上游 | ②③④金标准组装的整批 clip |

## 输入 schema（`input.json` · 别改）
```json
{
  "batch": [{
    "idx": 1,
    "title": "...", "one_argument": "...",
    "script_raw": "这条最终要剪进视频的选段原文"
  }]
}
```

## 输出金标准 schema（`golden.json` 的 `items` · 待 owner 填）
> 金标准用「规范分组」表达谁该跟谁合并（比动作列表更稳，评分好算）：
```json
{
  "groups": [[3, 9]],          // 每个子数组 = 该合并成一条的 idx 们（≥2 个）
  "drop": [14],                // 被覆盖且更弱、该删的 idx
  "keep": [1, 2, 4]            // 独立保留的 idx（其余默认 keep）
}
```
> 每个 idx 只能出现在一处（groups/drop/keep 三选一）。

## 评分口径
- **精确匹配（代码·自动）**：把"哪两条该合在一组"列成配对集合，候选 vs 金标准算 pairwise P/R/F1（该合的合了吗、误合了吗）；`drop` 命中率单算。
- **硬规则（代码）**：只操作真实 `idx`；每条只出现在一个动作里。

## 血缘
input ← ②总编金标准组装的整批（标题/论点/`script_raw`）。未填时种子兜底。
