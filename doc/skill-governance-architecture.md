# Skill 治理架构

这份文档讲的是“怎么管理所有 Skill”，不是某一个 Skill 的使用手册。

大白话：`registry.yaml` 像总花名册，`skills/` 像前台入口，`engines/` 像后厨工具，`doc/*-architecture.md` 像每条业务线的说明书，memory 像事故教训本。维护时要让这些东西说同一套话。

## 1. 真源怎么分工

| 位置 | 负责什么 | 不负责什么 |
|---|---|---|
| `registry.yaml` | 机器可读的正式清单：有哪些 skill、engine、vendor、废弃入口 | 不写长篇解释 |
| `CLAUDE.md` | Agent 每次进 tools 仓必须知道的硬规则 | 不复制完整清单 |
| `README.md` | 给人看的导览 | 不当机器校验依据 |
| `skills/<name>/SKILL.md` | 触发入口和执行规则 | 不放大段历史计划 |
| `skills/<name>/references/` | 按平台/场景拆开的操作细则 | 不放计划草稿 |
| `engines/<name>/` | 代码、CLI、测试、能力声明 | 不做可触发入口 |
| `doc/*-architecture.md` | 一条 skill/engine 线的现状、结构、维护方法 | 不当临时 todo |
| `doc/plan/` | 维护/迁移/迭代计划 | 不替代现状架构文档 |
| `feedback/` | 工具 bug、异常和长期追踪项 | 不放业务账号私有策略 |
| memory | 对话中学到、下次还会影响行为的教训 | 不放能从代码/文档推断出的普通说明 |

## 2. Skill 生命周期

| 阶段 | 应该做什么 | 机器怎么检查 |
|---|---|---|
| 新增 | 建 `skills/<name>/SKILL.md`，必要时加 `references/`、`assets/`、`scripts/` | `scripts/check-tools.py` 要求它登记进 `registry.yaml` |
| 接入 engine | 代码放 `engines/<id>/`，Skill 通过 reference 或命令调用 | `uses_engines` 必须指向 registry 里存在的 engine |
| 迭代行为 | 同步改 Skill、engine、测试、架构文档 | `CLAUDE.md` 要求结构/行为改动同步更新 `doc/*-architecture.md` |
| 废弃 | 在 `registry.yaml: deprecated` 标明 `replaced_by`，删除或显式标记旧入口 | `sync-skills.py` 移除旧软链；`check-tools.py` 检查遗留入口必须写清“已废弃” |
| 归档 | 历史计划放 `doc/plan/`，旧运行数据放 `var/` 或归档区 | 不允许把旧触发入口悄悄留在正式清单外 |

## 3. 新增或优化 Skill 前先看官方文档

Skill 设计知识不要写死在本仓库里。每次要新增、拆分、合并或优化 Skill 时，先打开下面的官方文档看最新说法，再回到本仓库按本地规则落地。

| 来源 | 什么时候看 | 链接 |
|---|---|---|
| OpenAI / Codex：Build skills | 设计 Codex 可用 Skill、写 `SKILL.md`、组织 `references/scripts/assets` 前 | [Build skills](https://developers.openai.com/codex/build-skills) |
| OpenAI / Codex：Skills & Plugins | 判断本地 Skill、插件分发、连接器组合怎么取舍时 | [Skills & Plugins](https://developers.openai.com/codex/skills-and-plugins) |
| OpenAI / Codex：AGENTS.md | 判断哪些规则应放 `AGENTS.md`、哪些应下沉到 Skill 或文档时 | [Custom instructions with AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md) |
| OpenAI / Codex：Customization | 判断 memory、项目规则、Skill、插件之间怎么分层时 | [Customization overview](https://developers.openai.com/codex/customization/overview) |
| Anthropic / Claude Code：Skills | 需要兼容 Claude Code 的 Skill 行为、触发、调试、插件关系时 | [Extend Claude with skills](https://docs.anthropic.com/en/docs/claude-code/skills) |
| Anthropic / Claude Code：Memory | 判断一条经验应进 memory、CLAUDE.md、path-scoped rule 还是 Skill 时 | [How Claude remembers your project](https://docs.anthropic.com/en/docs/claude-code/memory) |

执行要求：

1. 不把官方文档某一版内容整段复制进本仓库。
2. 只把“本项目已经拍板的本地规则”写进 `CLAUDE.md`、`registry.yaml` 或架构文档。
3. 如果官方文档的新建议和本项目现有规则冲突，先在 `doc/plan/` 写清差异、影响和迁移方式，再改规则。
4. 如果只是某次事故教训，先写 memory 或 feedback；只有重复影响维护时，才升级为 `CLAUDE.md` 硬规则或机器检查。

## 4. 什么该进 memory，什么该进文档

| 内容类型 | 放哪里 | 原因 |
|---|---|---|
| “用户纠正过，AI 下次还会犯”的行为教训 | memory | 这是对话学到的经验 |
| “每次进仓库都必须遵守”的硬规则 | `CLAUDE.md` | Agent 启动就要看到 |
| “某条业务线怎么组成、怎么维护” | `doc/*-architecture.md` | 用户和 Agent 都要能看懂现状 |
| “某次迁移计划、阶段安排、验收记录” | `doc/plan/` | 这是一次性项目过程 |
| “工具 bug、异常、待追踪项” | `feedback/` | 方便从问题入口回到修复闭环 |
| “能由 registry 或代码自动推断的清单” | 不手写，跑脚本 | 避免多份清单互相过期 |

## 5. 当前机器门

日常维护至少跑：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/scripts/check-tools.py
```

这道门负责：

- registry 里的 source 是否存在。
- skill 引用的 engine/vendor 是否存在。
- 全局 skill 软链是否正确。
- 废弃触发是否还装在 `~/.claude/skills`。
- `skills/` 下是否有未登记、未废弃的 `SKILL.md`。
- engine 目录里的 `SKILL.md` 是否写成了可触发入口。

反馈状态概览：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/scripts/check-feedback.py
```

这道门先做报告，不默认阻塞。需要严格清理时加：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/scripts/check-feedback.py --strict
```

Skill 定期巡检报告：

```bash
python3 /Volumes/ExtSSD2601/AI_Assistant/tools/scripts/skill-audit.py
```

这道门不自动修改代码，会把报告写到 `var/review/skill-audits/`。它额外看四类问题：

- 废弃或未登记的 Skill 入口是否还在。
- 某个 Skill 近期是否反复被改、当前是否有大量未提交相关改动。
- `SKILL.md` / `references/*.md` 是否过长，是否到了该拆分或整理的时候。
- L1/L2 工作流是否缺少架构文档，feedback 是否缺状态。

## 6. 维护动作的最小闭环

1. 先看 `git status --short`，确认不要覆盖别人的改动。
2. 查 `registry.yaml`，确认要改的是正式入口、engine，还是废弃遗留。
3. 如果是新增/优化 Skill，先按本文件第 3 节打开官方文档。
4. 改对应 Skill、engine、测试和文档。
5. 结构/行为变化同步更新对应 `doc/*-architecture.md`；没有对应文档且改动不小，就新建。
6. 跑 `scripts/check-tools.py`，必要时跑具体 engine 测试。
7. 有反馈文件时，把处理状态写回 `feedback/`。


## 自媒体命名与多端发现（2026-10-21）

显示名统一为“通用｜具体任务”或“项目名｜具体任务”；项目调用名以完整项目名加下划线开头。已有清楚的通用调用名保持稳定；仅有歧义的入口随职责收敛更名。显示名、frontmatter、目录、默认提示、registry 与当前引用一起迁移。

registry 每个共享入口可声明 hosts: [claude, codex]；缺省保持 Claude。Codex 的受管发现路径为 ~/.agents/skills，Claude 为 ~/.claude/skills；相同源不在同一 host 的用户和项目范围重复注册。项目特有流程留在项目，通用桥接不再复制到每个项目。工具目录保留通用代码与可按项目配置复用的引擎。

同步使用 scripts/sync-skills.py --dry-run 预览，再实际执行；--host 可只选一个 host。遇真实目录、无关软链或含其他文件的外部包装目录，保留内容并报告冲突。废弃清理只移除已确认指向 tools 根目录的自有链接，涵盖旧 ~/.codex/skills。绝不删除真实内容目录来“修复”注册。

scripts/check-tools.py --strict 检查所有已声明 host，并将漏安装和废弃残留作为失败；--host 可以缩小范围。第一方 frontmatter.name 必须等于 registry 名字；名称允许用户要求的完整项目名前缀。scope 非 global 的入口按既有项目规则安装，不擅自全局套用。

本轮废弃的轻量研究、独立巡看、综合小红书运营与发布准备包不再保留可触发 SKILL.md；历史参考与引擎分开保留。研究统一 content-creator-research，巡看归入 content-topic-planning，制作管理使用 content-production-prep，发布字段制作使用 content-package-create，实际平台动作使用 Agent-Publish。

官方行为依据：[Build skills](https://learn.chatgpt.com/docs/build-skills) 说明 Codex 使用 ~/.agents/skills、支持目录软链，以及同名入口可能在列表重复。本地结构检查不代替真实制作或平台验收。


项目归属与发现位置分别登记：project 标记只能应用哪个项目，scope/hosts 决定在哪里供选择。八毛三项和 MiMi 两项沿原来的全局可选方式登记到同一 registry（显示名与调用名仍带完整项目名）；张和现有本地流程仍只在项目中发现。通用规则不从这些项目专属 Skill 自动继承。这些字段及 source 使同步器也能恢复项目入口，避免手工链接另成一套清单。
