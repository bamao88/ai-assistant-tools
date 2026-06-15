"""
给"在 3 个群里但飞书客户管理表没行"的非 staff 群成员**新建行**。

每个新行只填 4 个字段：
  - wxid                  ← 直接是该成员的 wxid
  - 客户名称（微信号）       ← 填 wxid（飞书既有数据里这个字段允许填 wxid）
  - 姓名                  ← 群昵称 display_seen，如果空就留空
  - 群序号-四期 / 群序号-核心 / 群序号-4.5期 ← 该成员在哪些群、第几位

其他字段一律不动（让用户后续手工补"几期"、"成交时间"等业务字段）。

过滤掉 staff_exclude.json 里的 wxid。

用法:
  python3 -m workflow.student_employment_tracking.add_missing_group_members           # dry-run
  python3 -m workflow.student_employment_tracking.add_missing_group_members --apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# engine 根（capabilities/resolve/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

PROJECT_ROOT = config.PROJECT_ROOT
BY_WXID_FILE = config.BY_WXID_FILE
STAFF_EXCLUDE_FILE = config.STAFF_EXCLUDE_FILE
RUN_DIR_BASE = config.GROUP_ORDER_ADD_RUNS_DIR

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"

GROUP_FIELDS = ["群序号-四期", "群序号-核心", "群序号-4.5期"]
FIELD_WXID = "wxid"
FIELD_KEHUMING = "客户名称（微信号）"
FIELD_XINGMING = "姓名"

BATCH_SIZE = 100


def run_lark(args: list[str], timeout: int = 60) -> dict:
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"lark-cli failed: stderr={res.stderr[:300]}")
    data = json.loads(res.stdout)
    if data.get("code") != 0:
        raise RuntimeError(f"feishu error code={data.get('code')} msg={data.get('msg')}")
    return data.get("data", {})


def fetch_existing_wxids() -> set[str]:
    print("[fetch] 拉飞书表现有 wxid ...")
    out: set[str] = set()
    page_token = ""
    while True:
        params: dict[str, Any] = {"page_size": 500, "field_names": json.dumps(["wxid"])}
        if page_token:
            params["page_token"] = page_token
        data = run_lark([
            "api", "GET",
            f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            "--params", json.dumps(params, ensure_ascii=False),
        ])
        for it in (data.get("items") or []):
            val = (it.get("fields") or {}).get(FIELD_WXID)
            if isinstance(val, str) and val.strip():
                out.add(val.strip())
            elif isinstance(val, list) and val and isinstance(val[0], dict):
                t = val[0].get("text") or ""
                if t.strip():
                    out.add(t.strip())
        if not data.get("has_more"):
            break
        page_token = data.get("page_token") or ""
        if not page_token:
            break
        time.sleep(0.2)
    print(f"[fetch] 飞书表 wxid 集合：{len(out)} 个")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    by_wxid = json.loads(BY_WXID_FILE.read_text(encoding="utf-8"))
    staff_data = json.loads(STAFF_EXCLUDE_FILE.read_text(encoding="utf-8"))
    staff_wxids = {s["wxid"] for s in staff_data.get("staff", [])}

    existing = fetch_existing_wxids()

    # 待添加 = by_wxid - existing - staff
    to_add_wxids = [w for w in by_wxid.keys() if w not in existing and w not in staff_wxids]
    print(f"待添加：by_wxid 总数 {len(by_wxid)} - 飞书已有 {len(by_wxid) & set(existing) if False else sum(1 for w in by_wxid if w in existing)} - staff {sum(1 for w in by_wxid if w in staff_wxids)} = {len(to_add_wxids)}")

    new_records: list[dict] = []
    plan_rows: list[dict] = []
    for wxid in to_add_wxids:
        info = by_wxid[wxid]
        display = (info.get("display_seen") or "").strip()
        fields: dict[str, Any] = {
            FIELD_WXID: wxid,
            FIELD_KEHUMING: wxid,
        }
        if display:
            fields[FIELD_XINGMING] = display
        for f in GROUP_FIELDS:
            if f in info:
                fields[f] = int(info[f])
        new_records.append({"fields": fields})
        plan_rows.append({
            "wxid": wxid,
            "客户名称": wxid,
            "姓名": display,
            "群序号": {f: info.get(f) for f in GROUP_FIELDS},
        })

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    run_dir = RUN_DIR_BASE / f"{run_id}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(
        json.dumps(plan_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# 新建群成员行  ({mode})\n",
          f"- 待添加：{len(plan_rows)} 行（已排除 staff + 飞书已存在）\n",
          "## 前 30 条示例",
          "| wxid | 客户名称 | 姓名 | 四期 | 核心 | 4.5期 |",
          "|---|---|---|---|---|---|"]
    for r in plan_rows[:30]:
        go = r["群序号"]
        md.append(f"| {r['wxid']} | {r['客户名称']} | {r['姓名']} | {go.get('群序号-四期','')} | {go.get('群序号-核心','')} | {go.get('群序号-4.5期','')} |")
    (run_dir / "plan.md").write_text("\n".join(md), encoding="utf-8")

    print(f"[{mode}] 待新建 {len(new_records)} 行")
    print(f"  → plan: {run_dir / 'plan.md'}")

    if not args.apply:
        print("[dry-run] 不真写。要真写：加 --apply")
        return

    print(f"[apply] 批量创建 ...")
    t0 = time.time()
    ok = 0
    fail = 0
    for i in range(0, len(new_records), BATCH_SIZE):
        batch = new_records[i:i + BATCH_SIZE]
        try:
            run_lark([
                "api", "POST",
                f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_create",
                "--data", json.dumps({"records": batch}, ensure_ascii=False),
            ], timeout=120)
            ok += len(batch)
            print(f"  [batch {i//BATCH_SIZE+1}] ok ({len(batch)})")
        except RuntimeError as e:
            fail += len(batch)
            print(f"  [batch {i//BATCH_SIZE+1}] FAIL: {e}")
        time.sleep(0.5)
    elapsed = time.time() - t0
    print(f"[apply done] ok={ok} fail={fail} elapsed={elapsed:.1f}s")
    (run_dir / "result.json").write_text(json.dumps({
        "run_id": run_id, "mode": mode, "added_ok": ok, "added_fail": fail,
        "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
