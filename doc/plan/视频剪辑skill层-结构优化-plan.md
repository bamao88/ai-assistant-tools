# 视频剪辑 skill 层 + 文档结构优化计划

> 写于 2026-06-19。读者是不读代码的 owner——先讲"是什么/为什么"，技术名词配大白话。
> 配套：引擎层的六环重构见 [`视频剪辑skill-六环阶段化升级-plan.md`](./视频剪辑skill-六环阶段化升级-plan.md)；架构真源 [`../video-skill-architecture.md`](../video-skill-architecture.md)。
> **本计划只管"用户触发的 skill 入口层 + 文档"，不动引擎内部能力（那是上面那份计划的事）。**

---

## Context（为什么做）

引擎层刚被梳理成**六环主链（转写→选片→裁剪→字幕→铸造→组装）+ `video-compose` 组合层**这套清晰认知。但**用户实际触发的 skill 入口层还停在旧划分**，对不上新流程，也对不上"`video-compose` 是唯一正门"的设计。owner 反馈"skill 结构不太清晰"，本计划把入口层和文档梳理对齐。

**skill 与 engine 的关系（先认清）**：skill = 用户说句话就能触发的**入口**（`skills/<name>/SKILL.md`）；engine = skill 在背后调用的**代码**（`engines/<name>/`，不能单独触发）。一个 skill 可以调多个 engine。

---

## 一、现状诊断：skill 层到底哪里不清晰

当前两个视频 skill + 五个视频 engine：

| skill（入口） | 调的 engine | 管什么 |
|---|---|---|
| `video-content` | `video-research` | 转写/字幕/关键帧/素材研究/标题（faster-whisper + yt-dlp） |
| `video-clip` | `video-clip` + `video-slicer` | 剪辑/合成；复杂框架页切片**路由回业务项目** |

| engine（代码） | 角色 |
|---|---|
| `video-research` | 通用转写/关键帧/研究（faster-whisper） |
| `video-slicer` | LLM 选片 + **字级转写(火山/阿里)** + pages/srt_fix/script_clean |
| `video-clip` | 叠加原子库（拼接/进度条/片尾/字幕/遮名…） |
| `video-framework-render` | 框架页渲染（圆窗/翻页/药丸字幕） |
| `video-compose` | **组合层·唯一对外入口**（selector 选配方 / run 跑链） |

**五个具体问题**：

1. **正门没人开**：`video-compose` 被设计成"唯一对外入口"（`selector` 选配方 → `run.py` 跑链），但**没有任何 skill 用它**。`video-clip` skill 直接调单个原子 + 把框架页路由回业务项目脚本，**绕过了组合层**。结果："选条配方一键出片"这个能力，AI 触发不到。
2. **端到端主线无人认领**：把一场长视频剪成口播切片成片这条**六环主线**，横跨 `video-content`(转写) + `video-clip`(剪辑) + 业务项目(选片/框架页)。**没有一个 skill 拥有整条线**；②选片还被 `video-clip` skill 明确划为"不归我管"，却也没别的 skill 接。
3. **"转写"指向不清**：转写散在两个 engine、分给不同语境——`video-research`(video-content skill，通用素材化) vs `video-slicer/transcribe`(切片管线内部字级)。用户说"转写"该走哪个，没讲清。
4. **名实不符 + 撞名**：skill 名 `video-clip` 和 engine 名 `video-clip` 撞名；而该 skill 实际驱动 `video-clip`+`video-slicer` 两个引擎、还路由整条切片线——它管的远不止"clip 叠加"。
5. **decision_gate 用的是旧划分**：`video-clip` skill 按"编辑类型(simple_concat/chaptered_growth/zh_business)"散列判断，**不是按六环阶段**，和刚定的流程认知脱节。

**额外的文档缺口**：`doc/video-skill-architecture.md` 通篇只讲**引擎**，**完全没讲 skill 入口层**——skill 怎么映射到六环、怎么经 `video-compose` 调引擎，一字未提。

---

## 二、目标：skill 层对齐"六环主线 + video-compose 正门"

```
用户说"把这场录屏剪成口播切片成片"
        │
        ▼
 ┌──────────────────────────────┐         素材化需求（"转成逐字稿/研究这视频"）
 │  video-clip(成片工作流·正门)   │              │
 │  decision_gate 按六环+源类型+风格 │              ▼
 │   → video-compose selector/run  │      ┌─────────────────┐
 │   → 选配方:zh_clip_cut/zh_business│      │  video-content   │
 │      /landscape/simple_concat…  │      │ 转写/字幕/关键帧/  │
 └──────────────────────────────┘      │ 研究/标题(素材化) │
        │ run.py 跨引擎编排              └─────────────────┘
        ▼
 video-slicer / video-clip / video-framework-render（积木厂·背后被调）
```

**一句话目标**：让**一个工作流 skill 拥有整条口播切片成片主线，且它的前门是 `video-compose`**（选配方→跑链），不再绕过组合层、不再直接路由业务项目；`video-content` 专注"把视频变可读素材"；两者边界讲清。

---

## 三、具体改动

### 改动 1：把 `video-clip` skill 升级成"成片工作流·正门"（核心）
- **decision_gate 重写**：从旧的"编辑类型散列"改成**按六环 + 源类型 + 目标风格**：
  1. 是不是端到端"把长视频剪成口播切片成片"？→ 走 `video-compose` 配方。
  2. 源类型是什么（干净口播 / 录屏 / 带噪）→ 决定挂哪些源适配。
  3. 要哪种风格（裁剪版 `zh_clip_cut` / PPT 框架页 `zh_business` / 横屏 `landscape_business`）。
  4. 只是 ad-hoc 单步（拼两段 / 加进度条 / 加片尾）→ 走 `simple_concat`/`chaptered_growth` 或直接点某原子。
- **前门改为 `video-compose`**：`selector.py --list` 看配方 → `run.py --run <recipe>` 跑链。**框架页不再直接路由业务项目脚本**；业务项目 `run_pipeline.py` 降为 `video-compose` 在过渡期委派的薄胶水（架构文档已是此设计）。
- **保留 ad-hoc 原子入口**：拼接/进度条/片尾/遮名等单步仍可直接调原子（沿用现有命令块），服务"只想拼一下"的轻需求。
- **命名（待拍板，见五）**：建议**保留 `video-clip` 这个名**（不改触发词、零迁移成本），只重写它的 scope/decision_gate；撞名问题在 SKILL.md 顶部一句话说明（"本 skill 是成片工作流入口，背后引擎之一也叫 video-clip"）。

### 改动 2：`video-content` skill 澄清"转写"边界
- SKILL.md 加一句边界说明：**video-content 的转写 = "把任意视频变成可读逐字稿/研究素材"**（通用 faster-whisper，给写文章/调研用）；**口播切片管线内部的字级转写**（火山/阿里，`video-slicer/transcribe`，要精确到字给字幕对齐用）是**成片工作流的引擎内部步骤**，不归 video-content，用户无需单独触发。
- 其余能力（关键帧/研究/标题）不动。

### 改动 3：registry.yaml 同步
- 更新 `video-clip` skill 的 `purpose`（成片工作流·经 video-compose 编排）与 `uses_engines`（加 `video-framework-render`、`video-compose`）。
- 若最终决定改名（见五），按"super-skill + 移除低层触发"在 `deprecated` 段登记旧触发词。

### 改动 4：sync-skills 收口
- 改完 `registry.yaml` 跑 `python3 scripts/sync-skills.py`（重建 `~/.claude/skills` 软链）+ `python3 scripts/check-tools.py`（期望 0 error）。**不手编 `~/.claude/skills`。**

### 改动 5：补 `doc/video-skill-architecture.md` 的"skill 入口层"章节（文档缺口）
- 新增一节：**skill 入口层 ↔ 六环 ↔ video-compose** 的映射图 + 一句话讲清"用户触发哪个 skill、它怎么经 video-compose 调到哪些引擎"。当前架构文档只有引擎层，这一节是缺的。
- 同步把六环主链图、`zh_clip_cut` 配方也带进来（与引擎计划 WS-6 合并做，避免两次改同一文档）。

---

## 四、落地顺序（轻量，4 步）

| 步 | 做什么 | 验收 |
|---|---|---|
| **S1** | 重写 `skills/video-clip/SKILL.md`：decision_gate 按六环+源类型+风格、前门=video-compose selector/run、保留 ad-hoc 原子、顶部说明撞名 | 念一遍 SKILL.md，能照着把"录屏→裁剪版切片"走通到 `run.py --run zh_clip_cut` |
| **S2** | 改 `skills/video-content/SKILL.md` 加转写边界说明 | "转写"语境不再和切片管线字级转写混淆 |
| **S3** | 更新 `registry.yaml`（purpose/uses_engines）；跑 `sync-skills.py` + `check-tools.py` | check-tools 0 error；软链正确 |
| **S4** | 补 `doc/video-skill-architecture.md` 的 skill 入口层章节（与引擎计划 WS-6 合并改一次） | 文档有 skill↔六环↔video-compose 映射；路径/名称与实际一致 |

> **依赖**：S1 的"前门=video-compose 跑 `zh_clip_cut`"依赖引擎计划把 `zh_clip_cut` 配方和 `run.py` chain 做出来（引擎计划 WS-1/WS-6）。所以**建议引擎计划 WS-1 起步后再做本计划 S1**，或先写 SKILL.md 指向 `zh_business`（已可跑）、待 `zh_clip_cut` 就绪补上。

---

## 五、待拍板

1. **`video-clip` skill 改不改名**？
   - **方案 A（推荐·零迁移）**：保名 `video-clip`，只重写 scope/decision_gate，撞名靠文档一句话说明。
   - **方案 B（更名实相符·有迁移）**：改名如 `video-edit`/`video-slice`（视频剪辑成片），迁移触发词、`deprecated` 登记旧名、重跑 sync-skills。改名要承担触发竞争与肌肉记忆成本。
2. **ad-hoc 单步剪辑**是继续并在这个成片工作流 skill 里（按 intent 分流），还是另立一个极轻的"原子拼接"util skill？（建议并在一起，避免触发竞争。）

---

## 六、不做 / 边界
- **不动引擎内部能力**：新原子/承重墙/自检门是引擎计划的事，本计划只动 skill 入口层 + 文档。
- **不动 `video-content` 的 `video-research` 引擎**：转写/关键帧/研究功能保持，只在 SKILL.md 澄清边界。
- **不碰 `zh_business` 渲染**：G4 视觉基线冻结，本计划只在 skill 里把它表述成"⑤铸造的 PPT 风格配方"。
