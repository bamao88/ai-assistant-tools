# video-select · 第②环·选片（Eval Harness + 成片脚本）

> 六环主链 `①转写 → 【②选片】 → ③裁剪 → ④字幕 → ⑤铸造 → ⑥组装` 的第②环。
> **职责边界**：定「剪成什么内容」（成片脚本），不定「怎么剪」（渲染/执行归 ③–⑥）。
> 设计真源：[`doc/plan/视频剪辑skill-第二环选片-plan.md`](../../doc/plan/视频剪辑skill-第二环选片-plan.md)。

本环是一套 **Eval Harness 驱动的迭代闭环**：固定评测集上跑 Runner → 门禁 + 打分 → 翻 bad case → 改 prompt/代码/门禁 → 再跑。`golden.json` 只是闭环里的冻结参照快照，不是终点。

## 结构

```
prompts/         ★ 5 条提示词全在此（按功能命名·改 prompt 不动代码）
  topic-select.md   流程一·选题（选片标准基于 dbskill 选片灵魂 + 标题 5 铁律）
  body-edit.md      流程二·总编（全局取证 + 逻辑编排 + 精选合并）
  refine-deduct.md  流程二·字级去口水决策（删哪些字·带位置·可执行）
  hook.md           流程二·钩子（dbs-hook 方法论内容 + 本项目「整句优先·拼接兜底」排序）
  dedup-merge.md    流程二后·批量去重/合并（内容级）
video_select/    代码包（只管逻辑；提示词一律从 prompts/ 读）
  topics.py         选题 Runner          → _selection.json
  generate.py       候选 Runner          → golden_candidate.json + candidates/clip_NN.md
  dedup.py          批量去重 Runner      → golden_dedup.json（流程二后·内容级去重）
  gates.py          门禁（精选合并 + 时长 + 可执行 + 零编造）
  score.py          打分器（候选 vs 冻结 golden 参照·端到端）
  stage_run.py      单阶段测试口（从冻结 input 单跑 body_edit/refine_deduct/hook）
  select_clips_a.py 方案A·单阶段（备用对照）
  adapt_tencent.py  腾讯会议逐字稿(minutes·多说话人) → words.json（保留 speaker/is_host）
eval/            Harness 数据 + 分阶段评测（详见 eval/README.md）
  contracts/        5 阶段判分契约（真源）
  fixtures/<ds>/stages/<N_阶段>/{input,golden}.json   每阶段冻结输入 + 金标准
  scorers/          5 把尺（1_topic_select … 5_dedup_merge）+ judge.py + run_all.py
  build_inputs.py / seed_golden.py   派生各阶段 input / golden 种子
```

**依赖方向**：`video-select → video-slicer`（单向 import 它的 `transcribe.segment` / `llm` / `twostage.index`，复用「逐字稿→句/时间」核心，不重复造）。

**选题/标题/钩子方法论来源**：dontbesilent「dbskill」（`vendor/dbskill/skills/{dbs-content,dbs-hook,dbs-xhs-title}`；**CC BY-NC 4.0**，仓库 github.com/dontbesilent2025/dbskill）。`prompts/{topic-select,hook}.md` 蒸馏自其方法论 + videocut-zh `03 §7`／`07`，已在文件头署名。商用边界由 owner 把关。

## 从腾讯会议逐字稿开始（无需真实转录）

腾讯会议录制的逐字稿可直接下载（公网 API·无需 token·吃 `crm/cw` 分享链），再适配成 `words.json`：

```bash
# 1. 下载逐字稿（minutes 格式·多说话人）
python3 ../tencent-meeting/scripts/fetch_tencent_meeting_transcripts_stable.py \
    "https://meeting.tencent.com/crm/<short_code>" --strategy api --output-dir <下载目录>
# 2. 适配成 words.json（保留 speaker/is_host）
python -m video_select.adapt_tencent --in <下载目录>/files/<标题>.json --out <words.json> --host 张和
# 之后把 <words.json> 当下面命令里的 $F/words.json 用
```

## 迭代闭环命令（在 `engines/video-select/` 下跑）

```bash
F=eval/fixtures/agent_eval_0613

# 流程一·选题（整场逐字稿 → 选题清单）
python -m video_select.topics --words $F/words.json --out eval/runs/agent_eval_0613/_selection.json

# 流程二·生成候选（选题 → 成片脚本；总编出口已过精选合并门禁）
python -m video_select.generate --words $F/words.json --selection $F/selection.json \
    --out eval/runs/agent_eval_0613

# 流程二后·批量去重/合并（大模型看整批实际内容 → 合并同观点/删被覆盖）
python -m video_select.dedup --golden eval/runs/agent_eval_0613/golden_candidate.json \
    --words $F/words.json --out eval/runs/agent_eval_0613   # → golden_dedup.json

# 门禁（机器可判红线，不过就挡）
python -m video_select.gates --golden eval/runs/agent_eval_0613/golden_dedup.json \
    --words $F/words.json --out eval/runs/agent_eval_0613/gates_report.json

# 打分（候选 vs 冻结 golden 参照，看 prompt 改动有没有变好）
python -m video_select.score --golden $F/golden.json \
    --candidate eval/runs/agent_eval_0613/golden_dedup.json \
    --out eval/runs/agent_eval_0613/score_report.json
```

闭环顺序：`topics → generate → dedup → gates → score`。

LLM 凭证走 `.env`（Kimi/MiniMax，与 video-slicer 同源）。`gates` / `score` 不调 LLM，可离线跑。

## 分阶段评测（per-stage eval · 5 条提示词各一把尺）

整条链的总分看不出"哪一步烂"，故每条提示词单独评。规范总纲见 [`eval/README.md`](eval/README.md)，
判分契约见 `eval/contracts/`。

```bash
# 1) 派生各阶段 input/golden（input 来自上游金标准；golden 种子来自端到端 golden）
python3 eval/build_inputs.py --dataset agent_eval_0613
python3 eval/seed_golden.py  --dataset agent_eval_0613

# 2) 改某条提示词后，单跑该阶段（喂冻结 input，不串其余阶段）—— 要 LLM 出口
python3 -m video_select.stage_run --stage body_edit \
    --input eval/fixtures/agent_eval_0613/stages/2_body_edit/input.json \
    --words $F/words.json --out eval/runs/agent_eval_0613/2_body_edit.json

# 3) 出分（候选 vs 该阶段金标准）；或一键跑全部已填阶段的自比对冒烟
python3 eval/scorers/2_body_edit.py \
    --golden eval/fixtures/agent_eval_0613/stages/2_body_edit/golden.json \
    --candidate eval/runs/agent_eval_0613/2_body_edit.json
python3 eval/scorers/run_all.py --dataset agent_eval_0613
```

5 把尺：②句号F1 / ③字符P/R / ⑤配对P/R 是**纯代码自动评**（`run_all` 自比对 = 满分）；
①④硬规则自动 + 主观层（覆盖率/打分卡）走 `eval/scorers/judge.py` LLM 评委。
`scorers/*` 不碰网络可离线跑；只有 `judge.py`/`stage_run.py` 要 LLM（按 memory 先 route-bypass 本地出口）。

## 人工评审环

`candidates/clip_NN.md` 是人读评审稿：挑钩子、核对字级去口水决策、改状态（留/删/改）。
评审结论回写 `eval/fixtures/agent_eval_0613/golden.json`（冻结参照，随迭代升 v1/v2…），下一轮 `score` 自动对照。
