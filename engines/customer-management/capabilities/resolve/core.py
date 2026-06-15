#!/usr/bin/env python3
"""core.py — resolve 能力的可复用核（§5/§6，为 P4 的 health_check 配方铺路）。

死脚本考古发现 `find_missing_wxid`/`update_existing_wxids`/`fix_zh2_*`/
`fix_friends_column_*`/`audit_+merge_dup` 骨架完全相同：

    扫飞书表找某类毛病的行 → 出人读候选清单(plan) → dry-run 确认
      → --apply 幂等批量改 → 归档 run

本模块把这套**共享骨架**抽出来复用：lark-cli 调用 + 分页拉全表 + run 归档目录
+ 幂等 batch_update / batch_delete + dry-run/apply 门。各 resolve 脚本只保留
自己的「找毛病 + 出候选」逻辑，IO/写回骨架走这里。

⚠️ 本模块只提供 API，**不自己跑 --apply**；调用方决定何时真写（沿用授权门）。
P3 只抽核、不建 health_check 配方（那是 P4）。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# engine 根（capabilities/resolve/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

__all__ = [
    "APP_TOKEN",
    "TABLE_ID",
    "LARK_PROFILE",
    "DEFAULT_BATCH_SIZE",
    "LarkError",
    "run_lark",
    "fetch_all_records",
    "stringify",
    "multiselect_names",
    "clean_name",
    "make_run_dir",
    "write_plan",
    "batch_update",
    "batch_delete",
]

# 客户管理表（飞书唯一真源，tblfCYoeornDw0XF）
APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"
DEFAULT_BATCH_SIZE = 100


class LarkError(RuntimeError):
    """lark-cli 调用 / 飞书返回非 0 code。"""


# --- lark-cli 调用 ----------------------------------------------------------

def run_lark(args: list[str], *, timeout: int = 60,
             app_token: str = APP_TOKEN, table_id: str = TABLE_ID,
             profile: str = LARK_PROFILE) -> dict:
    """跑 lark-cli，返回解析后的 data 字段。失败 raise LarkError。

    兼容旧各脚本两种 code 校验口径：飞书成功 code 为 0（部分接口 None）。
    """
    cmd = ["lark-cli", "--as", "bot", "--profile", profile] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise LarkError(f"lark-cli failed: {' '.join(args[:6])}... stderr={res.stderr[:300]}")
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise LarkError(f"lark-cli non-JSON: {e} stdout_head={res.stdout[:200]}")
    if data.get("code") not in (None, 0):
        raise LarkError(f"feishu error code={data.get('code')} msg={data.get('msg')}")
    return data.get("data", {})


def fetch_all_records(*, page_size: int = 500, timeout: int = 60,
                      app_token: str = APP_TOKEN, table_id: str = TABLE_ID,
                      profile: str = LARK_PROFILE,
                      log: Callable[[str], None] | None = None) -> list[dict]:
    """分页拉飞书全表，返回 [{record_id, fields:{...}}]。"""
    _log = log or (lambda m: print(m, file=sys.stderr))
    _log("[fetch] 拉飞书全表 ...")
    all_items: list[dict] = []
    page_token = ""
    while True:
        params: dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        data = run_lark([
            "api", "GET",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            "--params", json.dumps(params, ensure_ascii=False),
        ], timeout=timeout, app_token=app_token, table_id=table_id, profile=profile)
        all_items.extend(data.get("items") or [])
        if not data.get("has_more"):
            break
        page_token = data.get("page_token") or ""
        if not page_token:
            break
        time.sleep(0.2)
    _log(f"[fetch] 共 {len(all_items)} 行")
    return all_items


# --- 飞书字段值规约 ---------------------------------------------------------

def stringify(v: Any) -> str:
    """飞书任意字段值 → 纯文本（str / list[{text|name}] / 其它）。"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "".join(
            (it.get("text") or it.get("name") or "") if isinstance(it, dict) else str(it)
            for it in v
        )
    return str(v)


def multiselect_names(value: Any) -> list[str]:
    """多选字段 → 选项名 list。"""
    if isinstance(value, list):
        return [str(it.get("name") if isinstance(it, dict) else it)
                for it in value if (it.get("name") if isinstance(it, dict) else it)]
    if isinstance(value, str) and value:
        return [value]
    return []


_CLEAN_KEEP_RE = re.compile(r"[^一-鿿぀-ヿA-Za-z0-9_\- ]")
_CLEAN_SPLIT_RE = re.compile(r"[-—()（）/@\s]")


def clean_name(s: str) -> str:
    """从昵称里抽"看起来像真名"的头部：去 emoji/期数后缀，截到第一个分隔符。"""
    if not s:
        return ""
    s = _CLEAN_KEEP_RE.sub(" ", s.strip())
    head = _CLEAN_SPLIT_RE.split(s)[0]
    return head.strip()


# --- run 归档 ---------------------------------------------------------------

def make_run_dir(base: Path, *, apply: bool, suffix: str = "") -> tuple[Path, str, str]:
    """建归档目录 base/<run_id>_[suffix_]{apply|dryrun}/，返回 (run_dir, run_id, mode)。"""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if apply else "dryrun"
    name = f"{run_id}_{suffix}_{mode}" if suffix else f"{run_id}_{mode}"
    run_dir = base / name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, run_id, mode


def write_plan(run_dir: Path, plan_json: Any, plan_md: str) -> None:
    """落人读 plan.md + 结构化 plan.json（dry-run 确认环节）。"""
    (run_dir / "plan.json").write_text(
        json.dumps(plan_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "plan.md").write_text(plan_md, encoding="utf-8")


# --- 幂等批量写回 -----------------------------------------------------------

def batch_update(updates: list[dict], *, batch_size: int = DEFAULT_BATCH_SIZE,
                 timeout: int = 120, app_token: str = APP_TOKEN, table_id: str = TABLE_ID,
                 profile: str = LARK_PROFILE,
                 log: Callable[[str], None] | None = None) -> tuple[int, int]:
    """batch_update 一批 [{record_id, fields}]，返回 (ok, fail)。空 → (0,0)。"""
    _log = log or (lambda m: print(m))
    ok = fail = 0
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        try:
            run_lark([
                "api", "POST",
                f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update",
                "--data", json.dumps({"records": batch}, ensure_ascii=False),
            ], timeout=timeout, app_token=app_token, table_id=table_id, profile=profile)
            ok += len(batch)
            _log(f"  UPDATE batch {i // batch_size + 1}: ok ({len(batch)})")
        except LarkError as e:
            fail += len(batch)
            _log(f"  UPDATE batch {i // batch_size + 1}: FAIL {e}")
        time.sleep(0.5)
    return ok, fail


def batch_delete(record_ids: list[str], *, batch_size: int = 500,
                 timeout: int = 120, app_token: str = APP_TOKEN, table_id: str = TABLE_ID,
                 profile: str = LARK_PROFILE,
                 log: Callable[[str], None] | None = None) -> tuple[int, int]:
    """batch_delete 一批 record_id，返回 (ok, fail)。"""
    _log = log or (lambda m: print(m))
    ok = fail = 0
    for i in range(0, len(record_ids), batch_size):
        batch = record_ids[i:i + batch_size]
        try:
            run_lark([
                "api", "POST",
                f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete",
                "--data", json.dumps({"records": batch}, ensure_ascii=False),
            ], timeout=timeout, app_token=app_token, table_id=table_id, profile=profile)
            ok += len(batch)
            _log(f"  DELETE batch {i // batch_size + 1}: ok ({len(batch)})")
        except LarkError as e:
            fail += len(batch)
            _log(f"  DELETE batch {i // batch_size + 1}: FAIL {e}")
        time.sleep(0.5)
    return ok, fail
