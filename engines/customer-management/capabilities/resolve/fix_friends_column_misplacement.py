"""
修复 sync_friends_to_feishu 时把 nick_name 误填进"微信名称"列的 209 行。

正确填法（与 add_missing_group_members 一致）：
  - 微信名称（fldvEPkuQG）   = alias (微信号)；alias 空时填 wxid
  - 备注及其他名称（fldgiiTd4X）= nick_name (微信昵称)；空时不填

幂等：
  - 只动 sync_friends 那 209 个 wxid（从 plan.json 读）
  - 备注及其他名称：飞书当前为空才填；非空不覆盖（尊重手填）
  - 微信名称：当前值 == nick_name → 纠正为 (alias or wxid)；否则不动

用法：
  python3 -m capabilities.resolve.fix_friends_column_misplacement          # dry-run
  python3 -m capabilities.resolve.fix_friends_column_misplacement --apply
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
FRIENDS_FILE = config.FRIENDS_INDEX_FILE
SYNC_RUNS_DIR = config.FRIENDS_SYNC_RUNS_DIR
FIX_DIR = config.FRIENDS_COLUMN_FIX_DIR

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"

FIELD_WXID = "wxid"
FIELD_WEIXIN_NAME = "微信名称"            # 旧名"客户名称（微信号）"，fldvEPkuQG
FIELD_BEIZHU = "备注及其他名称"           # 旧名"姓名"，fldgiiTd4X

BATCH_SIZE = 100


def run_lark(args: list[str], timeout: int = 60) -> dict:
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"lark-cli failed: stderr={res.stderr[:300]}")
    data = json.loads(res.stdout)
    if data.get("code") not in (None, 0):
        raise RuntimeError(f"feishu error code={data['code']} msg={data.get('msg')}")
    return data.get("data", {})


def stringify(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, str): return v
    if isinstance(v, list):
        return "".join((it.get("text") or it.get("name") or "") if isinstance(it, dict) else str(it) for it in v)
    return str(v)


def find_latest_sync_friends_plan() -> Path:
    runs = sorted([p for p in SYNC_RUNS_DIR.iterdir() if p.is_dir()], reverse=True)
    for r in runs:
        plan = r / "plan.json"
        if not plan.exists():
            continue
        d = json.loads(plan.read_text())
        if d.get("creates"):
            return plan
    raise RuntimeError("没找到 sync_friends 的 plan.json")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    # 1. 拿 sync_friends 209 个 CREATE wxid
    plan_path = find_latest_sync_friends_plan()
    plan = json.loads(plan_path.read_text())
    create_wxids = [c["wxid"] for c in plan["creates"]]
    print(f"[input] sync_friends 209 个 CREATE wxid（来自 {plan_path}）: {len(create_wxids)}", file=sys.stderr)

    # 2. 拿 friends.json 里这些 wxid 的 alias / nick_name
    friends_data = json.loads(FRIENDS_FILE.read_text())
    wxid_to_meta = {f["wxid"]: f for f in friends_data["friends"]}

    # 3. 拉飞书全表
    print("[fetch] 拉飞书全表 ...", file=sys.stderr)
    all_items = []
    page_token = ""
    while True:
        params = {"page_size": 500}
        if page_token: params["page_token"] = page_token
        d = run_lark(["api", "GET",
            f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            "--params", json.dumps(params)])
        all_items.extend(d.get("items") or [])
        if not d.get("has_more"): break
        page_token = d.get("page_token") or ""
        if not page_token: break
        time.sleep(0.2)

    wxid_to_record = {}
    for it in all_items:
        f = it.get("fields") or {}
        w = stringify(f.get(FIELD_WXID)).strip()
        if w and w in create_wxids:
            wxid_to_record.setdefault(w, it)
    print(f"[fetch] sync_friends 209 wxid 在飞书命中 {len(wxid_to_record)} 行", file=sys.stderr)

    # 4. 算 fix updates
    updates = []
    plan_rows = []
    for wxid in create_wxids:
        rec = wxid_to_record.get(wxid)
        if not rec:
            continue
        fields = rec.get("fields") or {}
        cur_weixin = stringify(fields.get(FIELD_WEIXIN_NAME)).strip()
        cur_beizhu = stringify(fields.get(FIELD_BEIZHU)).strip()
        meta = wxid_to_meta.get(wxid) or {}
        alias = (meta.get("alias") or "").strip()
        nick = (meta.get("nick_name") or "").strip()
        correct_weixin = alias or wxid  # 微信名称应是 alias 或 wxid，不是 nick

        patch: dict[str, Any] = {}
        # 微信名称：当前值是 nick（错位）→ 纠正
        if cur_weixin == nick and nick and cur_weixin != correct_weixin:
            patch[FIELD_WEIXIN_NAME] = correct_weixin
        # 备注及其他名称：当前空 + 我们有 nick → 补上
        if not cur_beizhu and nick:
            patch[FIELD_BEIZHU] = nick

        if not patch:
            continue
        updates.append({"record_id": rec.get("record_id"), "fields": patch})
        plan_rows.append({
            "wxid": wxid,
            "before_weixin": cur_weixin, "before_beizhu": cur_beizhu,
            "after_weixin": patch.get(FIELD_WEIXIN_NAME, cur_weixin),
            "after_beizhu": patch.get(FIELD_BEIZHU, cur_beizhu),
            "patch_fields": list(patch.keys()),
        })

    # 5. 写 plan
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    run_dir = FIX_DIR / f"{run_id}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(json.dumps(plan_rows, ensure_ascii=False, indent=2))

    md = [f"# 列错位修复 plan ({mode})\n",
          f"- 待修复 209 行 sync_friends CREATE 中触发的：{len(updates)}",
          "",
          "## 前 20 条示例",
          "| wxid | before 微信名称 | before 备注 | after 微信名称 | after 备注 | patch |",
          "|---|---|---|---|---|---|"]
    for r in plan_rows[:20]:
        md.append(f"| {r['wxid']} | {r['before_weixin']} | {r['before_beizhu']} | {r['after_weixin']} | {r['after_beizhu']} | {','.join(r['patch_fields'])} |")
    (run_dir / "plan.md").write_text("\n".join(md))

    print(f"\n[{mode}] 待修复 {len(updates)} 行")
    print(f"  → plan: {run_dir / 'plan.md'}")

    if not args.apply:
        print("[dry-run] 不真写。要真写：加 --apply")
        return

    print(f"[apply] 真写中 ...")
    t0 = time.time()
    ok = fail = 0
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i+BATCH_SIZE]
        try:
            run_lark(["api", "POST",
                f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update",
                "--data", json.dumps({"records": batch}, ensure_ascii=False)], timeout=120)
            ok += len(batch)
            print(f"  batch {i//BATCH_SIZE+1}: ok ({len(batch)})")
        except RuntimeError as e:
            fail += len(batch)
            print(f"  batch {i//BATCH_SIZE+1}: FAIL {e}")
        time.sleep(0.5)
    elapsed = time.time() - t0
    print(f"[apply done] ok={ok} fail={fail} elapsed={elapsed:.1f}s")
    (run_dir / "result.json").write_text(json.dumps({
        "run_id": run_id, "mode": mode, "ok": ok, "fail": fail,
        "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
