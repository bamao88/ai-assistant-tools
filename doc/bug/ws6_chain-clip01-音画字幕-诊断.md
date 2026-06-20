# 诊断报告：`ws6_chain/clip_01` 音画对不上 + 字幕错乱

> 对象：`var/zh_main/ws6_chain/clip_01/成片.mp4`（zh_clip_cut 裁剪版最新流程出片）
> 状态：**诊断报告（未改代码）**。本文 = 完整流程复述 + 逐行代码环节追踪 + 每个毛病精确钉到哪一环。
> 写给非研发的 owner 看：每个技术名词都配大白话；传送带式逐工位讲。

---

## 一、现象（用户反馈）

1. **音频跟画面对不上**——确认：人声口型不齐 + 字幕也错位，两种都有。
2. **字幕有很多错字**。
3. **字幕显示了已经被切掉的内容**（视频和音频都没了，字幕还挂在屏上）。

核对了现场产物（账本 `cut_manifest.json`、字幕 `clip.srt` / `cast/zh.ass`）、各环节代码、源逐字转写 `words.json`。结论：**三个毛病出在三个不同环节，且会互相放大**。

---

## 二、这条片子的"配方单"（job）

出片用 `var/zh_main/ws6_chain_job.json`，关键开关：

| 字段 | 值 | 含义（大白话） |
|---|---|---|
| `speed` | 1.2 | 整体加速 1.2 倍 |
| `denoise` | false | 不抽干净人声，直接用录屏原声当参考 |
| `ai_fix` | false | 字幕**不过** AI 纠错，只过静态术语表 |
| `vocals` | （无） | 不喂现成干净人声 |
| 源视频 | `源视频_20260613_Agent评测体系.mp4` | 3 小时 20 分的 hevc 录屏 |
| `spec` | `clip_01_spec.json` | 选段清单 |
| `words` | `source/words.json` | 逐字转写（字级时间戳） |

---

## 三、传送带：每一个代码环节 + 病灶定位

入口总指挥：`engines/video-compose/clip_cut_run.py`。五道工位写死在 `clip_cut_run.py:36`：
`STAGES = ["rough_cut", "trim", "subtitle", "cast", "assemble"]`。

### 工位 A：③a 粗剪（`clip_cut_run.py:69-79` → `video-clip/atoms/rough_cut.py`）

**干的事**：从 3 小时源里把选中的 4 段切出来、硬切拼成一条"身子" `body.mp4`(107.766s)。

逐行：
1. `rough_cut.py:_flatten_spec`(92-98)：把 spec 选段摊平成有序 `keeps`（**源时间轴**）：
   `[[872.95,902.3],[905.35,921.3],[923.5,934.7],[10562.3,10613.5]]`。
2. `build`(68-89) → 每段调 `cut_seg`(49-53)。**⚠️ 病灶② 在此行**：
   ```
   ffmpeg -ss {s} -i {源} -t {时长} -vf "...fps=30..." ...
   ```
   `-ss` 放在 `-i` **前面** = "快寻"：跳到目标点附近最近的关键帧再解码。源是 hevc 录屏、实测 `avg_frame_rate≈29.84`（变帧率 VFR）。第 4 段要深寻到 **源 10562.3 秒（2h56m）**——VFR + 快寻 + 强制 `fps=30`，**这一段的声音和画面容易不是从同一时刻起步** → 人声口型对不上，且只在成片后半段（第4段）明显。
3. `concat_hard`(56-65)：concat 滤镜重编拼接。
4. `add_keep_op`(83)：把 4 段 keep 记进账本，标的是**源时间轴**。

> **关键伏笔**：账本记的是"打算从源哪几段切"，但第 2 步快寻**实际切出来的边界**可能差零点几秒。账本和实物对不齐，这偏差会顺传送带流到字幕环放大。

### 工位 B：③ 去噪 + 去静音 + 变速（`clip_cut_run.py:82-95`）

**B-1 取参考音轨**(83-89)：本 job `denoise:false`、无 `vocals` → `denoise_voice.py` 把 `body.mp4` **原声**抽成 `vocals.wav`（demucs 缺失就优雅跳过、直接抽原音轨）。

**B-2 去长静音**(`trim_silence.py`)：
- `detect_silences`(43-53)：在 `vocals.wav` 上找 >1.5s 静音。
- `keep_intervals`(56-68)：算"保留区间 keeps"，标的是**拼接后(assembled)时间轴**(0~107s)。
- `apply_keeps`(71-87)：`trim/atrim` 滤镜**精确**裁切，画和音**套同一套 keeps** → `trimmed.mp4`(95.11s) 与 `vocals_trimmed.wav` 内部同步（这一环不背音画锅）。
- `add_keep_op`(114)：trim keeps 记进账本，**assembled 时间轴**。

**B-3 固定变速**(`speed_adapt.py:run_fixed` 38-64)：
```
[0:v]setpts=PTS/1.2[v]; [1:a]atempo=1.2[a]   # 画音都1.2倍，-shortest
```
画音同倍速、`add_speed_op`(59) 记 factor=1.2（这一环也同步）。

> **此处出现"两套时间轴"**：`words.json`（字幕的字时间）是**源时间轴**(10588s 这种)；trim keeps 是**assembled 时间轴**(0~107s)。字幕环要把源时间换算成 assembled 才能查"有没有被去静音删掉"——**而这个换算完全依赖工位 A 账本记的 rough_cut 边界准不准**。伏笔在这里接上。

### 工位 C：④ 字幕重放（`clip_cut_run.py:100-116` → `video-slicer/.../subtitle_align.py`）**← 病灶①+③都在这**

**核心函数 `build`(133-161)**，逐行：
1. `keeps = rough_cut_keeps(ops)`(136)：只取 rough_cut 的段，用来挑句子。
2. `derive_sent_indices`(71-80)：`words.json` 里和这 4 段有重叠的句子都纳入。
3. `sent_phrases`(83-104)：每句按标点拆短语、给每个字配源时间（实测这条片字数对得上、没串）。
4. **`remap_time`(36-47 / 同源 `_manifest.py:70-84`)**：把短语 begin/end 一路套 `源→rough_cut→trim→speed`。
   - `_through_keeps`(60-67)：落保留区→映射；**落删除区→返回 `None`**。
   - **⚠️ 病灶①-第1颗螺丝**（`subtitle_align.py:149`）：
     ```python
     if bb is None: continue   # 短语开头落删除区 → 整条字幕直接丢弃
     ```
     因工位 A 账本边界有偏差（病灶②连带），源句换算到 assembled 后**砸进 trim 删掉的缝里** → 这条字幕被丢。实测**源句1892「具体根据咱们客户情况…对吧」就这样消失了**。
5. **⚠️ 病灶①-第2颗螺丝**（`subtitle_align.py:157-158`）：
   ```python
   for i in range(len(cues)-1):
       cues[i][1] = cues[i+1][0]   # 每条结尾延到下一条开头·无上限
   ```
   本意补字幕间小缝。**但没有任何上限**：上面整条被丢出一个大洞后，前一条「要不了300还有更便宜的」被一路拉长 **14 秒**(`clip.srt` 第27条 00:56→01:10) 去补，直到下一条幸存字幕「卷死同行了」才接上。这 14 秒画面音频早讲到别处了——**这就是"字幕显示被切掉的内容、和音视频对不上"**。

**⚠️ 病灶③（错字·配置）**：`clip_cut_run.py:106` `if job.get("ai_fix")` = false → **跳过 LLM 纠错**，只在 `build`(143-144) 用静态术语表 `fixes.json` 替换。实测 `fixes.json` 已把 a景→Agent、Workbody→Workflow、接入到MC接入到→接入到 等修对，所以**文字大多其实对**；残留的只是没登记进术语表的词。"字幕全错"的观感主体其实是病灶①的时间错位。

### 工位 D：⑤ 铸造（`clip_cut_run.py:120-128`）

`subtitles_cli` 把 `clip.srt` 渲成药丸 `cast/zh.ass` → ffmpeg `ass=` 滤镜烧进画面 `body_subbed.mp4`，音轨 `-c:a copy` 原样搬。**只是把错误字幕忠实烧上去，不产生新错。**

### 工位 E：⑥ 组装（`clip_cut_run.py:132-143`）

`title_bar.py` 加标题 → `prepend_hook.py` 前面拼开篇钩子 + 翻页转场 → `成片.mp4`。

### 自检门（`clip_cut_run.py:146-152`）

`len_check`(时长) + `align_check`(门A切点/门D字幕/门S画音流时长)。**没拦住病灶①**——14 秒卡屏字幕在"时长一致/切点对"层面是合法的，门检测不到"字幕跨洞拉长"这种逻辑错。

---

## 四、一图钉死：毛病 ↔ 代码环节

| 你的反馈 | 出问题的工位 | 精确代码位置 | 性质 |
|---|---|---|---|
| 字幕卡屏14s / 显示切掉内容 | **C ④字幕** | `subtitle_align.py:149`(落删除区整条丢) + `:157-158`(无上限拉长补洞) | 逻辑缺陷·治本改这两处 |
| 人声口型对不上 | **A ③a粗剪** | `rough_cut.py:52` `-ss` 前置快寻 + VFR源 + 第4段深寻 | 寻址精度·治本改精确寻址 |
| 字幕错字 | **C ④字幕(配置)** | `clip_cut_run.py:106` `ai_fix:false`，只剩 `fixes.json` 静态兜底 | 配置·开 ai_fix 或补术语表 |
| （放大器）A 不准 → C 漂得更厉害 | A→C 耦合 | 账本 rough_cut 边界(源轴)与实物不齐 → C 换算 source→assembled 偏移 → 更易踩删除缝 | 根上要让账本边界=实物边界 |

**一句话总结**：真正的"承重墙裂缝"是 **C 工位 `subtitle_align.py` 的两颗螺丝（落删除区的处理 + 无上限 seam-merge）**；**A 工位的深寻精度**既单独造成口型漂、又顺传送带把 C 的漂移放大。D/E 只是忠实执行，不背锅。

---

## 五、实锤证据（实测数字）

- **症状①**：`clip.srt` 第 27 条「要不了300还有更便宜的」00:56.4→01:10.6 **撑 14 秒**（其余每条 1~3 秒）；源句 1892(源 10589~10598s) 在 SRT 中**完全消失**。
- **症状②**：源 `avg_frame_rate≈29.84`（VFR，标称 30）；第 4 段从源 10562.3s 深寻；段4=成片后半（约 46s 后）。`final.mp4` 总时长画 79.196s / 音 79.189s（差 6ms，说明问题不是总长漂移，而是段内深寻起步不齐）。
- **症状③**：`fixes.json` 已覆盖 a景/A景→Agent、Workbody→Workflow、接入到MC接入到→接入到、highagentagentsphere→HiAgent、AgentSphere 等；残留 = 未登记词。

---

## 六、修复方向（本次未动手，供判断下一步）

1. **C ④字幕（治本·优先）**：
   - 给"无缝衔接"(`subtitle_align.py:157-158`)加**上限**（单条不超过 N 秒，或遇"中间整句被删"时不跨洞拉长，宁可留空/断开）。
   - "落删除区"的短语(`:149`)改为**就近裁到删除边界**而非整条丢弃，避免留洞。
2. **A ③a粗剪（治音画）**：粗剪深寻改**精确寻址**（`-ss` 放到 `-i` 之后精确解码，或先精切再重编），消除 VFR 深寻漂移；并把**实际段边界回写账本**让 C 换算对齐。
3. **③↔④ 时间轴自检**：补一道门，校验"账本段边界"与"产物实际段边界"一致（超阈值报红），从根上防换算漂移。
4. **③ 错字**：打开 `ai_fix` 走 LLM 纠错，或继续补 `fixes.json`。

---

## 七、复现/确认清单

- **确认①**：`grep` `clip.srt` 找时长 >3s 的字幕条 → 第27条 14s；对照 `words.json` 句1892 在账本 `trim_silence` keeps 的落点，确认砸进删除缝。
- **确认②**：逐帧看 `final.mp4` 第 4 段（约 46s 后）人声口型偏移；对比 `body.mp4` 第 4 段是否已带漂移（定位粗剪还是后续引入）。
- **确认③**：核对 `clip.srt` 文字 vs `words.json` 原文，列出 `fixes.json` 未覆盖的残留错字。

---

## 附：涉及文件清单

| 角色 | 路径 |
|---|---|
| 总指挥（链式执行器） | `engines/video-compose/clip_cut_run.py` |
| ③a 粗剪 | `engines/video-clip/atoms/rough_cut.py` |
| ③c 去静音 | `engines/video-clip/atoms/trim_silence.py` |
| ③d 变速 | `engines/video-clip/atoms/speed_adapt.py` |
| 账本数据模型/重放 | `engines/video-clip/atoms/_manifest.py` |
| ④ 字幕重放（病灶核心） | `engines/video-slicer/video_slicer/subtitle_align.py` |
| 本次 job | `var/zh_main/ws6_chain_job.json` |
| 现场产物 | `var/zh_main/ws6_chain/clip_01/`（`cut_manifest.json` / `clip.srt` / `cast/zh.ass` / `成片.mp4`） |
| 源转写 | `var/zh_main/0618test/source/words.json` |
| 术语表 | `var/zh_main/0618test/clip_01_…/fixes.json` |
