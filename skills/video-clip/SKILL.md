---
name: video-clip
description: |
  口播 / 长视频 → 成片：这条线的统一入口（转录 → 选题 → 剪辑合成，三段都是本 skill 体系下的引擎在干，只是住在不同引擎目录）。
  两条默认成片线：①PPT 风格（手写白板 PPT + 圆窗人像，竖版默认 / 横版可选）②原视频风格（保留原画面、只收拾干净）。两条都自带共享默认（字幕 LLM 处理 + 默认变速），在此之上可选叠加：前钩子 / 片尾·后钩子 / 顶部标题 / 裁切放大盖UI / 遮名。不需要叠加就一键调用默认。
  当用户说"剪辑/合成/拼接这几段视频"、"做成片/出片"、"生成 PPT / PPT 风格成片 / 框架页竖版切片"、"出横屏成片"、"原视频风格剪 / 录屏裁剪"、"把这条长视频做成切片成片"、"加底部进度条 / 片尾 / 钩子 / 顶部标题"、"给视频加字幕/变速/遮名/裁切放大"时触发。
  也管这条线的前半截：长视频还没选题时，先一键转录 + 走选题流程出「成片脚本」，停下来给人 review，确认后再剪（详见下「入口分流」）。
  不管：纯逐字稿/字幕/关键帧提取且不出片(→ video-content)、发布分发(→ platform-publish)、平台内容抓取(→ platform-fetch)、把现成 .pptx/幻灯片文件转成视频(本 skill 的「PPT」是把口播内容页化，不是转换现成幻灯片)、起标题文案本身(→ 专门的起标题 skill 如 dbs-xhs-title，本 skill 只负责把给定标题烧进画面)。
  「PPT 风格成片」默认走 zh_business + layout:vertical（已定稿），不要自己换风格、不要改 prompt/CSS/几何（见「PPT 风格·定稿」）。
---

# video-clip — 口播 / 长视频 → 成片（统一入口）

这条线 = 一条口播 / 长视频 → 成片。分三段，**都是本 skill 体系下的引擎在干**（转录 / 选题 / 剪辑只是住在不同引擎目录，同属这一条线）：

```
① 转录 ──→ ② 选题（出成片脚本）──🛑人工 review──→ ③ 剪辑合成 ──→ 成片
engines/video-slicer  engines/video-select      engines/video-framework-render + video-clip
```

- 能力真源：各引擎 `capabilities.json`，配方在组合层 `engines/video-compose/recipes.json`，跨引擎总表 `engines/video-compose/catalog.json`。
- 全部能力按六环分组见下「能力全表」；想看分组展示跑 `python engines/video-compose/selector.py --list`。

## 入口分流（先判你手上是什么）

1. **已有「成片脚本 / 选好的段」**（或就是几段视频要拼 / 加工）→ 直接进 **③ 剪辑**（下面）。
2. **一条长视频、还没选题** → 走全程，别跳步：
   - **① 一键转录**：`engines/video-slicer/transcribe-01.sh <视频>`（自动本地出口 + 火山主·阿里兜底，出 `words.json`+`transcript.txt`）。腾讯会议逐字稿用 `python -m video_select.adapt_tencent`。
   - **② 选题出脚本**：`engines/video-select` —— `topics`（选题清单）→ `generate`（每条选题出**成片脚本**：总编+组装+字级去口水+钩子）→ 可选 `dedup`（批量去重），过 `gates` 门禁。产人读评审稿 `candidates/clip_NN.md`。
   - **🛑 停下来给人 review 脚本**：选题 / 成片脚本通常要人确认（讲哪几段、怎么编排、删哪些口水）。**确认无误再继续，不要自动往下剪。**
   - **③ 按确认的脚本进剪辑**（下面）。

## ③ 剪辑：先选默认线，再按需叠加

**两条默认线**，都自带**共享默认：字幕 LLM 处理 + 默认变速**。先认这两条，多数活一键就出：

| 默认线 | 是什么 | 版式 | 默认变速 | 配方 |
|---|---|---|---|---|
| **A. PPT 风格** | 口播内容重画成**手写白板 PPT** + 圆窗人像，翻页 | 竖版 `vertical`（默认）/ 横版 `landscape`（方框，视觉 DNA 同竖版） | 按语速自适应（🔒定稿锁） | `zh_business`（竖）/ `landscape_business`（横） |
| **B. 原视频风格** | **保留原画面**，只收拾干净（去废 / 去长静音 / 烧药丸字幕），**默认不裁切** | 原画幅 | 默认 **1.2x** | `zh_clip_cut` |

**可选叠加**（不需要就别加，一键默认即可）：

- **裁切放大 / 盖 UI**（录屏源适配）：`reframe_crop`（裁切放大铺满）+ `name_mask`（盖多余按钮/UI）。**录屏要放大铺满、盖掉多余 UI 时才加**；干净口播不加。原剪线把它做成「录屏源」才挂的源适配，默认不挂。
- **前钩子**：`prepend_hook`（开篇钩子 + 翻页转场，翻页时正文定格）。
- **片尾 / 后钩子卡**：`endcard`（片尾卡 / 试听课卡，卡片内容由调用方提供）。
- **顶部标题**：`title_bar`（`--style label` 白底黑字圆角贴纸 / `--style bar` 黑底白字整条）。**本 skill 只负责把「给定的标题」烧进画面，不自己写标题文案**——文案来源：优先取该条 item 的 `publish_copy.md`「标题候选」✅；没有现成的，就让 AI 先调专门的起标题 skill（如 `dbs-xhs-title`）产出文案，再用 `title_bar` 烧上去。
- **遮名**：`name_mask`（多块黑挡，遮学员名等）。
- 更轻的拼接型（不是口播成片时）：`simple_concat`（纯拼接）/ `chaptered_growth`（章节进度条成长片）/ `raw_quickcut`（极简词级快剪+烧字幕）。

### 一键最简调用

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools
# A·PPT 竖版（默认）：选段清单 → 成片（自带字幕LLM+语速自适应变速）
python engines/video-compose/run.py --run zh_business      --selection <sel>.json --profile zh_main
# A·PPT 横版：同一份 pages 出横屏
python engines/video-compose/run.py --run landscape_business --selection <sel>.json
# B·原视频风格：一键端到端（自带 1.2x + 字幕LLM；录屏要裁切就在 job 里开源适配）
python engines/video-compose/run.py --run zh_clip_cut --job <job>.json    # job 规格见 engines/video-compose/clip_cut_run.py --help
# 审链路（不出片，按六环分组看每个原子/挂载点/自检门）
python engines/video-compose/run.py --plan zh_clip_cut
```

需要叠加（钩子/标题/遮名/裁切）时，在配方的 `post_optional` / job 里开，或用下面「原子直调」单调。**产物落哪先过「输出落点决策」门。**

## 框架页竖版口播切片 / PPT 风格成片（zh_business）

「生成 PPT」「出 PPT 风格成片」「框架页竖版切片」= 同一条线，配方 `zh_business`，**默认 layout=vertical（手写白板 PPT 风格，定稿）**。渲染核心在 tools 引擎，不再路由回 assistant_zh。

两段产物，分工固定：
- **PPT 内容（几页 / 每页讲什么 / 翻页节奏）** ← 引擎 `video-slicer` 的 `pages_gen`，提示词 `engines/video-slicer/profiles/zh_main/pages_system_prompt.txt`。
- **PPT 外观（手写白板长什么样）** ← 引擎 `video-framework-render` 的 `render.py`：竖版手写样式 `PAGE_CSS`，几何（人像圆窗/字幕位置）`layouts/vertical.json`。

最小调用（一条切片 → 成片）：
```bash
SL=/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-slicer
FW=/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-framework-render
# ① 逐字稿(clip.srt) → pages.json（PPT 内容+翻页节奏，默认 profile zh_main）
$SL/.venv/bin/python -m video_slicer.pages_gen clip.fixed.srt --out pages.json
# ② job.json(含 video/srt/pages, "layout":"vertical") → 成片 accel.mp4
$FW/.venv/bin/python -m video_framework_render.render job.json --out OUTDIR --profile zh_main
```
端到端业务流（选片→去口水→pages→渲染→变速）：`python engines/video-compose/run.py --run zh_business --selection <sel>.json --profile zh_main`。

### 🔒 PPT 风格·定稿（未经用户明确指示，不得改）

PPT 风格已经用户拍板定稿 = **手写白板极简**（全程手写体 Hannotate SC、纯黑、左对齐、大留白、标题=问题/结论、列表用纯数字 `1. 2. 3.`、人像圆窗右下靠底）。以下文件是定稿载体，**默认调用就用它们、不带任何特殊参数**：

| 改这个文件 | = 改 PPT 的 | 红线 |
|---|---|---|
| `video-slicer/profiles/zh_main/pages_system_prompt.txt` | 内容 / 翻页节奏 / 文案逻辑 | 🔒 |
| `video-framework-render/render.py` 的 `PAGE_CSS`（竖版手写段） | 外观 / 字体 / 排版分层 | 🔒 |
| `video-framework-render/layouts/vertical.json` | 人像圆窗 / 字幕几何 | 🔒 |

- **没有用户明确指示，不要改上面任何一个、也不要新建/改用别的版式（`vertical_ppt` 卡片版已废弃，不要当默认）。** 想"优化"也不行——风格是用户的决定，不是工具的自由。
- 用户明确要改时：先改、出样片给用户看、用户拍板，再视为新定稿；并提示 **G4 逐帧基线需按新样式重冻**（页面像素/人像位置一变，旧基线必报红，属预期）。
- 之后可选用本引擎原子做遮名/片尾/标题条（见 `## 原子直调`）。

## 输出落点决策（跑任何原子前先定 OUT）

剪辑产物落哪，**先按项目语境路由，再跑原子**——映射真源是本 skill 目录下的 `output_routing.json`（`skills/video-clip/output_routing.json`；接新号 / 改某项目落点只改那份，不动本文件、不焊进引擎代码）。三步走：

1. **用户明确给了目标路径** → 一切以用户给的为准，直接用。
2. **否则判断「这次在为哪个项目干活」**（看源视频/任务路径、用户提到的 content_id 或项目名），对照 `output_routing.json` 的 `projects`：
   - 命中 **assistant_zh**（源在 `assistant_zh/` 下、提到 content_id 形如 `ZHC20260613_evc11_001`、某条 item、persona=zh_main/zh_assistant、或「把这条切片归位成成片」）→ 落 `assistant_zh/content/<persona>/items/<content_id>/`，**全部产物（中间切段/字幕/缓存 + 最终成片）都进这个 item 目录**，最终成片固定命名 `成片.mp4`（和该条的 `publish_copy.md` 同目录）。**不知道 content_id / persona 就先查 `assistant_zh/content/content_index.yaml`（按 title/topic/source 匹配）或问用户——绝不因为查不到就默认丢 var。**
   - 没命中任何项目（在 tools 仓自身做工具实验、调参、出样片）→ 落默认 `/Volumes/ExtSSD2601/AI_Assistant/tools/var/video-clip/<任务名>/`（git-ignored）。
3. 把定好的目录**显式**作为每个原子的 `OUT.mp4` / `--output` 传进去（原子都接受显式输出路径，无需改代码）；框架页走项目流程时用 `run_pipeline.py --out-root <目标根>` 覆盖默认 `out/`。

> 为什么单列这一门：旧版这里写「产物一律丢 tools/var」——对 assistant_zh 是错的，它的成片该和文案一起住进对应 item 目录。**落点是「为谁干活」的路由决策，不是固定常量。** 加新项目就往 `output_routing.json` 加一条 `projects` 条目，这一门和引擎都不用动。

## 原子直调（叠加 / 源适配；真源各引擎 capabilities.json）

```bash
ENG=/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-clip
PY=$ENG/.venv/bin/python    # 引擎 venv(含 pillow+opencv);首次:python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# —— 叠加（⑥收尾，按需）——
$PY $ENG/atoms/concat.py        OUT.mp4 --inputs a.mp4 b.mp4 c.mp4          # 直接拼接
$PY $ENG/atoms/prepend_hook.py  钩子.mp4 正文.mp4 OUT.mp4 [--flip 0.30 --trans slideleft]  # 前钩子+翻页转场
$PY $ENG/atoms/endcard.py       IN.mp4 OUT.mp4 --card /abs/card.png --seconds 3 --fade 0.5 # 片尾/后钩子卡
$PY $ENG/atoms/progress_bar.py  IN.mp4 OUT.mp4 --chapters 4 --index 2 --label "第二幕"     # 底部章节进度条
$PY $ENG/atoms/title_bar.py     IN.mp4 OUT.mp4 --text 标题 [--style label|bar]             # 顶部标题
$PY $ENG/atoms/subtitle_burn.py IN.mp4 OUT.mp4 --srt x.srt                                 # 烧药丸字幕
$PY $ENG/atoms/cover_frame.py   IN.mp4 cover.png --at 2 [--overlay title.png]              # 抽封面帧
# —— 源适配（录屏/带噪才挂）——
$PY $ENG/atoms/reframe_crop.py  --source X (--crop W:H:X:Y | --detect)                     # 裁切放大铺满(出 crop_vf)
$PY $ENG/atoms/name_mask.py     IN.mp4 OUT.mp4 --region 250x250+435+850 [--region ... --black]  # 盖UI/遮名(多块)
# —— 字幕/变速 ——
$PY $ENG/atoms/subtitle_ai_fix.py IN.srt OUT.srt --hint "..."                              # 字幕 LLM 纠错(需.env)
$PY $ENG/atoms/speed_adapt.py     IN.mp4 OUT.mp4 (--srt x.srt 自适应 | --fixed 1.2)        # 变速
$PY $ENG/atoms/face_locate.py     IN.mp4 --target 720x744                                  # 测脸/裁切(出JSON)
```
③粗剪/自检（`rough_cut`/`trim_silence`/`align_check`/`len_check`）、④字幕承重墙（`subtitle_align`/`subtitle_protect`/`script_clean`/`pages_gen`）、⑤铸造（`framework_reframe`/`compose`/`accelerate`/`subtitles`）一般由配方（`zh_clip_cut`/`zh_business`）按六环自动串，不单调；单调见各引擎 `capabilities.json`。

## 能力全表（六环分组·真源在各 capabilities.json）

| 环 | 引擎 | 原子 |
|---|---|---|
| **① 转录** | video-slicer | `transcribe`（火山主/阿里兜底）｜video-select `adapt_tencent`（腾讯会议逐字稿→words） |
| **② 选题/选段** 🛑人工review | video-select | `topic_select`→`generate_candidate`(出成片脚本)→`dedup`→`gates`→`score`；策略 `cut_sentence`/`cut_word`(句级·词级共存)；`select_clips_a`(方案A对照) |
| **③ 粗剪/收拾/变速** | video-clip | `rough_cut` `trim_silence` `speed_adapt`；自检门 `align_check` `len_check` |
| **④ 字幕承重墙** | video-slicer | `subtitle_align` `subtitle_protect` `srt_fix`(=subtitle_ai_fix) `script_clean` `pages_gen` |
| **⑤ 铸造/渲染** | video-framework-render | `framework_reframe` `compose` `accelerate` `subtitles` `reframe_locate` `raw`；版式 竖版 `vertical`/横版 `landscape` |
| **源适配**（录屏/带噪挂③） | video-clip | `reframe_crop` `name_mask` `denoise_voice` |
| **⑥ 叠加/收尾** | video-clip | `prepend_hook` `endcard` `progress_bar` `title_bar` `subtitle_burn` `concat` `cover_frame` `face_locate` |

- 配方（编排预设）：`zh_business`(PPT竖·🔒定稿) ｜`landscape_business`(PPT横) ｜`zh_clip_cut`(原视频风格) ｜`raw_quickcut`(极简) ｜`simple_concat` ｜`chaptered_growth`。
- 验证不回归：`python engines/video-compose/regression/run_regression.py [t0|t1|t2|t3|all]`（T3 含 G4 逐帧基线 + ①火山转录）。

## 硬边界

- 不改原片：所有原子输出到新路径，幂等可重跑。
- 产物按「输出落点决策」归位（tools 样片→`var/`；项目成片→该项目 item 目录，如 assistant_zh 的 `content/<persona>/items/<content_id>/`），绝不写原片目录。
- 长视频走全程时，**选题/成片脚本是人工 review 停顿点**，确认前不自动往下剪。
- 片尾卡/海报等卡片内容由调用方提供；本 skill/引擎不内置任何账号专属卡或二维码。
- PPT 风格（手写白板 + 圆窗 PIP）已定稿，未经用户明确指示不改 prompt/CSS/几何、不换版式（见「PPT 风格·定稿」）。
