# customer-management references

详细 runbook 与口径。SKILL.md 是薄入口，本目录是细节真源。

| 文件 | 内容 |
|---|---|
| `data-model.md` | 数据流（微信 → 数据湖 → 本地主数据 → 飞书）、飞书表归口、本地↔飞书关系、镜像、字段口径、解耦边界、故障排查 |
| `employment-tracking.md` | 就业回访子流程：输入/输出、飞书字段映射、运行模式、增量规则、回访开场白预过滤、prompt、守则、追问模板 |
| `intake-runbook.md` | 新学员入营标准流程（快速路径 Step0-4 + 整期 A/B/C），付款视觉卡用法 |
| `health-check.md` | 客户表数据体检/订正闭环：缺陷类、scan→plan→apply→archive |
| `payment-vision.md` | 付款金额视觉读卡（`cards/payment.md`）的 agent 用法 |
| `symlink-rebuild.md` | ⚠️ 双 host 软链重建 runbook（软链脆弱性 §12）；移动 tools 目录后必跑 |

## 命令速查（7 配方）

> 连字符目录名不能直接做 Python `-m` 模块名时用形式 B。

```bash
# 形式 A（推荐）
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines && python3 -m customer-management <cmd> [args]
# 形式 B
cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/customer-management && python3 __main__.py <cmd> [args]
```

| 旧调用（已删，仅供对照） | 新命令 |
|---|---|
| `python3 -m student_manage.run --dry-run` / `--skip-llm` | `python3 -m customer-management gather` （读取侧 Facade，默认只读）/ 周更编排见 `recipes/run.py` |
| `python3 -m workflow.student_employment_tracking.analyze --auto/--dry-run/--wxid/--sample/--bootstrap/--rerun-not-followed-up` | `python3 -m customer-management employment --auto/--dry-run/--wxid/--sample/--bootstrap/--rerun-not-followed-up` |
| `python3 -m workflow.student_employment_tracking.sync_to_feishu [--apply]` | `python3 -m customer-management.outputs.sync_to_feishu [--apply]`（就业字段 append/skip-if-marked/overwrite，独立一步）|
| `python3 -m workflow.student_employment_tracking.sync_friends_to_feishu --role zh2 [--apply]` + `audit_duplicate_creates` + `merge_duplicate_creates` | `python3 -m customer-management friends-sync --role zh2 [--apply]`（sync+audit+merge **三步合一**） |
| `python3 -m workflow.student_employment_tracking.sync_group_order [--apply]` | `python3 -m customer-management group-order [--apply]` |
| `student_manage/intake/intake_writer.py <worksheet.json> [--apply]` | `python3 -m customer-management intake <worksheet.json> [--apply]` |
| `student_manage/payment_proof/extract_payments.py --term N期 / --wxid <id>` | `python3 -m customer-management payment --term N期 / --wxid <id>` |
| `find_missing_wxid` / `update_existing_wxids` / `fix_zh2_weixin_name_to_nick` / `fix_friends_column_misplacement` / `audit_+merge_dup`（一次性死脚本） | `python3 -m customer-management health-check [缺陷类] [--apply]`（`--list` 看全部缺陷类） |
