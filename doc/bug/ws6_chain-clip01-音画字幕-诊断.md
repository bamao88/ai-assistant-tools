# 诊断报告 + 修改计划：`ws6_chain/clip_01` 音画对不上 + 字幕错乱

> 对象：`var/zh_main/ws6_chain/clip_01/成片.mp4`（zh_clip_cut 裁剪版最新流程出片）
> 状态：**诊断 + 重构计划（未改代码）**。
> 写给非研发的 owner：每个技术名词都配大白话；传送带式逐工位讲。
>
> ⚠️ **重要修订（2026-06-20）**：早先把"音画不同步"归因到 ③粗剪的 `-ss 快寻`，**经实测推翻**。
> 真凶是 ⑥组装的 `prepend_hook`（拼钩子转场）。详见 §三-病灶② 与 §五 实测。

---

## 一、现象（用户反馈）

1. **音频跟画面对不上**——人声口型不齐。
2. **字幕有很多错字**。
3. **字幕显示了已经被切掉的内容**（视频音频都没了，字幕还挂在屏上）。

核对了现场产物、各环节代码、源逐字转写，并**实测跑了 `align_check` 自检门**。结论：**三个毛病出在两个不同环节**——音画问题在⑥组装、字幕问题在④字幕——彼此独立。

---

## 二、这条片子的"配方单"（job `var/zh_main/ws6_chain_job.json`）

| 字段 | 值 | 含义（大白话） |
|---|---|---|
| `speed` | 1.2 | 整体加速 1.2 倍 |
| `denoise` | false | 不抽干净人声，直接用录屏原声当参考 |
| `ai_fix` | false | 字幕**不过** AI 纠错，只过静态术语表 |
| `vocals` | （无） | 不喂现成干净人声 |
| `hook` | `开篇钩子_打字效果_人脸版.mp4` | 片头钩子（**画 5.800s / 音 5.208s，自身画音差 0.59s**） |
| 源视频 | `源视频_20260613_Agent评测体系.mp4` | 3h20m 的 hevc 录屏 |
| `spec` / `words` | `clip_01_spec.json` / `source/words.json` | 选段清单 / 逐字时间戳 |

---

## 三、传送带：每一个代码环节 + 病灶定位

入口总指挥 `engines/video-compose/clip_cut_run.py`，五道工位写死在 `:36`：
`STAGES = ["rough_cut", "trim", "subtitle", "cast", "assemble"]`。

### 工位 A：③a 粗剪（`clip_cut_run.py:69-79` → `video-clip/atoms/rough_cut.py`）
从 3h 源里把选中 4 段切出来、硬切拼成 `body.mp4`(107.766s)。`cut_seg`(49-53) 用 `-ss` 前置 + **libx264/aac 重编码**。
> **此前的误判已撤回**：`-ss` 前置在**重编码**模式下，FFmpeg 2.1+ 默认 `accurate_seek`，会"快寻到关键帧→解码→丢弃多余帧→从精确点输出"，一般是帧精确的。实测 `final.mp4` 门S PASS（见§五）证明这条链音画是齐的。**粗剪不背音画锅。**

### 工位 B：③ 去噪 + 去静音 + 变速（`clip_cut_run.py:82-95`）
- 取参考音轨：`denoise:false` 无 `vocals` → `denoise_voice.py` 抽 `body.mp4` 原声成 `vocals.wav`。
- `trim_silence.py`：在 `vocals.wav` 上找 >1.5s 静音 → 算保留区间 keeps（**assembled 时间轴**）→ `trim/atrim` 滤镜**精确**裁切、画音套同一刀 → `trimmed.mp4`(95.11s)。记账 `add_keep_op`(114)。
- `speed_adapt.py:run_fixed`：`[0:v]setpts/1.2;[1:a]atempo 1.2`、画音同倍速 → `final.mp4`(79.196s)。
> **这一环画音也同步**（final.mp4 门S PASS）。但它埋了字幕的雷：trim keeps 是 **assembled 时间轴**、而字幕的字时间是**源时间轴**，两套对不上 → 工位 C 被迫"换算"。

### 工位 C：④ 字幕重放（`clip_cut_run.py:100-116` → `video-slicer/.../subtitle_align.py`）**← 病灶①（字幕）+③（错字）**
`build`(133-161)：取完整转录 → 按 rough_cut 选句 → 按标点拆短语 → **`remap_time` 把每个短语 begin/end 一路套 `源→rough_cut→trim→speed`**。两颗坏螺丝：
- **⚠️ 病灶①-1**（`subtitle_align.py:149`）`if bb is None: continue`：短语换算后落进 trim 删掉的缝里 → **整条字幕被丢**。实测源句1892「具体根据咱们客户情况…对吧」就这样消失。
- **⚠️ 病灶①-2**（`subtitle_align.py:157-158`）`cues[i][1]=cues[i+1][0]`：**无上限**把前一条结尾延到下一条开头。上面丢出一个洞后，前一条「要不了300还有更便宜的」被拉长 **14 秒**(`clip.srt` 第27条 00:56→01:10) 补洞 → 字幕卡屏、显示已切掉内容。
- **⚠️ 病灶③（错字·配置）**：`clip_cut_run.py:106` `ai_fix:false`，只靠静态术语表 `fixes.json`（已把 a景→Agent、Workbody→Workflow 等修对）→ **文字大多其实对**，残留＝未登记词。"字幕全错"的观感主体是病灶①的时间错位。

### 工位 D：⑤ 铸造（`clip_cut_run.py:120-128`）
`subtitles_cli` 渲药丸 `cast/zh.ass` → ffmpeg `ass=` 烧进 `final.mp4` → `body_subbed.mp4`，音轨 `-c:a copy`。**只是忠实烧字，不产生新错。**

### 工位 E：⑥ 组装（`clip_cut_run.py:132-143`）**← 病灶②（音画）**
`title_bar.py` 加标题 `titled.mp4`（实测画79.167/音79.189，齐）→ `prepend_hook.py` 拼钩子 + 翻页转场 `成片.mp4`。
- **⚠️ 病灶②**：`prepend_hook` 处理一个**自身画≠音**的钩子（画 5.800s / 音 5.208s）时，**视频转场 `xfade` 按"画面长度"定位**(`offset=hook_dur-flip`)、**音频转场 `acrossfade` 按"音频末尾"接缝**，两者基准不一致，那 0.59s 漏了出来。实测 `成片.mp4` 门S **FAIL，画音差 0.510s**（正片人声超前）→ 这就是你看到的"人声口型对不上"。
- `_norm`(28-44) 本想用 `apad`+`-shortest` 把钩子音频补到画面长度治本；**隔离复现里它确实补成功了（音→5.781s）**，但端到端 `成片` 仍 FAIL——说明问题不在 `_norm` 单步，而在 `xfade/acrossfade` 两条轨**基准不统一**这一步，钩子画音差没被吸收干净。

### 自检门（`clip_cut_run.py:146-152`）
`len_check` + `align_check`(门A/D/S)。**门S 其实抓到了 `成片` 的 0.510s FAIL**，但 `align_check` 是 `subprocess.run` **软调用、不 raise**，管线没被它拦停，照样出片。→ 门没起到"红线刹车"作用。

---

## 四、一图钉死：毛病 ↔ 代码环节（已修订）

| 你的反馈 | 出问题的工位 | 精确代码位置 | 实测 |
|---|---|---|---|
| 人声口型对不上 | **E ⑥组装 prepend_hook** | `prepend_hook.py` xfade(按画长)/acrossfade(按音尾) 基准不一；钩子自身画5.8/音5.208 | `成片.mp4` 门S **FAIL 0.510s** |
| 字幕卡屏14s / 显示切掉内容 | **C ④字幕** | `subtitle_align.py:149`(落删除区整条丢)+`:157-158`(无上限拉长补洞) | `clip.srt` 第27条撑14s；句1892消失 |
| 字幕错字 | **C ④字幕(配置)** | `clip_cut_run.py:106` `ai_fix:false` | `fixes.json` 已修大部分 |
| 门没刹车 | 自检门 | `clip_cut_run.py:149` `align_check` 软调用不 raise | 门S FAIL 但照样出片 |

**~~粗剪 `-ss`~~ 已排除**：`final.mp4` 门S PASS（差 7ms）。

---

## 五、实测证据（`align_check` + `ffprobe`）

```
final.mp4  门S 画音流时长: 视频79.196 / 音频79.189  差+0.007s  → PASS   ← 剪辑链音画齐
成片.mp4   门S 画音流时长: 视频84.967 / 音频84.457  差+0.510s  → FAIL   ← 钩子转场引入desync
钩子原文件  画5.800s / 音5.208s（自身差0.592s）
钩子过_norm 画5.800s / 音5.781s（apad补齐成功 — 说明_norm单步没问题）
clip.srt   第27条「要不了300还有更便宜的」00:56.4→01:10.6 撑14s；源句1892在SRT中消失
```

---

## 六、修改计划（本次未动手，按你的方向 + 两个"不出问题"的现成方案）

> 我对照了你点名的 **videocut-zh**(`~/Downloads/videocut-zh`) 和本仓 **PPT框架页流程**(`zh_business`)——它俩都**不出**这两个毛病。原因正好印证你的判断。

### 它俩为什么不出问题（结论先行）

| | videocut-zh | PPT框架页(zh_business) | 当前 clip_cut（出问题） |
|---|---|---|---|
| 真源 | **一份 keep 清单**同时驱动剪视频和出字幕 | 一份 SRT，**先烧进整段视频**再处理 | 剪辑清单 + 转录**两份**，中间靠 remap 拼 |
| 字幕与画面 | 同一清单、`out_time()` 机械换算一次 | **字幕先烧成画面像素**，之后跟着视频一起被切 | 视频先改、字幕**事后**重算到新时间轴 |
| 顺序 | 选词→定 keep→（同一刀）切视频+出字幕 | 渲染→**做字幕→烧进视频**→**之后**才变速/切 | 切+去静音+变速→**之后**才算字幕→烧 |
| 变速/去静音 | 没有 | **在"已烧字幕"的视频上**做，画音字一起切 | 在"还没字幕"的视频上做，逼出 remap |
| 音画同步 | 构造上锁死 | 构造上锁死 | 多级 remap，易漂 |

**一句话**：你说的"**先把带时间戳的脚本（含字幕）做完、字幕烧进画面，之后再去精减/去噪/变速**"——**PPT 流程就是这么干的，所以它从不音画/字幕错位**。当前 clip_cut 把顺序搞反了（先动视频、后补字幕），才逼出脆弱的 remap。

### 计划 A：字幕重构（核心·治本）——把工位 C 提到工位 B 前面

**新顺序**（你要的"B、C 交换"）：
```
③a 粗剪(切选段拼身子)
 → ④ 字幕(align：只做 源→assembled 一次简单换算 + LLM只改字不改时不增减)
 → ⑤ 烧字幕(把字幕烧成 assembled 视频的像素)
 → ③c 去静音 + ③d 变速(在"已带字幕"的视频上做，画+音+字幕同一刀一起切)
 → ⑥ 组装(标题+钩子)
```
**好处（为什么这样就根治）**：
1. 字幕只需换算**一道**（源→assembled，就是 rough_cut 那份 keep，边界已知、不经过 trim/speed），**`remap_time` 那串多级重放、落删除区返回 None、无上限 seam-merge 全部不再需要**——病灶①两颗坏螺丝直接消失。
2. 字幕一旦烧成像素，后面去静音/变速对视频怎么切，字幕就**一模一样**跟着切（它就是画面的一部分）——**音画字三者构造上锁死，永不漂**。这正是 PPT 流程的做法（`render.py`：先 `make_subtitles`+`compose` 烧字，再 `accelerate` 变速）。
3. 去静音若切掉某句中间的停顿，烧在画面上的那句字幕也一起被切短——**屏上字幕永远等于此刻在讲的话**，不会再有"显示已切掉内容"。

**落地要点**：
- `subtitle_align` 简化为只读 rough_cut keeps 做一次 `源→assembled` 换算（删掉对 trim/speed 的重放、删掉 `:149` 丢弃 + `:157-158` 无上限补洞）。
- `clip_cut_run.py` 的 `STAGES` 与执行顺序调整为 `rough_cut → subtitle → cast(烧) → trim → speed → assemble`；账本只需记 rough_cut（trim/speed 不再参与字幕换算）。
- 字幕文字订正（LLM `subtitle_ai_fix` / 术语表 / 别动清单）**严格 1:1**：只换字，不改时间、不增减条目（**这条现有代码已做对，保留**）。

### 计划 B：音画同步（prepend_hook）——独立小修

- 让钩子进 `prepend_hook` 前**画音严格等长**：要么把钩子音频补齐到画面长度（或反之裁画到音长），要么让 `xfade` 的 `offset` 与 `acrossfade` 的接缝**用同一个基准**（按规整后的"画音等长"值）。目标：`成片` 门S 由 FAIL→PASS。
- **把 `align_check` 门S 改成硬红线**：`clip_cut_run.py:149` 现在是软调用，应在 FAIL（画音差 > 阈值）时**直接报错停管线**，不许带病出片。

### 计划 C：错字（可选）
打开 `ai_fix:true` 走 LLM 1:1 纠错，或继续往 `fixes.json` 补未登记词。

---

## 七、复现/验证清单

- **音画**：`align_check.py --body final.mp4`（应 PASS）vs `--body 成片.mp4`（现 FAIL 0.510s）；修完 `prepend_hook` 后 `成片` 应 PASS。
- **字幕**：`grep` `clip.srt` 时长 >3s 的条（现有第27条14s）；重构后应无超长条、无被丢句。
- **错字**：核对 `clip.srt` vs `words.json`，列 `fixes.json` 未覆盖词。

---

## 附：参考实现与文件清单

| 角色 | 路径 |
|---|---|
| 总指挥 | `engines/video-compose/clip_cut_run.py` |
| ③a 粗剪 | `engines/video-clip/atoms/rough_cut.py` |
| ③c 去静音 / ③d 变速 | `engines/video-clip/atoms/{trim_silence,speed_adapt}.py` |
| 账本读写/重放 | `engines/video-clip/atoms/_manifest.py` |
| ④ 字幕重放（病灶①③核心） | `engines/video-slicer/video_slicer/subtitle_align.py` |
| ⑥ 拼钩子（病灶②核心） | `engines/video-clip/atoms/prepend_hook.py` |
| 自检门 | `engines/video-clip/atoms/align_check.py` |
| **参考A：单清单驱动** | `~/Downloads/videocut-zh/`（`scripts/cut_clip.py` trim/atrim+concat；`work_*/cut_build_mac.py` `out_time()` 机械换算） |
| **参考B：先烧字幕后变速** | `engines/video-framework-render/video_framework_render/render.py`（`make_subtitles`→`compose`烧→`accelerate`变速） |
| 现场产物 | `var/zh_main/ws6_chain/clip_01/` |
