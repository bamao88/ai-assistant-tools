# 视频剪辑工具集中化迁移计划

> 文档位置：`tools/doc/video-tools-migration-plan.md`
> 起草日期：2026-06-14
> 状态：**定稿待排期**（§7 决策已定；D3=C 暂不执行，留作后续启动蓝图）

---

## 1. 项目背景与目标

### 1.1 背景

我们围绕「张和口播 → 竖版框架页切片成片」这条业务，陆续做出了一整套视频剪辑能力：选段、切片、字幕纠错、框架页渲染、变速、发布。但这些代码**当前散落在两个项目里**，分布混乱：

- 一部分已经正确地落在共享工具层 `tools/engines/`（如 `video-slicer`、`video-clip`、`video-research`、`tencent-video-publish`）。
- 另一部分——尤其是**线上正在跑的成片主流程**——还留在业务项目 `assistant_zh/workflow/` 下（`video_framework_slicer/`、`video_vertical/`），并夹杂着实验脚本散在 `assistant_zh/tmp/`。

这违反了本仓库 `CLAUDE.md` 确立的四层规约：

> 代码归 `engines/`（可复用、不可独立触发）；触发入口归 `skills/`；业务编排与产物归 `var/`；外部 clone 归 `vendor/`。

`assistant_zh/workflow/video_framework_slicer/` 里同时混着两种东西：**可复用的引擎能力**（渲染管线、字幕纠错、人脸定位）和**张和这一个号的业务编排**（文案/标题/关键词生成、选段清单、成片产物、锁定的视觉版式）。两者纠缠在一起，导致：

- 换一个博主 / 第二个号想复用这套切片能力时，必须整目录复制改张和硬编码；
- 工具层（tools）无法把这套能力当作稳定 engine 对外提供，违背「业务 agent 调工具、不留私有副本」的原则；
- `registry.yaml`（schema v2，本仓库唯一真源）的 engine 清单**不完整**——线上最重要的成片能力根本没登记。

### 1.2 目标

把**可复用的视频剪辑引擎能力全部集中到 `tools/engines/` 下统一管理**，并把**各项目的定制化也集中在工具内**（按 account 组织的定制层，而非散回各项目）。调用方退化成「选 profile + 选产物落点」。完成态可检查：

| # | 可检查的完成标准 |
|---|---|
| G1 | 「框架页渲染 / 字幕纠错 / 分页 / 人脸定位」等通用能力全部位于 `tools/engines/` 下，`assistant_zh/workflow/` 不再含可复用引擎代码。 |
| G2 | 各账号的定制化（锁定几何 `GEOM`、HTML 模板、术语表、选题/文案/标题规则）**从引擎代码剥离并集中**到 `engines/<engine>/profiles/<account>/`，引擎通过 `--profile` 读取（沿用 `personas/zh_main.md` 模式，多租户）。**定制不散回各项目。**（见 §3.2） |
| G2b | 工具直出产物默认落 `tools/var/<account>/`，引擎暴露 `--out` 让各项目可指定自己预期的最终地址；项目在产物之上的额外加工（发布版/定稿文案）由项目自管。 |
| G2c | **能力即积木、组合可选**（架构主轴，见 §3.4）：剪辑/改造/叠加各项能力是 catalog 里的独立原子，AI 调用时按视频选组合；句级与词级剪辑**共存**为两个可选策略；当前业务流 = 一条命名 recipe。新能力（结尾卡、字幕加粗变色、画面多排布…）以"往 catalog 加一个原子 + 被 recipe 引用"接入，不改管线骨架。 |
| G3 | `registry.yaml` 的 engines 清单与实际目录一致：新增/更新所有视频引擎条目（含新增 `video-compose` 组合层），并补依赖关系。 |
| G4 | **线上生产流程在迁移后产出不变**：用迁移前的同一份选段清单跑迁移后的管线，成片与迁移前逐帧/逐字一致（或差异可解释）。 |
| G5 | `assistant_zh/tmp/` 下的视频实验脚本：有保留价值的固化进 tools（如方案A 基准 `select_clips.py`），其余清理或归档。 |

### 1.3 不在本次范围内（非目标）

- 不改任何剪辑算法 / 视觉版式效果——这是**纯搬运 + 解耦**，不是重构成片观感。锁定几何值原样迁移。
- 不**重做**方案B 本身——但本迁移必须与方案B 协调推进，见 §1.4。方案B 代码（`video-slicer/twostage/`）已在 tools 下、位置正确。
- 不动发布链路（`tencent-video-publish`、`platform-publish`）。
- 不做选段质量评测 / A-B 盲评（另立项）。

---

## 1.4 平行路线：核心业务流程的架构升级（方案B）

本迁移**不是孤立发生的**。与「代码集中化」同时进行的，还有另一条路线——**对核心切片业务流程本身的架构升级**，即方案B（引入字级时间戳后做的升级）。两条路线正交，必须并排讲清，否则迁移会把一个**正在被替换的旧架构当成稳定目标冻结下来**：

| | 这条路线解决什么 | 载体 |
|---|---|---|
| **本文档（集中化迁移）= 空间维度** | 代码**住在哪**：把可复用能力收拢到 `tools/engines/` | 全部视频引擎目录 |
| **方案B（架构升级）= 能力维度** | 选段 / 切片**怎么做得更准**：从单阶段升级为两阶段 + 字级时间戳 | `video-slicer/twostage/` |

### 方案B 涉及的内容（架构升级的实质）

1. **字级时间戳 ASR**：引入阿里百炼 paraformer-v2，拿到「字级 / 字聚集」时间戳。该 API 只接受公网 URL → 用阿里云 OSS 做临时中转（本地音频上传 → 预签名 URL → 转录 → 用完清理 OSS 对象）。凭证落 `var/credentials/aliyun.env`（gitignored）；spike 在 `video-research/spikes/paraformer_v2_eval.py`，**待产品化**为引擎可复用模块。
2. **架构原则「AI 只读文字、代码定时间戳」**：AI 只按内容选「要哪几段话」（按句号 ID），**绝不碰时间戳**；选中的句号 → 精确到毫秒的切点是后续代码的活。这与线上方案A（单次 LLM 同时定选题 + mm:ss）是**根本不同的架构**。
3. **两阶段选段**：阶段一选题（编辑判断 → 粗句号区间 `rough_sid_spans`，不吐时间戳）+ 阶段二定脚本（窗口内按 in/out 纪律精选 `keep_sids`，支持跳接）。已建成于 `video-slicer/twostage/`，张和人设隔离在 `personas/zh_main.md`。
4. **字级 resolver / 句中精剪**：`resolve.py` 把句级粗边界吸到 paraformer 字间静音中点。真正的大杠杆是「句中切」——软铺垫与钩子在同一句时，切到句中的钩子词——需要阶段二从「选句号」升级到「选字/词」。**此项待用户确认是否启动。**
5. **对照验证**：方案A（线上单阶段 `select_clips.py`）vs 方案B vs 金标准（已发布切片 `out_v1/out_v2`），**脚本级**对比，看哪条流程选得更好。

### 两条路线的耦合点（本迁移必须照顾，否则会撞车）

- **方案B 是本迁移的「活范本」**：它已经直接建在 `tools/` 下，遵循「AI 只读文本、账号特定内容进 persona」的解耦范式。其余要搬的代码应**照它的样子搬**，而不是另起一套。
- **句级（方案A）与词级（方案B）是共存的两种剪辑能力，不是替代关系**：二者都长期留在 catalog 里作 `cut_sentence` / `cut_word` 两个可选策略，**AI 按视频选用哪条**（见 §3.4）。不存在"谁胜出谁下线"——线上句级稳定在用，词级调通后作为另一可选项加入。本文档 §4 阶段 1「固化方案A 基准」即把句级策略固化进 catalog。
- **字级时间戳牵动引擎布局**：resolver 依赖 paraformer 词源 → 关联 `video-research/spikes` 的产品化与 OSS 凭证管理，这本身就是引擎层要安排的一部分（词源该由哪个引擎、哪条命令产出）。
- **选段→渲染目前根本不连通（最关键，见 §3.3）**：方案B 的产物与渲染管线的输入 schema **现在就对不上**，不是"将来字级才有的问题"。方案B 输出 `keep_sids / sentence_time_spans`（句级秒数），而 `run_pipeline.py` 要的是 `segments:[{start:"HH:MM:SS", end}]`。两条路线**现在物理上不连通**——中间缺一个适配层。本迁移必须把这个汇合点显式定义出来（哪个引擎拥有、字段怎么映射），否则端到端 G4 验证无从谈起。
- **字级的下游延伸**：在上面适配层之上，若阶段二进一步升级到字级「句中切」，渲染 / 切片侧还要能吃**毫秒级 spans**。故新建 `video-framework-render`（§4 阶段 3、5）时，切片入口直接按毫秒 spans 设计、**不要焊死在句级**，一步到位为字级预留。

---

## 2. 当前分布全景（迁移前快照，已逐目录核实）

### 2.1 ✅ 已在 `tools/` 下，位置正确，本次不动或仅登记

| 路径 | 能力 | 备注 |
|---|---|---|
| `engines/video-slicer/` | AI 选段规划（planner/renderer/subtitles/transcript/llm…） | 生产 |
| `engines/video-slicer/video_slicer/twostage/` | 方案B 两阶段选段（index/stage1/stage2/pipeline/resolve） | 新建，正确 |
| `engines/video-slicer/personas/zh_main.md` | 张和选题人设（**解耦范本**） | 新建，正确 |
| `engines/video-research/` | URL 字幕 / 关键帧 / 元数据；本地转写；`spikes/paraformer_v2_eval.py` 字级时间戳 | 生产 + spike |
| `engines/video-clip/` | 剪辑合成原子库（拼接/进度条/片尾/变速/字幕烧录/遮名/封面…） | 生产，已吸收部分后处理原子 |
| `engines/tencent-video-publish/` | 视频号发布 CLI | 生产 |
| `skills/video-content/`、`skills/video-clip/` | 触发入口 | 生产 |

### 2.2 🔴 在 `assistant_zh/`，需要处理

**`assistant_zh/workflow/video_framework_slicer/`（线上成片主流程，1595 行 py + js）**

| 文件 | 行数 | 性质 | 去向 |
|---|---|---|---|
| `slicer.py` | 300 | 渲染管线（locate→assets→pages→subs→compose→accelerate）；含锁定 `GEOM`/`SUB`/`PAGE_CSS` | **引擎**；视觉值→定制层① `profiles/<account>` |
| `render_page.js` | 15 | puppeteer 渲染页 PNG | **引擎** |
| `pages_gen.py` | 154 | LLM 逐字稿→框架页 spec（已复用 video-slicer 的 llm 客户端） | **引擎**；prompt→定制层① |
| `srt_fix.py` | 152 | LLM 字幕术语纠错（1:1 保时间轴；含张和领域术语表） | **引擎**；术语表→定制层① |
| `run_pipeline.py` | 152 | 编排：选段清单→切片→pages→渲染→挑片索引 | **引擎**（薄管线，`--profile` + `--out` 参数化） |
| `gen_copy.py` / `gen_title.py` / `batch_gen.py` / `batch_title.py` / `build_keywords.py` | ~325 | 文案/标题/关键词**生成逻辑**（prompt + 参数可定制） | **定制层①**：生成 prompt/参数 → `profiles/<account>`（集中，不散回项目） |
| `make_publish.py` | 118 | 遮学员名闪帧(通用) + 裁片头 `c01:33s` / `CLIPS` 名单(项目加工) | **拆分**：遮名→video-clip 原子；裁片头/名单→③项目自管 |
| `rerender_subs.py` | 54 | 字幕重渲工具 | 引擎或弃 |
| `parse_candidates.py` | 75 | 选段候选解析 | 视耦合度定 |
| `finalize.py` | 214 | 内嵌 `FINALS` **人工定稿文案** + 写 `publish_copy.md` | **③项目自管**：定稿是工具产物之上的人工加工，放哪项目决定 |
| `jobs/` `selections/` `keywords_pool.json` `fixes.json` | — | 每场选段输入 / 运行数据 | 工具直出②→默认 `tools/var/<account>/`（`--out` 可改） |
| `out_v1/` `out_v2/` 成片 | — | `accel.mp4` 渲染直出(②) + `publish.mp4` 遮名发布版(③) | ②直出→`var/<account>`；③发布版/金标准→项目自管 |

**`assistant_zh/workflow/video_vertical/`（竖屏布局成片）**

| 文件 | 性质 | 去向 |
|---|---|---|
| `reframe_locate.py` | 人脸重心定位（通用 CV 能力） | **引擎** |
| `render_transparent.js` / `render720.js` | 渲染 | **引擎** |
| `layout.html` / `endcard.html` / `title_overlay.html` | 版式模板（张和视觉） | **引擎**（作 template 资源） |
| `video_progress.yaml` / `make_sample.sh` | 配置 / 样例 | 随引擎或留业务 |

**`assistant_zh/tmp/`（实验 + 数据）**

| 路径 | 性质 | 去向 |
|---|---|---|
| `slice_prompt_iter/select_clips.py` | 单阶段选段（**方案A 基准**，方案B 对照用） | 固化进 tools 做基准 |
| `slice_copy_test/` | 文案多 LLM 对比 | 评估后弃/归档 |
| `semester3_slicing/`、`semester*_切片候选.md`、`*_transcript.md` | 期次素材 / 数据 | 留业务或归 var |
| `camp4_render_clips.py`、`migrate_v1_slices.py`、`mint_video_items.py`、`slicer_backstop_validation.py` | 零散一次性脚本 | 清理 / 归档 |

---

## 3. 目标架构（迁移后）

> **主轴是 §3.4 的「能力 + 组合」，不是引擎边界。** 本节(§3.1)只回答「原子代码物理住哪个引擎」——是布局，不是组织原则。对外暴露的是一张能力表 + 配方，不是三个引擎。

### 3.1 引擎布局（原子的物理归属）

每个引擎是一座「积木厂」，只**提供**它那类能力原子并在 `capabilities.json` 里声明；**不互相调用、不当指挥**（指挥权在 §3.4 的 `video-compose`）。

```
tools/engines/
├── video-slicer/             提供「剪辑策略」原子：cut_sentence(句级) · cut_word(词级·方案B)
│   ├── video_slicer/         planner + twostage + pages_gen + srt_fix（迁入）
│   ├── capabilities.json     声明本引擎提供的原子
│   └── profiles/<account>/   定制层①（见 §3.2）：persona + 术语表 + 文案/标题规则
│
├── video-framework-render/   提供「改造/渲染」原子：framework_reframe(PPT页化) · raw(不改造)
│   ├── render.py             ← slicer.py 渲染核心，拆成可被组合的原子（compose/accelerate/subs）
│   ├── reframe_locate.py     ← video_vertical 人脸定位
│   ├── render_page.js        ← puppeteer
│   ├── capabilities.json     声明本引擎提供的原子
│   └── profiles/<account>/   定制层①：GEOM/PAGE_CSS/HTML 模板（张和为内置默认）
│
└── video-clip/               提供「叠加」原子（现有）：progress_bar · endcard · subtitle_ai_fix ·
    ├── atoms/                  subtitle_burn · speed_adapt · name_mask · concat · cover_frame …
    └── capabilities.json     声明本引擎提供的原子
```

> D1（已定）：`pages_gen` / `srt_fix` 归 `video-slicer`——「读逐字稿做 LLM 决策」≈ slicer 家族，已复用其 llm 客户端，最内聚。见 §7.1。

### 3.2 多租户 + 定制化：定制集中在工具，不散回各项目

**核心原则（本节为架构基石）**：`tools/` 是**服务多个项目的平台**。每个项目（张和号 / 其他号 / 其他业务）各有自己的定制化部分。这些定制**本就属于 skill 的一部分——skill 支持定制化**，因此**集中在工具内、按 account 组织**，而**不是散回各项目**（散回去 = 多份近似副本，skill 必然失控）。项目调用时**只需「选中」自己那一份 profile**。即使某项目暂时还没有特殊定制，结构也先预留。

由此，原来想「回落 assistant_zh」的东西按**性质**重新归位到三个地方：

| 类别 | 例子 | 归位 |
|---|---|---|
| **① 定制化逻辑 / 配置**（skill 的定制层） | persona 选题规则、术语表、GEOM/模板、文案/标题生成的 prompt 与参数（`gen_copy`/`gen_title`/`build_keywords` 的可定制部分） | `tools/engines/<engine>/profiles/<account>/` —— **集中、版本管理** |
| **② 工具直出产物**（skill 直接产生的内容） | `accel.mp4` 渲染直出、`clip.srt`/`fixed.srt`、`pages.json`、AI 文案候选 | **默认** `tools/var/<account>/`（gitignored）；**且引擎暴露 `--out` 让各项目可指定自己预期的最终地址** |
| **③ 项目在产物之上的额外处理**（不归工具管） | `publish.mp4`（遮名+裁片头后的可发布版）、`FINALS` 人工定稿文案、发布记录/物料库 | **项目自己管**，放哪由项目决定 |

```
tools/engines/video-slicer/profiles/zh_main/      定制层①：persona + 术语表 + 文案/标题规则
tools/engines/video-framework-render/profiles/zh_main/   定制层①：GEOM/模板
tools/var/zh_main/                                工具直出产物②（默认家，--out 可改）
└── selections/ pages/ clips/ ...

assistant_zh（调用方）                            退化成「选 profile=zh_main + 触发」+ 管自己的③
└── 发布物料 / publish.mp4 / 定稿文案库            项目自管（②的产物之上的再加工）
```

调用方的 `run` 脚本变成**薄胶水**：调 `video-slicer --profile zh_main`（选内容）→ `video-framework-render --profile zh_main [--out 项目指定地址]`（渲染）→ `tencent-video-publish`（发布）。它**几乎不留视频逻辑**，只做 profile 选择、产物落点选择、以及③的项目自管部分。

> **关于「定制化逻辑」能否都做成配置**：当前张和的文案/标题/选题规则大多能表达为 profile 配置（prompt + 参数 + 术语表）。若将来某项目需要无法配置化的特殊代码，也作为该 engine 的 `profiles/<account>/` 下的定制 hook 集中存放，**仍不散回项目**。本计划先把这个定制层结构立起来，即使现在只有 zh_main 一个租户。

> ⚠️ **配置源反向依赖（待解决）**：当前 `tools/engines/video-slicer/.env` 是**符号链 → `assistant_zh/knowledge_base/.env`**，即「共享工具层」的 LLM provider 密钥/配置物理上归属业务项目。这与「tools 不依赖 assistant_zh」的目标 G2 相悖。迁移须把 .env 真源归位（落 `var/credentials/` 或 tools 侧，符号链反向），与已合规的 `var/credentials/aliyun.env` 对齐；否则 assistant_zh 一旦解耦/改名，所有走 LLM 的引擎（planner / twostage / srt_fix / pages_gen）会因断链静默失效。

### 3.3 集成缝隙：选段产物 → 渲染管线（两条路线的汇合点）

这是方案B（能力升级）与渲染引擎（本迁移）**必须对接**的接口，目前缺失：

| | 方案B 选段产物（`twostage/pipeline.py`） | 渲染入口（`run_pipeline.py`） |
|---|---|---|
| clip 标识 | `title` | `name` + `title` |
| 切点 | `keep_sids` / `sentence_time_spans:[[秒,秒]]` | `segments:[{start:"HH:MM:SS", end:"HH:MM:SS"}]` |
| 分页提示 | （无直接字段；候选 `one_argument`） | `hint`（pages_gen 用） |
| 时间粒度 | 句级秒数（将来字级毫秒） | MM:SS 字符串（句级） |

**必须定义**（建议作为执行前 grill / preflight 的输入）：
1. **适配层归属**：`keep_sids/sentence_time_spans → segments` 的转换，归 `video-slicer`（产出标准 job）还是 `video-framework-render`（消费时转换）？建议归 video-slicer，让它直接吐渲染可吃的 job schema。
2. **`hint` 来源**：从方案B 的 `title` / `one_argument` 映射，还是新增字段。
3. **粒度（已定，D6）**：适配层与切片入口走**数值秒 spans**（粒度中立，毫秒可塞入同一接口），不中转回 MM:SS 字符串。见 §7.2。
4. **统一 job schema**：定义一份「选段 → 渲染」的稳定中间契约 JSON，两个引擎按它对接，业务薄胶水只负责串联。

### 3.4 架构主轴：能力 → 配方 → 选择 → 引擎（四层）

整套视频剪辑的根本组织原则**不是引擎边界，而是「原子能力 + 可选组合」**。`video-clip` 现有的 `catalog.json`(能力表) + `recipes.json`(配方) 已是此模型的雏形（`framework_slice` 配方已把当前业务流建模为 `delegate`）。本计划把它**提升为整条管线的主轴**，并按**方案A：独立薄组合层**落地。

```
① 能力层 catalog（真源·跨引擎聚合）  原子，AI 可单选/组合：
     剪辑策略:  cut_sentence(句级·线上) │ cut_word(词级·方案B)   ← 共存，AI 按视频选
     改造:      framework_reframe(PPT页化) │ raw(不改造直出)
     叠加:      progress_bar │ endcard │ subtitle_ai_fix │ subtitle_burn │ speed_adapt │ name_mask
     (未来):    字幕加粗/变色 │ 画面多排布 …  ← 往这层丢一个原子即接入

② 配方层 recipes（真源·命名预设）   一条配方 = 能力的有序组合：
     zh_business = cut_sentence + framework_reframe + subtitle_ai_fix(默认开) + progress_bar + endcard
     raw_quickcut = cut_word + raw + subtitle_burn
     (AI 也可不走预设，按视频临时组合)

③ 选择层 select                     AI 读视频 → 选 recipe，或自由组合 capabilities

④ 引擎层（§3.1，代码住哪）           原子物理分布在三个"积木厂"引擎
```

**落地结构（方案A · 独立薄组合层 `video-compose`）**：

```
tools/engines/
├── video-compose/            ★ 组合层(新·薄)：唯一对外入口，只指挥不产原子
│   ├── catalog.json          总能力表（从各引擎 capabilities.json 汇总）
│   ├── recipes.json          命名预设（zh_business / raw_quickcut …）
│   ├── select.py             AI 读视频 → 选配方 / 自由组合
│   └── run.py                按组合编排，跨引擎调原子
│
├── video-slicer/             积木厂：剪辑策略原子（capabilities.json 声明）
├── video-framework-render/   积木厂：改造/渲染原子
└── video-clip/               积木厂：叠加原子（现有 catalog/recipes 内容上移到 video-compose）
```

- **依赖单向**：`video-compose → 各引擎`；各引擎互不依赖、不当指挥。每个引擎一个角色（只产积木）。
- **扩展即插**：新能力做好（如你正调的 `endcard`、未来字幕加粗变色、画面多排布）→ 在所属积木厂加原子 + 在 `capabilities.json` 声明 + 在 recipe 引用，**管线骨架不动**。
- **当前业务流 = `zh_business` 这条 recipe**：今天是 `recipes.json` 里的 `framework_slice`(delegate 到 assistant_zh)；迁移目标是把渲染核心拆原子后，它变成 `video-compose` 里一条 `chain` 配方。
- `video-clip` 现有的 `catalog.json`/`recipes.json` 内容**上移**到 `video-compose`（真源唯一）；`video-clip` 退回纯积木厂，只留 `capabilities.json` 声明自己的原子。

---

## 4. 迁移分期（按风险递增，可分批停下）

### 阶段 0 · 准备与基线锁定（零风险，先做）
1. 在迁移前，用现有线上流程跑 1–2 条代表 clip，保存成片 + 中间产物（pages JSON / fixed.srt / accel.mp4）作为 **G4 回归基线**。
2. 记录线上流程当前的精确调用方式与依赖（venv / node puppeteer / ffmpeg / .env）。

### 阶段 1 · 固化基准与实验脚本（零风险，不碰线上）
- 把方案A 基准 `tmp/slice_prompt_iter/select_clips.py` 复制进 tools（如 `engines/video-slicer/baselines/`）做方案对照。
- 清理 / 归档 `tmp/` 下确认无用的一次性脚本。

### 阶段 2 · 迁移「LLM 内容决策」能力（低风险）
- `pages_gen.py`、`srt_fix.py` 迁入 `video-slicer`。这两个本就 `sys.path` 反向依赖 video-slicer 引擎，迁入后改为正常包内导入，**消除跨项目硬路径**。
- 张和术语表 / 分页 prompt 风格抽到定制层 `profiles/zh_main/`（`personas/zh_main.md` 扩展或并列文件）。
- 验证：同一 clip.srt 跑迁移后 `pages_gen`/`srt_fix`，输出与基线一致。

### 阶段 3 · 迁移「像素渲染」能力，新建 video-framework-render（中风险）
- 新建 `engines/video-framework-render/`，迁入 `slicer.py`（渲染部分）、`render_page.js`、`reframe_locate.py`、渲染 js、HTML 模板。
- **渲染核心拆成可组合原子**（compose / accelerate / subs / framework_reframe / raw…），在 `capabilities.json` 声明，供 §3.4 组合层引用——不做成单体黑盒。
- 锁定几何 `GEOM`/`SUB`/`PAGE_CSS` 与 HTML 模板**原样**迁入定制层 `profiles/zh_main/`，引擎读 `--profile zh_main`。
- 建独立 venv（pillow + opencv-python-headless）+ node puppeteer 依赖说明。
- 验证：用阶段 0 基线的 pages JSON + clip 渲染，**逐帧比对**成片与基线一致。

### 阶段 4 · 后处理去重（中风险）
- 只处理 `make_publish.py` 的**遮学员名闪帧**：与 `video-clip` 原子比对，能合并的合并进 `video-clip`，避免两份实现。
- `make_publish.py` 的裁片头（`c01:33s`）+ `CLIPS` 名单 + 读 `out_v1` 是工具产物之上的项目加工，**③项目自管**。
- `finalize.py` **不在本阶段**——它内嵌人工定稿文案，属③项目自管（见 §2.2 更正）。

### 阶段 5 · 定制层归集 + 编排薄化（中风险，动线上入口）
- 建 `engines/<engine>/profiles/zh_main/`，把 persona / 术语表 / GEOM-模板 / 文案-标题 prompt 参数**集中迁入定制层**（不散回项目）。
- `run_pipeline.py` 的编排逻辑改造为组合层可调的形态，`--profile` + `--out`（可配置产物地址）参数化。
- `assistant_zh` 侧退化为薄胶水：选 `profile=zh_main`、选产物落点、管自己的③（发布版/定稿文案）。
- 验证 G4：同一份选段清单端到端跑通，成片与基线一致。

### 阶段 5b · 组合层 video-compose（中风险，架构主轴落地）
- 新建薄引擎 `engines/video-compose/`：`catalog.json`(总能力表，从各引擎 `capabilities.json` 汇总) + `recipes.json`(命名预设) + `select.py`(AI 选组合) + `run.py`(跨引擎编排)。见 §3.4。
- 三个积木厂引擎各加 `capabilities.json` 声明自己提供的原子；`video-clip` 现有 `catalog/recipes` 内容**上移**到 video-compose（真源唯一）。
- 把当前业务流固化为 `zh_business` recipe（cut_sentence + framework_reframe + subtitle_ai_fix + progress_bar + endcard）；句级/词级作 `cut_sentence`/`cut_word` 两个共存能力。
- 验证：经 `video-compose` 选 `zh_business` 跑通，成片与 G4 基线一致；另选一条最小 recipe(如 raw + subtitle_burn)验证组合可换。

### 阶段 6 · 登记与文档收口（零风险）
- 更新 `registry.yaml`：新增 `video-framework-render` + `video-compose`，更新各引擎 `purpose` 与依赖（compose→各引擎单向）。
- 跑 `scripts/check-tools.py`（必要时 `sync-skills.py`）。
- 更新本仓库 `CLAUDE.md` / `README.md` 与 engine 内 README，删除 `assistant_zh` 侧失效指引。

---

## 5. 关键风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 动到线上正在用的成片流程，产出回归 | 高 | 阶段 0 先锁基线；每阶段用基线逐帧/逐字比对（G4）；分批迁移，每批独立可验证可回退。 |
| 跨项目硬编码路径（`srt_fix`/`pages_gen` 里写死 video-slicer 绝对路径） | 中 | 迁入同仓后改为包内导入；全局搜 `assistant_zh` 绝对路径残留。 |
| 锁定几何/版式在搬运中被无意改动 | 中 | 视觉值原样平移到 template，禁止顺手调参；逐帧比对兜底。 |
| 依赖环境（venv / puppeteer / ffmpeg）在新 engine 缺失 | 中 | 每个新 engine 自带 requirements + README，首跑校验。 |
| 业务与引擎边界判断错误（把张和业务当通用件搬错） | 中 | §3 边界先评审（§7）再动手；区分①定制逻辑/②工具产物/③项目加工三类归位。 |
| **定制化散回各项目**：每个号一份近似副本，skill 失控 | 中 | 见 §3.2：定制集中在 `profiles/<account>` 定制层，调用方只选 profile，不持有视频逻辑。 |
| **与平行路线方案B 撞车**：把方案A 旧架构冻结为目标；渲染引擎切片入口焊死在句级，方案B 句中精剪落地时要回头改 | 高 | 见 §1.4 耦合点：引擎同时容纳方案A/B；新建 render 引擎时切片入口预留字级毫秒 spans。 |
| **选段→渲染不连通**：方案B 产物 schema 与渲染入口现在就对不上，缺适配层，端到端无法跑通 | 高 | 见 §3.3：执行前先定统一 job schema + 适配层归属，再动渲染引擎。 |
| **配置源反向依赖**：`video-slicer/.env` 符号链指向 `assistant_zh`，业务一解耦即断链，LLM 引擎静默失效 | 中 | 见 §3.2：.env 真源归位到 `var/credentials/` 或 tools 侧，符号链反向。 |

---

## 6. 验证清单（Definition of Done）

- [ ] G1：`assistant_zh/workflow/` 下无可复用引擎代码（grep 确认）。
- [ ] G2：各账号定制（视觉/术语/选题/文案-标题规则）全集中在 `engines/<engine>/profiles/<account>/`，引擎代码无账号硬编码，定制未散回任何项目。
- [ ] G2b：工具直出产物默认落 `tools/var/<account>/` 且 `--out` 可改落点；③项目加工归项目自管。
- [ ] G3：`registry.yaml` 引擎清单与目录一致；`scripts/check-tools.py` 通过。
- [ ] G4：同一选段清单，迁移后成片与阶段 0 基线一致（逐帧/逐字）。
- [ ] G4b（集成缝隙，见 §3.3）：选段产物经统一 job schema 能直接驱动渲染管线，方案B 端到端跑通一条 clip。
- [ ] G5：`tmp/` 实验脚本已固化或归档，无遗留散落脚本。
- [ ] G6（配置源，见 §3.2）：`video-slicer/.env` 不再反向依赖 `assistant_zh`，真源归位且各引擎 LLM 调用正常。
- [ ] 文档：`CLAUDE.md`/`README.md`/各 engine README 已更新，无失效指引。

---

## 7. 决策记录（已定）

### 7.1 已定（技术判断，可推翻）

- **D1 引擎边界**：`pages_gen` / `srt_fix` 归 **`video-slicer`**。两者都「读逐字稿 → LLM 决策」（分页 / 纠错），已复用 video-slicer 的 llm 客户端与 `.env` 发现，归内容决策家族最内聚；渲染引擎保持纯像素。
- **D2 新引擎命名**：新建 **`video-framework-render`**，不并入 `video-clip`。它是多阶段合成管线（locate→pages→subs→compose→accelerate）+ 重依赖（opencv / puppeteer），与 `video-clip` 的无状态原子库性质不同；并入会撑爆原子库。`video-clip` 继续只放原子。
- **D4 成片产物**（已由 §3.2 解决）：工具直出②默认落 `tools/var/<account>/` 且 `--out` 可改落点；项目在产物之上的加工③由项目自管。
- **D5 调用方命名**：默认把 `assistant_zh/workflow/video_framework_slicer/` 退化后的残留重命名为 `zh_video/`（薄胶水 + ③物料），反映「只选 profile + 管自己发布物料」。低风险、可改。

### 7.2 已定（用户拍板，2026-06-14）

- **D3 执行范围 = C：仅出本计划，暂不执行**。本计划定稿即停，不动任何代码，留作后续排期。下面的阶段 0–6 是「将来执行时」的蓝图，当前不启动。
- **D6 切片入口粒度 = 数值秒 spans（粒度中立）**。`video-framework-render` 的切片入口收 `[[start_sec, end_sec], ...]` 数值秒，**不用 MM:SS 字符串**。理由：
  - 数值秒是 MM:SS 的**超集**——线上**句级**现状直接可用（句边界秒数传入），迁移零额外风险，G4 逐帧比对照常；
  - **不焊死也不预投入**：方案B 将来若跑通要做字级句中切，毫秒精度天然塞进同一接口，不回头改引擎；
  - **不绑定方案B**：线上不依赖字级（见下），方案B 还没通，本迁移不替其未验证效果背书。

> **背景澄清（D6 前提）**：线上生产流程用的是腾讯 minutes 的**句级**时间、单阶段选段、ffmpeg 按句切——**句级精度，不依赖字级**。字级/毫秒（paraformer + 两阶段 + 句中精剪）是**方案B**，并行路线、效果调试中、整链未通（见 §1.4）。故切片接口按「数值秒」即可服务线上，无需为未通的方案B 预先字级化。

> ✅ **§7 全部决策已定。本计划状态 = 定稿待排期（D3=C，暂不执行）。** 将来启动时按阶段 0 起步。
