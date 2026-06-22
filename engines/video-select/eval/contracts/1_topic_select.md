# 契约 · ① 选题（1_topic_select）

| | |
|---|---|
| 提示词 | `prompts/topic-select.md` |
| 代码 | `video_select/topics.py` |
| 调用次数 | 1（整场一次性出全部选题） |
| 上游 | 源 `words.json` |

## 输入 schema（`input.json` · 别改）
```json
{
  "source_words": "../../words.json",   // 整场编号逐字稿，每行 #sid [说话人] 文本
  "host": "张和",
  "n_sentences": 2048,
  "sample_head": [{"sid": 0, "speaker": "...", "text": "..."}]  // 仅供人读的头部样例
}
```
> 真实喂模型的是整场 `words.json` 渲染成的 `#sid [说话人] 文本`。

## 输出金标准 schema（`golden.json` 的 `items` · 待 owner 填）
```json
{"items": [{
  "title": "钩子式标题（带AI/产品名·留悬念·张力≥2·≤20字）",
  "one_argument": "一句话观点",
  "hook_line": "主讲原话（逐字稿真有）",
  "audience": "破圈大众/AI从业者/创业者老板/转型求职 之一或组合",
  "mainstream": "高|中|低",
  "hit_dims": ["数据","金句"],        // 取自 {数据,转变故事,金句,权威背书,戳痛点}，≥3
  "rough_sid_spans": [[起句号, 止句号]],
  "why": "为什么会传播/认知增量在哪"
}]}
```

## 评分口径
- **硬规则（代码·自动）**：标题 ≤20 字且含 AI/产品名；`hit_dims`≥3 且在 5 维集合内；`rough_sid_spans` 落在 `[0, n_sentences)`；条数 18–25。
- **覆盖率（LLM 评委 + 人工抽检）**：候选 vs 金标准按**语义**对齐（标题措辞不同但同义算命中，不能字面比）→ 召回（金标准该选的漏没漏）/ 精确（选出来的有没有跑题、凑数）。

## 血缘
input ← 源 `words.json`（始终）。本阶段是链头，无上游金标准依赖。
