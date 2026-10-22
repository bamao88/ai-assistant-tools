# video-clip 日常工作流

> 处理真实剪辑任务时读。本文件回答“这一单怎么走”；能力库存看 `selector.py --list`，维护方法看 `maintenance.md`。

## 0. 每单先做六个决定

1. **输入是什么**：长视频、已确认成片脚本、已切好的片段，还是只做一个叠加动作。
2. **为谁干活**：读 `../output_routing.json` 决定所有中间产物和成片落点。用户给的路径优先。
3. **时间基准是什么**：只要切点来自字级 ASR，就先走 `quality-gates.md` 的时间基准门。
4. **源类型是什么**：干净口播、录屏、带噪、口播 PIP；它决定源适配，不决定主配方。
5. **成片风格是什么**：PPT 手写白板、横版 PPT、原视频快剪，或轻量拼接。
6. **哪里停下来给人看**：选题/成片脚本、PPT 视觉变更、美颜联系表都有人审门，不能自动越过。

## 1. 长视频，还没有成片脚本

```text
① 转录 → ② 选题/成片脚本 → 🛑 人工确认 → ③④⑤⑥ 剪辑成片
```

### ① 转录

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools
engines/video-slicer/transcribe-01.sh /abs/source.mp4
```

产出 `words.json` 和 `transcript.txt`。腾讯会议逐字稿不用重转录：

```bash
cd engines/video-select
python3 -m video_select.adapt_tencent --in /abs/minutes.json --out /abs/words.json --host 张和
```

### ② 选题与成片脚本

在 `engines/video-select/` 依次运行：

```text
topics → generate → （批量时可选 dedup）→ gates → 人读 candidates/clip_NN.md
```

具体 CLI 以 `engines/video-select/README.md` 为准。`gates` 通过只代表结构可执行，不代表内容已获批准。

### 🛑 人工确认

把 `candidates/clip_NN.md` 给用户看，确认：讲哪几段、顺序、删哪些口水、钩子是否采用。确认前不进入剪辑。

### ③④⑤⑥ 剪辑

把确认稿转成所选配方的 `selection` 或 `job`，走下方默认配方。

## 2. 已有成片脚本 / 已选好片段

跳过①②，先完成输出路由和时间基准门，再选配方。

| 目标 | 默认配方 | 调用 |
|---|---|---|
| 竖版手写白板 PPT + 圆窗人像 | `zh_business` | `run.py --run zh_business --selection ... --profile ...` |
| 横版 PPT 方框版式 | `landscape_business` | `run.py --run landscape_business --selection ... --profile ...` |
| 保留原画面、去废/静音、字幕、默认 1.2x | `zh_clip_cut` | `run.py --run zh_clip_cut --job ...` |
| 极简词级快剪 | `raw_quickcut` | 先 `--plan`；当前按原子计划执行 |
| 纯拼接 | `simple_concat` | 直接用 `concat` 原子通常更清楚 |
| 章节进度条成长片 | `chaptered_growth` | 按幕加 `progress_bar` 后 `concat` |

### PPT 竖版

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools
python engines/video-compose/run.py --plan zh_business
python engines/video-compose/run.py --run zh_business \
  --selection /abs/selection.json --profile zh_main
```

### PPT 横版

```bash
python engines/video-compose/run.py --run landscape_business \
  --selection /abs/selection.json --profile zh_main
```

### 原视频快剪

```bash
python engines/video-compose/run.py --plan zh_clip_cut
python engines/video-compose/run.py --run zh_clip_cut --job /abs/job.json
```

`job` 常用字段：

```json
{
  "spec": "/abs/clip_spec.json",
  "words": "/abs/words.json",
  "profile": "zh_main",
  "time_basis": "asr_audio",
  "asr_audio": "/abs/transcribed.wav",
  "source_time_offset": 0.750998,
  "speed": 1.2,
  "ai_fix": true,
  "title": "已确认标题",
  "hook": "/abs/hook.mp4",
  "out_dir": "/abs/item/assets/video_edit/work"
}
```

时间基准字段按素材填写，不要照抄数值。`rough_cut` 会把结果写进 `cut_manifest.json`；信息矛盾或非零起点未声明时直接停止。

## 3. 源适配只按实际需要挂

| 源况 | 适配 | 规则 |
|---|---|---|
| 干净口播 | 默认不挂 | 不为“可能更好”增加处理 |
| 录屏有外框/UI | `reframe_crop` + `name_mask` | crop/mask 尽量与粗剪同趟完成 |
| 背景噪声影响停顿判断 | `denoise_voice` | 缺 demucs 会降级抽原音，日志要说明 |
| WXP 口播 PIP 需轻美颜 | `beauty_face_pip` | 先出 compare/preview，人工确认后合成 |

具体原子命令见 `atomic-commands.md`。

## 4. 从中间阶段重跑

`zh_clip_cut` 支持：

```text
rough_cut → subtitle → trim → assemble
```

- 改了选段或时间基准：从 `rough_cut` 重跑。
- 只改字幕生成逻辑：从 `subtitle` 重跑。
- 只改字幕文字：编辑 `clip.srt` 后从 `trim` 重跑。
- 只改标题、钩子或最终烧字：从 `assemble` 重跑。

```bash
python engines/video-compose/run.py --run zh_clip_cut --job /abs/job.json --from trim
```

成功后可加 `--cleanup-cache` 清理可重生的大视频缓存；账本、SRT 链和成片必须保留。

## 5. 输出落点

读取 `skills/video-clip/output_routing.json`，不要在本文复制项目清单。

- 用户明确指定路径时，按用户路径。
- 命中项目时，所有中间产物、QC 和成片放进该内容 item 体系。
- 工具试验才进 `tools/var/video-clip/<task>/`。
- 不知道 content_id 且无法唯一解析时问用户；不要猜一个 item，也不要静默丢到 var。

