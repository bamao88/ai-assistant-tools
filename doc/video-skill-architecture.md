# 视频剪辑 Skill：架构与维护指南

> 更新口播/长视频成片这条线前先读。它讲清楚：系统分几块、信息以谁为准、要改某件事去哪改、怎样证明没有改坏。
> 迁移历史见 [`video-tools-migration-plan.md`](./video-tools-migration-plan.md)；本轮系统化计划见 [`plan/video-clip-skill-systematization-plan.md`](./plan/video-clip-skill-systematization-plan.md)。

## 一句话定位

`video-clip` 是口播/长视频到成片的唯一用户入口。它不亲自实现所有算法，而是让 `video-compose` 调度四个能力引擎，走完“转录 → 选题 → 剪辑 → 字幕 → 铸造 → 组装”。

大白话：Skill 是前台，`video-compose` 是调度员，四个能力引擎是不同工位。

## 真实结构：一个组合层 + 四个能力引擎

```text
用户
 │
 ▼
skills/video-clip/                 前台：分流、人工停顿、落点、质量门
 │
 ▼
engines/video-compose/             组合层：选配方、审链、执行、验契约
 ├── engines/video-select/         ② 选题与成片脚本
 ├── engines/video-slicer/         ① 转录、字/句时间、④字幕文字
 ├── engines/video-framework-render/ ⑤ PPT/字幕画面铸造
 └── engines/video-clip/           ③ 裁剪、源适配、⑥组装、自检
```

所以文档里出现的“两个引擎”“三个积木厂”“四个引擎”“五个引擎”要这样统一理解：**五个模块 = 一个组合层 + 四个提供能力的引擎**。

物理目录继续按运行环境分，不按六环搬家。原因很简单：渲染要 Pillow/OpenCV/Puppeteer，普通裁剪主要靠 FFmpeg，文字时间逻辑可以保持轻量。六环是业务认知，不是安装环境。

## 六环：每条成片的共同骨架

```text
① 转录 → ② 选题/成片脚本 → 🛑人工确认 → ③ 裁剪 → ④ 字幕 → ⑤ 铸造 → ⑥ 组装
```

- **① 转录**：视频/音频变成字级或句级时间稿。
- **② 选题**：决定“剪成什么内容”，产出可审的成片脚本。
- **🛑 人工确认**：机器门只证明可执行，不能替 owner 决定内容。
- **③ 裁剪**：粗剪、去口水/长静音、变速。
- **④ 字幕**：把字搬到剪后时间，唯一 `srt_fix` 只改文字，别动清单再钉回。
- **⑤ 铸造**：选择 PPT 手写白板或保留原画面，生成最终视觉层。
- **⑥ 组装**：标题、钩子、片尾、拼接和交付命名。

源适配横跨阶段：录屏裁框/挡 UI、带噪去噪、口播 PIP 轻美颜，只按源况挂，不另造主流程。

## 三条“承重墙”

### 1. 画、音、字幕共用一条时间线

字幕在中间阶段是一张 SRT “便签”，不是提前烧进画面的像素。谁裁画面、去静音、变速或拼钩子，谁就用同一映射处理画、音和字幕；最后只烧一次字。

每个动时间轴的出口跑 `align_check`：

- 门S：视频流和音频流时长一致。
- 门D：字幕贴口型。
- 门A：切点落在停顿附近。

失败就停管线，不能带病交付。

### 2. 字级时间先过“源时间基准门”

ASR 时间只对送去识别的音频负责。原 MOV 的音频轨若从 0.751 秒开始，而抽出的 WAV 从 0 开始，直接用 WAV 时间剪 MOV 会整体早 0.751 秒。

`rough_cut` 和字级 `run_cut/cut_video` 现在都要求：

- 切点已是原片轴：`time_basis=source`。
- 切点来自 ASR 音频：`time_basis=asr_audio`，同时给 `asr_audio` 自动计算，或给 `source_time_offset`。
- 原片音频起点明显非零却没说明基准：拒绝运行，不再默默早切。

账本保留原 ASR 切点给字幕映射，只在送给 FFmpeg 时加 offset。详细操作见 `skills/video-clip/references/quality-gates.md`。

### 3. 真源各司其职

| 要回答的问题 | 唯一真源 | 大白话 |
|---|---|---|
| 某引擎有哪些能力 | `engines/<engine>/capabilities.json` | 每个工位自己的货架清单 |
| 全链有哪些能力 | 生成的 `engines/video-compose/catalog.json` | 调度员汇总清单，不能手写 |
| 默认组合怎么串 | `engines/video-compose/recipes.json` | 标准套餐 |
| 原子怎么运行 | `run.py` / 专属 runner | 调度接线 |
| 账号差异 | 各引擎 `profiles/<account>/` | 每个账号自己的尺码 |
| 项目产物去哪 | `skills/video-clip/output_routing.json` | 收货地址簿 |
| 日常操作经验 | `skills/video-clip/references/` | 当班手册 |
| 方案与历史 | `doc/plan/` | 还没上线或已经完成的工程记录 |

## 当前默认配方

| 配方 | 用户得到什么 | 当前执行状态 |
|---|---|---|
| `zh_business` | 竖版手写白板 PPT + 圆窗人像 | 生产可用；组合层暂时 delegate 到已薄化业务脚本 |
| `landscape_business` | 横版方框 PPT | 生产可用；同上 |
| `zh_clip_cut` | 保留原画面、去废/静音、字幕、默认 1.2x | 真 chain，由 `clip_cut_run.py` 执行 |
| `raw_quickcut` | 极简词级快剪 | 可审链；原子级执行 |
| `simple_concat` | 纯拼接 | 原子可用 |
| `chaptered_growth` | 分幕进度条成长片 | 原子组合可用 |

`semantic_screencast_pip` 仍是待评审提案，见 [`plan/video-clip-semantic-screencast-pip-plan.md`](./plan/video-clip-semantic-screencast-pip-plan.md)，不属于现行配方。

## PPT 风格锁：未经明确要求不动

竖版默认已经拍板为“手写白板极简”：白底、手写体、纯黑、左对齐、大留白、标题是问题/结论、列表用 `1. 2. 3.`、圆窗人像右下靠底。

三个定稿载体：

| 文件 | 决定什么 |
|---|---|
| `engines/video-slicer/profiles/zh_main/pages_system_prompt.txt` | 分几页、每页讲什么、翻页节奏 |
| `engines/video-framework-render/video_framework_render/render.py` 的竖版 `PAGE_CSS` | 字体、字号、颜色、排版 |
| `engines/video-framework-render/layouts/vertical.json` | 圆窗和字幕几何 |

无用户明确要求，不改、不换、不新建默认样式。要改时先出样片，用户拍板后更新定稿并重冻 G4。`vertical_ppt` 是仍有代码/测试引用的旧兼容面，但不允许当默认。

## 账号定制和输出路由

账号特定的 prompt、术语、几何和 preset 放在对应引擎的 `profiles/<account>/`，不要散回业务项目，也不要焊进通用原子。

当前 WXP 人像能力用版本化 preset：`engines/video-clip/profiles/beauty_face_pip_presets.json`。`wxp_self_natural_v1` 只处理 PIP crop，正式合成前必须保留 manifest、compare，最好还有 preview。其他账号不自动套瘦脸。

产物落点只由 `skills/video-clip/output_routing.json` 决定：

- 用户明确路径优先。
- `assistant_zh`、`assistant_wxp_self` 等项目任务进入对应 item 体系。
- 工具试验才进入 `tools/var/video-clip/`。

加新账号时，profile 和 output routing 要成对考虑；否则能力有了，成片仍会靠现场人工归位。

## 入口命令

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools

# 看能力与配方
python engines/video-compose/selector.py --list

# 审链，不出片
python engines/video-compose/run.py --plan zh_clip_cut

# 原视频快剪
python engines/video-compose/run.py --run zh_clip_cut --job /abs/job.json

# 竖版 PPT
python engines/video-compose/run.py --run zh_business \
  --selection /abs/selection.json --profile zh_main

# 验证控制面没有漂移
python engines/video-compose/verify_contracts.py
```

## 维护场景：要做什么，去哪改

| 目标 | 改动路径 | 必须验证 |
|---|---|---|
| 加原子能力 | 所属引擎代码 + `capabilities.json` → 重建 catalog → recipe/dispatch | 契约检查 + 原子测试 + T0 |
| 加配方 | `recipes.json` + runner/dispatch | `--plan` + 契约检查 + 对应阶段测试 |
| 改选题 prompt | `engines/video-select/prompts/` | 对应 stage scorer + gates；必要时真实 LLM |
| 改账号术语/prompt/preset | 对应 `profiles/<account>/` | profile 单测/样片/人工门 |
| 加账号/项目落点 | profiles + `output_routing.json` | 路由解析和真实 item 落点 |
| 改时间轴行为 | `rough_cut`/账本/伴随轨原子 | 时间基准单元 + T0/T1/T2 |
| 改 PPT 视觉 | 三个锁定载体 | 用户样片确认 + G4 重冻/回归 |
| 改 Skill 入口/行为 | `skills/video-clip/` | 本文同步 + 契约/T0/check-tools |

更细步骤见 `skills/video-clip/references/maintenance.md`。

## 验证梯度

```bash
# L0/L1：控制面与时间基准
python engines/video-compose/verify_contracts.py
python -m unittest discover -s engines/video-clip/tests -p 'test_*.py'
(cd engines/video-slicer && python3 -m pytest tests/test_text_pipeline.py -q)

# L2：秒级确定性回归
python engines/video-compose/regression/run_regression.py t0

# L3：通用原子 smoke
bash engines/video-clip/test_atoms.sh

# 仓库登记
python scripts/check-tools.py
```

按风险追加：T1 单原子、T2 阶段集成、T3 端到端 + 火山转录 + G4。金标准变化必须先解释行为为什么变，再重冻；不能为了绿灯直接改期望值。

## 当前已知的过渡面

- `zh_business` / `landscape_business` 仍由组合层 delegate 到 `assistant_zh` 的薄脚本。迁回工具需要跨项目样片和 G4，不能夹进普通整理。
- `vertical_ppt` 已不是默认，但仍有代码和测试引用；删除要单独做视觉兼容迁移。
- `var/zh_main/` 的历史大媒体是本机验证证据，不是代码真源；换机器要按 regression README 重建 fixture。

## 完成定义

一次结构或行为修改只有在以下条件同时满足时才完成：代码/配置已改；本架构文档同步；契约、对应测试和 `check-tools.py` 通过；人工门/G4 等本地证据按风险完成或明确记录未跑原因。
