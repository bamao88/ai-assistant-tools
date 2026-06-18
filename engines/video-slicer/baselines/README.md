# video-slicer / baselines

固化的**选段方案基准 + 评测基准**，用于方案对照（脚本级对比，看哪条流程选得更好）。不进生产管线。

| 文件 | 是什么 | 来源 |
|---|---|---|
| `select_clips.py` | **方案A 基准**：单阶段选段（一次 LLM 同时定选题 + 选段）。只出选题层候选 JSON，不渲染/不切片。 | 由 `assistant_zh/tmp/slice_prompt_iter/` 固化（video-tools-migration 阶段1），去硬编码绝对路径。 |
| `global_evidence.py` | **金标准生成器（四级流水线）**：对每条**已选定选题**，把张和整场逐字稿喂给 AI 全局取证，产出一条 clip 的四级结构。只产候选(`human_status=pending`)，人工拍定后才是金标准。 | 计划 `doc/plan/video-golden-baseline-plan.md`。 |
| `score.py` | **逼近度打分器**：任意一版切片产出 vs 金标准 → 句号召回/精确/F1 + 时间 IoU。让"改 prompt 有没有变好"可量化。 | 同上。 |

## 金标准这条线（评测基准）

为什么要：选段质量"改 prompt 有没有变好"过去只能凭感觉。先建一份人工拍定的**标准答案(golden)**当尺子，之后所有 prompt 迭代跟它打分对照。

一条 clip 的**四级流水线**（钩子单独拎出来，只有一个出处）：

| 级 | 是什么 | 怎么产 |
|---|---|---|
| **① 开场钩子** | 短·炸·可跨句抠片段拼接的开场，给 2-3 个候选挑一个 | `gen_hook_options`（HOOK_TASK），约束在正文句子里抠真实子串、标 verbatim |
| **② 正文·论证结构** | 论点/论据/收尾，**不含钩子**；句号可回查时间 | `select_body`（BODY_TASK），全局取证、每段短而准、反串味 |
| **③ 组装脚本** | ②各段原话原始拼接（带口水） | 代码拼接 |
| **④ 精修脚本** | 去口水/去重复/顺语序 + **开篇独立**(剪掉承接上文的转折词) + **结尾干脆**(不拖尾引导) | `refine_script`（REFINE_TASK），只删理顺不改写实质，③原始版并排留着供核对 |

铁律：②只回**真实句号区间**（可校验、可经 `twostage/resolve.py` 换算成秒）；①每片段标 sid+verbatim；④允许调语序/合并但只用原话出现过的字词、不新增观点。句号索引复用生产线同一个 `segment.sentences_from_wordfile`，sid↔时间 与 `_selection.json` 完全一致。

> 注：边界承接句规则与 `../references/字级去口水与承接句保护.md` **相反**——那份是保护中间的承接句（删前保后），④精修是**剪掉开篇/结尾的承接句**（因为素材是从长视频切出来的，头尾的承接/引导在短视频里多余）。

```bash
# 1) 全新生成：每条做 ②正文 + ①钩子 + ④精修。先 --limit 1 小跑省钱。
python global_evidence.py \
    --words   ../../../var/zh_main/asr/agent_eval_0613/words.json \
    --selection ../../../var/zh_main/cuts/agent全量-volc-native/_selection.json \
    --out     ../../../var/zh_main/eval/agent_eval_0613 [--limit 1] [--only 6-22]
#   → golden_candidate.json + candidates/clip_NN_*.md（四级版式）

# 1b) 迁移：不重跑正文，对已存 golden 每条补①钩子+④精修+换新版式（保留人工定稿区）。
python global_evidence.py --words <words.json> --out <dir> --migrate [--only 6-22]

# 2) 人工定稿：每条 md 里挑一个钩子、核对④精修忠实度、改"状态"为 keep/cut/edited，
#    确认后把 golden_candidate.json 整理成 golden.json（human_status=done）。

# 3) 打分：任意切片产出 vs 金标准。
python score.py --golden <golden.json> \
    --candidate ../../../var/zh_main/cuts/agent全量-volc-native/_selection.json \
    --out score_report.json
```

产物落 `var/<account>/eval/<run>/`（运行时目录，默认不入库）。若要把某版 `golden.json` 当冻结基准长期保存，单独存档并在此标版本（类比 G4 基线在 `var/zh_main/baseline/`）。

## 对照三方（迁移计划 §1.4 item 5 / §7.2 D6）

- **方案A**（本目录 `select_clips.py`）：线上现状范式——单阶段、句级、不依赖字级。
- **方案B**（`../video_slicer/twostage/`）：两阶段选段 + 字级时间戳（paraformer），并行升级路线，效果调试中。
- **金标准**：已发布切片（基线冻结于 `tools/var/zh_main/baseline/`）。

句级（A）与词级（B）是 **共存** 的两个 `cut_*` 能力，不是替代关系（见计划 §3.4）。

## 用法

```bash
python select_clips.py <腾讯 minutes.json> [--persona zh_main] [--out cand.json]
```

> 张和选题 prompt 当前内嵌于脚本，作忠实基线原样保留；persona 解耦（抽到
> `profiles/zh_main`）属阶段2/5 范围，不在阶段1 固化内改动。
