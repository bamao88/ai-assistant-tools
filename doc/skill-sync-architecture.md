# 多台 Mac 共用 Skill

同一个 Skill 在任意一台 Mac 修改后，通过现有 [GitHub 工具仓库](https://github.com/bamao88/ai-assistant-tools)传给另一台。两台电脑都能新增 Skill，没有固定的“只读副机”。本次先接入 `daily-planning-partner`，以后逐个加入。

## 文件放在哪里

| 位置 | 用途 |
| --- | --- |
| `tools/skills/<name>/` | Skill 的共同源文件，说明、参考文档、脚本和必需素材放在同一个包里 |
| `tools/registry.yaml` | 唯一清单，记录来源以及可安装到 Codex 还是 Claude |
| 每台 Mac 的 `~/.agents/skills/`、`~/.claude/skills/` | 本机安装入口；软链接相当于指向上述源文件的快捷入口 |
| `tools/var/migrations/` | 本机迁移备份和回执，不上传 GitHub |

两台 Mac 的 `tools` 路径可以不同。安装脚本根据自己所在的位置找到源文件，然后生成这台电脑的绝对链接；不要把另一台机器的链接直接复制过来。Git 管共同版本，安装脚本管本机入口，这是两步不同的工作。

本仓库是公开的，只提交准备共享的 Skill 源码。登录凭证、机器权限、本机配置和业务记录继续放在各自原位置或 `var/`。Codex 内置与插件自带 Skill 由其安装器维护。

## 另一台 Mac 第一次使用

在希望存放工具的目录克隆仓库，目录名保持 `tools` 即可，不要求与第一台 Mac 的卷名相同：

```bash
git clone --depth 1 https://github.com/bamao88/ai-assistant-tools.git tools
cd tools
```

安装脚本使用 Python 和 PyYAML，后者负责读取清单。已有可用环境时可以直接使用 `python3`；缺少 PyYAML 时，在本地创建独立环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements-skills.txt
```

接着只安装需要的日程 Skill：

```bash
.venv/bin/python scripts/sync-skills.py --host codex --skill daily-planning-partner --dry-run
.venv/bin/python scripts/sync-skills.py --host codex --skill daily-planning-partner
.venv/bin/python scripts/check-tools.py --host codex --skill daily-planning-partner --strict
```

`--dry-run` 只展示要建立的链接；`--skill` 选择本机需要的名称，可以重复传入来安装多个。没有 `--skill` 时仍按原规则处理全部登记入口；新电脑不需要为了一个轻量 Skill 安装所有重型引擎。

Codex 支持在 `~/.agents/skills/` 中发现软链接。更改通常会自动被发现；若界面仍未显示，重新启动 Codex。依据见 [OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills)。

## 日常双向同步

在共享的 `main` 分支上工作。开始修改前，先取另一台机器的版本：

```bash
git status --short
git pull --ff-only origin main
```

修改 `tools/skills/<name>/`，新增 Skill 时也更新清单，然后检查、审阅并提交。例如修改日程规则：

```bash
.venv/bin/python scripts/check-tools.py --host codex --skill daily-planning-partner --strict
git add -- skills/daily-planning-partner
git diff --cached
git commit -m "Update planning skill"
git push origin main
```

另一台运行 `git pull --ff-only origin main`，再运行自己需要的 `sync-skills.py --skill ...`，即可使用新版本。反方向完全相同。新增目录、更名和删除也通过 Git 传递，不能只复制 `SKILL.md` 而漏掉参考文件。

有尚未提交的工作时先保留并审阅，不自动藏起修改、覆盖文件或强推。如果两台各有新提交，`--ff-only` 会停止，意思是“不能直接接上另一边的历史”，不是任何一边丢失。确认双方提交后，用 `git fetch origin` 和 `git merge origin/main` 合并；同一处有不同修改时会标出双方内容，处理并验证后再提交。不要用整目录覆盖解决这种冲突。Git 的行为见 [pull](https://git-scm.com/docs/git-pull) 与 [push](https://git-scm.com/docs/git-push) 官方说明。

已有多个开发分支的 tools 工作区，可以先在自己的分支修改，再把本次 Skill 修改单独合入共享 `main`。不要把其它工作尚未准备好的提交一并推送。

## 从任意一台 Mac 加入新的 Skill

独立安装的轻量 Skill 可以用同一个导入命令集中到 tools：

```bash
.venv/bin/python scripts/import-skill.py "$HOME/.codex/skills/某个技能" --host codex --dry-run
.venv/bin/python scripts/import-skill.py "$HOME/.codex/skills/某个技能" --host codex
```

导入器读取 Skill 自己的名称，完整复制包内源码并核对文件内容，在 `registry.yaml` 追加登记。原文件先备份，再把原入口变成指向 `tools/skills/` 的链接；保留原来的调用名。随后按该名称安装、检查，将新目录与清单一并提交、推送，另一台即可取回。

同名源文件已存在时，导入器停止并保留双方版本，交给维护者比较后合并。源目录本身是链接、包含独立 Git 仓库或依赖包外链接时，也先检查其归属，不能冒充自包含轻量包。虚拟环境、依赖缓存及 Git 元数据不随源码导入；原件仍在迁移备份中。第三方包保留许可证和来源，需持续跟上游更新的仓库按既有 `vendor/` 方式登记。

新 Skill 的包内资源按自身目录定位；机器路径从环境变量或本机配置取得。源码能同步不等于某台 Mac 已经安装了外部工具，新增运行依赖时需在该 Skill 中说明，并按实际业务验证。

## 日程 Skill 这次的迁移

正式源文件是 `skills/daily-planning-partner/`；原 `~/.codex/skills/daily-planning-partner` 保留为链接，标准 Codex 入口由安装脚本生成。规则、显示名和已有日程行为保持原有含义。

它的个人分类表仍读取 `$CODEX_HOME/calendar-registry.md`，没有设置 `CODEX_HOME` 时读取 `$HOME/.codex/calendar-registry.md`。这个位置不再依赖 Skill 的安装目录，所以 tools 搬到另一块硬盘不会把查找路径带错。本次没有复制分类表到仓库，也没有读取、修改或接管日历同步。

## 维护与验证

改安装或导入行为时，同步维护本说明和仓库入口，并遵循仓库治理规则。日常全仓检查仍使用原 `check-tools.py --strict`；按名称检查只验证选中的 Skill 及其声明的引擎/外部目录，不声称其它业务能力已安装。

```bash
python3 -m unittest discover -s scripts/tests -p test_skill_transfer.py -v
```

测试实际建立两个路径不同、用户目录不同的 tools 副本和一个本地 Git 远端：传递真实日程 Skill，在另一侧新建 Skill 并传回，在两侧分别生成链接，再制造同处修改验证冲突内容被保留。这是两个隔离工作副本的真实 Git 往返，不代表另一台实体 Mac 已经安装，也不代表日历业务链路验收。
