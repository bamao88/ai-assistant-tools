# video-clip 质量与安全门

> 真实出片必读。每一道门都来自已经发生过的返工或已锁定的用户决定。

## 门 1：不改原片，先定输出落点

- 原片只读；原子输出到新路径，允许幂等重跑。
- 先读 `../output_routing.json`，再启动耗时任务。
- 项目任务的中间产物和 QC 也随 item 归档；工具实验才进 `tools/var/`。

## 门 2：字级时间轴必须说明基准

### 为什么

ASR 时间戳只对“实际送去识别的音频”负责。iPhone/QuickTime MOV 的音频轨可能不是从 0 秒开始；抽成 WAV 后通常归零。直接用 WAV 字级时间剪原 MOV，会整体早切或晚切。

### 先探测

```bash
ffprobe -hide_banner -v error \
  -show_entries format=start_time,duration:stream=index,codec_type,start_time,duration,time_base,start_pts,codec_name \
  -of json /abs/source.mov

ffprobe -hide_banner -v error \
  -show_entries format=start_time,duration:stream=index,codec_type,start_time,duration,time_base,start_pts,codec_name \
  -of json /abs/transcribed.wav
```

### 选择一种合法做法

1. **切点已经是原片时间轴**：写 `"time_basis":"source"`，不加 offset。
2. **切点来自 ASR/WAV 时间轴**：写 `"time_basis":"asr_audio"`，并提供 `asr_audio` 让系统计算，或显式写：

```text
source_time_offset = 原片音频轨 start_time - ASR 音频 start_time
```

3. **先规范化工作源**：把音视频都归零，再从这个工作源抽音并转录。EDL 记录 `normalized_source`，后续只能剪它，不能混回原 MOV。

推荐 spec/job 字段：

```json
{
  "source": "/abs/original.mov",
  "asr_audio": "/abs/transcribed.wav",
  "time_basis": "asr_audio",
  "source_audio_start_time": 0.750998,
  "asr_audio_start_time": 0.0,
  "source_time_offset": 0.750998,
  "must_keep_phrases": ["大概有 2000 多个人"]
}
```

`rough_cut` 的规则：非零源起点但没有声明基准时拒绝运行；ASR 轴切点只在送给 FFmpeg 时加 offset，字幕仍按原 ASR 字级稿映射到剪后累计时间。

### 小样门

每个新素材至少先出 5-10 秒短样，检查首句、句尾和最靠近切点的 `must_keep_phrases`。不要用“多留 0.3 秒”掩盖基准错误。

## 门 3：谁动时间轴，谁同时动画、音、字幕

片段是不可分割的画面+声音+字幕对象。

- 裁时长、平移、变速、拼钩子：三轨必须使用同一映射。
- 只改内容但不改时间允许单轨处理，例如遮 UI、加标题、改字幕文字。
- 字幕作为 SRT “便签”随片段走，最后只烧一次。
- 每个动时间轴的出口跑 `align_check`：门S 看画音等长，门D 看字幕贴口型，门A 看切点落停顿。
- 任一门失败就停；`--no-gate-raise` 只用于诊断，不能作为交付方式。

## 门 4：选题/成片脚本必须人工确认

`video-select.gates` 只能证明脚本结构可执行、没有明显编造或碎段；它不能替用户决定“这条值不值得讲”。确认前不自动剪。

## 门 5：PPT 风格锁

默认 `zh_business + layout:vertical` 已定稿为手写白板极简：白底、手写体、纯黑、左对齐、大留白、标题是问题/结论、列表用 `1. 2. 3.`、圆窗人像右下靠底。

三个锁定载体：

- `engines/video-slicer/profiles/zh_main/pages_system_prompt.txt`：内容与翻页。
- `engines/video-framework-render/video_framework_render/render.py` 的竖版 `PAGE_CSS`：外观。
- `engines/video-framework-render/layouts/vertical.json`：几何。

未经用户明确要求，不改、不换、不新建默认版式。用户要求改时：先出样片，用户拍板，再更新定稿并重冻 G4。`vertical_ppt` 是旧兼容面，不得当默认。

## 门 6：美颜先看人，再合成

`beauty_face_pip` 只处理口播 PIP crop，不动主录屏。

- WXP 个人号可用 `wxp_self_natural_v1`；其他账号不自动套瘦脸。
- preset 是版本化风格档位，确认后不原地改；新风格建 v2/v3。
- 正式成片前必须保留 `manifest.json`、before/after `compare.jpg`，最好再出 `preview.mp4`。
- 检测不到脸会继续轻美颜并记录检测率；这不等于视觉已经通过。
- 强瘦脸不做默认，超过推荐阈值必须人工确认。

## 门 7：完成定义

- 目标文件存在、可播放，画音流时长门通过。
- 字幕条数/时间线门通过，必留句抽查通过。
- 人工门已有明确确认记录。
- 最终成片与账本/SRT/QC 证据落在正确 item。
- 不以“命令退出码 0”替代以上证据。

