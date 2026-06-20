# 诊断 + 修改计划：`ws6_chain/clip_01` 音画对不上 + 字幕错乱

> 对象：`var/zh_main/ws6_chain/clip_01/成片.mp4`（zh_clip_cut 裁剪版最新流程出片）。
> 状态：**诊断 + 重构计划（未改代码）**。写给非研发 owner：大白话 + 逐阶段说清。
>
> **这份文档怎么读**：先看 §1「现状管线总表」搞清现在每个阶段在干嘛、产出什么文件、坏在哪；
> 再看 §3「目标管线总表」看重构后顺序怎么变、每阶段产出什么、达成什么目标。
> （之前出问题的根因之一就是**流程不透明、看不到每阶段产出**——本文用两张总表把它钉死。）

---

## 〇、现象（owner 反馈）

1. **音频跟画面对不上**（人声口型不齐）。
2. **字幕有很多错字**。
3. **字幕显示了已经被切掉的内容**（视频音频都没了，字幕还挂屏上）。

实测定位（跑 `align_check` 自检门）：音画问题在 **⑥组装**、字幕问题在 **④字幕**，两者独立；**③粗剪此前被误判，已排除**。

---

## 一、现状管线·逐阶段总表（出问题的版本）

入口 `engines/video-compose/clip_cut_run.py`，顺序写死：`rough_cut → trim → subtitle → cast → assemble`。

| # | 阶段（做什么） | 调用 | **产出文件** | 实测时长/状态 | 现存 bug |
|---|---|---|---|---|---|
| 1 | ③a **粗剪**：从3h源切选中4段、硬切拼成身子 | `rough_cut.py` | `body.mp4`；账本 `cut_manifest.json`(记 rough_cut keeps·源时间轴) | 107.766s | ✅ 无（音画齐） |
| 2 | ③ **取人声**：抽 body 原声当去静音参考 | `denoise_voice.py` | `vocals.wav` | 107.7s | ✅ 无 |
| 3 | ③c **去长静音**：删>1.5s停顿，画音同一刀 | `trim_silence.py` | `trimmed.mp4` + `vocals_trimmed.wav`；账本记 trim keeps(assembled时间轴) | 95.11s | ✅ 无（画音齐） |
| 4 | ③d **变速**：画音都1.2倍 | `speed_adapt.py` | `final.mp4`（**正片·还没字幕**）；账本记 speed factor | 79.196s，**门S PASS(差7ms)** | ✅ 无（音画齐） |
| 5 | ④ **字幕搬时间**：把每个字从源时间换算到成片时间 | `subtitle_align.py` | `clip.srt` | 31条 | ⚠️**bug①**：换算落进删除区→整条丢；前一条无上限拉长补洞→卡屏14s |
| 5b | ④ **字幕改文字**（仅 `ai_fix:true`，本次=false 跳过）：术语表+LLM只改字 | `subtitle_ai_fix.py`+`subtitle_protect.py` | `clip.aifix.srt`→`clip.final.srt` | 本次未跑 | ⚠️**bug③**：没开→残留 ASR 错字（已被静态 `fixes.json` 修掉大部分） |
| 6 | ⑤ **铸造**：渲药丸字幕 + 烧进正片 | `subtitles_cli.py`+ffmpeg | `cast/zh.ass` + `body_subbed.mp4` | 79.2s | 忠实烧（不产生新错） |
| 7 | ⑥ **加标题** | `title_bar.py` | `titled.mp4` | 画79.167/音79.189 | ✅ 无 |
| 8 | ⑥ **拼钩子+翻页转场** | `prepend_hook.py` | `成片.mp4`（**最终交付**） | 84.97s，**门S FAIL(差0.510s)** | ⚠️**bug②**：钩子自身画(5.8)≠音(5.208)，转场画/音两个时钟→正片人声超前0.5s |
| 9 | **自检门** | `len_check.py`/`align_check.py` | （只打印） | — | ⚠️**bug④**：门S 是软调用、FAIL 不停管线，带病照样出片 |

---

## 二、四个 bug 的实测定位（钉死在阶段上）

| bug | 阶段 | 精确代码位置 | 实测证据 |
|---|---|---|---|
| ② 人声口型对不上 | ⑥ 拼钩子 | `prepend_hook.py`：`xfade` 按画面长度定位、`acrossfade` 按音频末尾接缝＝两个时钟 | `成片.mp4` 门S **FAIL 0.510s**；钩子画5.8/音5.208 |
| ① 字幕卡屏14s/显示切掉内容 | ④ 字幕搬时间 | `subtitle_align.py:149`(落删除区整条丢) + `:157-158`(无上限拉长补洞) | `clip.srt` 第27条 00:56→01:10 撑14s；源句1892消失 |
| ③ 字幕错字 | ④ 字幕改文字(配置) | `clip_cut_run.py:106` `ai_fix:false` | `fixes.json` 已修大部分，残留=未登记词 |
| ④ 门不刹车 | 自检门 | `clip_cut_run.py:149` `align_check` 软调用不 raise | 门S FAIL 仍出片 |

> **③粗剪 `-ss` 已排除**：`final.mp4` 门S PASS（差7ms·编码尾巴非错位）。重编码模式 FFmpeg 默认 accurate_seek 帧精确。

---

## 三、目标管线·逐阶段总表（重构后）

**核心改动**：把"字幕搬时间 + 烧字"**提到去静音/变速之前**——字幕烧成画面像素后，后面对视频怎么切、字幕一模一样跟着切（与 PPT 流程同构、与你说的"先做完脚本再后处理"一致）。

| # | 阶段（做什么） | **产出文件** | 该阶段达成目标 |
|---|---|---|---|
| 1 | ③a **粗剪**：切4段拼身子 | `body.mp4`(assembled时间轴)；账本只记 rough_cut | 身子干净、音画齐（现状已满足） |
| 2 | ④ **字幕搬时间**：只做 `源→assembled` **一次**简单换算 | `clip.srt`(assembled时间轴) | 字幕时间一次锁定·**无丢句、无超长条**（删多级 remap + 删丢弃 + 删无上限补洞） |
| 3 | ④ **字幕改文字**：术语表+LLM(可选) **严格1:1 只改字** | `clip.final.srt` | 错字修对·条数/时间不变（现有逻辑已对，保留） |
| 4 | ⑤ **烧字幕**：把字幕烧进身子 | `body_subbed.mp4`(assembled·**带字幕像素**) | 画+字幕合体成一个不可分割对象 |
| 5 | ③ **取人声** | `vocals.wav` | 去静音参考 |
| 6 | ③c **去长静音**：在**带字幕**视频上删停顿，画+音+字幕**同一刀** | `trimmed_subbed.mp4` + `vocals_trimmed.wav` | 三轨一起切·门S PASS·**屏上字幕永远=此刻在讲的话** |
| 7 | ③d **变速**：画+音+字幕都1.2倍 | `final_subbed.mp4`（带字幕正片） | 三轨同倍速·门S PASS |
| 8 | ⑥ **加标题** | `titled.mp4` | 不动时间 |
| 9 | ⑥ **拼钩子**：进转场前强制片段**画音严格等长**、转场**同一基准** | `成片.mp4`（最终交付） | **门S PASS**（音画不再超前） |
| 10 | **自检门（硬红线）**：每个动时间轴的原子出口跑门S，FAIL **即停** | — | 带病片**出不了厂** |

---

## 四、核心原则（贯穿全流程的硬不变量——这次要结构性落实，不再打补丁）

> owner 反复强调、之前一直没落实到位的那条：

- **INV-1 片段良构**：任一片段产出即 `画时长 == 音时长`（字幕若已存在也共享同一时间线）。
- **INV-2 整体操作**：任何"动时间轴"的操作（拼接/转场/裁剪/变速）对一个片段**只用同一个时间映射**作用到所有轨——**绝不允许视频一个时钟、音频另一个时钟**（这正是 prepend_hook 的病根）。
- **INV-3 硬门**：每个动时间轴的原子边界跑门S，`画音不等长`超阈值**直接报错停管线**，让原则没法再悄悄回退。

---

## 五、修完的总验收目标

1. `align_check --body final_subbed.mp4` 和 `--body 成片.mp4` **都门S PASS**。
2. `clip.srt` **无时长 >3s 的条、无被丢源句**；逐帧抽查第4段口型对齐。
3. 故意喂一个画≠音的钩子，门S **红线停管线**（验 INV-3 真生效）。
4. 跑回归 `engines/video-compose/regression/run_regression.py t3`（含 G4 + 门S）不回退。

---

## 待改文件 + 参考实现

| 角色 | 路径 |
|---|---|
| 总指挥（改顺序+门S硬raise） | `engines/video-compose/clip_cut_run.py` |
| ④字幕搬时间（简化为单次换算） | `engines/video-slicer/video_slicer/subtitle_align.py` |
| ⑥拼钩子（片段等长+转场同基准） | `engines/video-clip/atoms/prepend_hook.py` |
| 自检门（门S 作可 raise 红线） | `engines/video-clip/atoms/align_check.py` |
| ③去静音/变速 | `engines/video-clip/atoms/{trim_silence,speed_adapt}.py` |
| **参考A：单清单驱动** | `~/Downloads/videocut-zh/`（`scripts/cut_clip.py` trim/atrim+concat；`cut_build_mac.py` `out_time()`） |
| **参考B：先烧字幕后变速** | `engines/video-framework-render/.../render.py`（`make_subtitles`→`compose`烧→`accelerate`变速） |
| 同步更新 | `doc/video-skill-architecture.md`（顺序/承重墙变更） |
