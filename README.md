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
| `video-slicer` | Python 包（暂无独立技能） |
| `tencent-meeting` | Python — 官方 MCP 桥接 `scripts/mcp_cli.py`（legacy 下载脚本保留） |
| `screenshot` | Node — `screenshot.js` |
| `route-bypass` | Zsh — 小红书发布网络分流 |
| `calendar-task` | Shell — Apple 日历提醒 |

### 外部 clone（`vendor/`，各自带 upstream git）

`wechatsync`（多平台同步 + MCP server）· `humanizer` · `deep-research` · `dbskill` · `wechat-article-exporter`。

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
