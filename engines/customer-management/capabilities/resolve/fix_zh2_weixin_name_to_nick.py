"""
一次性修复：把某次 sync_friends CREATE 行的"微信名称"列改为昵称。

背景：sync_friends_to_feishu 旧策略写"微信名称"=alias/wxid，用户希望看 nick。

按 --role 选择 plan 范围 + 角色标签：
  --role zh2        范围: sync_runs/20260526_175515_zh2_apply/plan.json  标签: 张和2号
  --role assistant  范围: sync_runs/20260519_160713_apply/plan.json      标签: 小助理

修改两列：
  - 微信名称：alias/wxid → nick_name（nick 为空时跳过，不清空）
  - 添加微信：不含 role 标签时 append（保留其他选项）

幂等：两列都不需要改 → skip_no_change。

用法：
  python3 -m workflow.student_employment_tracking.fix_zh2_weixin_name_to_nick --role zh2
  python3 -m workflow.student_employment_tracking.fix_zh2_weixin_name_to_nick --role zh2 --apply
  python3 -m workflow.student_employment_tracking.fix_zh2_weixin_name_to_nick --role assistant --apply
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

from workflow.student_employment_tracking.friend_index import load_friend_index, ROLE_PRESETS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIX_DIR = PROJECT_ROOT / "analytics" / "friends_index" / "column_fixes"

ROLE_PLAN_FILES = {
    "zh2": PROJECT_ROOT / "analytics" / "friends_index" / "sync_runs" / "20260526_175515_zh2_apply" / "plan.json",
    "assistant": PROJECT_ROOT / "analytics" / "friends_index" / "sync_runs" / "20260519_160713_apply" / "plan.json",
}

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"

FIELD_WXID = "wxid"
FIELD_WEIXIN_NAME = "微信名称"        # fldvEPkuQG
FIELD_ADD_BY = "添加微信"             # fldjsVs1H5 多选

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


def multiselect_names(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(it.get("name") if isinstance(it, dict) else it) for it in value if (it.get("name") if isinstance(it, dict) else it)]
    if isinstance(value, str) and value:
        return [value]
    return []


def fetch_all_feishu_records() -> list[dict]:
    print("[fetch] 拉飞书全表 ...", file=sys.stderr)
    out: list[dict] = []
    page_token = ""
    while True:
        params: dict[str, Any] = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        d = run_lark([
            "api", "GET",
            f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            "--params", json.dumps(params, ensure_ascii=False),
        ])
        out.extend(d.get("items") or [])
        if not d.get("has_more"):
            break
        page_token = d.get("page_token") or ""
        if not page_token:
            break
        time.sleep(0.2)
    print(f"[fetch] 共 {len(out)} 行", file=sys.stderr)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--role", choices=["assistant", "zh2"], required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    plan_file = ROLE_PLAN_FILES[args.role]
    friends_src, role_tag = ROLE_PRESETS[args.role]

    # 1. role plan 里的 CREATE wxid
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    create_wxids = {c["wxid"] for c in plan["creates"]}
    print(f"[input] role={args.role} plan={plan_file.name} CREATE 范围: {len(create_wxids)} wxid", file=sys.stderr)

    # 2. friend 源里这些 wxid 的 nick_name
    friends = load_friend_index(friends_src)
    wxid_to_nick: dict[str, str] = {}
    for f in friends:
        w = f.get("wxid") or ""
        if w and w in create_wxids:
            wxid_to_nick[w] = (f.get("nick_name") or "").strip()
    print(f"[input] friend 源命中 {len(wxid_to_nick)} / {len(create_wxids)}", file=sys.stderr)

    # 3. 拉飞书全表
    records = fetch_all_feishu_records()

    updates: list[dict] = []
    plan_rows: list[dict] = []
    skip_no_nick = 0
    skip_no_change = 0
    skip_no_match_in_feishu = 0
    count_only_name = 0
    count_only_tag = 0
    count_name_and_tag = 0

    matched_feishu_wxids: set[str] = set()
    for rec in records:
        fields = rec.get("fields") or {}
        wxid = stringify(fields.get(FIELD_WXID)).strip()
        if not wxid or wxid not in create_wxids:
            continue
        matched_feishu_wxids.add(wxid)
        nick = wxid_to_nick.get(wxid, "")
        if not nick:
            skip_no_nick += 1
            continue

        patch: dict[str, Any] = {}
        cur_weixin = stringify(fields.get(FIELD_WEIXIN_NAME)).strip()
        if cur_weixin != nick:
            patch[FIELD_WEIXIN_NAME] = nick

        cur_tags = multiselect_names(fields.get(FIELD_ADD_BY))
        new_tags = cur_tags + [role_tag] if role_tag not in cur_tags else cur_tags
        if role_tag not in cur_tags:
            patch[FIELD_ADD_BY] = new_tags

        if not patch:
            skip_no_change += 1
            continue

        if FIELD_WEIXIN_NAME in patch and FIELD_ADD_BY in patch:
            count_name_and_tag += 1
        elif FIELD_WEIXIN_NAME in patch:
            count_only_name += 1
        else:
            count_only_tag += 1

        updates.append({"record_id": rec.get("record_id"), "fields": patch})
        plan_rows.append({
            "wxid": wxid,
            "before_weixin": cur_weixin,
            "after_weixin": nick,
            "before_tags": cur_tags,
            "after_tags": new_tags,
            "patch_keys": list(patch.keys()),
        })

    skip_no_match_in_feishu = len(create_wxids) - len(matched_feishu_wxids)

    # 4. 写归档
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    run_dir = FIX_DIR / f"{run_id}_{args.role}_weixin_to_nick_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(
        json.dumps({
            "scope": f"{args.role} sync 的 {len(create_wxids)} 个 CREATE (plan={plan_file.name})",
            "fields_changed": [FIELD_WEIXIN_NAME, FIELD_ADD_BY],
            "policy": f"微信名称 alias/wxid → nick_name; 添加微信 append {role_tag} (若缺)",
            "stats": {
                "plan_total": len(create_wxids),
                "matched_in_feishu": len(matched_feishu_wxids),
                "no_match_in_feishu": skip_no_match_in_feishu,
                "skip_no_nick": skip_no_nick,
                "skip_no_change": skip_no_change,
                "patch_name_only": count_only_name,
                "patch_tag_only": count_only_tag,
                "patch_name_and_tag": count_name_and_tag,
                "will_update": len(updates),
            },
            "updates": plan_rows,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = [
        f"# {role_tag} 微信名称→昵称 修复 plan ({mode})",
        "",
        f"- 范围（plan.json creates）: {len(create_wxids)} wxid",
        f"- 飞书命中: {len(matched_feishu_wxids)}",
        f"- 飞书未找到: {skip_no_match_in_feishu}",
        f"- 跳过-nick 为空: {skip_no_nick}",
        f"- 跳过-无需变更: {skip_no_change}",
        f"- patch 微信名称 only: {count_only_name}",
        f"- patch 添加微信 only: {count_only_tag}",
        f"- patch 两者: {count_name_and_tag}",
        f"- **待 UPDATE: {len(updates)}**",
        "",
        "## 前 30 条 UPDATE 示例",
        "| wxid | before 微信名称 | after 微信名称 | before tags | after tags | patch |",
        "|---|---|---|---|---|---|",
    ]
    for r in plan_rows[:30]:
        md.append(f"| {r['wxid']} | {r['before_weixin']} | {r['after_weixin']} | {','.join(r['before_tags']) or '∅'} | {','.join(r['after_tags'])} | {','.join(r['patch_keys'])} |")
    (run_dir / "plan.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\n[{mode}] 待修复 {len(updates)} 行 (name_only={count_only_name} tag_only={count_only_tag} both={count_name_and_tag})")
    print(f"  跳过: no_nick={skip_no_nick} no_change={skip_no_change} no_match_in_feishu={skip_no_match_in_feishu}")
    print(f"  → plan: {run_dir / 'plan.md'}")

    if not args.apply:
        print("[dry-run] 不真写。要真写: 加 --apply")
        return

    print(f"[apply] 真写中 ...")
    t0 = time.time()
    ok = fail = 0
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i + BATCH_SIZE]
        try:
            run_lark([
                "api", "POST",
                f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update",
                "--data", json.dumps({"records": batch}, ensure_ascii=False),
            ], timeout=120)
            ok += len(batch)
            print(f"  batch {i // BATCH_SIZE + 1}: ok ({len(batch)})")
        except RuntimeError as e:
            fail += len(batch)
            print(f"  batch {i // BATCH_SIZE + 1}: FAIL {e}")
        time.sleep(0.5)
    elapsed = time.time() - t0
    print(f"[apply done] ok={ok} fail={fail} elapsed={elapsed:.1f}s")
    (run_dir / "result.json").write_text(json.dumps({
        "run_id": run_id, "mode": mode, "ok": ok, "fail": fail,
        "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
