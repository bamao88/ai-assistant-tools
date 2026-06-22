# 契约 · ③ 去口水决策（3_refine_deduct）

| | |
|---|---|
| 提示词 | `prompts/refine-deduct.md` |
| 代码 | `video_select/generate.py::deduct_disfluency` |
| 调用次数 | N（每条 clip 1 次） |
| 上游 | ②总编金标准 |

## 输入 schema（`input.json` · 别改）
```json
{
  "clips": [{
    "idx": 1,
    "title": "...",
    "body_lines": [{"sid": 140, "text": "这句正文原话"}]   // 总编选段展开成逐句
  }]
}
```
> 顺序/去留已由总编定死，本阶段**不许增删句、不许调顺序**，只标删哪些字。

## 输出金标准 schema（`golden.json` 的 `items` · 待 owner 填）
```json
{"items": [{
  "idx": 1,
  "deletions": [{
    "sid": 140,
    "text": "要删掉的原话连续子串",      // 必须是该句原话一字不差子串
    "kind": "语气词|卡顿|重说|残句|其它"
  }]
}]}
```
> 金标准是「删哪些字」的决策集合，不是改写后的文本。

## 评分口径
- **精确匹配（代码·自动）**：把候选删除的字符 vs 金标准删除的字符当集合，算 P/R/F1（该删的删了吗、误删了吗）。按 sid 对齐。
- **硬规则（gates 已有）**：每个 `text` 是该句原话一字不差子串（`verbatim=true`）。
- **主观（LLM 评委）**：承接句有没有被当口水误删（最大的坑）；删完通读是否仍像正常说话。

## 血缘
input ← ②总编金标准（`stages/2_body_edit/golden.json` 的 segments 展开）。未填时种子兜底。
