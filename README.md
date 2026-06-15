# AI_Assistant Tools

这是 `AI_Assistant` 各工作区共享的**工具与技能层**。所有自媒体相关的能力（抓取、发布、调研、排版、研究…）都集中放在这里，业务 Agent 调用这里的工具，而不是各自保留一份副本。

> 这份 README 是**给人看的**导览。给 AI/Agent 看的规则在 `CLAUDE.md`，机器可读的清单在 `registry.yaml`。

---

## 它是怎么组织的

四层结构，各司其职：

```
tools/
├── skills/    技能 —— Agent 真正会"触发"的入口（每个含一个 SKILL.md）
├── engines/   引擎 —— 技能背后真正干活的代码 / CLI，本身不会被触发
├── vendor/    外部 —— 第三方 clone（各自带 upstream git）
└── var/       运行时 —— 状态/产物/日志/草稿/凭证，不进 git
```

一句话理解：**skills 是"做什么"，engines 是"怎么做"，vendor 是"借来的轮子"，var 是"跑出来的东西"。**

技能按层级分三类：

- **L1 动作入口**（一个动作、跨平台的统一路由）：`platform-fetch`（抓取）、`platform-publish`（发布）。
- **L2 工作流**（把多个能力编排成一件事）：`blogger-research`（博主调研）、`xhs-ops`、`video-content`、`deep-research`。
- **原子 / 工具类**：`xhs-auth`、`xhs-interact`、`markdown-to-cards`、`screenshot`、`humanizer`、`dbs-*`。

---

## 能力清单

### 技能（会被 Agent 触发）

| 技能 | 层级 | 作用 |
|---|---|---|
| `platform-fetch` | L1 | 封闭平台内容抓取统一入口（小红书 / 公众号 / 腾讯会议官方 MCP / 视频字幕封面关键帧） |
| `platform-publish` | L1 | 发布与多平台分发统一入口（小红书 / 公众号 / 知乎掘金 CSDN 等全平台） |
| `blogger-research` | L2 | 博主调研：批量抓取博主公开内容 + 出结构化分析报告 |
| `xhs-ops` | L2 | 小红书复合运营工作流（搜+看+发+互动） |
| `video-content` | L2 | 视频内容处理（本地/URL 逐字稿、字幕、关键帧、素材研究、标题备选） |
| `deep-research` | L2 | 多源研究、引用跟踪报告（外部 skill） |
| `xhs-auth` | 原子 | 小红书登录 / 账号管理 |
| `xhs-interact` | 原子 | 小红书评论 / 点赞 / 收藏 |
| `markdown-to-cards` | 工具 | Markdown 转小红书卡片图片 |
| `screenshot` | 工具 | 网页截图 / 视觉验证 |
| `humanizer` | 工具 | 去 AI 味写作润色（外部 skill） |
| `dbs-*` | 外部 | dontbesilent 商业诊断工具箱（含小红书标题公式 `dbs-xhs-title`） |

### 引擎（技能调用的代码）

| 引擎 | 运行方式 |
|---|---|
| `xiaohongshu` | Python `.venv` — `scripts/cli.py`（登录/搜索/发布/互动） |
| `gzh-publish` | Node/tsx — `src/index.ts`（公众号排版发布） |
| `gzh-scraper` | Python — `scripts/cli.py` + wechat-article-exporter 服务 |
| `markdown-to-cards` | Node — `cli.js` |
| `platform-draft-direct` | Node — `src/cli.js`（知乎 / 掘金 / CSDN / 百家号 / 51CTO / 博客园 / 思否 / 开源中国 / B站专栏 / 搜狐号无插件草稿直传） |
| `video-research` | Python `.venv` — `scripts/cli.py` |
| `video-slicer` | Python 包 — 积木厂·剪辑策略原子 cut_sentence/cut_word + 内容决策 pages_gen/srt_fix（暂无独立技能） |
| `video-framework-render` | Python 独立 `.venv`(pillow+opencv) — `video_framework_render.render`；积木厂·框架页竖版渲染原子（ffmpeg+puppeteer） |
| `video-clip` | Python `.venv` — `atoms/*.py`；积木厂·叠加/通用剪辑原子库 |
| `video-compose` | Python — `selector.py`/`run.py`；组合层·唯一对外入口（catalog+recipes，指挥各引擎） |
| `tencent-meeting` | Python — 官方 MCP 桥接 `scripts/mcp_cli.py`（legacy 下载脚本保留） |
| `screenshot` | Node — `screenshot.js` |
| `route-bypass` | Zsh — 小红书发布网络分流 |
| `calendar-task` | Shell — Apple 日历提醒 |

### 外部 clone（`vendor/`，各自带 upstream git）

`wechatsync`（多平台同步 + MCP server）· `humanizer` · `deep-research` · `dbskill` · `wechat-article-exporter`。

---

## 视频剪辑套件：四引擎「能力 + 组合」架构

> 把张和口播 → 框架页竖版切片成片这条业务，按「**原子能力 + 可选组合**」组织成四个引擎。
> 组织原则**不是引擎边界，而是能力组合**：能力是积木，配方是把积木串起来的预设，AI 按视频选配方或自由组合。
> 想动它先看这节，再看决策全文 `doc/video-tools-migration-plan.md`。

**四层模型**（catalog 能力 → recipes 配方 → select 选择 → engines 布局）：

```
engines/
├── video-compose/            ★ 组合层 · 唯一对外入口（只指挥，不产原子）
│   ├── catalog.json          总能力表（真源·跨引擎汇总，build_catalog.py 重建）
│   ├── recipes.json          命名配方：zh_business（线上主路径）/ raw_quickcut / simple_concat …
│   ├── selector.py           AI 读视频 → 选配方 / 自由组合
│   └── run.py                按配方解析能力链 → 跨引擎调原子
│
├── video-slicer/             积木厂 · 剪辑策略 + 内容决策
│   ├── capabilities.json     声明：cut_sentence(句级·线上) / cut_word(词级·方案B) 共存
│   ├── pages_gen / srt_fix   逐字稿→分页 / 字幕纠错（LLM，纯 urllib）
│   ├── personas/ profiles/zh_main/   账号定制（选题 persona + 分页/纠错 prompt）
│   └── baselines/            方案A 选段基准（对照用）
│
├── video-framework-render/   积木厂 · 框架页竖版渲染（独立 .venv: pillow+opencv）
│   ├── video_framework_render/render.py   6 阶段原子（locate/assets/pages/subs/compose/accelerate）
│   ├── capabilities.json     声明：framework_reframe / compose / accelerate / subtitles / raw
│   └── profiles/zh_main/     账号定制（fixes.json 术语表；GEOM/版式=引擎内置默认）
│
└── video-clip/               积木厂 · 通用叠加原子（独立 .venv）
    ├── atoms/                concat / progress_bar / endcard / name_mask / subtitle_* / …
    └── capabilities.json     声明 9 个叠加原子
```

- **依赖单向**：`video-compose → 各引擎`；三个积木厂**互不调用**、只声明能力。改一处不牵动骨架。
- **多租户定制集中、不散回项目**：账号特定的 prompt/术语/几何全在 `engines/<engine>/profiles/<account>/`，调用方只「选 profile」。
- **产物落点**：工具直出默认 `var/<account>/`（gitignored），`--out` / `--out-root` 可改；项目在产物之上的加工（发布版/定稿）归项目自管。
- **业务侧只剩薄胶水**：`assistant_zh/workflow/video_framework_slicer/` = `run_pipeline.py`（选 profile + 落点）+ ③项目加工；渲染/选段/叠加全在 tools。

**常用命令（入口都在 video-compose）**：

```bash
python engines/video-compose/selector.py --list                 # 看所有能力原子 + 配方
python engines/video-compose/run.py --plan zh_business           # 审一条配方的能力链（每步原子→引擎→entry）
python engines/video-compose/run.py --run zh_business \
       --selection sel.json --profile zh_main                    # 端到端跑一条切片
```

**想加新能力（管线骨架不动）**：① 在所属积木厂 `engines/<engine>/` 写原子代码 → ② 在该引擎 `capabilities.json` 声明 → ③ 跑 `python engines/video-compose/build_catalog.py` 重建总表 → ④ 在 `recipes.json` 里引用（或让 AI 自由组合）。

**想改定制（不碰代码）**：改对应 `engines/<engine>/profiles/<account>/`（选题 prompt / 术语表 / 几何版式）。新账号就新建一个 `profiles/<account>/`，调用时 `--profile <account>`。

**改完怎么验证不回归（G4）**：`var/zh_main/baseline/` 存了冻结基线（`primaries/` 含可重放的 `job.json`）。改渲染后用引擎 venv 重放该 job.json，与基线逐帧/逐字节比对——方法与上次结果见 `var/zh_main/baseline/{STAGE0-baseline.md,G4-result.md}`。

---

## 日常怎么用

校验目录结构、技能安装状态是否正常：

```bash
python3 scripts/check-tools.py            # 期望：xx ok / 0 warnings / 0 errors
```

把 `skills/` 安装/修复成 `~/.claude/skills` 下的软链（幂等，可反复跑）：

```bash
python3 scripts/sync-skills.py            # 加 --dry-run 先预览
```

> `~/.claude/skills` 下只放**软链**，全部由 `sync-skills.py` 按 `registry.yaml` 生成。不要手动在那里建/改文件——改 `skills/` 下的源，再跑一次 sync。

---

## 想改东西时

- **新增 / 修改一个技能**：编辑 `skills/<name>/SKILL.md`（薄入口 + `references/`），在 `registry.yaml` 的 `skills:` 登记，跑 `sync-skills.py`。
- **新增 / 修改一个引擎**：放进 `engines/<name>/`（kebab-case），在 `registry.yaml` 的 `engines:` 登记。引擎只放代码，跑出来的数据写在引擎内部 `data/`（已 gitignore）。
- **改目录结构 / 重命名**：注意技能和引擎里有**硬编码绝对路径**，重命名要全局改写并 `grep` 归零。
- **不要复活已废弃的触发**：发布类 `xhs-publish`/`gzh-publish`/`wechatsync` 已合并进 `platform-publish`；抓取类 `xhs-fetch`/`gzh-scraper`/`content-research-hub` 已合并进 `platform-fetch`。完整废弃清单见 `registry.yaml: deprecated`。

## 几条铁律

- **凭证、状态、日志、草稿、下载产物一律放 `var/`**，绝不进 git。
- **`vendor/` 整体不进 git**（各自保留 upstream git，避免嵌套仓库冲突）。
- **目录用 kebab-case**；每个技能的入口文件统一叫 `SKILL.md`（没有 `.claude.md` / `.openclaw.md` 变体）。
- 业务 Agent 默认对工具是只读的，除非明确要修工具。

---

## 反馈与维护

工具的 bug / 改进诉求写到 `feedback/`（一条一个带日期的 md）。维护流程：读 `feedback/` → 复现 → 只改对应工具 + 文档 → 跑 `check-tools.py`（必要时 `sync-skills.py`）→ 回写 feedback 结论。

机器可读的唯一事实源是 `registry.yaml`；这份 README 和 `CLAUDE.md` 都应与它保持一致，不要各写一套。
