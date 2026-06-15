"""
人工 review 通过的 5 条候选 wxid，写到飞书已有行的 wxid 字段。
同时把对应的 3 列群序号一起填上（这些 wxid 在 by_wxid.json 里都有数据）。

只更新这 4 个字段：wxid / 群序号-四期 / 群序号-核心 / 群序号-4.5期
不动其他任何字段。

5 条候选（来自 missing_wxid_review.md）：
  阅天     → wxid_e5j8ubua5lbf22 (M3-微信昵称)
  wy_nemo  → wy_nemo             (M0-客户名即wxid)
  anna011539 → anna011539        (M0-客户名即wxid)
  L&Lin    → wxid_aumw3dw2w9eu22 (M4-备注头部)
  杨羚     → wxid_mkn8v58ofzeq22 (M5-群昵称头部)

用法:
  python3 -m capabilities.resolve.update_existing_wxids           # dry-run
  python3 -m capabilities.resolve.update_existing_wxids --apply
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
CANDIDATES_FILE = config.MISSING_WXID_CANDIDATES_FILE
BY_WXID_FILE = config.BY_WXID_FILE
RUN_DIR_BASE = config.GROUP_ORDER_WXID_FILLS_DIR

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"

GROUP_FIELDS = ["群序号-四期", "群序号-核心", "群序号-4.5期"]

# 显式列出人工 review 通过的，避免误带入低置信
APPROVED_CONFIDENCES = {"high", "medium"}


def run_lark(args: list[str], timeout: int = 60) -> dict:
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"lark-cli failed: stderr={res.stderr[:300]}")
    data = json.loads(res.stdout)
    if data.get("code") != 0:
        raise RuntimeError(f"feishu error code={data.get('code')} msg={data.get('msg')}")
    return data.get("data", {})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    cands = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    by_wxid = json.loads(BY_WXID_FILE.read_text(encoding="utf-8"))

    updates = []
    plan_rows = []
    for c in cands:
        if not c["guesses"]:
            continue
        best = c["guesses"][0]
        if best["confidence"] not in APPROVED_CONFIDENCES:
            continue
        wxid = best["wxid"]
        record_id = c["record_id"]
        fields: dict[str, Any] = {"wxid": wxid}
        orders = by_wxid.get(wxid, {})
        for f in GROUP_FIELDS:
            if f in orders:
                fields[f] = int(orders[f])
        updates.append({"record_id": record_id, "fields": fields})
        plan_rows.append({
            "record_id": record_id, "客户名称": c["客户名称"], "姓名": c["姓名"],
            "几期": c["几期学员"], "信号": c["signals"],
            "wxid_to_set": wxid, "confidence": best["confidence"],
            "method": best["method"], "evidence": best["evidence"],
            "group_orders": {k: fields.get(k) for k in GROUP_FIELDS},
        })

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    run_dir = RUN_DIR_BASE / f"{run_id}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(
        json.dumps(plan_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# 给 5 条候选行回填 wxid + 群序号  ({mode})\n",
          f"- 总条数：{len(plan_rows)}\n",
          "| 客户名称 | 姓名 | 几期 | 候选 wxid | 信心 | 方法 | 四期 | 核心 | 4.5期 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in plan_rows:
        go = r["group_orders"]
        md.append(f"| {r['客户名称']} | {r['姓名']} | {r['几期']} | {r['wxid_to_set']} | {r['confidence']} | {r['method']} | {go.get('群序号-四期','')} | {go.get('群序号-核心','')} | {go.get('群序号-4.5期','')} |")
    (run_dir / "plan.md").write_text("\n".join(md), encoding="utf-8")

    print(f"[{mode}] 准备更新 {len(updates)} 行")
    print(f"  → plan: {run_dir / 'plan.md'}")

    if not args.apply:
        print("[dry-run] 不真写。要真写：加 --apply")
        return

    print(f"[apply] 真写中 ...")
    t0 = time.time()
    body = {"records": updates}
    run_lark([
        "api", "POST",
        f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update",
        "--data", json.dumps(body, ensure_ascii=False),
    ], timeout=120)
    elapsed = time.time() - t0
    print(f"[apply done] ok={len(updates)} elapsed={elapsed:.1f}s")
    (run_dir / "result.json").write_text(json.dumps({
        "run_id": run_id, "mode": mode, "updated": len(updates),
        "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
