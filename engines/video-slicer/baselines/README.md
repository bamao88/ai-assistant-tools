# video-slicer / baselines（已迁移）

> ⚠️ **本目录待废弃。** 评测/Harness 代码与文档已迁至 **`tools/eval/video-select/`**；生产选片在 **`tools/engines/video-select/`**。设计见 `doc/plan/视频剪辑skill-第二环选片-plan.md` §6。

日常跑片**不需要**本目录。只有做提示词或架构优化时,才使用 `eval/video-select/`。

## 临时用法（迁移完成前）

现有脚本仍可从此处运行,路径不变:

```bash
# 评测重跑（→ 将来 eval/video-select/runner.py）
python global_evidence.py --words ... --selection ... --out var/.../eval/...

# 打分（→ 将来 eval/video-select/score.py）
python score.py --golden ... --candidate ... --out score_report.json
```

迭代经验文档真源将迁至 `eval/video-select/doc/金标准建设-经验与提示词总结.md`（当前仍在 `var/zh_main/eval/agent_eval_0613/doc/`）。
