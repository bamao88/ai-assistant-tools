# ②选片 · 分阶段评测（per-stage eval）总纲

> 面向不读代码的 owner。本文是**规范真源**：定目录、命名、流程、评分标准、数据血缘。
> 设计计划：[`doc/plan/视频剪辑skill-第二环选片-分阶段评测-plan.md`](../../../doc/plan/视频剪辑skill-第二环选片-分阶段评测-plan.md)。

---

## 0. 一句话：这套东西干嘛的

把②选片的 **5 个 AI 步骤各配一把尺**，单独评、单独改。
旧办法只给整条链一个总分（"成片好不好"），改坏了不知道坏在哪一步。现在每步一把尺：改哪条提示词，就只看那把尺，其余步骤用**冻结的标准答案**钉死、不互相串味。

> 类比：旧办法只给整张卷子打总分；现在**每道大题单独给分**。

---

## 1. 五个阶段（= 5 条提示词 = 5 个评测点）

| # | 阶段 | 提示词文件 | 阶段目录名 | 一句话 |
|---|---|---|---|---|
| ① | 选题 | `prompts/topic-select.md` | `1_topic_select` | 整场稿里挑做哪些题 |
| ② | 总编 | `prompts/body-edit.md` | `2_body_edit` | 一条题，全场取证+编排成正文 |
| ③ | 去口水 | `prompts/refine-deduct.md` | `3_refine_deduct` | 正文里标删哪些口水字 |
| ④ | 钩子 | `prompts/hook.md` | `4_hook` | 给这条题选炸场开头 |
| ⑤ | 去重 | `prompts/dedup-merge.md` | `5_dedup_merge` | 整批里合并/删重复 |

> 组装是纯代码、不评。整场总调用 = `1 + 3N + 1`（N=选题数）。

---

## 2. 目录结构（规范 · 别乱放）

```
eval/
├── README.md                ← 本文（规范总纲·真源）
├── build_inputs.py          ← 派生脚本：从源/上游金标准生成各阶段 input.json
├── contracts/               ← 阶段契约（与数据集无关·真源）：每阶段一份
│   ├── 1_topic_select.md        每份写死：输入 schema / 输出金标准 schema / 评分口径 / 血缘
│   ├── 2_body_edit.md
│   ├── 3_refine_deduct.md
│   ├── 4_hook.md
│   └── 5_dedup_merge.md
├── fixtures/                ← 评测数据（入库·版本化）
│   └── <数据集名>/              一个数据集 = 一场逐字稿，如 agent_eval_0613
│       ├── words.json           源逐字稿（软链 → var/，不入库）
│       ├── golden.json          旧端到端金标准（当"种子"派生输入用，勿删）
│       ├── selection.json       旧选题（历史遗留）
│       └── stages/              ★分阶段数据：每阶段一个目录
│           ├── 1_topic_select/{input.json, golden.json}
│           ├── 2_body_edit/{input.json, golden.json}
│           ├── 3_refine_deduct/{input.json, golden.json}
│           ├── 4_hook/{input.json, golden.json}
│           └── 5_dedup_merge/{input.json, golden.json}
├── scorers/                 ← 评分器代码（每阶段一个·后续 P2/P4 实现）
├── runs/                    ← 每次跑的产物（gitignored·不入库）
└── notes/                   ← 迭代经验笔记（入库）
```

### 命名规范（钉死，后面不许改）
- **阶段目录/契约/评分器三者同名**：`N_snake_case`，数字前缀定顺序，名字对齐提示词去掉连字符（`topic-select.md` ↔ `1_topic_select`）。
- **每个阶段目录恒定两文件**：`input.json`（喂模型的输入）+ `golden.json`（标准答案）。名字固定，不加花样。
- **数据集名** = kebab/snake 短名 + 来源日期，如 `agent_eval_0613`、`ama_0614`。
- **入库口径**：`contracts/`、`scorers/`、`notes/`、`fixtures/**/golden.json`、`fixtures/**/input.json` **入库**；`runs/`、`words.json`（软链大文件）**不入库**。

---

## 3. 数据血缘：每阶段的输入从哪来（铁律）

**每个阶段的输入 = 上一阶段「已认可的金标准」重塑而来。** 这样输入永远是某个明确上游的函数，可追溯、不是手写孤儿数据。

```
源 words.json ─► ①选题.golden ─► ②总编.golden ─┬─► ③去口水.input
                      │                          ├─► ④钩子.input（也用①的选题）
                      └─► ②总编.input            └─► ⑤去重.input
```

| 阶段 | input 来自 | 谁生成 |
|---|---|---|
| ①选题 | 源 `words.json`（整场稿） | `build_inputs.py` |
| ②总编 | ①的金标准（选题清单）→ 每条 5 字段 + 共享全场句 | `build_inputs.py` |
| ③去口水 | ②的金标准（正文 segments）→ 展开成逐句 | `build_inputs.py` |
| ④钩子 | ①选题 + ②正文 → 标题/论点/受众 + 候选池(正文±3∪原选段±2) | `build_inputs.py` |
| ⑤去重 | ②③④组装出的整批 clip 摘要(idx/标题/论点/选段原文) | `build_inputs.py` |

> **金标准没填好之前**：`build_inputs.py` 用「种子」(`fixtures/<ds>/golden.json` 这份旧端到端金标准，含全部中间产物) 兜底派生，让你先看到每阶段输入长什么样。
> **金标准填好后**：重跑 `python3 build_inputs.py --dataset <ds> --chained`，下游输入即从你认可的金标准刷新。**输入忠实于真实提示词所见**（对齐 `generate.py`／`dedup.py` 的真实取数逻辑）。

---

## 4. 评测流程（改一条提示词，怎么验收）

```
改 prompts/<阶段>.md
  └─► 用 fixtures/<ds>/stages/<阶段>/input.json 单跑这一阶段（喂冻结输入）
        └─► 输出 vs 同目录 golden.json
              └─► scorers/<阶段>.py 出分
                    └─► 分涨了→留；跌了→看 bad case 再改（只动这一层）
```

**只动一层**：测②总编时，①的金标准固定喂、③④⑤不参与，确保分数变化只归因于总编提示词。

---

## 5. 评分标准总览（两类尺子，别混用）

| 尺子 | 怎么判 | 自动吗 | 哪些阶段 |
|---|---|---|---|
| **精确匹配** | 跟金标准算召回/精确/F1 | ✅ 纯代码 | ②总编(选了哪些句)、③去口水(删了哪些字)、⑤去重(哪些该合并)、各阶段硬规则 |
| **主观质量** | 打分卡(rubric)，LLM 评委 + 人工抽检 | ❌ | ①选题(该不该选)、④钩子(哪个最炸)、③去口水(承接句误删) |

每阶段具体用哪把尺、字段口径 → 看对应的 `contracts/<阶段>.md`。

---

## 5b. 提示词版本管理（两层 · 让版本对得上分数）

改提示词必须能回答"v3→v4 分涨了没"，所以提示词有版本账（真源在 `../prompts/`，不在 eval 下）：

| 层 | 在哪 | 干嘛 |
|---|---|---|
| **账本层**（人看） | `../prompts/versions/<name>/vN.md` + `../prompts/CHANGELOG.md` + `versions.json`(当前指针) | 里程碑版本归档 + 一行行记"vN·日期·改了啥·分变化" |
| **快照层**（机器真相） | `runs/<run>/prompts/`（每次跑分自动复制） | 把当时 5 条提示词原文 + 版本号冻进 run，分数永远查得到是哪段文本跑的 |

- **升版**（改完提示词后）：`python3 ../prompts/_version.py bump <name> "改了啥"` → 自动归档旧版、改指针、CHANGELOG 追一行（分变化先留"未测"，跑完评测再补）。
- **跑分自动快照**：`generate.py`／`dedup.py` 跑完会把提示词原文+`versions.json` 写进 `runs/<run>/prompts/`，并把版本号记进 `golden_candidate.json` 的 `prompt_versions` 字段。**无需手动操作。**
- **铁律**：CHANGELOG 的"分变化"栏没跑评测就写"未测"，别凭感觉填。

## 6. 给 owner：金标准怎么填

1. 打开要填的阶段目录，如 `fixtures/agent_eval_0613/stages/2_body_edit/`。
2. `input.json` 是题面（**别改**）；`golden.json` 现在是占位 `待填 · TODO_FILL_GOLDEN`。
3. 按同阶段 `contracts/2_body_edit.md` 里的「输出金标准 schema」把标准答案填进 `golden.json` 的 `items`。
4. 可以拿 `runs/.../golden_candidate.json` 里 AI 跑出来的结果当**草稿种子**，人工核对/修正后冻结——不用从零写。
5. 填完通知我，我接 `scorers/` 把这阶段的自动评分跑起来。

> 排期建议（见计划 §5）：先填**能纯代码自动评**的（②总编已有评分器 → ③去口水 → ⑤去重），再填要评委的（①选题、④钩子）。
