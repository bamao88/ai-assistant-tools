---
name: video-clip
description: |
  视频剪辑/合成技能。把已有的视频片段加工成成片：直接拼接、底部章节进度条、片尾钩子卡、变速、字幕烧录/AI加工字幕、遮名等原子能力，按编辑「类型」组合。
  当用户说"剪辑/合成/拼接这几段视频"、"把几个片段合成一条"、"加个底部进度条"、"末尾加片尾/钩子/试听课卡"、"做成长片/混剪"、"给视频加字幕/变速/遮名"时触发。
  本 skill 管【画面的剪辑与合成】，不管：视频转逐字稿/字幕提取/关键帧(→ video-content)、发布分发(→ platform-publish)、AI选哪几段成片的规划(→ engines/video-slicer)、选题/文案(业务项目内容流程)。
  复杂的「框架页竖版口播切片」(张和专属圆形人像PIP+手写翻页)不在本 skill 渲染，识别为该类型后路由回业务项目 workflow/video_framework_slicer。
---

# video-clip — 视频剪辑/合成

把已有视频片段，按一种**编辑类型**、用一组**原子能力**组合成成片。
能力与类型的真源（迁移后）：原子在本引擎 `capabilities.json`，配方上移到组合层（真源唯一）：

- 原子目录：`engines/video-clip/capabilities.json`（本引擎 9 个叠加原子）
- 编辑类型：`engines/video-compose/recipes.json`（`simple_concat`/`chaptered_growth`/`raw_quickcut`；框架页竖版切片现名 `zh_business`）
- 总能力表（跨引擎汇总）：`engines/video-compose/catalog.json`

引擎绝对路径：`/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-clip/`

## decision_gate（先判类型，再串原子）

1. 用户要的是哪种**编辑类型**？
   - 直接把几段拼一条 → `simple_concat`
   - 多幕片段做成带章节进度条的成长片/系列片 → `chaptered_growth`
   - 张和框架页竖版口播切片 → `zh_business`（旧名 framework_slice，**不在此渲染**，见下「路由」）
2. 该类型需要哪些**原子**（见 `video-compose/recipes.json` 的 chain），按序跑。
3. 产物一律写 `tools/var/video-clip/<任务名>/`，不写业务真源、不写原片目录。

## invoke（9 个原子全部 ready；真源 capabilities.json）

```bash
ENG=/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-clip
PY=$ENG/.venv/bin/python    # 引擎 venv(含 pillow+opencv);首次:python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
$PY $ENG/atoms/concat.py          OUT.mp4 --inputs a.mp4 b.mp4 c.mp4   # 直接拼接
$PY $ENG/atoms/progress_bar.py    IN.mp4 OUT.mp4 --chapters 4 --index 2 --label "第二幕·被批评"
$PY $ENG/atoms/endcard.py         IN.mp4 OUT.mp4 --card /abs/card.png --seconds 3 --fade 0.5
$PY $ENG/atoms/speed_adapt.py     IN.mp4 OUT.mp4 --srt x.srt --target_cps 8   # 按语速变速
$PY $ENG/atoms/subtitle_burn.py   IN.mp4 OUT.mp4 --srt x.srt                  # 烧药丸字幕
$PY $ENG/atoms/subtitle_ai_fix.py IN.srt OUT.srt --hint "..."                 # AI加工字幕(需.env)
$PY $ENG/atoms/face_locate.py     IN.mp4 --target 720x744                     # 测脸/裁切(出JSON)
$PY $ENG/atoms/name_mask.py       IN.mp4 OUT.mp4 --region 250x250+435+850 --trim 0
$PY $ENG/atoms/cover_frame.py     IN.mp4 cover.png --at 2 [--overlay title.png]
```

## 路由：framework_slice（复杂型，不在此渲染）

需要张和框架页竖版切片时，本 skill 不复制其渲染核心，直接调用业务项目现成流程：

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/assistant_zh/workflow/video_framework_slicer
python3 run_pipeline.py selections/<x>.json     # 出 accel.mp4
# 之后可选用本引擎原子做遮名/片尾，或用项目 make_publish.py
```

## 产物落点约定（默认 + 可传参）

剪辑能力**默认落通用位置，调用方可传参直写目标位置**：

- **不传目标路径** → 产物落默认 scratch `tools/var/video-clip/<任务名>/`（git-ignored，本 skill 的通用默认）。
- **调用方传目标路径** → 原子直接写到该位置（9 个原子都接受显式输出路径 `OUT.mp4`/`--output`，无需改代码）。
- **框架页切片**走项目流程时，用 `run_pipeline.py --out-root <目标根>` 覆盖默认 `out/`（项目调用即传 media/ 与 content item 目标位置；不传走默认，向后兼容）。

谁负责把产物归位到业务真源：**调用方/项目侧**，不是本通用 skill。assistant_zh 的归位规则（成片→`media/tencent/<场次>/clips/...`，配文→`content/personas/<persona>/items/<content_id>/`，状态→`content_index`）见该项目 `claude_md_design/slice_content_pipeline_refactor.md`。本 skill 只保证「能落到你传的位置」，不内置任何具体项目路径。

## 硬边界

- 不改原片：所有原子输出到新路径，幂等可重跑。
- 测试/样片进 `tools/var/video-clip/`，绝不进 `content/`、原片目录或业务真源。
- 片尾卡/海报等卡片内容由调用方提供；本 skill/引擎不内置任何账号专属卡或二维码。
- 复杂型一律路由回项目，不在共享库重造张和锁定版式。
