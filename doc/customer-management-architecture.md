# 学员管理 skill：架构 + 维护指南

> **要更新 / 迭代学员管理 skill（客户/学员资产管理这条线）就先读这份文档。** 它告诉你东西在哪、怎么改、怎么验证不回归。
> 这份是「现状真源 + 怎么动手」；要看**为什么这么设计 / 迁移决策 / 历史**，去记忆 `customer-management-migration` 与 `video-tools-migration-plan`（同一波 tools 集中化）。

## 一句话定位

把「**微信现场（客户真人）↔ 飞书客户管理表 `tblfCYoeornDw0XF`（总账本，唯一真源）**」对齐这条业务，按「**4 能力 + 任务卡 + 配方**」组织成**一个引擎**。
组织原则**不是脚本边界，而是工序**：所有客户数据活儿拆开只有 4 道工序（能力是不变的积木），任务卡是可改的参数（改一句话就改判定口径，不动代码），配方是把能力+卡+写策略+出口串起来的业务编排。

- **代码真源**（engine）：`tools/engines/customer-management/`
- **业务数据真源**（留 assistant_zh，engine 经 `config.py` 单点读写）：`assistant_zh/student_manage/` + `assistant_zh/analytics/`
- **skill 入口**（薄 router）：`tools/skills/customer-management/SKILL.md`，`scope: assistant_zh`——**不进全局 `~/.claude/skills`**，仅 assistant_zh 项目本地双 host 软链。

## 4 能力模型 + 目录布局

```
工序组织：① 任务卡 cards/（analyze 的参数）→ ② 4 能力 capabilities/ → ③ 7 配方 recipes/ → ④ 出口 outputs/

tools/engines/customer-management/
├── __main__.py              ★ 唯一对外入口 · 7 命令分发（_DISPATCH → recipes/ 或 capabilities.analyze）
├── config.py                ★ 跨仓单点路径解析器——所有路径收口于此（DATA_ROOT 锚 assistant_zh，CUSTOMER_MGMT_DATA_ROOT 可覆盖）
├── write_policy.py          ★ 写入策略层：命名纯函数（append/overwrite/skip_if_marked/reset/fill_only_if_empty/idempotent_field），卡片用名字引用
│
├── cards/                   任务卡库（analyze 的参数，非工程师可直接编辑 .md 改行为，立即生效）
│   ├── employment.md        就业回访（flow=employment；gate=开场白 exact-match，未发→0-LLM「未回访」stub）
│   ├── profile.md           客户画像富化（flow=profile；SYSTEM_PROMPT 注入 FIELD_SPEC.md）
│   ├── leads.md             线索分层（flow=leads；确定性分层 0-LLM）
│   └── payment.md           付款金额视觉读（flow=vision_agent；agent 自己视觉读 montage，不走文本 LLM 通道）
│       └─ 卡 = 怎么读(prompt) + 要什么(result 字段) + 写回规矩(write_policy 策略名) + 先过滤(gate)；由 capabilities/analyze/cards.py 的 load_card() 加载
│
├── capabilities/            4 能力（所有客户数据任务拆开只有这 4 道工序）
│   ├── acquire/             ① 采集（无 LLM）：decrypt_dat（解密付款图）/ get_img_key / mirror（拉飞书镜像）
│   ├── recognize.py         ② 认（无 LLM）：确定性规则——群成员/wxid/手机号/开场白匹配
│   ├── analyze/             ③ 读懂（LLM）：一台机器换卡干活——cards.py(加载) + core.py(规范化) + employment.py / profile.py（按卡跑 flow）
│   └── resolve/             ④ 对人（无 LLM）：core.py / friend_index.py / add_missing_group_members.py——确认谁是谁、并重、补全、纠错
│
├── recipes/                 7 配方（业务编排 = 能力 + 卡 + 写策略 + 出口）
│   ├── gather.py            ★读取侧 Facade（本地+飞书镜像+微信+付款+diff/回填建议，默认只读 0-LLM）
│   ├── intake.py            新学员入表：gather → 判断 → 写回
│   ├── friends_sync.py      好友刷新建行：sync + audit + merge 三步合一
│   ├── group_order.py       群序号同步：resolve → 写回
│   ├── payment.py           付款金额：acquire(解图) + analyze(视觉卡读 montage) → 写回
│   ├── health_check.py      客户表数据体检/订正闭环：scan→plan→dry-run→apply→archive（吸收死脚本）
│   └── run.py / update_and_notify.py   学员主数据周更新顶层编排
│       └─ 注：employment 命令直接分发到 capabilities/analyze/employment.py（不经 recipes）
│
└── outputs/                 出口（写回飞书/本地的执行层 + 通知）
    ├── sync_to_feishu.py            客户管理表字段写回（就业 sync 幂等核心：skip_if_marked）
    ├── sync_friends_to_feishu.py    好友索引写回
    ├── sync_group_order.py          群序号写回
    ├── intake_writer.py             入表写盘
    └── notify.py                    通知
```

业务数据（engine 经 `config.py` 读写，**不搬进 tools**）：

```
assistant_zh/
├── student_manage/                          ← config.STUDENT_MANAGE_DIR（主数据目录）
│   ├── all_student.{json,csv}               本地主数据（飞书 7 字段子集，1300+ 条）
│   ├── customer_management_mirror.json      飞书镜像（gather/health-check 默认读它，不碰网络）
│   ├── FIELD_SPEC.md                        字段口径（profile 卡注入；写回映射的真源）
│   ├── staff_exclude.json                   员工排除名单（不当学员处理）
│   ├── feishu_config.json                   飞书表/字段配置
│   ├── state/ pending/ logs/ CHANGELOG.md   运行态 + 变更总账（写动作必留痕）
│   └── payment_proof/{out,montage}/         付款凭证解图产物（gitignore）
├── knowledge_base/client/raw/chat/          ← config.DATA_DIR：微信采集数据湖（只读上游，§13 边界）
└── analytics/student_employment_tracking/   就业回访产物
```

## 铁律

- **依赖单向 + 单引擎**：`skill(SKILL.md) → __main__.py → recipes/capabilities → outputs`；路径只走 `config.py`，**任何模块不再自己拼绝对路径**。
- **数据留 assistant_zh**：engine 住 tools、数据住 assistant_zh，经 `config.py` 桥接；换租户/搬仓只改 `CUSTOMER_MGMT_DATA_ROOT` 一处。
- **本地是子集不是镜像**：本地只回写飞书 7 字段（wxid/微信名称/备注/客户画像/拿到offer/添加微信/加好友日期），其余 38 字段飞书侧人工维护，本地不碰。
- **写回须授权门 + 留痕**：`intake/friends-sync/group-order/health-check apply` 全以 `--apply` 为门，且**须用户明说「同步飞书」**才真写；每个写动作备份 + 写 `CHANGELOG.md` + `logs/<date>.log`，没写日志不算做完。
- **非工程师改卡不改码**：要调「什么算转型成功 / 画像怎么填 / 怎么读」，改 `cards/<name>.md` 里那句话即可，立即生效。

## 入口命令

```bash
# 形式 A（推荐）：把连字符目录当命名空间包
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines && python3 -m customer-management <命令> [args]
# 形式 B：从 engine 根直接跑
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/customer-management && python3 __main__.py <命令> [args]

# 7 命令：gather / intake / employment / friends-sync / group-order / payment / health-check
python3 -m customer-management gather --new --limit 3          # 只读冒烟：读真实学员 + diff/回填建议
python3 -m customer-management employment --wxid <id>          # 单人核验：走 stdout 不写盘
python3 -m customer-management health-check --dry-run          # 只读体检出 plan
python3 -m customer-management <命令> --help                    # 各命令具体 flag
```

## 维护场景：要做某件事 → 改哪里

| 想做的事 | 怎么做 |
|---|---|
| **改判定口径**（什么算转型成功 / 画像怎么填 / 怎么读聊天，不碰代码） | 改对应 `cards/<name>.md` 里的 prompt 段（fenced 块）。`employment/profile/leads/payment` 四张卡，编辑即生效。 |
| **加一张新任务卡**（新分析维度） | ① 写 `cards/<new>.md`（front-matter 声明 `flow / gate / write_back`，正文 `## 段名 + ``` 块`）→ ② 若复用现有 flow 直接跑；要新 flow 则在 `capabilities/analyze/` 加 `<flow>.py`（参考 employment.py / profile.py）。 |
| **改写回规矩**（覆盖 / 追加 / 只填空 / 幂等） | 改卡 front-matter 的 `write_back` 引用 `write_policy.py` 里的**命名策略**（append/overwrite/skip_if_marked/reset/fill_only_if_empty/idempotent_field）。只有要**新策略**才动 `write_policy.py`（加纯函数 + 注册 POLICIES）。 |
| **改字段口径 / 新增飞书字段映射** | 改 `assistant_zh/student_manage/FIELD_SPEC.md`（口径真源，profile 卡会注入）；写回映射在 `outputs/sync_*.py`。 |
| **加 / 调一级命令** | 在 `__main__.py` 的 `_DISPATCH` 加映射 → 在 `recipes/<name>.py` 写配方（或指到 `capabilities.analyze.<flow>`）。 |
| **改员工排除 / 学员判定** | `assistant_zh/student_manage/staff_exclude.json`（员工名单）；确定性识别规则在 `capabilities/recognize.py`。 |
| **接新账号 / 换租户** | 当前 `scope: assistant_zh` 单租户。换号：设 `CUSTOMER_MGMT_DATA_ROOT` 指向新仓根，并在其 `student_manage/` 备齐数据；引擎代码不动。 |
| **跑只读验证 / 体检** | `gather`（默认只读 0-LLM）、`health-check --dry-run`（只读镜像出 plan）。要 live 拉飞书须显式 `--source live`。 |
| **真写飞书** | 对应命令带 `--apply`，且**须用户明说「同步飞书」**。就业飞书写回是独立一步：`python3 -m customer-management.outputs.sync_to_feishu [--apply]`。 |
| **验证 employment/profile 不误写**（红线·P3 事故教训） | analyze 默认 `--auto`（真写本地 state + 飞书）。**任何试跑必须先 `--dry-run`**；单人核验用 `--wxid <id>`（走 stdout 不写盘）；批量先 `--dry-run` 看清单 + token 预估；mutate 前先备份。 |
| **ad-hoc 读聊天 / 找人**（"谁私聊领回放""谁要退差价"这类自由检索） | `python3 -m customer-management search-chat --any <kw> --side from-them --layer all`（跨人找候选）/ `read-chat --wxid X --layer all`（读一人，含信息地图）。只读 / 0-LLM，在 `recipes/read_chat.py` + `recipes/search_chat.py`。**先用命令别直接啃 raw JSON**。见 `references/ad-hoc-chat-read.md`。 |
| **改聊天信息分层 / 信息地图 / zstd 解码口径**（哪些算文字 L0、媒体/系统怎么归类、地图怎么描述） | 改 `capabilities/analyze/core.py`：分类 `classify_message`、无损入库 `normalize_messages`、地图 `build_info_map`、默认喂层 `text_layer`、**zstd 解压 `try_decode_zstd`**（`28b52ffd…` 是压缩非加密,绝大多数是真人对话,已自动解压恢复）。**入库无损不删**,取舍在消费端。见 `doc/plan/customer-management-media-visibility-plan.md`。 |
| **按需读某人聊天图片**（文字不足时解密看图取证：付款截图/海报等） | `capabilities/acquire/resolve_images.py`：`python3 -m capabilities.acquire.resolve_images --wxid <wxid>` 或 `resolve_person_images(wxid)`。按 `md5(wxid)` 解 `config.WECHAT_ATTACH_DIR` 下该人全部 `.dat`。⚠️仅本机、按账号容器(env `CUSTOMER_MGMT_WECHAT_ATTACH` 覆盖)、按人解非按消息、wxgf 跳过。 |
| **取加好友日期等确定性派生事实** | `recognize.friend_add_date(wxid)`（0-LLM，读系统事件「你已添加了X」回退首条消息）；analyze 侧同口径在 `core.friend_add_date`。 |
| **结构变更后收口** | 改了引擎结构就更新 `registry.yaml`（engine `id: customer-management` + skill 块），跑 `python3 scripts/check-tools.py`（期望 0 error）；skill 软链变动再跑 `sync-skills.py`。 |

## 环境依赖（首跑准备）

- **engine 本体**：系统 python3 即可（标准库 + urllib LLM）；无独立 venv。
- **LLM**（analyze flow）：密钥走 tools 侧 `var/credentials/llm.env`（与视频线同源）。
- **付款解图**（acquire）：WeChat v4 `.dat` 解密 + OCR/视觉读；上游微信采集 `assistant_zh/mac/wechat/state/`（仓外 Node，可能不存在）。
- **飞书**：`student_manage/feishu_config.json` + 飞书应用凭证；只读默认走本地 `customer_management_mirror.json`，`--source live` 才连网。

## 待验收门（代码已完成，需本地实跑签收）

结构 / 冒烟已过（check-tools 0 error、7 命令 `--help` 正常、`gather` 端到端只读跑通）。剩下需用户本地真跑确认：

1. **飞书 `--apply` 真写** parity——字段口径正确。
2. **LLM analyze parity**——employment/profile 读聊天结论质量对比迁移前。
3. **视觉读 payment**——解图 + 视觉卡金额准确度。

## 相关真源

- 机器可读引擎/skill 清单：`registry.yaml`（engine `id: customer-management`、skill `name: customer-management`）
- agent 入口（薄 router）+ runbook：`tools/skills/customer-management/SKILL.md` + `references/`
- 字段口径：`assistant_zh/student_manage/FIELD_SPEC.md`
- 变更总账 / 写痕：`assistant_zh/student_manage/CHANGELOG.md` + `logs/<date>.log`
- 决策 / 迁移历史：记忆 `customer-management-migration`
