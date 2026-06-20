# 第②环 · 选片 —— Eval Harness 驱动迭代 + 引擎独立 + 流程改造计划

> 面向不读代码的 owner 写。先讲**做什么/为什么/最后长什么样**,技术名词都配一句大白话。
> 本文是「视频剪辑六环主链」**第②环·选片**的计划真源。六环主链全貌与 ③–⑥ 的实现见
> [`视频剪辑skill-六环阶段化升级-plan.md`](./视频剪辑skill-六环阶段化升级-plan.md)。

---

## 0. 本文档的范围(务必先读)

**位置**:整条业务是一条**六环主链**——

```
① 转写 → 【② 选片 ★本文】 → ③ 裁剪 → ④ 字幕 → ⑤ 铸造 → ⑥ 组装成片
```

③–⑥ 已经实施(见六环计划)。**本文只管第 ② 环 · 选片。**

**②选片做什么**:从逐字稿 → 产出一份**「成片脚本」**——它定义"这条视频最终该剪成什么内容"。这份脚本含两层:

1. **提取哪些部分**:选哪些题(选题)、每题选哪些句/段、按什么逻辑顺序排(选段+编排)。
2. **在这些部分上做哪些精简**:句子内部删掉哪些口水字词(**字级去口水决策**)。

| 在范围内 ✅ | 不在范围内 ❌(归 ③–⑥) |
|---|---|
| 选题(做哪些题) | 按脚本 trim+concat 实际剪(③) |
| 选段 + 逻辑顺序编排(总编) | 把"该删的字"真从视频剪掉(③ 执行字级去口水) |
| **字级去口水决策**(删哪些字词、带位置) | 去长静音、变速(③) |
| 钩子(选开场那句/几片段) | 字幕渲染烧录、裁框、挡块、铸造、组装(④⑤⑥) |

> **一句话边界**:**我们定「剪成什么」(脚本/内容),不定「怎么剪」(渲染/执行)。** 字级去口水的"**删哪些字**"=决策(我们),"**把那些字从视频剪掉**"=执行(③)。

**本环怎么建、怎么迭代**:不是先堆一份"标准答案"就结束,而是把②选片整环做成 **Eval Harness 驱动的迭代闭环**——固定评测集上跑生成器 → 自动门禁 + 打分 → 翻 bad case → 改 prompt/代码/门禁 → 再跑,直到门禁全绿、分数稳定。**Harness 是主架构;`golden.json` 只是闭环里的冻结参照快照,不是终点。**

| Harness 组件 | 大白话 | 对应产物/代码 |
|---|---|---|
| **评测集** | 固定输入:一场逐字稿 + 已认可的选题清单 | `words.json` + `_selection.json`(如 agent_eval_0613 的 22 条) |
| **Runner** | 把选片流水线跑一遍,落候选 | `eval/video-select/runner.py`(调生产核心,写 var 产物) |
| **门禁(Gates)** | 机器可判的红线,不过就挡、不让进下一轮 | `eval/video-select/gates.py` |
| **打分器(Scorers)** | 跟冻结参照比"逼近度",量化 prompt 改动有没有变好 | `eval/video-select/score.py` |
| **人工评审环** | 人在环里给参照打标、挑钩子、核对忠实度——**是 Harness 的一环,不是 Harness 之外的"定稿仪式"** | `var/.../candidates/clip_NN.md` 评审 → 更新 `golden.json` |
| **迭代闭环** | 北极星=**迭代周期**:发现问题→定位层→改→重跑→验收 | `eval/video-select/doc/`(迭代经验) + `var/.../eval/<run>/`(运行产物) |

> **和生产的关系**:
> - **日常生成**走 `engines/video-select/`(生产引擎),**不加载、不 import** 任何 Eval 代码。
> - **只有**做提示词优化或架构优化时,才进 `eval/video-select/` 跑 Harness。
> - Harness 改的是生产引擎里的 prompt/编排;验收通过后,生产路径自动受益。**Harness 不进③–⑥,也不绑在日常命令上。**

**为什么要重做这一环**:
1. **质量不可取**:现在选片产出的候选**切太碎 / 句间跳得大 / 两刀挨太近吞掉中间 / 重复段**——没有 Harness,改 prompt 只能凭感觉。
2. **代码没独立、生产与 Eval 混在一起**:②生产逻辑与 baselines 评测脚本**同堆在 `engines/video-slicer/`**,日常跑片和改 prompt 共用一套目录,认知混乱。**本计划拆成两条线:**
   - **生产** → `engines/video-select/`(六环日常用)
   - **Eval Harness** → `eval/video-select/`(仅优化时用;文档+门禁+打分+重跑脚本,与生产代码分目录)

---

## 1. 选片在六环里的位置(流程图一 · 全景)

```
六环主链(线性·每条片必经):
 ① 转写  →  【② 选片】★本文  →  ③ 裁剪  →  ④ 字幕  →  ⑤ 铸造  →  ⑥ 组装
  听成字     产出「成片脚本」      ───────── 照脚本执行「怎么剪」─────────
            (决定剪成什么内容)      粗剪/去静音    搬时间/改错词   风格化    合并/转场
                  │                  /变速/执行去口水            /标题/片尾
                  │
                  └─ Eval Harness(与生产并行·驱动②迭代,不进③–⑥):
                       评测集 → Runner 重跑 → 门禁 → 打分 vs 冻结参照
                            → 翻 bad case → 改 prompt/代码 → 再跑(闭环)
                       golden.json = 闭环里的「冻结参照」,不是一次性终点
```

**大白话**:六环像工厂传送带,每件产品(每条切片)都要过这六道工位。**②选片是第二道,它产出的"成片脚本"是后面四道工位的施工图纸。** 但②本身不是"做一张标准图纸就收工"——而是搭一套 **Eval Harness**:固定 22 条当评测集,每次改 prompt 都重跑、过门禁、跟参照打分,从 bad case 里改,转得越快质量越稳。`golden.json` 是参照快照,Harness 才是发动机。

### 1.1 Eval Harness 迭代闭环(②环的工作方式)

```
        ┌─────────────────────────────────────────────────────────┐
        │  评测集(固定)  words.json + _selection.json (22 条)      │
        └───────────────────────────┬─────────────────────────────┘
                                    ▼
        ┌─────────────────────────────────────────────────────────┐
        │  Runner  generate.py  选题→总编→组装→去口水→钩子       │
        └───────────────────────────┬─────────────────────────────┘
                                    ▼
              golden_candidate.json + candidates/clip_NN.md
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────────┐       ┌───────────────────────┐
        │  Gates  gates.py       │       │  Scorer  score.py      │
        │  结构/时长/可执行/零编造 │       │  vs golden.json 冻结参照│
        └───────────┬───────────┘       └───────────┬───────────┘
                    │  不过                          │  分跌
                    └───────────────┬───────────────┘
                                    ▼
        ┌─────────────────────────────────────────────────────────┐
        │  Look at bad case → 定位层(选题/总编/去口水/钩子/门禁)   │
        │  → 改 prompt / 代码 / gates → 重跑 Runner              │
        └───────────────────────────┬─────────────────────────────┘
                                    │  循环
                                    ▼
        ┌─────────────────────────────────────────────────────────┐
        │  人工评审环(人在环里)  挑钩子·核对忠实度·更新 golden.json  │
        │  → 升版冻结参照(v1→v2…) → 下一轮 Scorer 自动对照         │
        └─────────────────────────────────────────────────────────┘
```

**北极星**:不是"做出一份 golden",而是**缩短迭代周期**——从发现 bad case 到 prompt/门禁改好、Harness 重跑验收,转得越快,②选片越稳。

---

## 2. ②选片内部:阶段 / 输入输出 / 文件流向(流程图二)

> ⚠ 注意:下面是 **②选片环内部的工序**,用「总编 / 组装草稿 / 去口水决策 / 钩子」这些**名字**称呼,**不要和六环主链的 ③裁剪 / ⑥组装 混淆**(那是另外的环)。

### 2.1 文件流向图(每步:输入文件 →〔工具·提示词〕→ 输出文件)

```
┌─ 上游 ①转写(不在本文) ───────────────────────────────────────┐
│  [源视频.mp4] ──火山ASR──> [words.json]  句/字级时间戳+全文        │
│                            ★「句号↔秒」「字↔毫秒」锚点,选片全靠它   │
└──────────────────────────────────────────────────────────────────┘
        │ (整场逐字稿)
╔═ 第②环·选片 = Eval Harness(驱动迭代) + 成片脚本产出 ═════════════════╗
║                                                                    ║
║ 〖Harness · 评测集(固定输入)〗                                      ║
║   [words.json] + [_selection.json 选题清单]                         ║
║                                                                    ║
║ 〖流程一 · 生成选题〗(Runner 第 1 段)                               ║
║   输入 [words.json] + [personas/zh_main.md]                        ║
║     │ 选题(stage1) · STAGE1_TASK                                   ║
║     ▼                                                              ║
║   输出 [选题清单 _selection.json]  题目 + rough_sid_spans(粗区间)   ║
║   〔⚠ 现状还跑"定段 stage2"→近视且被总编覆盖,改造=停用〕            ║
║                                                                    ║
║ 〖流程二 · 生成候选〗(Runner 第 2 段) 对每条选题循环:               ║
║   输入 [选题清单](取1条) + [words.json](全场) + [zh_main.md]        ║
║     │                                                              ║
║     ├─ 总编      · BODY_TASK   → 选段 segments(句级区间+顺序)       ║
║     ├─ 组装草稿  · 代码        → script_raw(带口水草稿)            ║
║     ├─ 字级去口水决策 · REFINE_TASK → 删哪些字(带位置)             ║
║     └─ 钩子      · HOOK_TASK   → hook_options(2-3个)               ║
║     ▼  (汇总落盘)                                                  ║
║   输出 [golden_candidate.json](机读真源) + [candidates/clip_NN.md](人读)║
║                                                                    ║
║ 〖Harness · 门禁 + 打分〗                                          ║
║   输入 候选 + [golden.json 冻结参照](有则比,无则先建参照)            ║
║     │ 阶段检查 hook(结构/时长/可执行/零编造…)                       ║
║     │ score.py(句号 F1 + 时间 IoU)                                 ║
║     ▼  不过门禁 / 分数掉 → 翻 bad case → 改 prompt/代码 → 重跑     ║
║                                                                    ║
║ 〖Harness · 人工评审环〗(参照打标,不是"做完就归档")                 ║
║   输入 [clip_NN.md] + [golden_candidate.json]                      ║
║     │ 挑钩子 / 核对 / 改状态(留·删·改)                            ║
║     ▼                                                              ║
║   输出 [golden.json]  ←★ 冻结参照快照(供下一轮打分;可版本化)       ║
╚══════════ 边界到此:脚本已定死「剪成什么内容」 ═════════════════════╝
        │ (golden.json 当施工图纸)
┌─ 下游 ③–⑥(不在本文) ─────────────────────────────────────────┐
│  照脚本:裁剪(执行去口水/去静音/变速)→字幕→铸造→组装 → [成片.mp4]   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 逐步骤主表(输入 / 工具·提示词 / 输出 / 涉及文件)

> `R`=读 ｜ `W`=写 ｜ `内存`=同一次运行内的中间数据,不单独落文件。

| # | 步骤 | 输入(数据) | 工具 · 提示词 | 输出(数据) | 涉及文件 |
|---|---|---|---|---|---|
| 0 | ①转写(上游) | 源视频 | 火山 ASR | 句/字级时间戳+全文 | `源视频.mp4`(R)→`words.json`(W) |
| 1 | **流程一·选题** | 整场编号逐字稿 | 选题(stage1)·**STAGE1_TASK** | 选题清单(题+`rough_sid_spans`) | `words.json`(R)+`zh_main.md`(R)→`_selection.json`(W) |
| 1b | ~~定段(停用)~~ | 选题粗区间±6句小窗 | ~~stage2·STAGE2_TASK~~ | ~~keep_sids(近视·被总编覆盖)~~ | ~~`_selection.json`±窗(R)~~ |
| 2 | **流程二·总编** | 1条选题 + **全场**编号句 | 总编·**BODY_TASK** | 选段 `segments[{role,sids,reason}]` | `_selection.json`(R·1条)+`words.json`(R·全场)+`zh_main.md`(R)→内存 |
| 3 | **流程二·组装草稿** | 总编的 segments + 句表 | 代码(+句号↔时间) | `keep_sids`/`time_spans`/`script_raw` | `words.json`(R·回查时间)→内存 |
| 4 | **流程二·字级去口水决策** | 草稿 + 字级时间戳 | 去口水·**REFINE_TASK** | 删哪些字(带位置) | `words.json`(R·字级)→内存 |
| 5 | **流程二·钩子** | 1条选题 + 候选池句 | 钩子·**HOOK_TASK** | `hook_options`(2-3) | `words.json`(R·候选池)+`zh_main.md`(R)→内存 |
| 6 | **流程二·汇总落盘** | 步骤2-5(内存) | 代码 | 候选切片 | 内存→`golden_candidate.json`(W)+`candidates/clip_NN.md`(W) |
| 7 | **Harness·门禁+打分** | 候选 + 冻结参照 | 检查 hook + `score.py` | 过/不过 + 逼近度分 | `golden_candidate.json`(R)+`golden.json`(R·可选)→`score_report.json`(W) |
| 8 | **Harness·人工评审环** | 候选 + 人工判断 | 人工 | 更新冻结参照 | `clip_NN.md`(R)+`golden_candidate.json`(R)→`golden.json`(W) |
| 9 | ③–⑥执行(不在本文) | 成片脚本(门禁已通过) | 六环 ③–⑥ | 成片视频 | `golden.json`(R)→`成片.mp4`(W) |

> 第 2-6 步在**同一次运行**里完成(总编/组装/去口水决策/钩子都是内存数据),第 6 步一次性写成两个文件:`golden_candidate.json`(机读真源)+ `clip_NN.md`(人读评审稿)。文件完整路径见第 6 节目录树。

---

## 3. 流程一 · 生成选题(各阶段 I/O + 现状问题)

**正确只有 1 个 AI 阶段:选题。**

| 阶段 | 输入 | 输出 |
|---|---|---|
| **选题** | 整场编号逐字稿 + 人设 | 选题清单:`title / one_argument / hook_line / audience / mainstream / why / rough_sid_spans` |

- 它只决定**"做哪些题、大概在哪几句"**,不给精确边界、不给时间戳。

**⚠ 现状问题:多了一个"近视"的定段步骤**。现状还跑 `stage2`(定脚本边界):只在选题落点前后各 6 句小窗(`WINDOW_PAD=6`)里挑句子定 `keep_sids`。打个比方——选题夹了张书签"这观点大概在第 140 页",定段就只读那一页前后凑稿;可张和常在 3 小时里别处把同一观点讲得更好、举了更狠的例子,这逻辑看不见。而且它的 `keep_sids` 到流程二会被**总编整段重选覆盖**。所以它**又近视又冗余**。**改造:选题到 stage1 为止,停用 stage2。**

---

## 4. 流程二 · 生成候选(产出成片脚本)

**正确分 4 步**(主轴 总编→组装草稿→去口水决策,钩子是支线):

| 步骤 | 一句话职责 | 输入 | 输出 | 现状⚠ |
|---|---|---|---|---|
| **总编**(全局取证+逻辑编排) | 选料 + 编成逻辑连续的结构 | 1条选题 + 全场句 | 选段+顺序 | `BODY_TASK` 只写了"选(取证)",还逼它"每段≤6句、禁圈几十句、多段跳接"→ **碎/跳/吞**;代码不去重不合并 |
| **组装草稿**(代码) | 把总编原话按序粘成草稿 | segments+句表 | `script_raw`(带口水) | 无 |
| **字级去口水决策** | 句内删哪些口水字词 | 草稿 + 字级时间 | 删哪些字(带位置) | `REFINE_TASK` **出的是改写文本(free-text)**,对不回原视频、没法执行;还**兼做"顺语序/合并"**(那是编排,该归总编) |
| **钩子** | 选炸开场 | 选题+候选池 | hook_options | `HOOK_TASK` 是"短句拼接"思路→蹦字、丢限定词("95%以上"→"95%") |

**顺序铁律:先总编把骨架编对,再去口水擦表面。** 剪刀口 = 总编(句级) + 去口水决策(字级)。

---

## 5. 贯穿原则(铁律)

1. **一个动作只有一个家**:"选+编"全归总编(别在 stage2 重做、别在去口水偷做);"删口水字"全归去口水决策。
2. **先编骨架,再擦表面**:总编定"留哪些、怎么连"(逻辑),去口水只做字级表面清理(不动结构)。
3. **全局取证 = 总编**:从全场选内容并编排成一条片子,"选+编"是一个动作。
4. **只引真实原话、禁编造**:总编只回真实句号编号(指向 `words.json` 真有的句子)→ 可校验 + 可换算成秒/毫秒(剪得出来)。
5. **精选合并原则**(2026-06-19 张和拍板,解决"碎"):源头连续(或隔≤2句)的相邻刀→合并连续播、承接句原声补回;源头不连续的整句→保留编辑排序(不强行按时间拉平);去重叠→删前留后;判定钥匙=只合并"列表相邻且中间≤2句"的刀。
6. **字级去口水准则**(参考 `references/字级去口水与承接句保护.md` + videocut-zh):删前保后、承接句必留、不过碎、断了从原声补回。
7. **字级去口水必须可执行**:产出是"删哪些字(带位置)",不是改写文本——否则脚本落不了地、③ 没法照着剪。
8. **Eval Harness 驱动迭代**:改 prompt/代码的唯一验收方式是**重跑 Harness**——门禁全绿 + 分数相对冻结参照不跌 + bad case 被消化;人工评审是 Harness 里给参照打标的一环,不是闭环外的"一次性定稿"。
9. **一次只动一层**:bad case 先定位是哪一段(选题/总编/去口水/钩子/门禁),只改那一层再重跑,别全推倒。
10. **生产与 Eval 分目录**:prompt/人设真源在生产引擎(`engines/video-select/`);门禁、打分、Harness 文档、评测重跑脚本**只在** `eval/video-select/`。**生产代码不得 import eval**;eval 可 import 生产核心做对照重跑。

---

## 6. 目录拆分:生产引擎 + Eval Harness(分放)

**决定**:②选片拆成**两条独立目录**,职责不混:

| 路径 | 什么时候用 | 放什么 |
|---|---|---|
| **`engines/video-select/`** | **日常**跑六环、出成片脚本 | 选题 + 总编 + 去口水决策 + 钩子 + persona/profile/reference(prompt 真源) |
| **`eval/video-select/`** | **仅**提示词优化 / 架构优化 | Harness README、迭代文档、`runner.py`/`gates.py`/`score.py`、方案A对照 |
| **`var/.../eval/<run>/`** | Harness 跑出来的 | 候选 json/md、score_report、冻结参照(运行时,默认不入库) |

- **为什么分目录**:平时生成**用不到**评测代码;混在生产引擎里会让人误以为日常也要跑 score/gates,也污染 registry/check-tools 的认知。
- **共享方式**:Eval **import 生产核心**(`engines.video_select`),prompt 只维护一份;Eval 侧只加门禁/打分/重跑编排,不 fork 一套 prompt。
- **依赖方向**:`eval/video-select` → `engines/video-select` → `engines/video-slicer`(单向)。

```
tools/
├── engines/
│   ├── video-select/                         🆕 生产·第②环选片(日常管线)
│   │   ├── capabilities.json                 🆕 stage=select · 注册进 registry
│   │   ├── README.md                         🆕 生产用法(选题→成片脚本→交③)
│   │   ├── video_select/                     🆕 包
│   │   │   ├── topics.py                     🆕← twostage/stage1_topics.py
│   │   │   └── select.py                     🆕 生产 Runner(总编+组装+去口水+钩子)
│   │   ├── personas/zh_main.md               🆕 prompt 真源(生产与 eval 共用)
│   │   ├── profiles/zh_main/
│   │   └── references/字级去口水与承接句保护.md
│   │         ▲ import(不搬): video-slicer 的 llm / transcribe / twostage.index / resolve
│   │
│   └── video-slicer/                         ①转写 + ③④执行 + 共享核心
│       └── video_slicer/
│           ├── transcribe/                   ✅ ①
│           ├── twostage/                     stage2 DEPRECATED; index/resolve ♻️
│           ├── cut_video.py pipeline.py ...  ✅ ③④
│           └── (无 baselines/)               ➡️ 删/留 stub README 指 eval/video-select
│
├── eval/
│   └── video-select/                         🆕 Eval Harness(优化时才进)
│       ├── README.md                         🆕 generate → gates → score 命令
│       ├── doc/
│       │   └── 金标准建设-经验与提示词总结.md  🆕← 从 var/.../eval/.../doc/ 迁入仓库
│       ├── run.py                            🆕 一键 Harness 入口
│       ├── runner.py                         🆕← baselines/global_evidence.py
│       ├── gates.py                          🆕 门禁(精选合并/时长/可执行/零编造…)
│       ├── score.py                          🆕← baselines/score.py
│       └── select_clips_a.py                 🆕← baselines/select_clips.py(方案A对照)
│             ▲ import engines.video_select + video_slicer 核心
│
├── video-framework-render/  video-clip/  video-compose/   ③⑤⑥ 其余不动
│
var/zh_main/
├── asr/agent_eval_0613/words.json            ♻️ 评测集输入(也是生产 ASR 产物)
├── cuts/agent全量-volc-native/_selection.json 📦 评测集选题清单
└── eval/agent_eval_0613/                      📦 Harness 运行产物(var,不入库)
    ├── candidates/clip_NN_*.md                📦 人工评审稿
    ├── golden_candidate.json / golden.json    📦 候选 / 冻结参照
    └── score_report.json                      📦 Scorer 产出
    （迭代经验文档已迁到 eval/video-select/doc/, var 只留运行数据)

doc/plan/视频剪辑skill-第二环选片-plan.md        本计划(第②环真源)
doc/video-skill-architecture.md / registry.yaml  🔶 拆分后同步
```

> **图例**:🆕新建 ｜ ➡️移走/删 ｜ ⚠️停用 ｜ ♻️复用(import) ｜ ✅留 ｜ 🔶同步 ｜ 📦运行时产物。

**日常 vs 优化,各走各的门**:

```bash
# 日常生产(六环②)——不碰 eval/
python engines/video-select/... select --words ... --selection ... --out var/.../cuts/...

# 仅在做 prompt/架构优化时——进 eval/
python eval/video-select/run.py --suite agent_eval_0613   # → runner → gates → score
```

---

## 7. 改造计划(要动的)

| # | 改什么 | 现状 → 目标 | 验收 |
|---|---|---|---|
| 0 | **目录拆分** | baselines 混在 `video-slicer/` → 生产进 `engines/video-select/`;Harness+文档进 `eval/video-select/`;`var/` 只留运行产物 | 日常命令不 import eval;优化命令不污染生产 registry |
| 1 | **Eval Harness 成形** | 散脚本 + 文档在 var → `eval/video-select/` 内 `run.py` + gates + score + README + doc | 固定评测集上一键 `run → gates → score` |
| 2 | **生产引擎独立** | 新建 `engines/video-select/`(仅 select/topics/persona);注册 registry;import video-slicer 核心 | `check-tools.py` 0 error;日常选片可独立跑通 |
| 3 | **选题停用 stage2** | 选题只给粗区间;`stage2_script.py` 标 DEPRECATED | 选题产出只含 `rough_sid_spans`,无 `keep_sids` |
| 4 | **总编 `BODY_TASK`** | 从"取证"升级"总编"(加逻辑连续+精选合并原则);门禁进 `eval/.../gates.py` | 重跑 22 条:连续区间与手工合并版一致、gates 全绿 |
| 5 | **去口水 `REFINE_TASK`** | 从"出改写文本"改"出**字级删除决策**(删哪些字、带位置);删掉"顺语序/合并"(上交总编) | 产出能对回原视频字级时间、可直接驱动 ③ 执行 |
| 6 | **钩子 `HOOK_TASK`** | "短句拼接"→"整句优先、拼接兜底" | 钩子不丢限定词、不失真 |

---

## 8. 当前状态

- **Harness 已跑通(初版)**:agent_eval_0613 上 baselines 脚本可跑;迭代经验目前在 `var/.../doc/`(待迁入 `eval/video-select/doc/`)。
- **已做(临时补丁)**:22 条总编选段手工 `_merge_segments.py`(待迁入 eval 或 gates 替代)。
- **待做**:§7 目录拆分 + 生产引擎 + Harness 收口 + prompt 改造项。

---

## 9. 验收门(怎么算 Harness 闭环跑通)

- [ ] **生产** `engines/video-select/` 独立成形,日常选片不依赖 eval;`check-tools.py` 0 error;registry 只登记生产引擎。
- [ ] **Eval** `eval/video-select/` 独立成形,文档在 `eval/.../doc/`(不在 var、不在 engines);`run → gates → score` 可一键跑。
- [ ] `engines/video-slicer/baselines/` 清空/改 stub,指向 `eval/video-select/`。
- [ ] 固定评测集(agent_eval_0613·22 条)上:Runner 重跑可复现;`score_report.json` 可出基线分。
- [ ] **门禁代码化**(`eval/video-select/gates.py`):22 条全绿(不靠手工 `_merge_segments.py`)。
- [ ] 选题停用 stage2,产出只含粗区间。
- [ ] 总编 prompt 升级后重跑:连续区间与手工合并版一致或更好。
- [ ] 去口水产出**可执行的字级删除决策**(对得回原视频时间)。
- [ ] 钩子整句优先,不丢限定词。
- [ ] 人工评审环可更新 `golden.json` 冻结参照;下一轮 Scorer 能自动对照。

---

## 10. 待你拍板(parked · 我先按这些写了,要改告诉我)

1. **新引擎名**:我用了 `engines/video-select/`(选片环)。若你想要别的名(如 `video-script` / `clip-select`),说一声。
2. **②/③ 字级去口水的边界**:本计划把②选片的范围**扩展**为含"字级去口水**决策**"(删哪些字),③ 只负责**执行**(把字剪掉)。这比六环计划里②的窄定义(只选句段)更宽——**需同步更新六环计划 §② + 架构文档**。确认这个边界。
3. **共享核心的依赖方式**:`video-select` **import** video-slicer 的句/时间核心(单向依赖),不重复造、也不另起共享包。若你想要更彻底的解耦(抽一个独立 transcript-core 包),那是更大改动,另议。
4. **本文件名**:真源为 `视频剪辑skill-第二环选片-plan.md`。旧名 `video-golden-baseline-plan.md` 若仍有引用,应改指向本文(旧名偏"金标准终点",已不符合 Harness 定位)。
5. **冻结参照版本化**:`var/` 不入库;人工评审环确认后的 `golden.json` 复制到明确版本目录(如 `var/zh_main/baseline/select-v1/`)并标版本——它是 **Scorer 的参照**,随 Harness 迭代可升 v2/v3,不是"做完就封存"。

---

## 附录:当下提示词原文

> 真源在代码里;此处便于对照。`persona zh_main` 贴在 STAGE1/BODY/HOOK 前,REFINE 不带。

### persona `zh_main`
张和编辑判断,6 块:①选题闸5关(独立可懂/单一论点/看反认知度/价值一句话/炸点可前置) ②富集度排序(数据·转变故事·金句·背书·痛点 ≥3类优先) ③标题硬要求(挂流量锚/默认疑问反问) ④in/out纪律 ⑤数量纪律(覆盖优先18-25条) ⑥独家流量锚(前小米/出海CEO/一线Claude Code+Codex)。

### 流程一 · `STAGE1_TASK`(选题,在用)
```
【你的任务·阶段一选题】读【编号逐字稿】(每行 #句号 [说话人] 文本)。按「选题闸5关+标题硬要求+数量纪律」,
从张和(host)发言里挑少而精的切片选题。学员的话只作背景。
【关键:只负责"选什么",不负责"切在哪一毫秒"】不输出时间戳;每条只给大致【句号区间】(rough_sid_spans),
可略宽,精确in/out交下一步;不连续的几段就给多个区间。
【输出JSON】{"clips":[{title,one_argument,hook_line,audience,mainstream,why,rough_sid_spans:[[起,止]]}]}
按mainstream高→低;覆盖优先、宁多勿漏,目标18-25条。
```

### 流程一 · `STAGE2_TASK`(定段,⚠近视/冗余,改造=停用)
```
【你的任务·阶段二定脚本】给一条选题 + 它附近的【张和候选句】。按in/out纪律挑真正进切片的句子:
in点=从hook那句起砍前面软铺垫;out点=论点说完即收;允许跳接(砍中间废话、保时间先后);只能选给你的候选句号、不编造。
【输出JSON】{"keep_sids":[[起,止],...]}  // 连续闭区间;多段=跳接
```
> 代码 `WINDOW_PAD=6`:只把选题粗区间两侧各放宽6句喂给它 → 近视来源。

### 流程二 · 总编 `BODY_TASK`(⚠只写了"取证"、待加"编排")
```
【你的任务·全局取证定正文】选题已定不要更换。只产正文(论点→论据→收尾),不产钩子。
【根本区别】不要只盯落点附近;扫全场跨位置取证,把散落各处最有力的原话聚到一条。
【结构】argument一句立住观点;evidence从全场任意位置调最有力论据/案例/数据/金句(允许跨很远);closing一句收口(没有就不要)。
【反串味】每段只服务这条选题。【结尾】closing落在完整有力的话上。
【通用纪律】只引真实句号、不编造不改写;每段连续闭区间[起,止],多段=跳接;
  每段短而准~6句内、禁一段圈几十句;  ← ⚠ 这条在逼它切碎,待改成"源头连续就合并、按精选合并原则"
  总时长约60–120秒;按论证逻辑顺序排。
【输出】{"segments":[{role,sids:[起,止],reason}],"title_suggestion":""}
```

### 流程二 · 钩子 `HOOK_TASK`(⚠拼接思路、待整句优先)
```
设计2-3个开场钩子,按吸引力高→低。【三要素】戳痛点/中目标用户/让人看到答案。
【形态】一个钩子=几个短句拼成一句;片段必须是短句≤12字,长句只抠最炸小短语;2-4个顺次拼、整条≤~30字;
  stitched≈各短句原话顺次拼接(只补极少衔接字)。允许直接用招牌原话整句立住。  ← ⚠ 待改"整句优先、拼接兜底"
【硬约束】每片段≤14字、是原话一字不差子串;stitched字数≤片段和×1.2。
【铁律】片段必须是原话连续子串,不编造、不跨到没给的句子。
【输出】{"hooks":[{fragments:[{sid,text}],stitched,why}]}
```

### 流程二 · 字级去口水 `REFINE_TASK`(⚠出free-text+兼做编排、待改字级删除决策)
```
对张和原话做【精修】,产出能直接当成片用的脚本。
【必须做】1.去口水:删"啊/嗯/这个/那个/然后/就是/对吧/你知道吧"等口头禅与口吃;同句重说只留一遍最顺的。
  2.去重复+顺语序:把绕回、同意思的几句合并成一句,语序可调。  ← ⚠ 这是"编排",该上交总编
  3.开篇独立:第一句不承接上文,剪掉承接/转折词。 4.结尾干脆:不停在"那接下来…/后面再说…"。
【铁律】只用原话出现过的字词,不新增观点、不改写实质——是"删和理顺",不是重写。
【输出】{"refined":"精修后纯文本"}   ← ⚠ 应改"字级删除决策(删哪些字、带位置)",纯文本对不回原视频
```

### 流程二 · 组装草稿
纯代码,无提示词:把总编的 segments 原话按序粘成 `script_raw` + 算 `keep_sids/time_spans/est_dur`。
