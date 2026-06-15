#!/usr/bin/env python3
"""config.py — customer-management engine 的唯一路径解析器（跨仓单点）。

engine 代码住 tools/，业务数据住 assistant_zh/。原本散落在各模块里的硬编码
绝对路径（BASE_DIR / DATA_DIR / STATE_DIR / PROJECT_ROOT.parents[2] / ...）
全部收口到这里：每个迁移模块从本文件读路径，绝不再自己拼绝对路径。

设计要点
--------
* **import-time 廉价**：只算路径，不读写任何数据文件（assert 留给 verify 脚本/调用方）。
* **可被环境变量覆盖**：`CUSTOMER_MGMT_DATA_ROOT` 指向 assistant_zh 仓根，便于多租户/测试
  /仓库搬家时改一处即可；缺省回落到当前已知绝对路径。
* **数据留 assistant_zh**：本文件解析出的所有路径都落在 DATA_ROOT（assistant_zh）下，
  engine 经此读写，从不把数据搬进 tools。

迁移前后路径锚点对照
-------------------
旧 student_manage/*.py            : BASE_DIR = ".../assistant_zh/student_manage"（硬编码）
旧 workflow/student_employment_*  : PROJECT_ROOT = Path(__file__).resolve().parents[2]
                                    （恰好等于 assistant_zh 仓根）
迁移后两者统一 = 本文件的 DATA_ROOT（assistant_zh 仓根）/ STUDENT_MANAGE_DIR。
"""

from __future__ import annotations

import os
from pathlib import Path

# --- 锚点：assistant_zh 仓根（业务数据真源所在仓库）----------------------------
# 迁移前 workflow/.../*.py 的 `Path(__file__).resolve().parents[2]` 即此目录。
_DEFAULT_DATA_ROOT = "/Volumes/ExtSSD2601/AI_Assistant/assistant_zh"

DATA_ROOT = Path(os.environ.get("CUSTOMER_MGMT_DATA_ROOT", _DEFAULT_DATA_ROOT)).resolve()

# 向后兼容别名：旧 workflow 模块语义里的 PROJECT_ROOT == assistant_zh 仓根。
PROJECT_ROOT = DATA_ROOT

# --- 学员主数据目录（旧 student_manage/）-------------------------------------
STUDENT_MANAGE_DIR = DATA_ROOT / "student_manage"
BASE_DIR = STUDENT_MANAGE_DIR  # 旧 student_manage/*.py 的 BASE_DIR 别名

STUDENT_FILE = STUDENT_MANAGE_DIR / "all_student.json"
CSV_FILE = STUDENT_MANAGE_DIR / "all_student.csv"
STAFF_EXCLUDE_FILE = STUDENT_MANAGE_DIR / "staff_exclude.json"
FIELD_SPEC_FILE = STUDENT_MANAGE_DIR / "FIELD_SPEC.md"
FEISHU_CONFIG_FILE = STUDENT_MANAGE_DIR / "feishu_config.json"
MANUAL_OVERRIDES_FILE = STUDENT_MANAGE_DIR / "manual_overrides.json"
MIRROR_FILE = STUDENT_MANAGE_DIR / "customer_management_mirror.json"
SUMMARY_FILE = STUDENT_MANAGE_DIR / "last_update_summary.json"
DIFF_FILE = STUDENT_MANAGE_DIR / "incremental_changes.json"

# 运行态目录（留 assistant_zh，engine 读写）
STATE_DIR = STUDENT_MANAGE_DIR / "state"
PENDING_DIR = STUDENT_MANAGE_DIR / "pending"
LOG_DIR = STUDENT_MANAGE_DIR / "logs"

# llm_enrich 断点 / pending
ENRICH_PROGRESS_FILE = STATE_DIR / "enrich_progress.json"
DECISIONS_FILE = PENDING_DIR / "decisions.json"
PARSE_FAILURES_FILE = PENDING_DIR / "parse_failures.json"

# --- 共享数据湖（微信采集产物，只读边界，§13）-------------------------------
DATA_DIR = DATA_ROOT / "knowledge_base" / "client" / "raw" / "chat"
CHAT_DIR = DATA_DIR  # analyze.py 旧名

# --- 仓外微信上游（acquire 的上游，可能不存在 / gitignore）-------------------
WECHAT_STATE_DIR = DATA_ROOT / "mac" / "wechat" / "state"
DASHBOARD_PATH = WECHAT_STATE_DIR / "dashboard.json"
SYNC_SUMMARY_FILE = WECHAT_STATE_DIR / "last_sync_summary.json"

# --- analytics 产物（原地留 assistant_zh，§6）-------------------------------
ANALYTICS_DIR = DATA_ROOT / "analytics"
EMPLOYMENT_ANALYTICS_DIR = ANALYTICS_DIR / "student_employment_tracking"
FRIENDS_INDEX_DIR = ANALYTICS_DIR / "friends_index"
GROUP_MEMBER_ORDER_DIR = ANALYTICS_DIR / "group_member_order"

# 就业追踪 state / 产物
EMPLOYMENT_PROGRESS_FILE = STATE_DIR / "student_employment_tracking_progress.json"
EMPLOYMENT_LATEST_FILE = STATE_DIR / "student_employment_tracking_latest.json"
EMPLOYMENT_PER_STUDENT_DIR = EMPLOYMENT_ANALYTICS_DIR / "per_student"
EMPLOYMENT_RUNS_DIR = EMPLOYMENT_ANALYTICS_DIR / "runs"
EMPLOYMENT_SYNC_RUNS_DIR = EMPLOYMENT_ANALYTICS_DIR / "sync_runs"

# friends_index 产物
FRIENDS_INDEX_FILE = FRIENDS_INDEX_DIR / "friends.json"
FRIENDS_SYNC_RUNS_DIR = FRIENDS_INDEX_DIR / "sync_runs"
FRIENDS_AUDIT_DIR = FRIENDS_INDEX_DIR / "duplicate_audits"
FRIENDS_MERGE_DIR = FRIENDS_INDEX_DIR / "merges"
FRIENDS_COLUMN_FIX_DIR = FRIENDS_INDEX_DIR / "column_fixes"

# group_member_order 产物
BY_WXID_FILE = GROUP_MEMBER_ORDER_DIR / "by_wxid.json"
GROUP_ORDER_SYNC_RUNS_DIR = GROUP_MEMBER_ORDER_DIR / "sync_runs"
GROUP_ORDER_ADD_RUNS_DIR = GROUP_MEMBER_ORDER_DIR / "add_runs"
GROUP_ORDER_WXID_FILLS_DIR = GROUP_MEMBER_ORDER_DIR / "wxid_fills"
MISSING_WXID_CANDIDATES_FILE = GROUP_MEMBER_ORDER_DIR / "missing_wxid_candidates.json"


def ensure_dir(p: Path) -> Path:
    """按需建目录（运行态目录懒创建，沿用旧模块行为）。"""
    p.mkdir(parents=True, exist_ok=True)
    return p
