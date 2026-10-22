# 数据模型 / 飞书归口 / 边界

> 合并自原 `assistant_zh/student_manage/README.md`。代码已迁入 engine；业务数据留 assistant_zh。

## 数据流

```
mac/wechat/weekly_sync.sh (Tue 9:10，仓外 Node，本 skill 不接管)
    │
    └── 写入: knowledge_base/client/raw/chat/   （数据湖，只读）
            members_*_chatroom.json
            messages_*_chatroom.json
            messages_user_<wxid>.json (268+)
            friends_<role>.json (assistant/zh2 各账号好友 → 添加微信 标签 + 群外好友建行)
                    │ 只读，不写
                    ▼
        customer-management 引擎（recognize 规则抽取 + analyze profile 富化）
                    │
                    ▼
        all_student.json（本地主数据，留 assistant_zh/student_manage/）
                    │ 被以下消费
                    ▼
        employment 配方（取学员档案作 LLM hint）→ 飞书客户管理表（项目配置 `feishu.table_id`）
```

周更编排（原 `run.py` / `update_and_notify.py`，去掉 merge_refer 步）在 engine `recipes/run.py`。
新学员整理用 `gather`（读取侧 Facade，默认只读 0-LLM）拿现状，再判断写回。

## 飞书表 = 唯一真源

资源与账号值读取项目根 `config/customer-management.private.json` 的 `feishu`：

| 字段 | 含义 |
|---|---|
| `wiki_node` | 客户管理表所在 wiki 节点 |
| `app_token` | Base 的 App Token |
| `table_id` | 当前唯一客户总表的 ID |
| `profile` | 使用该资源的 lark-cli profile |
| `url` | 当前表的可打开链接 |
| `retired_table_ids` | 已废弃表，仅供核对历史，不作为目标 |

读取及直接运行 CLI 的例子见 SKILL.md「项目身份与资源配置」。值必须从项目配置传给原命令，
不复制本文件中的字段名充当 ID。当前表规模由最近只读镜像确认，不把历史计数写成配置事实。

## 本地 ↔ 飞书 关系（重要）

- **飞书是真源，本地是子集来源，不是镜像。** `all_student.json`由微信群成员/好友抽取
  而来，只是喂给飞书的来源之一；飞书表中还含大量本地没有的线索行。
- 本地只回写飞书 **7 个字段**：`wxid`/`微信名称`/`备注`/`客户画像`/`拿到offer`/`添加微信`/
  `加好友日期`，其余 38 字段（渠道/成交/分成/手机号/几期学员等）**飞书侧人工维护，本地不碰**。
- 写飞书唯一入口 = engine 的 `outputs/`（就业字段 + 好友 roster + 群序号），由 `employment` /
  `friends-sync` / `group-order` / `intake` 配方调用；字段映射在各 outputs 模块顶部常量。
- `feishu_config.json`（留 `student_manage/`）里 `app_token`/`table_id`/`fields` 指向已废弃旧表，
  失效仅留历史；仍在用的只有 `chat_id` / `user_open_id`（notify 发告警用）。

## 本地只读镜像（快速查询用）

```bash
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines && python3 -m customer-management gather --new   # 本地有飞书镜像缺的人
```

- 镜像产物 `student_manage/customer_management_mirror.json`（带 `synced_at` 的整表快照）
  由 acquire 的 mirror 能力拉取（只发 GET，绝不回写）。要最新数据就重新拉。
- 之后按期次、渠道或标签统计时直接读这个 JSON，并注明其快照时间。
- 文件较大（~4M），已 gitignore。
- 本地主数据字段定义见 `student_manage/FIELD_SPEC.md`（含 `添加微信`：roster 派生）。

## 解耦边界

- **只读**：`knowledge_base/client/raw/chat/`（数据源）、`knowledge_ingest.core`（共享 call_llm 机器核）、
  `knowledge_base/.env`（共享 LLM key）。
- **不写**：`content/*` / `knowledge_base/*` / `mac/wechat/state/*` / `shared/*`。
- **自有运行态**（留 `assistant_zh/student_manage/`，engine 经 config 读写）：
  `state/enrich_progress.json`（per-student 富化断点）、
  `state/student_employment_tracking_*.json`（就业 checkpoint）、
  `logs/YYYY-MM-DD.log`、`pending/decisions.json`（低置信建议）、
  `all_student.json` / `all_student.csv`（主数据）。
- **仓外上游**：`mac/wechat/`（19 .js + weekly_sync.sh）是 acquire 的上游 Node 采集层，本 skill
  只读其产出的数据湖，不接管、不重写。

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| LLM 反复 429 | rate limit | 加备用 key，或降低并发 |
| lark-cli `permission denied` | 项目 `feishu.profile` 失效 | 先读取该字段，再运行 `lark-cli auth login --profile <实际profile>` |
| WeFlow Mac 没跑 | `mac/wechat/state/` 不存在 | engine 仍可基于上次 raw/chat 跑（数据可能旧 1 周），不阻塞 |
| engine 找不到数据 | `config.py` 的 DATA_ROOT 不对 | 确认 `CUSTOMER_MGMT_DATA_ROOT` 或默认指向 assistant_zh 仓根 |
