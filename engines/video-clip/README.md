# video-clip 引擎

视频剪辑/合成的**原子能力库 + 编辑类型配方**。被 `skills/video-clip` 调用，自身不触发。

- 真源：`catalog.json`（原子目录）、`recipes.json`（编辑类型）。文档不重复清单，看这两个 JSON。
- 共享工具：`vutil.py`（`run`/`probe`/`ffprobe_dur`/`x264`，去重散落各处的 helper）。
- 原子约定：`atoms/<name>.py IN OUT [--params]`，**幂等、不改原片、可单跑可串联**。
- 产物/测试：一律写 `tools/var/video-clip/`，不进 git、不进业务真源。

## 已实现原子（status=ready）

```bash
python3 atoms/concat.py       OUT.mp4 --inputs a.mp4 b.mp4 ...
python3 atoms/progress_bar.py IN.mp4 OUT.mp4 --chapters 4 --index 2 [--label 第二幕]
python3 atoms/endcard.py      IN.mp4 OUT.mp4 --card /abs/card.(png|jpg|html) [--seconds 3]
```

`planned` 原子（speed-adapt / subtitle-burn / subtitle-ai-fix / face-locate / name-mask / cover-frame）
已在 `catalog.json` 标注 `copy_from` 源路径，待从业务项目移植统一进本引擎。

## 边界

- 复杂型「框架页竖版切片」(framework_slice) 不在本引擎实现：张和锁定版式，留
  `assistant_zh/workflow/video_framework_slicer/`，由 skill 路由调用。
- 与 `engines/video-slicer` 分工：video-slicer = AI 选段规划（切哪几段），video-clip = 画面剪辑合成（怎么做出来）。
- 依赖：`ffmpeg`(含 libass)、`python3`+`pillow`、`node`+puppeteer（仅 endcard 渲 html 卡时）。
