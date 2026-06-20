# video-slicer / baselines（已迁出 → video-select）

> ✅ **已迁移。** 第②环·选片的 Eval Harness（Runner + 门禁 + 打分 + 人工评审环）已独立成引擎
> **`engines/video-select/`**。本目录的三件脚本是旧址副本，**不再维护**，新工作一律去 video-select。

| 旧址（本目录，停更） | 新址（正式真源） |
|---|---|
| `global_evidence.py`（总编/钩子/精修一把抓·内嵌 prompt） | `video-select/video_select/generate.py` + `prompts/{body-edit,refine-deduct,hook}.md` |
| `select_clips.py`（方案A 单阶段） | `video-select/video_select/select_clips_a.py` |
| `score.py`（逼近度打分） | `video-select/video_select/score.py` |
| 选题 `twostage/stage1_topics.py` | `video-select/video_select/topics.py` + `prompts/topic-select.md` |
| 定段 `twostage/stage2_script.py` | ⚠️ DEPRECATED·停用（选题到粗区间为止，边界交总编全局取证） |
| 门禁（原手工 `_merge_segments.py`） | `video-select/video_select/gates.py`（精选合并代码化） |

设计真源：[`doc/plan/视频剪辑skill-第二环选片-plan.md`](../../../doc/plan/视频剪辑skill-第二环选片-plan.md)。
迭代命令见 `engines/video-select/README.md`。
