"""
群序号 sync — 把 analytics/group_member_order/by_wxid.json 的 3 列群序号同步到飞书客户管理表

匹配键: wxid
覆盖语义: 3 个 number 字段每次都按当前 by_wxid.json 覆盖；不在某个群里 → 该字段写 null

用法:
    python3 -m workflow.student_employment_tracking.sync_group_order            # 默认 dry-run
    python3 -m workflow.student_employment_tracking.sync_group_order --apply    # 真写
    python3 -m workflow.student_employment_tracking.sync_group_order --wxid X
    python3 -m workflow.student_employment_tracking.sync_group_order --limit 5
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BY_WXID_FILE = PROJECT_ROOT / "analytics" / "group_member_order" / "by_wxid.json"
SYNC_RUNS_DIR = PROJECT_ROOT / "analytics" / "group_member_order" / "sync_runs"

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"

FIELD_WXID = "wxid"
GROUP_FIELDS = ["群序号-四期", "群序号-核心", "群序号-4.5期"]

BATCH_SIZE = 100


def run_lark(args: list[str], timeout: int = 60) -> dict:
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"lark-cli failed: {' '.join(args[:6])}... stderr={res.stderr[:300]}")
    data = json.loads(res.stdout)
    if data.get("code") != 0:
        raise RuntimeError(f"feishu error code={data.get('code')} msg={data.get('msg')}")
    return data.get("data", {})


def fetch_all_feishu_records() -> list[dict]:
    print("[sync] 拉飞书全表 ...", file=sys.stderr)
    all_items: list[dict] = []
    page_token = ""
    while True:
        params: dict[str, Any] = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        data = run_lark([
            "api", "GET",
            f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            "--params", json.dumps(params, ensure_ascii=False),
        ])
        all_items.extend(data.get("items") or [])
        if not data.get("has_more"):
            break
        page_token = data.get("page_token") or ""
        if not page_token:
            break
        time.sleep(0.2)
    print(f"[sync] 共拉到 {len(all_items)} 行", file=sys.stderr)
    return all_items


def index_by_wxid(records: list[dict]) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for r in records:
        val = r.get("fields", {}).get(FIELD_WXID)
        wxid = val.strip() if isinstance(val, str) else ""
        if not wxid or wxid in idx:
            continue
        idx[wxid] = r
    return idx


def build_update_payload(latest_orders: dict, feishu_fields: dict) -> tuple[dict, list[str]]:
    """对一行飞书生成 payload。3 个字段都按 latest 覆盖；latest 缺失（学员不在该群）→ 设 null（清空）。"""
    payload: dict[str, Any] = {}
    reasons: list[str] = []
    for f in GROUP_FIELDS:
        new_val = latest_orders.get(f)  # int 或 None
        cur_val = feishu_fields.get(f)
        if isinstance(cur_val, (int, float)):
            cur_int = int(cur_val)
        else:
            cur_int = None
        new_int = int(new_val) if isinstance(new_val, int) else None
        if cur_int != new_int:
            payload[f] = new_int  # None 时飞书会清空字段值
            reasons.append(f"{f}:{cur_int}→{new_int}")
    return payload, reasons


def batch_update_records(updates: list[dict], apply: bool, logger) -> tuple[int, int]:
    if not updates or not apply:
        return 0, 0
    ok_cnt = 0
    fail_cnt = 0
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i + BATCH_SIZE]
        body = {"records": batch}
        try:
            run_lark([
                "api", "POST",
                f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update",
                "--data", json.dumps(body, ensure_ascii=False),
            ], timeout=120)
            ok_cnt += len(batch)
            logger(f"  [batch {i//BATCH_SIZE+1}] ok ({len(batch)} records)")
        except RuntimeError as e:
            fail_cnt += len(batch)
            logger(f"  [batch {i//BATCH_SIZE+1}] FAIL: {e}")
        time.sleep(0.5)
    return ok_cnt, fail_cnt


def main():
    p = argparse.ArgumentParser(description="把 by_wxid.json 的 3 列群序号同步到飞书客户管理表")
    p.add_argument("--apply", action="store_true", help="真写（默认 dry-run）")
    p.add_argument("--wxid", type=str, default="")
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    by_wxid = json.loads(BY_WXID_FILE.read_text(encoding="utf-8"))
    print(f"[sync] by_wxid.json 共 {len(by_wxid)} 学员", file=sys.stderr)

    feishu_records = fetch_all_feishu_records()
    feishu_idx = index_by_wxid(feishu_records)
    print(f"[sync] 飞书表 wxid-indexed {len(feishu_idx)} 行（共 {len(feishu_records)} 行）", file=sys.stderr)

    # 目标 = by_wxid ∪ 飞书已存在的 wxid 行（后者为了把退群的人字段清空）
    target_wxids = set(by_wxid.keys()) | set(feishu_idx.keys())
    if args.wxid:
        if args.wxid not in target_wxids:
            print(f"[ERROR] {args.wxid} 不在 by_wxid 也不在飞书", file=sys.stderr)
            sys.exit(1)
        target_wxids = {args.wxid}
    target_list = sorted(target_wxids)
    if args.limit:
        target_list = target_list[:args.limit]

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    run_dir = SYNC_RUNS_DIR / f"{run_id}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "sync.log"
    log_fh = log_path.open("w", encoding="utf-8")

    def logger(msg: str):
        log_fh.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
        log_fh.flush()

    updates: list[dict] = []
    plan_rows: list[dict] = []
    no_match: list[str] = []  # 在 by_wxid 里但飞书没行 — 学员存在但客户管理表没登记

    for wxid in target_list:
        latest_orders = by_wxid.get(wxid, {})  # 退群的人 → 空 dict，3 个字段都清空
        feishu_row = feishu_idx.get(wxid)
        if not feishu_row:
            no_match.append(wxid)
            logger(f"NO_MATCH wxid={wxid} display={latest_orders.get('display_seen','')}")
            continue
        record_id = feishu_row.get("record_id") or feishu_row.get("id")
        feishu_fields = feishu_row.get("fields", {})
        payload, reasons = build_update_payload(latest_orders, feishu_fields)
        if not payload:
            logger(f"SKIP_NO_CHANGE wxid={wxid}")
            continue
        plan_rows.append({
            "wxid": wxid,
            "display_seen": latest_orders.get("display_seen", ""),
            "record_id": record_id,
            "reasons": reasons,
            "fields": list(payload.keys()),
        })
        updates.append({"record_id": record_id, "fields": payload})
        logger(f"PLAN_UPDATE wxid={wxid} reasons={reasons}")

    (run_dir / "plan.json").write_text(
        json.dumps(plan_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "no_match.json").write_text(
        json.dumps(no_match, ensure_ascii=False, indent=2), encoding="utf-8")

    plan_md = [
        f"# 群序号 sync {mode} — {run_id}",
        "",
        f"- by_wxid 总数：{len(by_wxid)}",
        f"- 飞书 wxid-indexed：{len(feishu_idx)}",
        f"- 目标 wxid：{len(target_list)}",
        f"- 计划更新行数：{len(updates)}",
        f"- 无匹配 wxid（在 by_wxid 但飞书没行）：{len(no_match)}",
        "",
    ]
    if plan_rows:
        plan_md.append("## 前 20 条更新示例\n")
        plan_md.append("| wxid | display | reasons |")
        plan_md.append("|---|---|---|")
        for row in plan_rows[:20]:
            r = ", ".join(row["reasons"])
            plan_md.append(f"| {row['wxid']} | {row['display_seen']} | {r} |")
    (run_dir / "plan.md").write_text("\n".join(plan_md), encoding="utf-8")

    print(f"[{mode}] target={len(target_list)} updates={len(updates)} no_match={len(no_match)}")
    print(f"  → plan: {run_dir / 'plan.md'}")

    if not args.apply:
        print("[dry-run] 不真写。要真写：加 --apply", file=sys.stderr)
        return

    print(f"[apply] 开始真写 {len(updates)} 行 ...")
    t0 = time.time()
    ok, fail = batch_update_records(updates, apply=True, logger=logger)
    elapsed = time.time() - t0
    print(f"[apply done] ok={ok} fail={fail} elapsed={elapsed:.1f}s")

    (run_dir / "result.json").write_text(json.dumps({
        "run_id": run_id, "mode": mode,
        "target_count": len(target_list),
        "updated_ok": ok, "updated_fail": fail,
        "no_match": len(no_match), "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
