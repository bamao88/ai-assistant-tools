# video-clip 维护手册

> 修改 Skill、配方、能力、profile、输出路由或验证体系时读。先读 `doc/video-skill-architecture.md`，先在 `doc/plan/` 写计划。

## 1. 一套系统，五个模块

```text
video-compose             组合层：选、审、跑、验；不产原子
├── video-select          ② 选题/成片脚本
├── video-slicer          ①转录 + 字/句时间 + ④字幕文字
├── video-framework-render ⑤ PPT/字幕画面铸造
└── video-clip            ③裁剪 + 源适配 + ⑥组装 + 自检
```

“五个模块”包含一个组合层和四个能力引擎。物理目录按运行环境分，不按六环搬家。

## 2. 真源只认这些

| 问题 | 真源 | 不要做 |
|---|---|---|
| 某引擎有哪些能力 | `engines/<provider>/capabilities.json` | 在 SKILL.md 手抄全能力表 |
| 全链有哪些能力 | 生成的 `engines/video-compose/catalog.json` | 手改 catalog |
| 默认组合是什么 | `engines/video-compose/recipes.json` | 把 recipe 逻辑塞进说明文 |
| 原子怎么执行 | `engines/video-compose/run.py` / runner | 给同一原子维护第二套入口 |
| 账号差异 | 各引擎 `profiles/<account>/` | 把账号参数焊进通用代码 |
| 产物去哪 | `skills/video-clip/output_routing.json` | 把项目落点焊进原子 |
| 日常决策与经验 | Skill 主文件 + `references/` | 把临时计划放进运行 reference |
| 架构与维护全景 | `doc/video-skill-architecture.md` | 结构变更后只改代码 |

## 3. 加一个能力

1. 在所属能力引擎实现原子。
2. 在该引擎 `capabilities.json` 声明 `stage/layer/required`，源适配再声明 `source_types`。
3. 重建总表：

```bash
python engines/video-compose/build_catalog.py
```

4. 如果默认配方需要它，在 `recipes.json` 引用；同时保证 `run.py` 有执行映射或专属 runner 实际调用。
5. 给能力补最小确定性测试；视觉/LLM 能力还要按对应质量门留证据。
6. 更新架构文档和必要的按需 reference，不在主 Skill 复制能力库存。

## 4. 加或改配方

- 配方是稳定的用户意图预设，不是某次任务的临时命令。
- 能用现有原子组合就不要复制代码。
- 新配方先能 `--plan`，再有真实 runner，最后才在主 Skill 宣布“可一键运行”。
- 草案放 `doc/plan/` 并明确状态；未评审草案不能放在 Skill references/ 冒充现行流程。

## 5. 加账号 / 改账号定制

- prompt、术语、几何和 preset 进入对应引擎的 `profiles/<account>/`。
- profile id 在调用时显式传递。
- 账号一旦需要项目归位，同时补 `output_routing.json`。
- profile/preset 改动要版本化；不要原地改变已确认视觉而不留迁移记录。

## 6. 改选片提示词

提示词在 `engines/video-select/prompts/`。五个评测点各有契约和冻结输入，改哪条就先看哪把尺：

```bash
cd engines/video-select
python3 eval/scorers/run_all.py --dataset agent_eval_0613
```

需要真实 LLM 时再运行阶段 Runner；结构门和离线 scorer 先跑。经验更新到 `eval/notes/`，不要塞回主 Skill。

## 7. 改视觉

先看 `quality-gates.md` 的 PPT 风格锁。涉及 prompt、CSS 或几何就必须：用户明确要求 → 出样片 → 用户拍板 → 更新架构定稿 → 重冻/重跑 G4。

## 8. 验证阶梯

```bash
# 控制面契约：能力、catalog、配方、dispatch、registry
python engines/video-compose/verify_contracts.py

# 时间基准单元
python -m unittest discover -s engines/video-clip/tests -p 'test_*.py'

# 字级 cut_word 路径的同一时间基准门
(cd engines/video-slicer && python3 -m pytest tests/test_text_pipeline.py -q)

# 快速确定性回归
python engines/video-compose/regression/run_regression.py t0

# 原子 smoke（含新近美颜能力；真人 fixture 没有时脚本会说明跳过）
bash engines/video-clip/test_atoms.sh

# 全工具登记
python scripts/check-tools.py
```

按风险追加：T1 单原子、T2 阶段集成、T3 端到端/转录/G4。不要为了让测试变绿而静默改金标准；先解释行为变化，再重冻。

## 9. 常见漂移，机器应该拦住

- 新增了 capability 却忘了 catalog。
- 配方引用了不存在的原子或没有 dispatch。
- Skill 实际使用引擎和 registry 不一致。
- 用硬编码“总共 N 个原子”做健康判断，新增能力后马上假红。
- 同一个能力维护两份代码/两个名字，文档和运行时各选一份。
- 把一次事故的长复盘直接堆进主 Skill，导致入口越来越难读。

以上前四类由 `verify_contracts.py` 或 `check-tools.py` 阻断；后两类在维护审查时清理。
