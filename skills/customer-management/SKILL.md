---
name: customer-management
description: |
  张和自媒体的客户/学员资产管理统一入口：把「微信现场」准确记进飞书客户管理表
  `tblfCYoeornDw0XF`（唯一真源）。一句话调度现成命令——抓数据 → AI 按任务卡读懂 →
  回写飞书，不再手跑十几个脚本。
  处理：把新学员整理入表、看就业/回访情况、整理客户资产（数据体检/订正）、
  好友刷新建行、付款金额从截图补全、客户表同步飞书、缺 wxid/重复/填错列等数据修复。
  当用户说「把这个新学员整理进表」「X期新学员入群了」「看下就业情况/哪些学员转型成功」
  「统计 offer」「做一份回访分析」「整理客户资产」「客户表体检/订正」「刷新好友/建行」
  「补付款金额/付款截图」「同步飞书客户管理表」时触发。
  不处理：内容抓取/博主调研（→ platform-fetch）、内容发布分发（→ platform-publish）、
  私域转化话术/朋友圈/群发（→ private-ops）、招生季统筹物料（→ campaign-ops）、
  知识库 wiki（→ knowledge-management）。微信采集层 mac/wechat（仓外 Node）是上游，
  本 skill 只读其产出的数据湖，不接管。
scope: assistant_zh
compatibility: claude-code
allowed-tools:
  - Bash
  - Read
  - Edit
---

# customer-management — 客户/学员资产管理

薄入口（router，不是手册）。两个世界：**微信（客户真人现场）↔ 飞书客户管理表
`tblfCYoeornDw0XF`（总账本，唯一真源）**。所有活儿本质都是「把微信现场准确记进总账本」。

- **代码真源**：`/Volumes/ExtSSD2601/AI_Assistant/tools/engines/customer-management/`（engine）。
- **业务数据**：留在 `assistant_zh/student_manage/`（`all_student.{json,csv}` / 飞书镜像 /
  FIELD_SPEC / staff_exclude / state / pending）与 `assistant_zh/analytics/`，engine 经
  `config.py` 单点读写（`CUSTOMER_MGMT_DATA_ROOT` 可覆盖）。
- 详细 runbook、字段口径、踩坑见 `references/`。

## 怎么跑（两种等价形式）

```bash
# 形式 A（推荐）：从 tools/engines 目录，把连字符目录当命名空间包
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines && python3 -m customer-management <命令> [args]

# 形式 B：从 engine 根直接跑入口（连字符目录名不能做 -m 模块名时用这个）
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/customer-management && python3 __main__.py <命令> [args]
```

## 4 个能力（所有客户数据任务拆开只有这 4 道工序）

| 能力 | 一句话 | LLM |
|---|---|---|
| **① 采集 acquire** | 把原始材料弄到手边（解密付款图 / 拉飞书镜像） | 否 |
| **② 认 recognize** | 认出规矩死的信息（确定性规则：群成员/wxid/手机号/开场白匹配） | 否 |
| **③ 读懂 analyze** | 让 AI 按**任务卡**读聊天出结论（一台机器换卡干活，含视觉读图） | 是 |
| **④ 对人 resolve** | 确认谁是谁、并重、补全、纠错（= 整理客户资产） | 否 |

## 任务卡库（analyze 的参数，人可改）

一张卡 = 怎么读（提示词）+ 要什么（输出字段契约）+ 写回规矩（落飞书哪字段、覆盖/追加）。
**张和/吴湘萍想调「什么算转型成功」「画像怎么填」，自己改卡里一句话，不动代码，编辑后立刻生效。**

| 卡 | 路径 | flow / 先过滤 gate |
|---|---|---|
| 就业回访 | `cards/employment.md` | employment / 开场白 exact-match（未发→0-LLM「未回访」stub） |
| 客户画像富化 | `cards/profile.md` | profile / 无 gate，增量窗口喂有新消息的人 |
| 线索分层 | `cards/leads.md` | leads / 确定性分层 0-LLM（⚠️ 从产物倒推重建，重跑前复核阈值） |
| 付款金额视觉读 | `cards/payment.md` | vision_agent（agent 自己视觉读 montage，**不走** call_llm 纯文本通道） |

## 7 个配方（业务编排 = 能力 + 卡 + 写策略 + 出口）

| 命令 | 干什么 | 写回安全 |
|---|---|---|
| `gather` | ★读取侧 Facade：本地+飞书镜像+微信+付款+diff/建议回填 | **默认只读 0-LLM**（`--analyze` 读 latest.json 仍不调 LLM） |
| `intake` | 新学员入表：gather → 判断 → 写回 | 写回类，`--apply` 授权门 |
| `employment` | 就业回访：recognize gate → analyze 就业卡 → 写本地 latest/state | **默认 `--auto` 真写本地**；试跑必须先 `--dry-run`。飞书写回是独立一步 `python3 -m customer-management.outputs.sync_to_feishu [--apply]` |
| `friends-sync` | 好友刷新建行：sync+audit+merge **三步合一** | 写回类，`--apply` 授权门 |
| `group-order` | 群序号同步 | 写回类，`--apply` 授权门 |
| `payment` | 付款金额：acquire 解图 → 视觉卡读 montage | 解图+拼 montage（写盘到付款产物，不碰飞书） |
| `health-check` | 客户表数据体检/订正闭环：scan→plan→dry-run→apply→archive（吸收死脚本：缺 wxid/填错列/重复/昵称误填） | **默认 dry-run / 只读镜像**；`--apply` 授权门 |

各命令具体 flag 见 `<命令> --help`。

## 🚨 红线（操作前必读）

1. **gather / health-check 默认只读**：飞书读本地镜像（`customer_management_mirror.json`），
   不碰网络、不写飞书。要 live 拉飞书须显式 `--source live`（health-check）。
2. **写回飞书须授权门**：`friends-sync` / `group-order` / `intake` / `health-check apply`
   全部以 `--apply` 为门，且**须用户明说「同步飞书」**才真写。默认 dry-run 出 plan，不写。
3. **⚠️ employment / profile analyze 默认 `--auto`（真写本地 state + 飞书）** —— 任何验证 / 试跑
   **必须先带 `--dry-run`**，且 mutate 前先备份。**这是 P3 事故的教训**：worker 误跑无 `--dry-run`
   的 `employment`，stub 路径直接 mutate 了 `all_student.json` / employment state / per_student
   jsonl。**单人核验用 `--wxid <id>`（走 stdout 不写盘）；批量先 `--dry-run` 看清单 + token 预估。**
4. **隐私**：学员真名 / 手机号 / 微信号 / 未脱敏证言**不外流** `content/` / `campaigns/` / `private_ops/`。
5. **写动作必留痕**：每个写动作备份 + 写 `student_manage/CHANGELOG.md` + `student_manage/logs/<date>.log`；
   没写日志不算做完。飞书 sync 失败不假装成功，看 `analytics/.../sync_runs/<最近>/result.json`。
6. **本地是子集不是镜像**：本地只回写飞书 7 字段（wxid/微信名称/备注/客户画像/拿到offer/添加微信/
   加好友日期），其余 38 字段飞书侧人工维护，本地不碰。
