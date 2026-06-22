# 评分器目录（5 阶段 5 把尺）

每阶段一个评分器，命名对齐阶段（`N_stage.py`）。公共小工具在 `_common.py`，主观维度的 LLM
评委封装在 `judge.py`。判分口径以 `../contracts/<stage>.md` 为准。

| 阶段 | 文件 | 类型 | 主指标 | 自动吗 |
|---|---|---|---|---|
| ①选题 | `1_topic_select.py` | 硬规则 + 覆盖率 | 硬规则通过率（标题/hit_dims/越界/条数）；覆盖率走 judge | 硬规则✅ / 覆盖率需评委 |
| ②总编 | `2_body_edit.py` | 精确匹配 | 句号 F1（+可选时间 IoU `--words`） | ✅ 纯代码 |
| ③去口水 | `3_refine_deduct.py` | 精确匹配 + 子串硬规则 | 字符 P/R/F1（按 sid 对齐）；承接句误删走 judge | ✅ 纯代码 |
| ④钩子 | `4_hook.py` | 硬规则 + 打分卡 | 硬规则通过率（子串/限定词/字数/strategy）；炸不炸走 judge | 硬规则✅ / rubric 需评委 |
| ⑤去重 | `5_dedup_merge.py` | 精确匹配（聚类） | pairwise P/R/F1 + drop 命中 | ✅ 纯代码 |

> `../video_select/score.py` 是②总编评分器的旧实现（吃旧 `keep_sids/time_spans` 格式）；
> 新 `2_body_edit.py` 吃分阶段 `items[].segments[].sids` 格式，二者口径一致（句号 F1）。

## 怎么用

```bash
# 一键跑全部「金标准已填」的阶段（自比对冒烟：golden vs golden 应满分=接线对）
python3 eval/scorers/run_all.py --dataset agent_eval_0613

# 单阶段：改完提示词 → stage_run 单跑出候选 → 评分器对金标准
python3 -m video_select.stage_run --stage body_edit \
    --input eval/fixtures/agent_eval_0613/stages/2_body_edit/input.json \
    --words <words.json> --out runs/x/2_body_edit.json
python3 eval/scorers/2_body_edit.py \
    --golden eval/fixtures/agent_eval_0613/stages/2_body_edit/golden.json \
    --candidate runs/x/2_body_edit.json
```

## 验收基线（2026-06-22 实测）

- **②总编**：自比对 `sid_f1=1.0`（22/22 命中）。改 `body-edit.md` 即可秒出分差。✅ 闭环转起来了
- **③去口水 / ⑤去重**：合成自测——完美=1.0；漏删/误删、漏合/误合分别拉低 recall/precision（口径正确）。
  待 owner 填金标准（③需重建 deletions、⑤需标 groups/drop/keep）后即可上真数据。
- **①选题 / ④钩子**：硬规则跑通并如实标红草稿缺口（①缺 hit_dims、④旧钩子缺 strategy/超 30 字）——
  这是正确信号，提示草稿待 owner 补全；主观层（覆盖率/打分卡）接口在 `judge.py`，需配 LLM 出口才跑。

## 边界

- 自动评分器**不碰网络**（`_common.py` 纯函数）。只有 `judge.py`（主观维度）要 LLM；按 memory
  「发布/转录走本地出口」，跑评委前先 route-bypass。
- 「自比对冒烟」对精确匹配类（②③⑤）= 满分；对硬规则类（①④）不是满分而是「金标准自身的
  硬规则体检」——金标准草稿没补全就会标红，符合预期。
