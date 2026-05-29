# Video Slicer CLI 计划

## 状态

已通过 `intuitive-flow` 审阅，并接受为第一版实现切片。

## Autoplan 审阅决策

本节记录实现前已经接受的审阅决策。

| # | 决策 | 分类 | 理由 |
|---|---|---|---|
| 1 | 第一版保持为本地 CLI，不包含下载器或导入器。 | 机械性决策 | 用户明确延后了素材下载处理；本地输入能让核心渲染器复用于 YouTube、腾讯会议和其他未来来源。 |
| 2 | 第一版先使用 Python 标准库 CLI，同时保留公开命令形态。 | 务实决策 | 避免强制第三方运行时依赖，更容易在本地运行 MVP；后续可在不改变用户命令的前提下加入 Typer/Pydantic。 |
| 3 | 手动剪辑必须在没有 LLM 密钥的情况下可用。 | 机械性决策 | 手动模式是确定性兜底，不应被规划或翻译提供方阻塞。 |
| 4 | 英文 `auto` 字幕应优先输出双语；需要翻译但没有提供方或中文字幕时，要给出可执行错误信息。 | 范围澄清 | 期望默认输出适合中文用户观看的双语英文视频，但缺失中文字幕时必须依赖提供方生成。工具应明确告诉用户如何继续。 |
| 5 | LLM 规划输出必须按严格 JSON 解析，并在任何 ffmpeg 命令运行前完成校验。 | 安全性 | 防止幻觉时间戳和格式错误的剪辑方案生成错误片段。 |
| 6 | 纯文本逐字稿只作为语义上下文，不能驱动渲染。 | 机械性决策 | 没有时间戳时，无法可靠地把片段边界映射到视频时间。 |
| 7 | 第一版竖屏和方屏布局使用确定性的中心裁切模板。 | 范围控制 | 智能裁切和人脸追踪有价值，但不属于第一版范围。 |

## 问题

需要一个本地优先的视频切片工具，把已经下载好的长视频和带时间轴的逐字稿或字幕转成短视频片段。第一版需要同时支持 AI 辅助选择时间戳，以及完全手动的时间戳剪辑。

系统不能绑定 YouTube。只要具备本地视频文件和带时间轴的逐字稿或字幕文件，YouTube、腾讯会议、飞书、Zoom、本地录屏和其他未来来源都应成为有效输入。

## 第一版目标

构建一个轻量 Python CLI，支持：

- 本地视频输入
- 本地带时间轴逐字稿输入，初始支持 VTT/SRT
- 手动时间戳剪辑方案
- 基于逐字稿和用户查询生成 AI 剪辑方案
- AI 自动推荐片段
- 默认按片段分别导出视频
- 可选多片段合并
- 中文视频默认使用中文字幕
- 英文视频默认使用中英双语字幕
- 用于规划和翻译的 OpenAI 兼容 LLM 提供方
- 基础输出布局：原始、竖屏、方屏

## 非目标

第一版不实现：

- YouTube、腾讯会议、飞书、Zoom 或其他来源下载器
- 浏览器、桌面端或 Web UI
- 没有时间戳时从原始音视频做 ASR
- 纯文本逐字稿到视频时间戳的对齐
- 说话人分离
- 声音克隆或配音
- 复杂字幕重分段或重对齐
- 智能裁切、人脸追踪或当前说话人重构图
- 直接 fork 或依赖 FunClip/KrillinAI 内部实现

## 参考项目

这些项目可作为产品和实现参考，但第一版不复制它们的内部实现。

- [modelscope/FunClip](https://github.com/modelscope/FunClip)：可参考 ASR 驱动剪辑、文本片段选择、多片段剪辑、目标片段字幕、偏移控制和 LLM 智能剪辑。
- [krillinai/KrillinAI](https://github.com/krillinai/KrillinAI)：可参考字幕翻译、LLM 字幕分段/对齐、OpenAI 兼容模型配置、跨平台视频合成和双语输出流程。

## 来源模型

第一版输入严格本地化：

```text
输入视频文件 + 带时间轴的逐字稿/字幕文件 -> 剪辑方案 -> 渲染片段
```

示例：

```text
input.mp4
subtitles.en.vtt
subtitles.zh.srt
clip_plan.json
```

规则：

- 真实剪辑需要 VTT/SRT 或其他带时间轴的逐字稿。
- 纯文本逐字稿只能作为可选语义上下文。
- 如果只有纯文本，工具可以生成笔记或章节想法，但不能声称可以渲染准确片段。
- 下载和导入逻辑不在当前范围内，后续应作为独立导入器增加。

## 用户可见术语

使用对用户友好的命名：

- 用户概念：`clip plan` / `剪辑方案`
- 文件：`clip_plan.json`
- CLI 选项：`--clip-plan`
- 不要把 `manifest` 暴露为主要用户术语。

## CLI 形态

### 验证输入

```bash
video-slicer validate \
  --video input.mp4 \
  --transcript subtitles.en.vtt
```

检查：

- 输入文件存在
- 可通过 ffprobe 读取视频时长
- 可解析逐字稿时间戳
- 逐字稿时间范围与视频时长兼容

### 手动剪辑方案

快速命令行剪辑：

```bash
video-slicer render \
  --video input.mp4 \
  --clip 00:12:30-00:13:45 \
  --clip 00:28:10-00:29:05
```

复用剪辑方案：

```bash
video-slicer render \
  --video input.mp4 \
  --clip-plan clip_plan.json
```

### AI 剪辑规划

查询驱动模式：

```bash
video-slicer plan \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --mode query \
  --query "找关于 AI 产品经理能力变化的片段，适合做 60 秒短视频" \
  --out clip_plan.json
```

自动推荐模式：

```bash
video-slicer plan \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --mode auto \
  --out clip_plan.json
```

手动模式也可以生成规范化方案文件：

```bash
video-slicer plan \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --mode manual \
  --clip 00:12:30-00:13:45 \
  --clip 00:28:10-00:29:05 \
  --out clip_plan.json
```

### 渲染

默认每个片段导出一个视频。

```bash
video-slicer render \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --clip-plan clip_plan.json \
  --out-dir outputs/
```

显式合并片段：

```bash
video-slicer render \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --clip-plan clip_plan.json \
  --join \
  --out outputs/highlights.mp4
```

布局：

```bash
video-slicer render \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --clip-plan clip_plan.json \
  --layout vertical
```

字幕模式：

```bash
video-slicer render \
  --video input.mp4 \
  --transcript subtitles.en.vtt \
  --clip-plan clip_plan.json \
  --subtitle auto
```

## 剪辑方案结构

`clip_plan.json` 是严格、可执行、机器校验的文件。

```json
{
  "version": 1,
  "source": {
    "video": "input.mp4",
    "transcript": "subtitles.en.vtt",
    "language": "en"
  },
  "defaults": {
    "layout": "vertical",
    "subtitle": "auto",
    "join": false,
    "padding_start_seconds": 0.8,
    "padding_end_seconds": 1.0
  },
  "clips": [
    {
      "id": "ai-pm-speed",
      "title": "AI 产品经理需要更快行动",
      "start": "00:17:42.000",
      "end": "00:18:38.000",
      "reason": "解释 AI 原生产品工作如何压缩功能交付周期。",
      "tags": ["AI 产品", "产品经理", "交付"],
      "subtitle": {
        "mode": "bilingual"
      }
    }
  ]
}
```

校验规则：

- `version` 必须受支持。
- `clips` 不能为空。
- 每个片段必须有稳定的 `id`、`start` 和 `end`。
- `id` 必须可安全作为文件名。
- `start < end`。
- 片段范围必须落在视频时长和逐字稿范围内。
- 默认片段长度策略应可配置，初始为 15-180 秒。
- padding 不能把片段推出视频时长范围。
- AI 生成的时间戳必须能映射回逐字稿字幕片段。
- 无效 AI 输出必须在 ffmpeg 运行前失败。

## 逐字稿时间轴

内部时间轴应把 VTT/SRT 规范化为统一字幕片段模型：

```text
Cue {
  index
  start_seconds
  end_seconds
  text
  speaker?
  language?
}
```

对于带词级内联时间戳标签的 YouTube 风格 VTT，第一版行为应为：

- 从显示文本中移除内联词级时间标签
- 默认使用字幕片段级时间戳作为可执行时间轴
- 可选择保留词级数据，为后续更精细的边界吸附做准备

清理后的逐字稿文本可以切块用于 LLM 提示词，但所有接受的片段时间戳都必须解析回字幕片段级时间。

## AI 规划流程

对于 `query` 和 `auto` 模式：

1. 把逐字稿解析成 cues。
2. 把字幕片段切分成模型友好的段落，同时保留片段 id 和时间。
3. 要求 LLM 只使用提供的片段 id/时间戳提出片段。
4. 要求输出符合剪辑方案 schema 的严格 JSON。
5. 校验 JSON 结构。
6. 根据逐字稿和视频校验时间戳。
7. 可选地把起止时间吸附到附近 cue 边界。
8. 写出 `clip_plan.json`。

提示词要求：

- 模型不得编造不可用时间戳。
- 模型必须为每个片段给出理由。
- 模型应优先选择完整语义片段，而不是孤立金句。
- 除非用户明确要求，否则模型应避开赞助口播、开场、结尾和泛泛过渡段。
- 查询模式应把与用户查询的相关性排在泛化爆款性之前。
- 自动模式应优先考虑独立可理解性、洞察密度和短视频适配度。

## LLM 提供方

使用 OpenAI 兼容提供方抽象。

环境变量：

```bash
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
VIDEO_SLICER_MODEL=...
```

行为：

- `manual` 渲染不需要 LLM 密钥。
- `plan --mode query` 和 `plan --mode auto` 需要 LLM 提供方。
- 英译中文字幕需要 LLM 提供方，除非已经提供中文字幕文件。
- 提供方代码应隔离在小接口后面，方便后续增加其他提供方。

## 字幕策略

字幕模式：

- `none`：无字幕
- `soft`：输出旁路 `.srt`/`.vtt`，条件允许时 mux 软字幕
- `burned`：把字幕烧录进视频
- `auto`：根据源语言和可用字幕文件选择默认行为

默认语言行为：

- 中文视频：默认使用中文字幕。
- 英文视频：默认使用中英双语字幕。
- 如果已有双语字幕，直接复用。
- 如果英文视频只有英文字幕，则生成中文翻译，并对齐到原英文字幕片段时间戳。

第一版双语对齐：

- 保持原始字幕时间轴。
- 按字幕片段或小批量翻译，保留片段 id。
- 第一版不重分段、不重对齐字幕。
- 默认烧录双语字幕时，每个字幕片段显示两行。
- 字幕行顺序应可配置；面向中文用户观看英文视频时，默认中文在前。

## 渲染流程

媒体操作使用 `ffmpeg`/`ffprobe`。

单片段渲染：

1. 校验视频、逐字稿和剪辑方案。
2. 根据 padding 解析片段起止时间。
3. 提取片段时间范围内的字幕片段。
4. 平移字幕时间戳，让每个输出片段从 0 开始。
5. 每个片段渲染一个输出视频。
6. 按需写出旁路字幕。
7. 按需烧录字幕。

合并渲染：

1. 把每个片段渲染或抽取成临时规范化片段。
2. 平移并拼接跨片段字幕。
3. 使用 ffmpeg concat 流程。
4. 生成一个输出视频。

输出命名：

```text
outputs/
  ai-pm-speed.mp4
  ai-pm-speed.zh.srt
  ai-pm-speed.bilingual.srt
  product-taste.mp4
```

## 布局

第一版支持布局：

- `original`：保留原始宽高比和分辨率，除非用户覆盖。
- `vertical`：用固定模板输出 9:16 视频。
- `square`：用固定模板输出 1:1 视频。

第一版竖屏/方屏行为：

- 支持中心裁切或模糊背景模板。
- 保持字幕位置可读。
- 不实现人脸追踪或当前说话人检测。

## 建议 Python 模块

```text
video_slicer/
  cli.py
  models.py
  transcript.py
  planner.py
  llm.py
  subtitles.py
  renderer.py
  ffmpeg.py
  validation.py
tests/
  fixtures/
```

建议依赖：

- `typer` 用于 CLI
- `pydantic` 用于 `clip_plan.json` 校验
- `httpx` 或官方 OpenAI SDK 用于 OpenAI 兼容调用
- 标准库 subprocess 调用 `ffmpeg`/`ffprobe`
- 轻量 VTT/SRT 库，或带测试的小型解析器

## 验收标准

第一版满足以下条件即可验收：

- `video-slicer render` 可以基于本地 mp4 和手写 `clip_plan.json` 导出片段。
- `video-slicer render --clip ...` 不需要手写方案也可以工作。
- `video-slicer plan --mode query` 可以基于带时间轴逐字稿生成有效 `clip_plan.json`。
- `video-slicer plan --mode auto` 可以生成多个有效推荐片段。
- 无效剪辑方案会在 ffmpeg 运行前失败，并给出可执行错误信息。
- 中文源视频默认使用中文字幕。
- 英文源视频默认使用中英双语字幕。
- 可提供现有中文字幕，避免调用翻译。
- 只提供英文字幕且没有中文字幕时，LLM 翻译可以生成对齐的中文字幕。
- 默认输出为每个片段一个 mp4。
- `--join` 生成一个拼接后的 mp4。
- `--layout original`、`--layout vertical` 和 `--layout square` 能在样例视频上成功渲染。
- 样例 YouTube 逐字稿 `/tmp/yt_cat_wu.en.vtt` 可以解析，并用于生成查询驱动剪辑方案。

## 测试计划

单元测试：

- 解析 VTT 字幕片段时间戳和文本
- 解析 SRT 字幕片段时间戳和文本
- 移除 YouTube 内联 VTT 词级标签
- 校验剪辑方案 schema
- 拒绝反向或超范围时间戳
- 提取并平移片段字幕
- 在翻译批处理中保留片段 id

集成测试：

- 从极小 fixture 视频渲染一个手动片段
- 分别渲染多个片段
- 渲染合并片段
- 渲染软字幕
- 在 ffmpeg 支持时渲染烧录字幕
- 使用 mock LLM 响应生成剪辑方案
- 使用 mock 翻译响应生成双语字幕

手动/本地验证：

- 使用 `/tmp/yt_cat_wu.en.vtt` 运行
- 可用真实本地 mp4 时运行
- 至少检查一个原始布局输出和一个竖屏布局输出

## 未来扩展

来源导入器：

- 使用本地 `yt-dlp` 的 YouTube 下载器
- 腾讯会议本地导出导入器
- 飞书妙记导入器
- Zoom 录制导入器

媒体智能：

- 没有字幕的视频 ASR
- 逐字稿/视频强制对齐
- 说话人分离
- 静音移除
- 词级边界吸附

产品/UI：

- 用于审阅和编辑剪辑方案的 Web UI
- 逐字稿搜索和时间轴预览
- 批量渲染
- 可复用样式预设
- 渲染前人工审阅流程

高级输出：

- 智能竖屏裁切
- 人脸/当前说话人追踪
- 抖音、小红书、Bilibili、TikTok、YouTube Shorts 平台预设
- 配音和声音克隆
