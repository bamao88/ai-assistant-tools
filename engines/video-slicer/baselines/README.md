# video-slicer / baselines

固化的**选段方案基准**，用于方案对照（脚本级对比，看哪条流程选得更好）。不进生产管线。

| 文件 | 是什么 | 来源 |
|---|---|---|
| `select_clips.py` | **方案A 基准**：单阶段选段（一次 LLM 同时定选题 + 选段）。只出选题层候选 JSON，不渲染/不切片。 | 由 `assistant_zh/tmp/slice_prompt_iter/` 固化（video-tools-migration 阶段1），去硬编码绝对路径。 |

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
