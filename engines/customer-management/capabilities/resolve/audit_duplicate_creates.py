"""
审计：sync_friends 的 209 个 CREATE 行是否跟飞书 wxid 空的现有行重复。

匹配规则（按强度降序）：
  HIGH 1. friend.alias (微信号) == 飞书"微信名称" 字段
  HIGH 2. friend.alias == 飞书"备注及其他名称" 字段
  MID  3. friend.nick_name == 飞书"微信名称" 字段
  MID  4. friend.nick_name == 飞书"备注及其他名称" 字段
  LOW  5. friend.remark 头部 == 飞书"备注及其他名称"头部（clean_name 后）

输出 audit_duplicates.md / .json，不写飞书。

用法：
  python3 -m workflow.student_employment_tracking.audit_duplicate_creates
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# engine 根（capabilities/resolve/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config
from capabilities.resolve.friend_index import load_friend_index, resolve_role

PROJECT_ROOT = config.PROJECT_ROOT
SYNC_RUNS_DIR = config.FRIENDS_SYNC_RUNS_DIR
AUDIT_DIR = config.FRIENDS_AUDIT_DIR

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"


def run_lark(args: list[str], timeout: int = 60) -> dict:
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"stderr={res.stderr[:300]}")
    data = json.loads(res.stdout)
    if data.get("code") not in (None, 0):
        raise RuntimeError(f"code={data['code']} msg={data.get('msg')}")
    return data.get("data", {})


def stringify(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, str): return v
    if isinstance(v, list):
        return "".join((it.get("text") or it.get("name") or "") if isinstance(it, dict) else str(it) for it in v)
    return str(v)


def clean_name(s: str) -> str:
    if not s: return ""
    s = re.sub(r"[^一-鿿぀-ヿA-Za-z0-9_\- ]", " ", s.strip())
    head = re.split(r"[-—()（）/@\s]", s)[0]
    return head.strip()


def main():
    ap = argparse.ArgumentParser(description="审计 sync_friends CREATE 行与空 wxid 老行的重复")
    ap.add_argument("--role", choices=["assistant", "zh2"], default="assistant",
                    help="对哪个账号角色的 sync run 做审计")
    ap.add_argument("--friends", type=str, default="", help="显式指定 friend 源（覆盖 role）")
    args = ap.parse_args()
    src, _ = resolve_role(args.role, args.friends or None, None)

    # 1. 拉 sync_friends CREATE 列表（取最新 该 role 的 apply run plan.json）
    runs = sorted([p for p in SYNC_RUNS_DIR.iterdir()
                   if p.is_dir() and "apply" in p.name and f"_{args.role}_" in p.name], reverse=True)
    # 兼容旧命名（无 role 段的 assistant run）
    if not runs and args.role == "assistant":
        runs = sorted([p for p in SYNC_RUNS_DIR.iterdir() if p.is_dir() and "apply" in p.name], reverse=True)
    plan_path = None
    for r in runs:
        p = r / "plan.json"
        if p.exists():
            d = json.loads(p.read_text())
            if d.get("creates"):
                plan_path = p
                break
    if not plan_path:
        print(f"没找到 role={args.role} 的 sync_friends apply plan.json（含 creates）", file=sys.stderr); sys.exit(1)

    plan = json.loads(plan_path.read_text())
    create_wxids = [c["wxid"] for c in plan["creates"]]
    print(f"[input] role={args.role} CREATE wxid: {len(create_wxids)} (from {plan_path})", file=sys.stderr)

    # 2. friend 源里这些 wxid 的元数据（规约成英文键）
    wxid_to_friend = {f["wxid"]: f for f in load_friend_index(src)}

    # 3. 拉飞书全表
    print("[fetch] 拉飞书全表 ...", file=sys.stderr)
    all_items = []
    pt = ""
    while True:
        params: dict[str, Any] = {"page_size": 500}
        if pt: params["page_token"] = pt
        d = run_lark(["api", "GET",
            f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
            "--params", json.dumps(params)])
        all_items.extend(d.get("items") or [])
        if not d.get("has_more"): break
        pt = d.get("page_token") or ""
        if not pt: break
        time.sleep(0.2)
    print(f"[fetch] 总 {len(all_items)} 行", file=sys.stderr)

    # 4. 把飞书行分类
    # 4a. "wxid 空 + 有任何业务字段" 的现有行 → 待反查目标
    # 4b. 我们新建的 209 行（wxid 在 create_wxids）→ 嫌疑源
    empty_wxid_rows = []
    our_new_rows = {}  # wxid → record_id
    for it in all_items:
        f = it.get("fields") or {}
        w = stringify(f.get("wxid")).strip()
        if w in create_wxids:
            our_new_rows[w] = it.get("record_id")
            continue
        if w:
            continue  # 别的 wxid 非空行，不参与反查
        # wxid 空：判断是否有业务字段
        has_biz = any(stringify(f.get(k)).strip() for k in
            ["微信名称", "备注及其他名称", "手机号", "几期学员", "复训（陪跑和一期学员2次）", "付定金", "实付"])
        if has_biz:
            empty_wxid_rows.append({
                "record_id": it.get("record_id"),
                "微信名称": stringify(f.get("微信名称")).strip(),
                "备注及其他名称": stringify(f.get("备注及其他名称")).strip(),
                "手机号": stringify(f.get("手机号")).strip(),
                "几期学员": stringify(f.get("几期学员")).strip(),
                "复训": stringify(f.get("复训（陪跑和一期学员2次）")).strip(),
                "付定金": f.get("付定金"),
                "实付": stringify(f.get("实付")).strip(),
                "_fields": f,
            })
    print(f"[scan] wxid 空 + 有业务字段的现有行: {len(empty_wxid_rows)}")

    # 5. 反查匹配
    suspects = []
    for wxid in create_wxids:
        friend = wxid_to_friend.get(wxid) or {}
        alias = (friend.get("alias") or "").strip()
        nick = (friend.get("nick_name") or "").strip()
        remark = (friend.get("remark") or "").strip()
        remark_head = clean_name(remark)

        matches = []
        for row in empty_wxid_rows:
            kemingming = row["微信名称"]
            beizhu = row["备注及其他名称"]
            beizhu_head = clean_name(beizhu)
            row_match = []
            if alias and kemingming == alias: row_match.append(("HIGH", f"alias={alias} == 微信名称"))
            if alias and beizhu == alias: row_match.append(("HIGH", f"alias={alias} == 备注及其他名称"))
            if nick and kemingming == nick: row_match.append(("MID", f"nick={nick} == 微信名称"))
            if nick and beizhu == nick: row_match.append(("MID", f"nick={nick} == 备注及其他名称"))
            if remark_head and beizhu_head and remark_head == beizhu_head:
                row_match.append(("LOW", f"remark_head={remark_head} == 备注头部"))
            if row_match:
                matches.append({"feishu_row": row, "rules": row_match})

        if matches:
            best = "HIGH" if any(r[0] == "HIGH" for m in matches for r in m["rules"]) else (
                   "MID" if any(r[0] == "MID" for m in matches for r in m["rules"]) else "LOW")
            suspects.append({
                "wxid": wxid,
                "our_record_id": our_new_rows.get(wxid),
                "friend_alias": alias, "friend_nick": nick, "friend_remark": remark,
                "confidence": best,
                "candidates": [
                    {
                        "feishu_record_id": m["feishu_row"]["record_id"],
                        "微信名称": m["feishu_row"]["微信名称"],
                        "备注及其他名称": m["feishu_row"]["备注及其他名称"],
                        "几期学员": m["feishu_row"]["几期学员"],
                        "rules": m["rules"],
                    }
                    for m in matches
                ],
            })

    suspects.sort(key=lambda x: {"HIGH":0,"MID":1,"LOW":2}[x["confidence"]])

    # 6. 输出
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_dir = AUDIT_DIR / run_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "suspects.json").write_text(json.dumps(suspects, ensure_ascii=False, indent=2))

    md = [f"# {args.role} sync_friends CREATE 重复审计  ({run_id})\n",
          f"- CREATE 总数：{len(create_wxids)}",
          f"- 嫌疑重复：{len(suspects)}",
          f"- 高置信：{sum(1 for s in suspects if s['confidence']=='HIGH')}",
          f"- 中置信：{sum(1 for s in suspects if s['confidence']=='MID')}",
          f"- 低置信：{sum(1 for s in suspects if s['confidence']=='LOW')}",
          ""]
    for tag in ["HIGH", "MID", "LOW"]:
        same = [s for s in suspects if s["confidence"] == tag]
        if not same: continue
        md.append(f"## {tag} 置信（{len(same)} 条）\n")
        md.append("| wxid | alias | nick | remark | 飞书行 微信名称 | 飞书行 备注 | 几期 | 规则 |")
        md.append("|---|---|---|---|---|---|---|---|")
        for s in same:
            for c in s["candidates"]:
                rules = ";".join(f"{r[0]}:{r[1]}" for r in c["rules"])
                md.append(f"| {s['wxid']} | {s['friend_alias']} | {s['friend_nick']} | {s['friend_remark']} | {c['微信名称']} | {c['备注及其他名称']} | {c['几期学员']} | {rules} |")
        md.append("")
    (audit_dir / "audit.md").write_text("\n".join(md))

    print(f"\n嫌疑重复总数: {len(suspects)}")
    print(f"  HIGH={sum(1 for s in suspects if s['confidence']=='HIGH')}")
    print(f"  MID={sum(1 for s in suspects if s['confidence']=='MID')}")
    print(f"  LOW={sum(1 for s in suspects if s['confidence']=='LOW')}")
    print(f"  → {audit_dir / 'audit.md'}")


if __name__ == "__main__":
    main()
