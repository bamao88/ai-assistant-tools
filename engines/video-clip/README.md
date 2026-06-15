# video-clip 引擎

积木厂：视频剪辑/合成的**叠加原子能力库**。被 `skills/video-clip` 调用，自身不触发。

- 真源：`capabilities.json`（本引擎 9 个原子声明）。编辑类型配方 + 总能力表已上移到 `engines/video-compose/`（`recipes.json` / `catalog.json`，真源唯一）。
- 共享工具：`vutil.py`（`run`/`probe`/`ffprobe_dur`/`x264`，去重散落各处的 helper）。
- 原子约定：`atoms/<name>.py IN OUT [--params]`，**幂等、不改原片、可单跑可串联**。
- 产物/测试：一律写 `tools/var/video-clip/`，不进 git、不进业务真源。

## 首次准备（venv，含 pillow+opencv，.venv 已 gitignore）

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## 原子（全部 ready，详见 catalog.json；统一用 .venv/bin/python 跑）

```bash
PY=.venv/bin/python
$PY atoms/concat.py          OUT.mp4 --inputs a.mp4 b.mp4 ...
$PY atoms/progress_bar.py    IN.mp4 OUT.mp4 --chapters 4 --index 2 [--label 第二幕]
$PY atoms/endcard.py         IN.mp4 OUT.mp4 --card /abs/card.(png|jpg|html) [--seconds 3]
$PY atoms/speed_adapt.py     IN.mp4 OUT.mp4 --srt x.srt [--target_cps 8]
$PY atoms/subtitle_burn.py   IN.mp4 OUT.mp4 --srt x.srt [--fs 36] [--y h-130]
$PY atoms/subtitle_ai_fix.py IN.srt OUT.srt [--hint ...]      # 走 LLM,需共享 .env
$PY atoms/face_locate.py     IN.mp4 [--target 720x744]        # 只读,出 JSON;需 cv2(在 venv)
$PY atoms/name_mask.py       IN.mp4 OUT.mp4 --region WxH+X+Y [--mask circle.png] [--trim 0]
$PY atoms/cover_frame.py     IN.mp4 cover.png [--at 2] [--overlay title.png]
```

回归测试：`bash test_atoms.sh`（24 用例打到每个原子每条路径，产物写 var/video-clip/_test/）。
只有 `face-locate` 强依赖 cv2；其余原子 base python3 也能跑（pillow 系统多已自带），但统一走 venv 最省心。

## 边界

- 复杂型「框架页竖版切片」(framework_slice) 不在本引擎实现：张和锁定版式，留
  `assistant_zh/workflow/video_framework_slicer/`，由 skill 路由调用。
- 与 `engines/video-slicer` 分工：video-slicer = AI 选段规划（切哪几段），video-clip = 画面剪辑合成（怎么做出来）。
- 依赖：`ffmpeg`(含 libass)、`python3`+`pillow`、`node`+puppeteer（仅 endcard 渲 html 卡时）。
