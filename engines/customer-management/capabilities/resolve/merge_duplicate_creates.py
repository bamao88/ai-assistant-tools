"""
合并 audit_duplicate_creates 识别出来的 61 个嫌疑重复。

策略：
  低重名风险（55 条）→ 自动合并：
    - PATCH 飞书老行 wxid 字段 + 把我们 friends.json 里的 alias / nick 等业务信息也补到老行
      （客户名称/姓名 改成 alias 或 wxid，备注及其他名称 加 nick；只填空字段）
    - DELETE 我们新建的那行

  高重名风险（6 条）→ 导出到 manual_review.md，不动飞书。
    nick ∈ {ss, 十一, 流浪猫, 克柔, Dustinn, Thor}

用法：
  python3 -m workflow.student_employment_tracking.merge_duplicate_creates           # dry-run
  python3 -m workflow.student_employment_tracking.merge_duplicate_creates --apply
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

from workflow.student_employment_tracking.friend_index import load_friend_index, resolve_role

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = PROJECT_ROOT / "analytics" / "friends_index" / "duplicate_audits"
MERGE_DIR = PROJECT_ROOT / "analytics" / "friends_index" / "merges"

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"

BATCH_SIZE = 100

# 用户标注的"高重名风险"昵称，跳过自动合并交人工 review
HIGH_COLLISION_NICKS = {"ss", "十一", "流浪猫", "克柔", "Dustinn", "Thor"}


def run_lark(args: list[str], timeout: int = 60) -> dict:
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"stderr={res.stderr[:300]}")
    data = json.loads(res.stdout)
    if data.get("code") not in (None, 0):
        raise RuntimeError(f"code={data['code']} msg={data.get('msg')}")
    return data.get("data", {})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--role", choices=["assistant", "zh2"], default="assistant",
                   help="friend 元数据源角色（决定 alias/nick 补行取值）")
    p.add_argument("--friends", type=str, default="", help="显式指定 friend 源（覆盖 role）")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    src, _ = resolve_role(args.role, args.friends or None, None)

    # 1. 找最新 audit
    latest = sorted([d for d in AUDIT_DIR.iterdir() if d.is_dir()], reverse=True)[0]
    suspects = json.loads((latest / "suspects.json").read_text())
    friends = {f["wxid"]: f for f in load_friend_index(src)}
    print(f"[input] audit: {latest}, suspects: {len(suspects)}, friend源: {src}", file=sys.stderr)

    auto_plan = []
    manual_plan = []

    for s in suspects:
        wxid = s["wxid"]
        nick = s.get("friend_nick", "") or ""
        # 只接受 candidates 里第 1 个（最强匹配）；多个候选时跳过给人工
        if len(s["candidates"]) > 1:
            manual_plan.append({**s, "_reason": f"{len(s['candidates'])} 个候选行，无法决定"})
            continue
        if nick in HIGH_COLLISION_NICKS:
            manual_plan.append({**s, "_reason": f"高重名 nick: {nick}"})
            continue
        # 自动合并候选
        cand = s["candidates"][0]
        friend_meta = friends.get(wxid) or {}
        alias = (friend_meta.get("alias") or "").strip()
        new_weixin = alias or wxid
        # 老行的 patch
        old_patch: dict[str, Any] = {"wxid": wxid}
        # 老行"微信名称"是 nick（重复源），改成 alias 或 wxid
        if cand["微信名称"] == nick and nick:
            old_patch["微信名称"] = new_weixin
        # 老行"备注及其他名称"如果当前为空 + 有 nick，补 nick
        if not cand["备注及其他名称"] and nick:
            old_patch["备注及其他名称"] = nick
        auto_plan.append({
            "wxid": wxid,
            "alias": alias, "nick": nick,
            "old_record_id": cand["feishu_record_id"],
            "old_before": {k: cand[k] for k in ["微信名称","备注及其他名称","几期学员"]},
            "old_patch": old_patch,
            "new_record_id_to_delete": s["our_record_id"],
        })

    # 2. 写 plan
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    run_dir = MERGE_DIR / f"{run_id}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "auto_plan.json").write_text(json.dumps(auto_plan, ensure_ascii=False, indent=2))
    (run_dir / "manual_review.json").write_text(json.dumps(manual_plan, ensure_ascii=False, indent=2))

    md = [f"# 重复合并  ({mode})\n",
          f"- 自动合并：{len(auto_plan)}",
          f"- 人工 review：{len(manual_plan)}",
          "",
          "## 自动合并前 20 条预览",
          "| wxid | alias | nick | 老行 record | 老行 微信名称→ | 老行 备注→ | 删新行 |",
          "|---|---|---|---|---|---|---|"]
    for p in auto_plan[:20]:
        before = p["old_before"]["微信名称"]
        wei_after = p["old_patch"].get("微信名称", before)
        bei_after = p["old_patch"].get("备注及其他名称", p["old_before"]["备注及其他名称"])
        md.append(f"| {p['wxid']} | {p['alias']} | {p['nick']} | {p['old_record_id']} | {before}→{wei_after} | →{bei_after} | {p['new_record_id_to_delete']} |")

    md.append("\n## 人工 review 清单（高重名词或多候选）\n")
    md.append("| wxid | alias | nick | remark | 候选行数 | 原因 |")
    md.append("|---|---|---|---|---|---|")
    for m in manual_plan:
        md.append(f"| {m['wxid']} | {m['friend_alias']} | {m['friend_nick']} | {m['friend_remark']} | {len(m['candidates'])} | {m['_reason']} |")
    (run_dir / "merge.md").write_text("\n".join(md))

    print(f"\n[{mode}] auto={len(auto_plan)} manual={len(manual_plan)}")
    print(f"  → {run_dir / 'merge.md'}")

    if not args.apply:
        print("[dry-run] 不写。要写：加 --apply")
        return

    # 3. 真写：PATCH 老行 + DELETE 新行
    print(f"[apply] PATCH {len(auto_plan)} old rows + DELETE {len(auto_plan)} new rows ...")
    t0 = time.time()

    # 3a. PATCH 老行
    patch_records = [{"record_id": p["old_record_id"], "fields": p["old_patch"]} for p in auto_plan]
    ok_p = fail_p = 0
    for i in range(0, len(patch_records), BATCH_SIZE):
        batch = patch_records[i:i+BATCH_SIZE]
        try:
            run_lark(["api", "POST",
                f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update",
                "--data", json.dumps({"records": batch}, ensure_ascii=False)], timeout=120)
            ok_p += len(batch)
            print(f"  PATCH batch {i//BATCH_SIZE+1}: ok ({len(batch)})")
        except RuntimeError as e:
            fail_p += len(batch)
            print(f"  PATCH batch {i//BATCH_SIZE+1}: FAIL {e}")
        time.sleep(0.5)

    # 3b. DELETE 新行
    delete_ids = [p["new_record_id_to_delete"] for p in auto_plan]
    ok_d = fail_d = 0
    for i in range(0, len(delete_ids), 500):
        batch = delete_ids[i:i+500]
        try:
            run_lark(["api", "POST",
                f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_delete",
                "--data", json.dumps({"records": batch}, ensure_ascii=False)], timeout=120)
            ok_d += len(batch)
            print(f"  DELETE batch {i//500+1}: ok ({len(batch)})")
        except RuntimeError as e:
            fail_d += len(batch)
            print(f"  DELETE batch {i//500+1}: FAIL {e}")
        time.sleep(0.5)

    elapsed = time.time() - t0
    print(f"[apply done] patch_ok={ok_p} patch_fail={fail_p} delete_ok={ok_d} delete_fail={fail_d} elapsed={elapsed:.1f}s")
    (run_dir / "result.json").write_text(json.dumps({
        "run_id": run_id, "mode": mode,
        "patch_ok": ok_p, "patch_fail": fail_p,
        "delete_ok": ok_d, "delete_fail": fail_d,
        "manual_pending": len(manual_plan),
        "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
