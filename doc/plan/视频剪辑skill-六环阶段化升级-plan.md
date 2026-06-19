# 视频剪辑 skill 升级：把整条流程讲清楚 + 阶段化重构

> 写于 2026-06-19。读者是不读代码的 owner——先讲"是什么/为什么"，每个技术名词都配一句大白话。
> 真源文档：[`../video-skill-architecture.md`](../video-skill-architecture.md)（改完同一次同步更）。本计划合并并取代两份分计划：
> [`录屏竖版切片-流程固化-plan.md`](./录屏竖版切片-流程固化-plan.md) 和 [`clip-cut-recipe-plan.md`](./clip-cut-recipe-plan.md)。

---

## Context（为什么做这件事）

这几天剪"录屏裁剪版竖版切片"（区别于已冻结的 PPT 框架页版 `zh_business`），反复栽两件事：

1. **音画对齐**（最痛、17 条踩坑里最多）：字幕和声音对不上、修好又复发。根因——字幕被当成"第二样要事后去对齐的东西"，从 3 小时大转写里硬扛着穿过"切段→去静音→加速"，链条越长越脆。
2. **流程散、阶段认知不清**：去长静音、去背景音、源级裁切挡块这些做法散在 `var/zh_main/0618test/` 的临时脚本里，没进引擎。更深的问题——**我们的原子是按"引擎(代码住哪)"组织的，不是按"剪辑到了哪个阶段"组织的**，看不出哪个原子属于哪阶段、哪个必须、哪个是为某种源文件特设的。没有阶段认知，新能力就只能往 `video-clip` 里乱堆。

**本次目标**：先把**整条剪辑流程讲清楚**（这是这份计划的主体），在清晰的流程/阶段认知上，把所有原子（已有+新增）按阶段归位、标注必须/可选/源类型；用"同一把剪刀"的目标设计从根上根治对齐；端到端落成新配方 `zh_clip_cut`（= ⑤铸造选"裁剪版"风格）。

> **关于 `zh_business`（PPT 框架页版）**：它**同属这条六环主链**，只是⑤铸造选了"PPT 风格"（重绘设计页+圆窗），和"裁剪版"风格并列——**不是另一条独立的线**。所谓"冻结"只指：它的渲染实现 + 视觉输出已定型，有一条 **G4 基线（逐帧/逐字节不许回归）**；本轮**不改它的渲染代码**，但概念上它就是⑤的一个风格。

---

## 零、业务流程：这条线到底在干什么（真实场景）

- **输入**：张和一段 3.3 小时**录屏**大录像（画面=PPT + 右下角他本人小窗 + 外层黄色标题条）+ 整条逐字稿 + 金标准选出来的候选脚本。**源类型 = 录屏**。
- **要出**：每条候选剪成可发布的**竖版切片成片**（发视频号 / 小红书）。两种风格：
  - **裁剪版**：把录屏本身收拾干净——裁切放大铺满 + 盖掉多余 UI + 烧药丸字幕。（本轮要做成熟的就是这条）
  - **PPT 框架页版**：⑤铸造时选"PPT 风格"——按内容重绘设计页 + 人脸抠成圆窗。它**就在这条六环主链里**（= `zh_business`），只是⑤换个风格；"冻结"指它渲染已定型、G4 基线不许回归，本轮不改其渲染。
- **走的就是下面六环主链**：① 整条转写 → ② 从 3.3h 里选 6–10 段金句（开篇去转折）→ ③ 裁剪（粗剪拼身子 → 去长静音 → 1.2x）→ ④ 字幕（搬时间 + AI 改 ASR 错词）→ ⑤ 铸造（裁剪版 / 钩子片）→ ⑥ 组装（钩子翻页 + 标题）。
- **源适配怎么挂**：因为源是录屏 → ③粗剪时挂 `reframe_crop`（裁外框）+ `name_mask` 多块（盖菜单栏/Upgrade/缩略图）；若录屏带"叮"提示音 → 挂 `denoise_voice`。换成干净口播的源，这些就都不挂。
- **痛点根因**：以前裁剪版是 `var/zh_main/0618test/` 一堆临时脚本手搓的，没进引擎、新对话复现不了，且字幕反复对不上。本轮把这条线沉淀成正式配方 + 承重墙根治对齐。

---

## 一、整条流程全景（先看这张图）

```
骨干主链（线性·必经，6 环）
 ① 转写  →  ② 选片  →  ③ 裁剪(时间轴)  →  ④ 字幕(文字)  →  ⑤ 铸造(风格化)  →  ⑥ 组装成片
 听成字     剪哪句     粗剪/重排/精剪      搬时间/分句       裁剪版/PPT版/      多片合并+转场
                       /去静音/变速        /术语表/AI改错     钩子片(在这生产)    +标题/片尾
                       ★最易错·承重墙       ★最易错·承重墙                      (钩子在这接上)

横切层（贯穿全程，不占主链，谁需要谁挂载）
  ◇ 源适配（按"源类型"，主要挂在 ③）： 画面→裁切/挡UI/圆窗   声音→去噪换干净轨
        干净口播=啥都不挂    录屏=裁切+挡块    带噪=去噪
  ◇ 自检门（每阶段后报数，③④门最重）：切点准 / 画面干净 / 时长对 / 字幕贴口型 / 转场连续
```

**大白话**：骨干=每条片都要走的六环流水线，像工厂传送带（每件产品都过这几道工位）。**横切层不是独立工位，是"贯穿在传送带上、谁需要谁才挂"的东西**——
- 源适配=按"这块毛料是什么"决定加哪道清洗的**选配件**（干净口播啥都不挂、录屏挂裁切+盖按钮、带噪挂去背景音），主要挂在③裁剪的粗剪那里。
- 自检门=每过一站旁边的**质检员**，每环做完跑个几十秒小脚本读出数字，AI 自己判过/不过，不过就停。③④ 最易错，质检员最严。

抽成横切层（而不是塞进主链当普通一环），是因为它们**按条件触发**（不同源类型挂不同附件）且**到处复用**（同一裁切原子这条挂那条不挂、同一对齐自检在好几个阶段后都跑）；这样主链永远是干净的六环。

---

## 二、逐阶段讲清楚（这份计划的主体）

每环都说清四件事：**干嘛 / 产出什么 / 必须还是可选 / 对应哪些原子（已有✅·新建❌·升级🔶）**。

### ① 转写（必须）
- **干嘛**：把口播听写成"逐字带时间"的账本——每个字落第几秒都记下。一切的地基。
- **产出**：逐字账本 `words.json`（字 + 时间）。
- **原子**：`transcribe` ✅（火山 seedasr 主 + 阿里 paraformer 兜底）。

### ② 选片（必须·内容判断，交给 AI）
- **干嘛**：通读全文，决定**剪哪几句/几段**、它们的**先后顺序**（可跳接重排）、**开篇去转折**（去掉第一句前面承接上文的铺垫/转折，从钩子句开篇）。
- **产出**：剪辑清单（选中句段时间 + 顺序 + 开篇处理）。
- **原子**：`cut_sentence` ✅（句级·线上稳定，本轮整句版用它）/ `cut_word` ✅（词级·支持句中精剪）。🔶 补"开篇去转折"口径。
- **大白话**：只产"剪哪些"的清单，不动视频。被选中那些句子的字，**本身就是字幕**——文字和时间是同一次选择一起带出来的。

### ③ 裁剪（时间轴处理）★ 最易错·承重墙
- **干嘛**：纯**时间段**操作，把选中内容剪成一条干净身子。内部有序子步：
  - **3a 粗剪·拼身子**：按清单从源切段、**按顺序拼**成一整条（源适配画面/声音挂这里）。
  - **3b 精剪·去口水**（可选·owner 暂缓）：字级删"嗯/啊/那个"碎口水，**自然停顿保留**（v2 法：只剪口水词、长停顿交 3c）。
  - **3c 去长静音**：>1.5s 长停顿压短，**吐出"保留了哪些区间"**。
  - **3d 固定变速**：整体 1.2x，变速不变调。
  - **边界细节**（最易错）：切点落逗号/句末停顿、pad 不削字头字尾、结尾不带下一句残尾。
- **产出**：干净身子（画面+声音两轨）+ **剪辑账本**（记下每个时间操作，给④用）。
- **原子**：`rough_cut` ❌新建（产品化 assemble.py 的切段+按序拼接）/ `script_clean` 🔶（暂缓）/ `trim_silence` ❌新建★（吐保留区间写进账本）/ `speed_adapt` 🔶升级（加固定倍速档 + 换干净音轨）。

### ④ 字幕（文字加工）★ 最易错·承重墙
- **干嘛**：字幕的**时间**跟着③"同一把剪刀"免费带出（照剪辑账本重放，不另算）；这环只做**文字**：
  - **搬时间对齐**：照③的剪辑账本，把每个选中的字搬到成片时间。
  - **分句成行**：逗号/句号处切分句，一条起=首字、灭=末字，太长在逗号折两行。
  - **术语表打底**：套静态 `fixes.json`（mcp→MCP、哈尼森→Harness…几十条）。
  - **AI 改错词**：`subtitle_ai_fix` **1:1 等条**只订正听错专名 + 删紧邻结巴，**不碰时间/不增减条数**。
  - **别动清单钉回**：自造叫法（如"爱马仕"）被 LLM 改了，最后强制钉回。
- **产出**：定稿字幕（文本 + 成片时间，srt/账本）。
- **原子**：`subtitle_align` ❌新建★（读账本搬时间，复用现成 `segment`/`align`/`resolve`）+ 术语表 `fixes.json` ✅ + `subtitle_ai_fix` ✅ + 别动清单（小配置）。
- **大白话**：剪刀（③）管对齐、AI（④）只换字——AI 收到纯文字吐回纯文字，碰不到时间，所以再聪明也搞不乱同步。

### ⑤ 铸造（风格化渲染）
- **干嘛**：把干净身子 + 定稿字幕**渲成某种风格的"片段"**。三种风格代码同源（切/渲/叠加），都属铸造：
  - **裁剪版**：源画面已裁切（源适配）+ 把定稿字幕渲药丸 + 烧进画面。
  - **PPT 框架页版**：重绘设计页 + 人脸圆窗 PIP + 药丸字幕（framework 一次渲完）。
  - **钩子片**：打字机卡片 / 金句片——**钩子在这"生产"**（独立片段，不是正片的一部分）。
- **产出**：风格化片段（正片 + 钩子片，各自独立）。
- **原子**：裁剪版 → `subtitles` ✅（药丸 ASS 渲染，**复用现成几何，弃 build_subs.py**）+ `subtitle_burn` ✅；PPT 版 → `framework_reframe` ✅ + `pages_gen` ✅；钩子片 → 打字卡素材 + `prepend_hook` 的钩子片部分。

### ⑥ 组装成片
- **干嘛**：把⑤产出的多个片段**拼成最终成片**：
  - **多片段合并**：钩子片 + 正片（或多段正片）。
  - **转场特效**：钩子→正片**翻页**（翻页期间正片定格）、片段间 xfade 转场。
  - **收尾包装**：顶部标题条、章节进度条、片尾卡、封面帧。
- **产出**：可发布成片。
- **原子**：`concat` ✅（硬切合并）/ `prepend_hook` ✅（钩子接正片+翻页转场）/ `title_bar` ✅ / `progress_bar` ✅ / `endcard` ✅ / `cover_frame` ✅。

### ◇ 横切 A：源适配（按源类型，主要挂在③粗剪——回答"为不同原文件的处理"）
| 源类型 | 挂什么 | 原子 |
|---|---|---|
| **干净口播**（对镜头说） | 啥都不挂 | — |
| **录屏**（PPT+人窗+UI按钮） | 画面裁切去外框铺满 + 多块挡 UI（菜单栏/Upgrade/缩略图） | `reframe_crop` ❌新建 + `name_mask` 🔶升级（单块→多块 + 抽帧判编辑/放映模式） |
| **带噪**（提示音"叮"/底噪） | 声音去噪换干净人声 | `denoise_voice` ❌新建（demucs 人声分离，video-clip 可选 audio venv，缺失则优雅跳过） |

（框架页 PPT 版的圆窗人脸定位 `face_locate`/`reframe_locate` ✅ 在⑤铸造时用。）

### ◇ 横切 B：自检门（每阶段后报数，③④门最重——核心价值）
| 环节后 | 查什么 | 怎么查 | 原子 |
|---|---|---|---|
| ② 选片后 | 切点合理 | 句段边界落在停顿处 | （审清单） |
| **③ 裁剪后**★ | 切点准 / 画面干净 / 时长对 | 门A 切点前后帧+能量包络互相关(偏移≈0、相关>0.99)；门B 抽顶帧判编辑/放映模式、挡块盖住没；`len_check` 身子时长==基准(防烧错身子)；去静音后无残留长空白 | `align_check` ❌ + `len_check` ❌ |
| **④ 字幕后**★ | 字幕贴口型 / 没乱改 | 门D 抽头/中/尾 3 帧字幕与口型同步、起音点 vs 切换点偏差报数；别动清单核对("爱马仕"没被改)；1:1 条数核对(没增减/合并)；无空格吞字 | `align_check` ❌ |
| ⑤ 铸造后 | 风格正确 | 圆窗构图/版式/字幕样式一致 | （抽帧） |
| ⑥ 组装后 | 衔接干净 | 转场处画音连续、总时长合理、结尾没被 2s 淡出吃掉 | （抽帧/听） |

---

## 三、承重墙：剪辑账本（③记账 → ④重放，同一把剪刀）

**核心原则**：字幕不是第二样要事后对齐的东西，它的时间就是**③裁剪那把剪刀剪出来的结果**。靠一份**「剪辑账本」（cut manifest）**做③和④之间的接口：

```
③ 裁剪每个时间操作都记一笔进账本：
   选段keep+顺序 ─┐
   3b 删的口水词区间─┤
   3c 去静音保留区间─┼──→ 剪辑账本(cut manifest)
   3d 变速 factor  ─┘            │
                                 ▼
④ 字幕照账本重放：把逐字账本里每个选中的字，依次套上同一串操作 → 它在成片里的时间
                                 │（只搬时间·不从 3h 源重映射·不重转写）
                                 ▼
                    定稿字幕(文本+成片时间) →⑤ 渲药丸+烧
```

- **③ 忠实记账 + ④ 照账本重放 = 字幕时间永远等于"画音被同一把剪刀剪过后的时间"**，从不另算。根因 A（烧错身子）、根因 B（深处漂移）由此一起根除。
- **唯一要拧紧的螺丝**：`trim_silence` 必须把保留区间**吐出来写进账本**，④ 才能拿到同一份。
- **重转写降级为验收手段**：`build_subs_retime.py` 的"对拼好音频重转写"不进生产线，只当④自检门的兜底体检。

---

## 四、已有 / 新增 / 消重（一眼分清，不盲目加）

- **✅ 已有、直接复用**：`transcribe` / `cut_sentence` / `cut_word` / `concat` / `subtitles`(药丸+术语表) / `subtitle_burn` / `subtitle_ai_fix` / `prepend_hook` / `title_bar` / `progress_bar` / `endcard` / `cover_frame` / `face_locate` / `framework_reframe` / `pages_gen` / `segment`/`align`/`resolve`。
- **❌ 真新建**：`rough_cut`(③切段拼接) / `trim_silence`★(③去长静音吐区间) / `subtitle_align`★(④读账本搬时间) / `reframe_crop`(源适配裁切) / `denoise_voice`(源适配去噪) / `align_check`+`len_check`(自检门)。
- **🔶 升级**：`speed_adapt`(加固定倍速档+换轨) / `name_mask`(单块→多块) / `cut_sentence`(补开篇去转折) / `script_clean`(v2 法·暂缓)。
- **消重——废 var/ 手搓重复**：`build_subs.py` 药丸几何 → 废（走 `subtitles`）；`build_subs.py` map_time → 废（走 `subtitle_align`）；`build_subs_retime.py` → 降级自检手段；`finalize.py` 1.2x → 走 `speed_adapt --fixed`；`assemble.py` 拼接 → 走 `rough_cut`；`prepend_hook.py`(var) → 用引擎版。

---

## 五、怎么在系统里表达这套流程

**1. catalog 加阶段标签**（各引擎 `capabilities.json` 加字段，跑 `build_catalog.py` 汇总）：
- `stage`: `transcribe | select | trim | subtitle | cast | assemble`（六环）
- `layer`: `backbone | source_adapt | self_check`
- `required`: `required | optional`
- `source_types`: `[clean_oral, screencast, noisy]`（仅 source_adapt 原子）
- `substep`: `3a | 3b | 3c | 3d`（仅 trim 阶段，记顺序）

`selector.py` 按 stage 分组展示；`recipe` 声明走哪条路径 + 源类型，自动带上对应源适配原子。

**2. 新配方 `zh_clip_cut`**（`recipes.json`，与 `zh_business` 并列，`kind: chain`）：
```
源适配(screencast): reframe_crop + name_mask(多块)        源适配(noisy): denoise_voice
① transcribe → ② cut_sentence(开篇去转折)
③ trim[ 3a rough_cut → (3b 暂缓) → 3c trim_silence → 3d speed_adapt(--fixed 1.2 --replace-audio) ] + 记剪辑账本
④ subtitle[ subtitle_align(读账本) → 术语表 → subtitle_ai_fix(1:1) → 别动清单钉回 ]
⑤ cast[ 裁剪版: subtitles(药丸) + subtitle_burn ]   (钩子片在此生产)
⑥ assemble[ prepend_hook(钩子+翻页) + title_bar(--style label) (+ concat 多片) ]
自检门: ③门A/B+len_check · ④门D+别动核对 · ⑥转场连续
```
因这是**新线、无 G4 基线包袱**，`zh_clip_cut` 直接做成 `run.py` 可跑的真 `chain`，剪辑账本作为产物在原子间流转。

---

## 六、落地工作流（端到端一次做完，6 个 WS）

| WS | 做什么 | 验收 |
|---|---|---|
| **WS-1 阶段骨架** | catalog 加六环 stage/layer/required/source_types/substep 标签 + `selector` 按阶段分组 + `zh_clip_cut` 空配方框架 | `selector --list` 按六环分组；`run.py --plan zh_clip_cut` 审得出完整阶段链 |
| **WS-2 承重墙③④★** | 剪辑账本 + `rough_cut` + `trim_silence`(吐区间) + `speed_adapt` 固定档 + `subtitle_align`(读账本) + 复用 `subtitles` 渲染；同步建③④自检门(`align_check`+`len_check`) | clip_01 复跑：身子 78.683s；抽头/中/尾 3 帧字幕与口型对得上、后半段 ±0.2s；门A/D+len_check 出数字 |
| **WS-3 源适配(挂③)** | 录屏：`reframe_crop` + `name_mask` 多块 + 抽帧判模式(门B)；带噪：`denoise_voice`(可选 venv，缺失优雅跳过)；干净口播=空 | 抽顶帧挡块盖住黄条/菜单栏/Upgrade；带噪片听感无"叮"声 |
| **WS-4 字幕加工④** | `subtitle_align` 接 `subtitle_ai_fix` + 术语表打底 + 别动清单钉回 + 分句成行 | 字幕专名订正、"爱马仕"没被改、1:1 条数、无空格吞字 |
| **WS-5 铸造⑤+组装⑥** | 裁剪版铸造(裁切身子+渲药丸+烧)；钩子片生产；组装(`prepend_hook` 钩子+翻页 + `title_bar` 收尾 + `concat` 多片) | 钩子→正片翻页顺、标题烧对；转场处画音连续、结尾没被淡出吃 |
| **WS-6 串配方 + 收口** | 串成 `zh_clip_cut` chain，`run.py` 端到端接管；废 var/ 重复脚本(或标注例外)；更新 `doc/video-skill-architecture.md`(流程图+六环+子步+配方+新原子+源类型)；`registry.yaml`；`check-tools.py` | `run.py --run zh_clip_cut` 一键出片；var/ 无重复脚本；架构文档同步；`check-tools.py` 0 error；**G4 回归：`zh_business` 逐帧/逐字节零变化** |

---

## 七、目录树（改完后的样子；❌新建 · 🔶升级 · ✅复用，方括号=所属环节）

> **结构决定（owner 拍板）**：物理目录**保持按引擎/运行环境分**，**不**按六环阶段搬动——因为引擎边界是"运行环境边界"（框架渲染要装重库 pillow+opencv+puppeteer、video-clip 自带 ffmpeg+pillow、slicer 纯轻量），而一个引擎常横跨多个阶段。**阶段认知只在两处表达**：① catalog 里每个原子的 `stage` 标签（机器可读，selector 按阶段分组）；② 下面这棵带 `[①②③]` 标注的目录树（人读）。下面每个文件后的方括号 = 它属于哪个阶段。

```
engines/
├── video-compose/                      组合层·唯一对外入口（只指挥）
│   ├── catalog.json                    总能力表(加六环 stage 标签)        🔶
│   ├── recipes.json                    配方(加 zh_clip_cut)                🔶
│   ├── selector.py                     选配方(按六环分组展示)              🔶
│   ├── run.py                          跑配方(chain 执行 + 剪辑账本流转)   🔶
│   └── build_catalog.py                重建总表
│
├── video-slicer/                       积木厂·剪辑策略+内容决策   [①转写 ②选片 ④字幕搬时间]
│   ├── capabilities.json               声明(加 stage 标签)                 🔶
│   └── video_slicer/
│       ├── planner.py                  cut_sentence 句级选段              ✅ [②]
│       ├── twostage/                   cut_word 词级·选段/切片/吸附        ✅ [②③]
│       ├── transcribe/{segment,align}.py  字级转写+分句对齐  ✅ [①·复用给④]
│       ├── subtitle_align.py           读剪辑账本搬字幕时间        ❌新建★ [④]
│       ├── srt_fix.py                  subtitle_ai_fix LLM 1:1 校字        ✅ [④]
│       ├── subtitles.py                分句成行                            ✅ [④]
│       ├── script_clean.py             字级去口水(v2法·暂缓)               🔶 [③3b]
│       └── ...
│   └── profiles/ personas/ references/ 账号定制·去口水承接句红线           ✅
│
├── video-framework-render/             积木厂·框架页渲染          [⑤铸造·PPT版]
│   ├── capabilities.json               声明(加 stage 标签)                 🔶
│   ├── video_framework_render/render.py  framework_reframe / make_subtitles(药丸) / accelerate  ✅ [⑤·④渲染复用]
│   ├── layouts/{vertical,landscape}.json 几何外置                          ✅
│   └── profiles/zh_main/fixes.json     ASR 术语表                          ✅ [④打底]
│
└── video-clip/                         积木厂·通用裁剪/叠加  [③裁剪 ④烧 ⑤⑥ 源适配 自检]
    ├── capabilities.json               声明(加 stage 标签)                 🔶
    ├── requirements.txt                + requirements-audio.txt(demucs可选) 🔶
    └── atoms/
        ├── rough_cut.py                3a 粗剪·按序拼身子          ❌新建  [③3a]
        ├── trim_silence.py             3c 去长静音·吐保留区间      ❌新建★ [③3c]
        ├── speed_adapt.py              3d 加固定倍速档+换干净轨    🔶升级  [③3d]
        ├── reframe_crop.py             源级裁切去外框铺满          ❌新建  [源适配·录屏]
        ├── name_mask.py                挡 UI 块·单块→多块          🔶升级  [源适配·录屏]
        ├── denoise_voice.py            demucs 人声分离去噪(可选)   ❌新建  [源适配·带噪]
        ├── face_locate.py              人脸定位                    ✅      [⑤圆窗]
        ├── subtitle_burn.py            烧字幕·修空格坑             🔶      [⑤]
        ├── subtitle_ai_fix.py          =srt_fix                    ✅      [④]
        ├── concat.py                   多片硬切合并                ✅      [⑥]
        ├── prepend_hook.py             钩子片+翻页转场             ✅      [⑤⑥]
        ├── title_bar.py progress_bar.py endcard.py cover_frame.py  收尾包装  ✅ [⑥]
        ├── align_check.py              对齐自检·起音点偏差/互相关  ❌新建  [自检③④]
        └── len_check.py                时长核对·防烧错身子         ❌新建  [自检③]

var/zh_main/0618test/                   手搓来源(WS-6 原子化后废弃/标例外)
  └── {trim_silence,assemble,build_subs,build_subs_retime,finalize}.py   → 见四·消重

doc/video-skill-architecture.md          架构真源(WS-6 同步：六环+子步+配方+新原子+源类型)
registry.yaml                            机器可读引擎清单(结构变更后更新)
```

**落点原则**：③④⑤⑥ 的通用裁剪/叠加/自检原子都进 `video-clip`（它本就是"通用叠加积木厂"）；唯独 **④的 `subtitle_align` 进 `video-slicer`**，因为它要复用那儿现成的 `segment`/`align`/`resolve` 字级机器；药丸字幕**渲染**继续复用 `video-framework-render` 的 `make_subtitles`（**绝不在 video-clip 再写第二份几何**）。

---

## 八、端到端验证
1. **阶段链可审**：`selector.py --list` 按六环分组；`run.py --plan zh_clip_cut` 审出完整链（含源适配挂载点 + 自检门）。
2. **承重墙复跑**：clip_01（基准 78.683s）跑 `zh_clip_cut`，身子时长一致；`align_check` 报后半段 ±0.2s；抽 3 帧字幕与口型对得上。
3. **源适配三类**：干净口播片（不挂）/ 录屏片（挂 reframe_crop+多块挡UI，抽顶帧确认盖住）/ 带噪片（挂 denoise_voice，无"叮"声）各跑一条。
4. **自检门报数**：③门A/B+len_check、④门D 都吐数字证据，超阈值当场停。
5. **零回归**：`zh_business` 不动——用引擎 venv 重放 `var/zh_main/baseline/primaries/job.json` 与 G4 基线逐帧/逐字节比对，0 差异。
6. **收口**：`scripts/check-tools.py` 0 error；`doc/video-skill-architecture.md` 的流程图/六环/子步/配方/新原子/源类型与实际一致。

---

## 状态：已实施（2026-06-19 · WS-1~6 全部落地）

六个 WS 全部完成，对真实 clip_01 端到端验过。关键证据：
- **承重墙 ③④**：`run.py --run zh_clip_cut --job`（给现成干净人声）身子 **78.683s 分毫不差**；抽头/中/尾 3 帧字幕「火山引擎阿里云也在/是因为我可以给你做的更灵活/我进入下一个时代了」全部对上；门A 去静音接缝 6/6 落停顿、门D 无可判定漂移、len_check 偏差 +0.000s。
- **G4 零回归**：zh_business 重放——5/5 框架页 PNG 逐像素一致(mean-abs-diff=0.0000)、zh.ass byte-identical、accel.mp4 720×1280·101.729s、SSIM=1.000000。**未碰渲染代码**。
- **一键出片**：`run.py --run zh_clip_cut --job job.json` 端到端跑通六环（③裁剪→④字幕→⑤铸造→⑥组装）出成片；`clip_cut_run.py` 串链、剪辑账本 `cut_manifest.json` 在原子间流转。
- **收口**：catalog 30 原子全带六环 stage 标签；架构文档 + registry.yaml 同步；`check-tools.py` 0 error；0618test 手搓脚本标 SUPERSEDED。

**全部 local-validation 已补跑（2026-06-19 当天）**：
- **带噪去噪真跑** ✅：demucs 4.0.1 既装在 `var/zh_main/0618test/.audio_venv`，`denoise_voice` 已自动探测；实跑 htdemucs 出干净人声 107.712s（与 6-18 基线逐位一致），全链 `denoise:true` → 身子 78.683s 精确 PASS。
- **LLM 真专名订正** ✅：真 Kimi/MiniMax 跑 `subtitle_ai_fix`，30→30 条 1:1 维持、口语清理/语法订正精准；`subtitle_protect` 1:1+无吞字 PASS、别动清单逻辑正确。
- 仅 ① 火山转写未跑新实拍 smoke（key 已存、原子早先 spike 跑通；现成 words.json 可用）。

---

## 九、Preflight 执行契约（2026-06-19 锁定 · 已批准并实施）

> 大白话：这一节是"动工前的施工合同"——把要做什么、不碰什么、怎么算做完、怎么验、谁来跑，都钉死，免得开工后边做边改口径。owner 说 LGTM/批准/go ahead 即开工。

```text
Preflight status: IMPLEMENTED（2026-06-19 批准并落地 WS-1~6；G4 零回归）
Task source: plan path
Canonical source: doc/plan/视频剪辑skill-六环阶段化升级-plan.md
Route: durable $intuitive-flow（主会话监督 + skill-runner/tmux worker 按 WS 执行）
Goal: 把"录屏裁剪版竖版切片"沉淀成正式配方 zh_clip_cut，用剪辑账本根治音画对齐，六环阶段化归位所有原子，且 zh_business G4 零回归。

Scope: WS-1 阶段骨架(catalog 六环标签+selector 分组+zh_clip_cut 空框架) / WS-2 承重墙③④(剪辑账本+rough_cut+trim_silence 吐区间+speed_adapt 固定档+subtitle_align 读账本+复用 subtitles 渲染+align_check/len_check) / WS-3 源适配(reframe_crop+name_mask 多块+denoise_voice 可选) / WS-4 字幕④(术语表+subtitle_ai_fix 1:1+别动清单+分句) / WS-5 铸造⑤+组装⑥(裁剪版渲药丸烧+钩子片+prepend_hook 翻页+title_bar+concat) / WS-6 串 chain+收口+架构文档+registry+check-tools+G4 回归。
Non-goals: 不改⑤"PPT 风格"(=zh_business)的渲染实现——它和本轮新增的⑤"裁剪版"风格(=zh_clip_cut)是同一条六环主链下并列的两种风格，"冻结"只指 PPT 风格渲染代码+视觉输出已定型(render.py 全 6 阶段渲染逻辑不动、G4 基线不许回归)，概念上它仍是⑤的一个风格；不改 G4 基线本身；不做 3b 精剪去口水(script_clean v2，owner 暂缓)；不改业务侧选题/文案流程；不动其它账号 profile。
Context: must-read=本计划 + doc/video-skill-architecture.md + var/zh_main/baseline/{G4-result.md,STAGE0-baseline.md,primaries/,_g4_replay/}(G4 口径=确定性产物逐字节/逐像素一致+成片 SSIM 可解释，非整片字节相同) + var/zh_main/0618test/{assemble,trim_silence,build_subs,build_subs_retime,finalize}.py(产品化来源·消重对照) + 三引擎 capabilities.json + video-compose/{catalog,recipes,selector,run}.py；useful=现有 recipe zh_business 作 chain 写法范例、clip_01 基准 78.683s 素材；avoid-unless-needed=其它账号 baseline、历史分计划(已被本计划取代)。

Acceptance:
- SUCCESS: run.py --run zh_clip_cut 端到端一键出片；clip_01 身子时长 == 基准 78.683s；align_check 报后半段偏移 ±0.2s、门A 互相关>0.99；len_check 身子时长==基准；抽头/中/尾 3 帧字幕贴口型(人工判)；源适配三类各跑一条(干净口播不挂/录屏挂裁切+多块挡UI 顶帧确认盖住/带噪挂 denoise 无"叮")；selector --list 按六环分组、run.py --plan zh_clip_cut 审出完整链含挂载点+自检门；var/ 无重复脚本(废弃或标例外)；check-tools.py 0 error；架构文档+registry 同步。
- BLOCKED_NEEDS_DECISION: none（口径与边界已在本计划钉死）
- BLOCKED_NEEDS_LOCAL_VALIDATION: G4 回归必须本地用 video-framework-render/.venv(pillow+opencv+puppeteer+Hannotate/PingFang 字体)重放 baseline/primaries 比对——若当前环境无 venv/字体则此门挂起；denoise_voice 需 demucs audio venv，缺失则原子优雅跳过(非阻断)。
- INTERMEDIATE_ONLY: 仅 owner 显式同意时——可按 WS 逐段验收交付(如先交 WS-1+2 承重墙)，未跑完 6 WS 不算全绿。
- No regressions: zh_business 走 G4 replay——确定性产物(框架页 PNG/zh.ass/时长/画幅)逐字节/逐像素一致 + 成片 SSIM≥0.98 且差异仅 x264 重编码可解释；现有 recipe(landscape_business/raw_quickcut/simple_concat/chaptered_growth) 解析不破。

Verification:
  deterministic = python3 scripts/check-tools.py(0 error) · selector.py --list(六环分组) · run.py --plan zh_clip_cut(审链通过)
  integration = align_check/len_check 在 clip_01 吐数字证据 · 字幕 1:1 条数核对 · 别动清单("爱马仕"未被改)核对 · catalog build_catalog.py 重建无错
  product-run = run.py --run zh_clip_cut 端到端出片(clip_01 78.683s 身子) · 源适配三类各一条
  local-live-manual = G4 replay 逐帧比对(本地 venv，必跑·完成门) · 抽 3 帧字幕对口型(人工判) · 录屏顶帧挡块确认(人工判) · 带噪片听感无"叮"(人工/可选 demucs)
  optional = denoise_voice(demucs 装了才跑) · script_clean v2(暂缓)
Execution: main=主会话守 root goal+路由+验 worker 产物+G4 终判+语义提交；worker=skill-runner/tmux 按 WS 一段一 worker(WS-2/WS-5 体量大优先隔离)；worker-goal=每 worker 一个 bounded 子目标(如"WS-2 承重墙③④：建剪辑账本+5原子+自检门，clip_01 复跑身子78.683s+门A/D出数")，结束交 handoff 不动 root goal。
To execute: /goal execute doc/plan/视频剪辑skill-六环阶段化升级-plan.md with intuitive-flow
Approval: LGTM/批准/go ahead 即开工；要改则指出改哪段。
```

**Plan-file recommendation**：本契约已写入本计划第九节（canonical source），批准后即按此执行，免得后续上下文压缩丢了口径。
