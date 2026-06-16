# 学员管理 skill —— 剩余问题清单(待做完整修改计划)

> 面向 owner 的 backlog。无损分层 + zstd 解码 + read-chat/search-chat + 读图 这几轮改造已落地并由干净 agent 复测通过(见 `customer-management-media-visibility-plan.md` 与 `~/.claude/plans/sub-agent-skill-bug-functional-ullman.md`)。本文件记**还剩什么、怎么修、谁来做**,供你之后排完整修改计划。
> 状态:2026-06-16 记录。技术细节在最后一节。

## 已经确认没问题的(不用再查)

避免下次重复排查,先记下这几项实测 OK:
- **search-chat 性能**:全量 1323 文件检索 **0.4 秒**,不慢。
- **zstd 解压质量**:抽样 3048 条 L0 文字 **0 条乱码**,解压干净。
- **read-chat / search-chat / employment dry-run**:都能正常跑,只读、不写业务数据。

## 还剩的问题(按优先级)

### 🔴 P0-1 · employment / profile 的"分析质量"没复验(唯一"已改未验"风险)
- **问题**:这轮我改了这两个流程的**输入**——现在多喂了恢复出来的 ~11% 压缩消息,而且提示词前面加了一段"信息地图"。但 dry-run 不调 AI,所以"喂了这些之后,就业判定/客户画像会不会变差或跑偏"**没测过**。
- **影响**:这两个流程会**真写飞书**(默认就真写),输入变了却没验输出 = 潜在风险。
- **怎么修**:本地拿 2–3 个已有结论的学员,跑改前/改后对比真实 AI 结论是否一致;若变差,就决定"信息地图只给 ad-hoc 检索用、不进 employment/profile"。
- **谁做**:**张和/吴湘萍本地验**(需要 AI key + 你判断质量),我替不了。

### 🟡 P1-2 · 没有"退差价"任务卡,业务判断没固化
- **问题**:`search-chat` 能找出候选,但"训练营学员要不要除外""差价金额怎么算""隐式表达(我8900买的)算不算"全靠 AI 临场发挥,每次可能不一样。
- **怎么修**:写一张 `退差价` 任务卡,把判定口径 + 召回口径 + 读图复核固化下来(就是之前说的 C4)。
- **谁做**:我能直接做(等公式定了)。

### 🟡 P1-3 · 差价公式还没拍板
- **问题**:你说的是"差价 = 8900 − 实付",但聊天里运营(你)实际说的是"差价 = 实付 − 8600",两者结论相反(付得最多的人,前者退 0、后者退最多)。
- **怎么修**:**你定一个**,定了写进退差价卡。
- **谁做**:**你拍板**。

### 🟡 P1-4 · Will / kammy 的"实付金额"客户表里是空的,且 Will 截图疑似 8800 ≠ 自称 8900
- **问题**:这两人 `累计有效消费金额` 为空;Will 自报 8900,但解出的付款缩略图像 ¥8800,没核实。
- **怎么修**:用 `resolve_images` 解高清核实金额 → 回填客户表。属数据修补,不是代码。
- **谁做**:我能解图给你看,**金额以谁为准你确认**后回填。

### 🟢 P2-5 · `payment` 配方里有自己的解图函数,和新的 `resolve_images` 重复
- **问题**:同一套解密逻辑两份,以后改一处忘另一处。
- **怎么修**:让 payment 复用 `resolve_images`,删掉重复。
- **谁做**:我能直接做(低风险)。

### 🟢 P2-6 · wxgf 格式图片解不了
- **问题**:微信新图片格式(Will 13 张里有 5 张),当前跳过,看不到内容。
- **怎么修**:接 Wxam2pic 转码;依赖外部工具,看需要再做。
- **谁做**:看需求,优先级低。

### 🟢 P2-7 · 消息方向判断依赖"员工名单"完整
- **问题**:判断"谁发的"靠 `staff_exclude.json`,漏登记一个员工号就会把该消息方向判错。
- **怎么修**:偶尔核对员工名单是否齐全;无代码改动。
- **谁做**:维护性,低优先级。

## 建议的处理顺序(供你排计划参考)

1. **P0-1 本地复验**(你跑)——确认我对 employment/profile 的改动没搞坏,这是唯一未验风险;
2. **P1-3 差价公式**(你定);
3. **P1-2 退差价卡** + **P2-5 payment dedup**(我做,这两个明确、低风险);
4. P1-4(实付回填)、P2-6(wxgf)、P2-7(员工名单)按需再排。

---

## 技术细节(给执行 agent 看 —— owner 可略过)

| ID | 落点 | 关键 |
|---|---|---|
| P0-1 | `capabilities/analyze/employment.py`、`profile.py` | 输入变更:`text_layer` 现含 zstd 恢复消息 + `build_info_map` 前置进 transcript/user_prompt。验收:同 wxid 改前/改后真实 LLM 结论对比;若回退,把 info_map 从 employment/profile 拿掉、只留给 read-chat/search-chat。 |
| P1-2 | 新 `cards/refund.md` + 可能新 analyze flow | 卡三要素:prompt(读退差价意图,含隐式"我X买的")+ result 字段 + write-back;gate/召回锚=`累计有效消费金额` > 新价反查 + `search-chat`;读图复核走 `resolve_images`。 |
| P1-3 | `cards/refund.md` 内的公式常量 | 二选一:`实付-8600`(聊天口径) vs `8900-实付`(用户原话)。 |
| P1-4 | `assistant_zh/student_manage/all_student.json` | `resolve_images --wxid {Will=B879623389, kammy=qq261078661}` 解高清读金额 → 回填 `累计有效消费金额`;留 CHANGELOG。 |
| P2-5 | `recipes/payment.py::decrypt_student` → 复用 `capabilities/acquire/resolve_images.resolve_person_images` | dedup;payment 的 montage 拼图保留,只把"解某人 .dat"换成调 resolve_images。 |
| P2-6 | `capabilities/acquire/decrypt_dat.py`(wxgf 分支)+ Wxam2pic | 当前 `dat2img` 对 `ext=='wxgf'` 直接跳过。 |
| P2-7 | `assistant_zh/student_manage/staff_exclude.json` | `core.is_staff_sender` 依赖其完整性。 |

收口:做完任一项,同步更新 `doc/customer-management-architecture.md` 维护表 + 本文件状态 + 记忆 [[customer-management-lossless-layering]]。
