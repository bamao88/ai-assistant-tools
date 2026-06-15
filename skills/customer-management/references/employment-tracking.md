# 学员就业情况追踪（employment 配方）

> 合并自原 `assistant_zh/workflow/student_employment_tracking/README.md`。
> 从助理 ↔ 学员的 1v1 微信对话抽取学员求职转型状态，沉淀到飞书「客户管理」表。
> 提示词真源 = `cards/employment.md`（编辑立刻生效，不改 Python）。

## 何时进入

| 用户的交付物 | 进本流程？ |
|---|---|
| 「看一下学员就业情况」「哪些学员转型成功了」「统计 offer」「做一份回访分析」 | ✅ |
| 「私聊话术 / 跟进话术 / 朋友圈」 | ❌ → private-ops |
| 「招生季 / 第五期物料」 | ❌ → campaign-ops |

## 输入

| 数据 | 路径（留 assistant_zh，engine 经 config 读） |
|---|---|
| 1v1 对话原始数据 | `knowledge_base/client/raw/chat/messages_user_<wxid>.json` |
| 学员档案 hint | `student_manage/all_student.json` |
| 助理排除名单 | `student_manage/staff_exclude.json` |
| LLM 配置 | `knowledge_base/.env` |

## 输出

| 数据 | 路径 |
|---|---|
| 每次跑结果归档 | `analytics/student_employment_tracking/runs/<run_id>/`（analysis.json / skipped.json / changes.md / summary.md / logs/run.log）|
| 跨 run 增量 checkpoint | `student_manage/state/student_employment_tracking_progress.json` |
| 最新结论快照（飞书写回读这个） | `student_manage/state/student_employment_tracking_latest.json` |
| per-学员长期时间线（append-only） | `analytics/student_employment_tracking/per_student/<wxid>.jsonl` |
| 客户管理表 sync 归档 | `analytics/student_employment_tracking/sync_runs/<run_id>_<dryrun\|apply>/`（plan.md / plan.json / no_match.json / result.json / sync.log）|

## 飞书字段映射（写回策略，真源在 `cards/employment.md` front-matter `write_back`）

| 飞书字段 | field_id | 策略 |
|---|---|---|
| `wxid` | fldrd6BKOZ | 匹配键 |
| `拿到offer` | fld2PAblzH | **overwrite** |
| `客户画像` | fldGS7fJ2S | **skip-if-marked**（飞书现内容含 `AI回访分析` 标记则跳过，否则 append）|
| `备注` | fldOlBS35I | 同上 |

> `--rerun-not-followed-up` 修复模式在本地 latest.json 走 **reset 而非 append**（清错误数据）。

## 运行模式

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines
# 预览，不调 LLM（先跑这个看清单 + token 预估）—— 试跑/验证一律先 --dry-run
python3 -m customer-management employment --dry-run
# 单人核验（stdout 输出，不写盘）
python3 -m customer-management employment --wxid <wxid>
# 抽样 N 人
python3 -m customer-management employment --sample 10
# 首次全量
python3 -m customer-management employment --bootstrap
# 增量（推荐常用，跳过无新消息的学员）—— ⚠️ 默认 --auto 真写本地 state + 飞书
python3 -m customer-management employment --auto
# 忽略 checkpoint 全量重跑
python3 -m customer-management employment --force-rerun-all
# 一次性修复：把所有未发过回访开场白的学员 reset 成「未回访」（0 LLM）
python3 -m customer-management employment --rerun-not-followed-up
# 控成本：本轮最多 N 人后停
python3 -m customer-management employment --auto --limit 20
```

> 🚨 **employment 默认走 --auto（真写）**。验证 / 试跑务必先 `--dry-run`，mutate 前备份。
> P3 事故即误跑无 `--dry-run` 的 employment、stub 路径 mutate 了 all_student.json/state/per_student。

## 增量判断（--auto）

1. `messages_user_<wxid>.json` 不存在 → 跳过（file_missing）
2. 当前 `total` == 上次 `last_message_count` → 跳过（no_new_messages）
3. 最新 `createTime` ≤ 上次 `last_message_timestamp` → 跳过（no_newer_messages）
4. 距上次 run 超 60 天 → 强制重跑
5. 否则 → 触发 LLM 分析

## 回访开场白预过滤（gate=follow_up_exact_match）

进 LLM 前先用**严格 exact match** 检测助理是否对该学员发过开场白：

```
同学，回访一下，最近面试和求职情况怎么样呢？
```

| 检测结果 | 路径 | LLM |
|---|---:|---:|
| 发过 | 正常 LLM 分析 | 1 次 |
| 没发过 | stub：`transition_outcome="未回访"`、`got_offer=false`、`confidence=1.0` | 0 |

stub 约定：`remark_append` 每次跑写一段带日期戳「未回访」块；`customer_profile_append` 只在首次
检测到未回访时写一段。`--rerun-not-followed-up` 是一次性修复路径（reset、0 LLM、~5 秒）。

## 守则

- 原始对话只读，不写回 raw/chat。
- 不写 `content/content_index.yaml`、`all_student.json`、`knowledge_base/client/wiki/`。
- 默认先 `--sample 10` 人工核验，再 `--bootstrap` 全量（约 268 次 LLM，成本可观）。
- per-学员 JSONL 是 append-only，禁止覆盖整行。
- LLM 严禁瞎编：prompt 强制未提及写「对话未提及」。
- 学员真名/手机号不能流到 `content/`、`campaigns/`。

## 标准追问模板

```
我先跑 --dry-run 看 268 人清单、token 预估、按 transcript 长度排序，
确认没问题再决定 --sample 或 --bootstrap。可以吗？
```
```
本次 pending/decisions.json 有 N 个学员低置信。你想：
1. 现在逐个人工核对 2. 跳过先看 summary 3. 下一轮新消息进来后再说
```

## 飞书 sync（就业字段写回）

由 `employment` 配方内的 outputs 写回承接（原独立 `sync_to_feishu.py` 已并入 engine outputs），
把 latest.json 同步到客户管理表。默认 dry-run 出 `plan.md`；真写须 `--apply` 且用户明说「同步飞书」。
合并幂等：`拿到offer` 覆盖、`客户画像`/`备注` skip-if-marked（含 `AI回访分析` 标记则跳过，否则 append）。
`no_match`（飞书行没填 wxid）一般补完飞书 wxid 后重跑即可，已 sync 的不会重复写。
