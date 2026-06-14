# 视频剪辑工具集中化迁移计划

> 文档位置：`tools/doc/video-tools-migration-plan.md`
> 起草日期：2026-06-14
> 状态：**待评审**（执行前需用户确认范围，见 §7）

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

把**可复用的视频剪辑引擎能力全部集中到 `tools/engines/` 下统一管理**，让 `assistant_zh` 只保留「张和这个号的业务编排与产物」。完成态可检查：

| # | 可检查的完成标准 |
|---|---|
| G1 | 「框架页渲染 / 字幕纠错 / 分页 / 人脸定位」等通用能力全部位于 `tools/engines/` 下，`assistant_zh/workflow/` 不再含可复用引擎代码。 |
| G2 | 张和特定内容（锁定几何 `GEOM`、HTML 模板视觉、术语表、选题/文案/标题规则）**从引擎代码中剥离**，落到 persona / template 配置文件，引擎通过 `--persona`/`--template` 参数读取（沿用已建成的 `personas/zh_main.md` 模式）。 |
| G3 | `registry.yaml` 的 engines 清单与实际目录一致：新增/更新所有视频引擎条目，并补 `tools/engines` 下视频引擎之间的依赖关系。 |
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
- **迁移不能把方案A 当唯一目标冻结**：`video-slicer` 引擎要**同时容纳**方案A（作基准/对照）与方案B（新主线），二者并存，直到方案B 验证胜出再决定是否下线方案A。本文档 §4 阶段 1「固化方案A 基准」正是为此服务。
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
| `slicer.py` | 300 | 渲染管线（locate→assets→pages→subs→compose→accelerate）；含锁定 `GEOM`/`SUB`/`PAGE_CSS` | **引擎**（视觉值→template 配置） |
| `render_page.js` | 15 | puppeteer 渲染页 PNG | **引擎** |
| `pages_gen.py` | 154 | LLM 逐字稿→框架页 spec（已复用 video-slicer 的 llm 客户端） | **引擎**（prompt→persona） |
| `srt_fix.py` | 152 | LLM 字幕术语纠错（1:1 保时间轴；含张和领域术语表） | **引擎**（术语表→persona） |
| `run_pipeline.py` | 152 | 编排：选段清单→切片→pages→渲染→挑片索引 | **引擎**（薄管线，persona 参数化） |
| `make_publish.py` | 118 | **半生半业务**：遮学员名闪帧(通用) + 裁片头 `c01:33s` / `CLIPS` 名单 / 读 `out_v1`(张和业务) | **拆分**：遮名→video-clip 原子；裁片头/名单→业务 |
| `rerender_subs.py` | 54 | 字幕重渲工具 | 引擎或弃 |
| `parse_candidates.py` | 75 | 选段候选解析 | 视耦合度定 |
| `finalize.py` | 214 | ⚠️**纯业务，非视频后处理**：写 `publish_copy.md`（内嵌 `FINALS` 张和定稿文案 + 关键词），硬编码 `assistant_zh` 绝对路径 | **留 assistant_zh** |
| `gen_copy.py` / `gen_title.py` / `batch_gen.py` / `batch_title.py` / `build_keywords.py` | ~325 | 张和文案/标题/关键词生成 | **留 assistant_zh**（纯业务） |
| `jobs/` `selections/` `out*/` `keywords_pool.json` `fixes.json` | — | 业务输入 + 成片产物（`out_v1/out_v2` = 已发布金标准） | **留 assistant_zh**（产物，规约上属 var 类） |

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

### 3.1 引擎边界（清晰三分）

按「**做什么决策**」切分，而不是「都跟视频有关」：

```
tools/engines/
├── video-slicer/          内容决策：读逐字稿，AI 决定「要哪几段话 / 怎么分页 / 字幕怎么纠」
│   ├── video_slicer/      （现有 planner + twostage）
│   │   ├── twostage/      方案B 两阶段选段
│   │   ├── pages_gen.py   ← 从 framework_slicer 迁入（分页器）
│   │   └── srt_fix.py     ← 从 framework_slicer 迁入（字幕纠错）
│   └── personas/          张和等账号的「编辑判断 + 术语表 + 分页风格」
│
├── video-framework-render/   新引擎 · 像素渲染：把 spec + video 渲染成竖版成片
│   ├── render.py          ← slicer.py 渲染管线（compose/accelerate/subs）
│   ├── reframe_locate.py  ← video_vertical 人脸定位
│   ├── render_page.js     ← puppeteer
│   ├── pipeline.py        ← run_pipeline.py 薄编排（persona 参数化）
│   └── templates/         ← GEOM/PAGE_CSS/HTML 模板（按账号，张和为默认）
│
└── video-clip/            原子操作：拼接/进度条/片尾/变速/遮名/封面（现有 + 吸收 finalize/make_publish 去重）
```

> 备选方案：把 `pages_gen` / `srt_fix` 也放进 render 引擎而非 slicer。判据是「它读逐字稿做 LLM 决策」≈ slicer 家族，且已复用 slicer 的 llm 客户端，故归 slicer 更内聚。**此点待 §7 确认。**

### 3.2 `assistant_zh` 迁移后只剩业务

```
assistant_zh/workflow/zh_video/   （或保留原名）
├── gen_copy.py / gen_title.py / build_keywords.py   张和文案/标题/关键词
├── finalize.py                                       写 publish_copy.md（张和定稿文案物料）
├── selections/                                       张和选段清单（业务输入）
└── （成片产物 out*/ 按规约移入 var/ 或保留业务侧）
```

业务侧的 `run` 脚本变成**薄胶水**：调 `tools/engines/video-slicer`（选内容）→ `tools/engines/video-framework-render --persona zh_main`（渲染）→ `tools/engines/tencent-video-publish`（发布）。

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
3. **粒度**：适配层是否直接走秒级/毫秒 spans（一步到位为字级预留，呼应 §1.4 与决策点 6），而非中转回 MM:SS 字符串。
4. **统一 job schema**：定义一份「选段 → 渲染」的稳定中间契约 JSON，两个引擎按它对接，业务薄胶水只负责串联。

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
- 张和术语表 / 分页 prompt 风格抽到 persona（`personas/zh_main.md` 扩展或并列文件）。
- 验证：同一 clip.srt 跑迁移后 `pages_gen`/`srt_fix`，输出与基线一致。

### 阶段 3 · 迁移「像素渲染」能力，新建 video-framework-render（中风险）
- 新建 `engines/video-framework-render/`，迁入 `slicer.py`（渲染部分）、`render_page.js`、`reframe_locate.py`、渲染 js、HTML 模板。
- 锁定几何 `GEOM`/`SUB`/`PAGE_CSS` 与 HTML 模板**原样**迁入 `templates/zh_main/`，引擎读 `--template zh_main`。
- 建独立 venv（pillow + opencv-python-headless）+ node puppeteer 依赖说明。
- 验证：用阶段 0 基线的 pages JSON + clip 渲染，**逐帧比对**成片与基线一致。

### 阶段 4 · 后处理去重（中风险）
- 只处理 `make_publish.py` 的**遮学员名闪帧**：与 `video-clip` 原子比对，能合并的合并进 `video-clip`，避免两份实现。
- `make_publish.py` 的裁片头（`c01:33s`）+ `CLIPS` 名单 + 读 `out_v1` 属张和业务，**留 assistant_zh**。
- `finalize.py` **不在本阶段**——它是写文案物料的纯业务脚本，留 assistant_zh（见 §2.2 更正）。

### 阶段 5 · 编排薄化 + 业务回填（中风险，动线上入口）
- `run_pipeline.py` 改造为 `video-framework-render/pipeline.py`，persona/template 参数化。
- `assistant_zh` 侧留薄胶水脚本调三个引擎；文案/标题/选段清单留业务侧。
- 验证 G4：同一份选段清单端到端跑通，成片与基线一致。

### 阶段 6 · 登记与文档收口（零风险）
- 更新 `registry.yaml`：新增 `video-framework-render`，更新各引擎 `purpose` 与依赖。
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
| 业务与引擎边界判断错误（把张和业务当通用件搬错） | 中 | §3 边界先评审（§7）再动手；文案/标题/选题规则一律留业务。 |
| **与平行路线方案B 撞车**：把方案A 旧架构冻结为目标；渲染引擎切片入口焊死在句级，方案B 句中精剪落地时要回头改 | 高 | 见 §1.4 耦合点：引擎同时容纳方案A/B；新建 render 引擎时切片入口预留字级毫秒 spans。 |
| **选段→渲染不连通**：方案B 产物 schema 与渲染入口现在就对不上，缺适配层，端到端无法跑通 | 高 | 见 §3.3：执行前先定统一 job schema + 适配层归属，再动渲染引擎。 |
| **配置源反向依赖**：`video-slicer/.env` 符号链指向 `assistant_zh`，业务一解耦即断链，LLM 引擎静默失效 | 中 | 见 §3.2：.env 真源归位到 `var/credentials/` 或 tools 侧，符号链反向。 |

---

## 6. 验证清单（Definition of Done）

- [ ] G1：`assistant_zh/workflow/` 下无可复用引擎代码（grep 确认）。
- [ ] G2：张和视觉/术语/选题规则全在 persona/template，引擎代码无账号硬编码。
- [ ] G3：`registry.yaml` 引擎清单与目录一致；`scripts/check-tools.py` 通过。
- [ ] G4：同一选段清单，迁移后成片与阶段 0 基线一致（逐帧/逐字）。
- [ ] G4b（集成缝隙，见 §3.3）：选段产物经统一 job schema 能直接驱动渲染管线，方案B 端到端跑通一条 clip。
- [ ] G5：`tmp/` 实验脚本已固化或归档，无遗留散落脚本。
- [ ] G6（配置源，见 §3.2）：`video-slicer/.env` 不再反向依赖 `assistant_zh`，真源归位且各引擎 LLM 调用正常。
- [ ] 文档：`CLAUDE.md`/`README.md`/各 engine README 已更新，无失效指引。

---

## 7. 执行前需确认的决策点

1. **引擎边界**：`pages_gen` / `srt_fix` 归 `video-slicer`（内容决策家族，推荐），还是归新的 `video-framework-render`？
2. **新引擎命名**：`video-framework-render` 是否合适？（或 `video-vertical-render` / 并入 `video-clip`？）
3. **执行范围与节奏**：
   - **A. 仅阶段 0–2**（基线 + 实验固化 + LLM 能力迁移，不碰渲染/线上入口，低风险先行）；
   - **B. 阶段 0–6 全量**（含动线上渲染与编排，按阶段分批验证）；
   - **C. 仅出本计划，暂不执行**。
4. **成片产物 `out*/`**：迁后落 `var/`（合规约）还是保留 `assistant_zh` 业务侧？
5. **目录命名**：`assistant_zh` 侧业务残留是否重命名（如 `zh_video/`）以反映「只剩业务」？
6. **与方案B 的协同节奏**（见 §1.4）：本迁移与方案B 架构升级是**先迁移后升级**、**先升级后迁移**、还是**交织推进**？尤其：新建 `video-framework-render` 时是否现在就把切片入口改成字级 spans（为句中精剪预留），还是等方案B 阶段二升级确定后再改？

> 确认以上后即可从阶段 0 开始执行。默认建议：**先走 A**，验证解耦范式无误，再决定是否推进到动线上的 B。
