# video-select · 第②环·选片（Eval Harness + 成片脚本）

> 六环主链 `①转写 → 【②选片】 → ③裁剪 → ④字幕 → ⑤铸造 → ⑥组装` 的第②环。
> **职责边界**：定「剪成什么内容」（成片脚本），不定「怎么剪」（渲染/执行归 ③–⑥）。
> 设计真源：[`doc/plan/视频剪辑skill-第二环选片-plan.md`](../../doc/plan/视频剪辑skill-第二环选片-plan.md)。

本环是一套 **Eval Harness 驱动的迭代闭环**：固定评测集上跑 Runner → 门禁 + 打分 → 翻 bad case → 改 prompt/代码/门禁 → 再跑。`golden.json` 只是闭环里的冻结参照快照，不是终点。

## 结构

```
prompts/         ★ 4 条提示词全在此（按功能命名·无人设/账号概念·改 prompt 不动代码）
  topic-select.md   流程一·选题
  body-edit.md      流程二·总编（全局取证 + 逻辑编排 + 精选合并）
  refine-deduct.md  流程二·字级去口水决策（删哪些字·带位置·可执行）
  hook.md           流程二·钩子（整句优先·拼接兜底）
video_select/    代码包（只管逻辑；提示词一律从 prompts/ 读）
  topics.py         选题 Runner          → _selection.json
  generate.py       候选 Runner          → golden_candidate.json + candidates/clip_NN.md
  gates.py          门禁（精选合并 + 时长 + 可执行 + 零编造）
  score.py          打分器（候选 vs 冻结 golden 参照）
  select_clips_a.py 方案A·单阶段（备用对照）
eval/            Harness 数据（fixtures 入库 / runs 不入库 / words 软链 / notes 经验）
```

**依赖方向**：`video-select → video-slicer`（单向 import 它的 `transcribe.segment` / `llm` / `twostage.index`，复用「逐字稿→句/时间」核心，不重复造）。

## 迭代闭环命令（在 `engines/video-select/` 下跑）

```bash
F=eval/fixtures/agent_eval_0613

# 流程一·选题（整场逐字稿 → 选题清单）
python -m video_select.topics --words $F/words.json --out eval/runs/agent_eval_0613/_selection.json

# 流程二·生成候选（选题 → 成片脚本；总编出口已过精选合并门禁）
python -m video_select.generate --words $F/words.json --selection $F/selection.json \
    --out eval/runs/agent_eval_0613

# 门禁（机器可判红线，不过就挡）
python -m video_select.gates --golden eval/runs/agent_eval_0613/golden_candidate.json \
    --words $F/words.json --out eval/runs/agent_eval_0613/gates_report.json

# 打分（候选 vs 冻结 golden 参照，看 prompt 改动有没有变好）
python -m video_select.score --golden $F/golden.json \
    --candidate eval/runs/agent_eval_0613/golden_candidate.json \
    --out eval/runs/agent_eval_0613/score_report.json
```

LLM 凭证走 `.env`（Kimi/MiniMax，与 video-slicer 同源）。`gates` / `score` 不调 LLM，可离线跑。

## 人工评审环

`candidates/clip_NN.md` 是人读评审稿：挑钩子、核对字级去口水决策、改状态（留/删/改）。
评审结论回写 `eval/fixtures/agent_eval_0613/golden.json`（冻结参照，随迭代升 v1/v2…），下一轮 `score` 自动对照。
