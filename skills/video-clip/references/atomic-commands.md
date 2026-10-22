# video-clip 原子直调

> 只做一个叠加/源适配动作，或诊断某个原子时读。端到端任务优先走 `video-compose` 配方。

```bash
ROOT=/Volumes/ExtSSD2601/AI_Assistant/tools
ENG=$ROOT/engines/video-clip
PY=$ENG/.venv/bin/python
```

首次没有 venv：

```bash
python3 -m venv "$ENG/.venv"
"$ENG/.venv/bin/pip" install -r "$ENG/requirements.txt"
```

## 叠加 / 收尾

```bash
$PY $ENG/atoms/concat.py OUT.mp4 --inputs a.mp4 b.mp4 c.mp4
$PY $ENG/atoms/prepend_hook.py hook.mp4 body.mp4 OUT.mp4 --flip 0.30 --trans slideleft
$PY $ENG/atoms/endcard.py IN.mp4 OUT.mp4 --card /abs/card.png --seconds 3 --fade 0.5
$PY $ENG/atoms/progress_bar.py IN.mp4 OUT.mp4 --chapters 4 --index 2 --label 第二幕
$PY $ENG/atoms/title_bar.py IN.mp4 OUT.mp4 --text 已确认标题 --style label
$PY $ENG/atoms/subtitle_burn.py IN.mp4 OUT.mp4 --srt /abs/final.srt
$PY $ENG/atoms/cover_frame.py IN.mp4 cover.png --at 2
```

字幕 LLM 纠错的唯一入口在 `video-slicer`：

```bash
cd "$ROOT/engines/video-slicer"
python3 -m video_slicer.srt_fix /abs/in.srt --profile zh_main --out /abs/fixed.srt
```

## 源适配

```bash
$PY $ENG/atoms/reframe_crop.py --source /abs/source.mp4 --crop W:H:X:Y
$PY $ENG/atoms/name_mask.py IN.mp4 OUT.mp4 --region 250x250+435+850 --black
$PY $ENG/atoms/denoise_voice.py --in IN.mp4 --out voice.wav
$PY $ENG/atoms/beauty_face_pip.py IN.mp4 OUT.mp4 \
  --profile wxp_self --crop 1080:1080:0:500 \
  --manifest OUT.manifest.json --compare OUT.compare.jpg --preview OUT.preview.mp4
```

美颜结果必须按 `quality-gates.md` 人工看 compare 后再合成。

## 自检

```bash
$PY $ENG/atoms/align_check.py --body 成片.mp4 --srt final.srt --manifest cut_manifest.json
$PY $ENG/atoms/len_check.py final.mp4 --baseline 78.683
```

基准值来自该任务已经确认的身子时长，不能照抄示例。

