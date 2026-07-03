# legacy/ — 冻结的一次性批次脚本（不再运行，仅存档）

`batch_gen.py` / `batch_title.py` / `finalize.py` 是切片线早期的**一次性批次胶水**：内嵌具体批次的
硬编码数据（`CLIPS` 队列 / `FINALS` 定稿正文 / `out_v1` 路径），为 v1 / d2c 那几批切片跑过一次。

它们被 `video_pipeline_sop.md` 的**原子能力 + agent 编排**（弃僵化 pipeline，slice_content_pipeline_refactor D1）
取代——现在由 `publish-prep` skill 的 SKILL.md 逐条编排 engine 的 3 个可复用原子
（`gen_copy` / `gen_title` / `build_keywords`）+ 模板落 `publish_<account>.md`，不再跑批次脚本。

保留原因：这些脚本产出的物料已进各已发布 item，脚本本身留作历史参考。**不要运行**（import 路径已随
原子迁移失效，且硬编码数据对应旧批次）。要复现某批，参考其中的 prompt/流程，用新 engine 原子重跑。
