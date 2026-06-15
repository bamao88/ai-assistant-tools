# 新学员入营数据整理 · 标准流程

> 合并自原 `assistant_zh/student_manage/new_student_intake_runbook.md`。
> 每期新学员进群后，把「群成员 + 私聊报名信息 + 付款截图」整理进本地主数据并同步飞书。
> 触发：用户说「X期新学员入群了/同步到本地/整理新学员/把新学员数据弄好/补付款金额」。

**两条路径**：滚动进 1~几个人 → 走「快速路径」（首选）；整期开课首抽几十人 → 走 Phase A/B/C。
两者字段口径一致。入表写回统一走 `intake` 配方（吃 worksheet.json）。

## 真源 / 工具

| 项 | 位置 |
|---|---|
| 本地主数据 | `student_manage/all_student.json`（+ `.csv`）（留 assistant_zh）|
| staff 排除 | `student_manage/staff_exclude.json` |
| 群抽取 / 加好友日期 / 全量聊天（仓外 Node，本 skill 不接管）| `/Volumes/ExtSSD2601/mac/wechat/`（`list_rooms.js` / `wechat_extract.js` / `sync_groups.js` / `probe_first_msg.js` / `dump_chat.js`）|
| 抽取产物（数据湖，只读）| `knowledge_base/client/raw/chat/`（members_<room>.json, messages_user_<wxid>.json）|
| 付款截图子流程 | `payment` 配方 + `cards/payment.md`（见 `payment-vision.md`）|
| 入营写入器 | `intake` 配方（`python3 -m customer-management intake <worksheet.json>`）|
| 飞书真源 | `tblfCYoeornDw0XF`（app `YTcFbyGS4arILPseQJscA6J7nqb`, profile zhanghe）|

WeFlow 跑法（仓外采集）：`cd /Volumes/ExtSSD2601/mac/wechat && ELECTRON_RUN_AS_NODE=1 /Applications/WeFlow.app/Contents/MacOS/WeFlow <脚本>`。

## 铁律

- 每个写动作都备份 + 写 `student_manage/CHANGELOG.md` + `student_manage/logs/<date>.log`（没日志不算做完）。
- 飞书只填空不覆盖；缺行不自动建；真写飞书要用户明确授权「同步飞书」。
- 数据源账号 = 小助理号（八毛 `ZH_WXID_NEW`），不用张和2号。
- 加好友日期对入表的人**永不为空**（查不到首聊用入表当天兜底）。
- 私戳过的潜客一旦成交（进本期群），删其「活动标签」里的「…私戳」选项。
- 渠道：聊天里说的来源命中「渠道」字段已有选项才填；在两个直播群任一里→渠道含「黄钊」。

## 快速路径 — 单个/小批量（固定流程）

**Step 0 · 发现新学员**：刷新本期群成员（`sync_groups.js --members-only --skip-old`）→ diff
本期群学员（排除 staff）−「飞书已标本期」= 新学员 wxid。

**Step 1 · 取数（每个新学员，进 worksheet）**
- **加好友日期** = 最早一条消息日期（`probe_first_msg.js` openMessageCursor 强制取最早，别用
  messages_user 文件判断——增量同步会漏；查不到→入表当天兜底，**永不为空**）。
- **全量聊天**（`dump_chat.js`）读：自我介绍（保守，无内容留空不编造）/ 手机号（正则 `1[3-9]\d{9}`，
  真号优先取群备注名里的）/ 渠道（映射到「渠道」字段已有选项才填）。
- **直播群→黄钊**：查该 wxid 是否在 `members_57142409146_chatroom.json` / `members_54283028472_chatroom.json`。
- **付款**：`python3 -m customer-management payment --wxid <wxid>` → 读 montage 定位交易页 → 实付(取整) +
  付款方式 + 凭证图。无清晰支付页→实付留空 + 备注待核 + 传证据图。（视觉读用法见 `payment-vision.md`）

**Step 2 · 写飞书 + 本地**（`intake` 配方吃 worksheet）
- worksheet：`{wxid: {name, ziwo, qudao[], mark5(默认True), del_huodong_sizhuo, phone, pay{amt,method,img}}}`。
- `cd tools/engines && python3 -m customer-management intake <worksheet.json>`（dry-run）→ 核对 → 加 `--apply`。
- writer 行为：几期 append「5期」/ 渠道多选 append / 自我介绍只填空 / 删私戳 / 实付付款方式只填空 /
  凭证上传。**写完 record-search 核验，别靠重跑诊断。** 本地 all_student.json 同步回写 + csv，先备份。

**Step 3 · 删私戳标签**（已并入 writer 的 `del_huodong_sizhuo`）。

**Step 4 · 日志**：`student_manage/logs/<date>.log` + CHANGELOG。

## 整期首抽（大批量） · A → B → C

**Phase A — 群成员 → 本地主数据**：`list_rooms.js` 定位群 → `wechat_extract.js --account 2 --members <room>`
→ 排除 staff → 补抽缺私聊学员 → 逐条读私聊提取字段 → merge 进 all_student.json（先 `cp` 备份）→
字段完整性检查 → CHANGELOG + 日志。

**Phase B — 付款金额从截图补全**：用 `payment` 配方（`--term N期` 批量解 + 拼九宫格）→ 视觉读
montage 定位付款交易页 → 回填 `累计有效消费金额`。✅交易详情/支付成功页；❌收款码/课程页/群聊。详见 `payment-vision.md`。

**Phase C — 同步飞书（需授权「同步飞书」）**：新学员入库必填字段全集一次填全（`加好友日期`/`wxid`/
`微信名称`/`备注及其他名称`/`自我介绍`/`手机号`/`渠道`多选/`几期学员`多选/`活动标签`/`实付`/`付款方式`/
`提成截图凭证`）。匹配按 `wxid`。**金额一律填整数**（截图带小数=真实到账含手续费/零头，取整填约定价；
取整后仍拿不准就传截图让用户 review）。全量补行前先**审计**（逐个 record-search 分三类：已有标签/有行缺
标签/缺行）。⚠️ **写命令别靠「重跑看返回」诊断**（CLI 输出常非纯 JSON，重跑会重复写）——要么 `--dry-run`，
要么事后 `record-search` 核验。`几期学员` 多选必须 append 本期标签，否则飞书看不到这批人。
