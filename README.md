# AI_Assistant Tools

这是 `AI_Assistant` 各工作区共享的**工具与技能层**。所有自媒体相关的能力（抓取、发布、调研、排版、研究…）都集中放在这里，业务 Agent 调用这里的工具，而不是各自保留一份副本。

> 这份 README 是**给人看的**导览。给 AI/Agent 看的规则在 `CLAUDE.md`，机器可读的清单在 `registry.yaml`。

查找新媒体运营能力，从 [按用途分类的 Skill 导航](doc/media-operations-catalog.md) 开始；通用方法、项目工作台、平台执行及下一轮合并安排见 [体系说明](doc/media-operations-architecture.md)。本轮集中 Skill 源码，实际运行继续依赖本机项目、引擎和登录环境。

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

技能分为跨平台动作入口、业务工作流和配套工具。当前入口、源目录、适用项目及 Claude/Codex 安装范围只在 `registry.yaml` 维护；运行 `scripts/check-tools.py --strict` 核对真实安装状态。

自媒体流程按结果衔接：研究来源与账号 → 比较选题 → 管理制作素材与版本 → 完成长文/卡片/成片 → 制作发布文案与内容包 → 按授权进入平台发布 → 维护发布记录、官方数据和复盘。

列表显示名使用用途或项目名辅助查找；项目新建或更名的调用名以前缀“项目名_”开头。废弃入口以 `registry.yaml: deprecated` 为准，不再参与自动发现；历史正文从 Git 查找，底层引擎继续复用。

## 能力与代码

### 引擎（技能调用的代码）

| 引擎 | 运行方式 |
|---|---|
| `xiaohongshu` | Python `.venv` — `scripts/cli.py`（登录/搜索/发布/互动） |
| `platform-scout` | Python — `scripts/xhs_recommend_scout.py`（推荐流/关键词搜索候选采集、指定候选详情和作者主页核验） |
| `gzh-publish` | Node/tsx — `src/index.ts`（公众号排版发布） |
| `gzh-scraper` | Python — `scripts/cli.py` + wechat-article-exporter 服务 |
| `markdown-to-cards` | Node — `cli.js` |
| `platform-draft-direct` | Node — `src/cli.js`（知乎 / 掘金 / CSDN / 百家号 / 51CTO / 博客园 / 思否 / 开源中国 / B站专栏 / 搜狐号无插件草稿直传） |
| `publish-prep` | Python — `gen_title.py` / `gen_copy.py` / `build_keywords.py` / `check.py` / `check_bundle.py`（内容包制作与发布前校验，分别由两个 Skill 按职责调用） |
| `video-research` | Python `.venv` — `scripts/cli.py` |
| `video-select` | Python 包 — 第②环选题/成片脚本 + 分阶段 Eval Harness（暂无独立技能） |
| `video-slicer` | Python 包 — 积木厂·转录/剪辑策略/字句时间 + 内容决策 pages_gen/srt_fix（暂无独立技能） |
| `video-framework-render` | Python 独立 `.venv`(pillow+opencv) — `video_framework_render.render`；积木厂·框架页竖版渲染原子（ffmpeg+puppeteer） |
| `video-clip` | Python `.venv` — `atoms/*.py`；积木厂·叠加/通用剪辑原子库 |
| `video-compose` | Python — `selector.py`/`run.py`；组合层·唯一对外入口（catalog+recipes，指挥各引擎） |
| `tencent-meeting` | Python — 官方 MCP 桥接 `scripts/mcp_cli.py`（legacy 下载脚本保留） |
| `screenshot` | Node — `screenshot.js` |
| `route-bypass` | Zsh — 本地网络分流工具（转录链路与历史诊断使用） |
| `calendar-task` | Shell — Apple 日历提醒 |

### 外部 clone（`vendor/`，各自带 upstream git）

`wechatsync`（多平台同步 + MCP server）· `deep-research` · `dbskill` · `wechat-article-exporter`。

---

## 抓取线

`platform-fetch` 是封闭平台内容抓取的统一入口：小红书、公众号、视频号博主作品列表、腾讯会议录制/逐字稿/智能纪要，以及 URL 视频的字幕、封面和关键帧都从这里分诊。

> 📄 架构和维护见 [`doc/platform-fetch-architecture.md`](doc/platform-fetch-architecture.md)。新增抓取平台、修改平台命令、调整账号边界或处理废弃抓取入口前先读它。

## 视频剪辑套件

口播/长视频 → 成片这条线，按「原子能力 + 可选组合」组织成**五个模块**：`video-compose` 组合层 + `video-select` / `video-slicer` / `video-framework-render` / `video-clip` 四个能力引擎。

> 📄 **架构 + 维护全在 [`doc/video-skill-architecture.md`](doc/video-skill-architecture.md)** —— 要更新/迭代视频 skill（加能力、改定制、接新账号、验证不回归、跑一条切片）先读它。
> 设计决策 / 迁移历史见 [`doc/video-tools-migration-plan.md`](doc/video-tools-migration-plan.md)。

## 发布线

`content-package-create`生成`core_brief.md`和各平台`publish_<account>.md`；`Agent-Publish`固定在本机复用已登录的日常Chrome，三阶段会话hook通过后再检查、上传或按授权提交。无登录请本人在原页登录，不另开配置或启用其它电脑；只读接管验证不重发已有稿件。

> 📄 架构和维护见 [`doc/publish-architecture.md`](doc/publish-architecture.md)。改标题字数、模板、上传能力、发布套装或降级规则前先读它。

---

## 日常怎么用

校验目录结构、技能安装状态是否正常：

```bash
python3 scripts/check-media-skills.py --installed
python3 scripts/check-tools.py --host codex --strict
```

查看 feedback 状态概览：

```bash
python3 scripts/check-feedback.py
```

生成 Skill 定期巡检报告：

```bash
python3 scripts/skill-audit.py
```

把共享 Codex 入口安装/修复成 `~/.agents/skills` 下的软链（先预览，再执行）：

```bash
python3 scripts/sync-skills.py --host codex --dry-run
python3 scripts/sync-skills.py --host codex
```

> 修改 `skills/` 下的规范源码；全局发现位置跟随 `registry.yaml` 的 `hosts/scope`，项目旧入口由 `project_entry` 记录。此次不修改 Claude 专用安装。

---

## 想改东西时

- **新增 / 拆分 / 合并 / 优化技能前**：先读 [`doc/skill-governance-architecture.md`](doc/skill-governance-architecture.md)。里面只保存本项目治理规则和官方文档入口；具体 Skill 设计最佳实践以 OpenAI / Anthropic 官方文档实时版本为准。
- **新增 / 修改一个技能**：编辑 `skills/<name>/SKILL.md`（薄入口 + `references/`），在 `registry.yaml` 的 `skills:` 登记，跑 `sync-skills.py`。
- **新增 / 修改一个引擎**：放进 `engines/<name>/`（kebab-case），在 `registry.yaml` 的 `engines:` 登记。引擎只放代码，跑出来的数据写在引擎内部 `data/`（已 gitignore）。
- **改目录结构 / 重命名**：注意技能和引擎里有**硬编码绝对路径**，重命名要全局改写并 `grep` 归零。
- **不要复活已废弃的触发**：`publish-prep`/`dbs-xhs-title` 的内容制作入口由 `content-package-create` 接管；`xhs-publish`/`gzh-publish`/`wechatsync` 的发布入口由 `Agent-Publish` 接管；抓取类 `xhs-fetch`/`gzh-scraper`/`tencent-meeting-downloader`/`content-research-hub` 已合并进 `platform-fetch`。完整废弃清单见 `registry.yaml: deprecated`。

## 几条铁律

- **凭证、状态、日志、草稿、下载产物一律放 `var/`**，绝不进 git。
- **`vendor/` 整体不进 git**（各自保留 upstream git，避免嵌套仓库冲突）。
- **通用目录用 kebab-case，项目专属目录保留完整项目名前缀**；每个技能的入口文件统一叫 `SKILL.md`（没有 `.claude.md` / `.openclaw.md` 变体）。
- Agent 可以按任务需要修改 Skill、工具代码、测试和文档。动手前先定位所属 git 仓库，查看 `git status --short`，必要时先提交 checkpoint，并且不要把无关改动混进提交。

---

## 反馈与维护

工具的 bug / 改进诉求写到 `feedback/`（一条一个带日期的 md）。维护流程：读 `feedback/` → 复现 → 只改对应工具 + 文档 → 跑 `check-tools.py`（必要时 `sync-skills.py`）→ 回写 feedback 结论。

机器可读的唯一事实源是 `registry.yaml`；这份 README 和 `CLAUDE.md` 都应与它保持一致，不要各写一套。
