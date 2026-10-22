# 资产归属与最小数据契约

用于初始化时选择事实源，以及给后续 Agent 规定写回位置。已有项目的等价字段优先，下面是新项目默认约定，不是强制迁移格式。

## 文件与事实源

- `account.yaml`：结构化标识与路径；路径相对项目根。未知名称/平台使用 `null` 或空列表，不能用某个旧号代填。凭据只记环境变量名或工具 profile 引用，不写密码、Cookie、token。
- `profile/positioning.md`：叙事定位的唯一主版本。把“已确认 / 假设 / 待确定”分开，并标明依据、日期。
- CSV 台账是一行一条实体/快照；文件存长文和原始材料，台账存路径。正确引用含逗号、换行、双引号的字段。未知数值留空，真实 0 才填 0。
- 一份内容可在多个平台发布：选题、作品、发布记录分别建 ID；一条发布记录关联一个平台账号。不同平台的数据不能混成一个成绩。
- `START-HERE.md` 记录交接与缺口，链接事实源，不再复制账号策略、名单和全部发布状态。

## 实体与关联

ID 在项目内稳定且不可复用，可用 `cmp-001`、`sample-001`、`topic-001`、`item-001`、`pub-001`、`review-001`。名称、标题和路径变化不应换 ID。平台的原生 ID 另存。

| 资产 | 默认文件 | 一行代表什么 / 关键字段 |
|---|---|---|
| 对标 | `research/accounts.csv` | 一个外部账号：id, platform, native_id, name, profile_url, reference_reason, reference_dimension, status, reviewed_at, report_path |
| 对标内容 | `research/samples.csv` | 一条外部作品：id, account_id, native_id, source_url, canonical_url, title, published_at, captured_at, raw_path, analysis_path, status |
| 自有素材 | `materials/index.csv` | 一个文件/资料：id, kind, source_path, source_url, received_at, usage_notes |
| 选题 | `topics/index.csv` | 一个选题：id, question, audience, hypothesis, source_ids, status, decision_reason, updated_at |
| 自有作品 | `content/index.csv` | 一个内容 item：id, topic_id, format, artifact_path, status, updated_at |
| 发布 | `content/publications.csv` | 一次平台发布：id, item_id, platform_account_id, status, published_at, url, evidence_path |
| 指标 | `reviews/metrics.csv` | 某时点的一项指标：id, subject_type, subject_id, metric, value, unit, captured_at, source, window |
| 经验 | `reviews/index.csv` | 一条可追溯判断：id, claim, status, evidence_ids, scope, reviewed_at, report_path |

列表字段如 `source_ids` 用分号分隔；跨资产引用用 `sample:sample-001`、`material:material-001`、`publication:pub-001` 等前缀区分。`metrics.subject_type` 使用 `sample` 或 `publication` 等已定义类型，subject_id 必须存在。自有历史作品可无 topic_id，标记历史导入，不能虚构来源链。

空 ID 引用字段表示未知/不适用；非空必须可解析。分析报告可以尚不存在，此时 report_path/analysis_path 留空，状态为待研究。不要用不存在的占位路径通过检查。

## 状态与证据

| 对象 | 默认状态 | 何时升级 |
|---|---|---|
| 对标账号 | candidate / researched / paused | 阅读代表性材料并有报告后才 researched |
| 外部内容 | link-only / captured / analyzed / unavailable | 有正文/可读原件才 captured；有拆解才 analyzed |
| 选题 | candidate / selected / in-progress / completed / dropped | 项目明确选题决定与原因；completed 指制作完成，发布另记 |
| 自有作品 | draft / review / ready / archived | 成稿与本项目审核条件满足后 ready |
| 发布记录 | planned / draft-uploaded / published / failed | 有可核验平台返回/链接或用户明确提供的发布证据才 published |
| 经验 | observation / hypothesis / validated / outdated | 自有作品反馈支持，并说明样本、适用范围和反例后 validated |

模板中的 `account.stage` 表示运营阶段（exploring / starting / operating），不能当作就绪程度。初始化报告另外说明资料底座、能力接入、定位验证各自状态。

指标记录必须带来源与观测时间；例如发布 24 小时阅读和累计阅读记录不同 window，不直接比较。竞品互动是公开观察，不代表其后台转化、粉丝画像或自身未来效果。缺失指标不补零，不跨平台加总不同口径。

## 增量整理

1. 原生平台 ID 相同优先判同一内容；没有 ID 时比较 canonical URL，保留原始 URL。不要随意删掉承载身份的 URL 参数；标题相同只是候选重复。
2. 未知或冲突保留两份来源、标记关系待确认，不自动合并两个可能不同的账号。
3. 更新同一实体，新的指标增加快照；同一主体、指标、时间、来源和窗口的完全重复快照不再追加。
4. 原始文件不静默移动。必要时把原位置和新位置记入交接，更新引用并核验文件存在。
5. 已有主库在表格或其他目录时，`account.yaml` 指向原主库；不要同时维护 CSV 镜像为另一个可写主库。

## 何时升级存储

默认本地文件；记录量导致检索困难、经常要跨表查询时再考虑 SQLite，多个操作者确有同时编辑需求时再评估协作系统。选型先确认使用习惯、数据归属和导出方式，不为“起号”先开发管理后台。升级时保留 ID、来源、历史快照与导出能力。
