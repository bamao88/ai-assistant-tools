"""
把某个账号的好友名单同步到飞书"客户管理"表（按 wxid 对齐）。

多账号：用 --role 选数据源 + "添加微信"标签（见 friend_index.ROLE_PRESETS）：
  --role assistant  助理号好友（analytics/friends_index/friends.json）→ 添加微信 小助理
  --role zh2        张和2号好友（raw/chat/friends_zh2.json）→ 添加微信 张和2号
也可 --friends <path> / --add-by <选项名> 显式覆盖。默认 role=assistant（向后兼容）。

字段映射（只填空，不覆盖手填）：
  wxid           → friend.wxid（匹配键）
  微信名称        → nick_name (昵称)；空 → alias → wxid（飞书第一眼看人名，不看微信号）
  备注及其他名称   → " | ".join(nick_name, remark) 非空部分；都空时不填
  加好友日期      → first_chat_date 转 Unix ms（无则不填；friend_index 会从私聊最早消息推断）
  添加微信        → 多选 append --add-by 选项（已含则跳过；保留已有选项）

行匹配：按 wxid
  - 已在飞书：仅 update 当前为空的字段 + append 添加微信
  - 不在飞书：新建行（按 wxid 建；与"空 wxid 老行"的潜在重复由 audit/merge 后置处理）

staff_exclude.json 里的 wxid 一律跳过（自己人不进客户管理表）。

用法：
  python3 -m outputs.sync_friends_to_feishu                    # 助理号 dry-run
  python3 -m outputs.sync_friends_to_feishu --role zh2         # 张和2号 dry-run
  python3 -m outputs.sync_friends_to_feishu --role zh2 --apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# engine 根（outputs/ → up 1）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from capabilities.resolve.friend_index import load_friend_index, resolve_role

PROJECT_ROOT = config.PROJECT_ROOT
STAFF_EXCLUDE_FILE = config.STAFF_EXCLUDE_FILE
RUN_DIR_BASE = config.FRIENDS_SYNC_RUNS_DIR

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"

FIELD_WXID = "wxid"
FIELD_WEIXIN_NAME = "微信名称"        # fldvEPkuQG = nick_name；空 → alias → wxid
FIELD_BEIZHU = "备注及其他名称"        # fldgiiTd4X = nick_name
FIELD_JIA_DATE = "加好友日期"
FIELD_ADD_BY = "添加微信"             # 多选

BATCH_SIZE = 100
TZ_CN = timezone(timedelta(hours=8))


def run_lark(args: list[str], timeout: int = 60) -> dict:
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"lark-cli failed: stderr={res.stderr[:300]}")
    data = json.loads(res.stdout)
    if data.get("code") not in (None, 0):
        raise RuntimeError(f"feishu error code={data['code']} msg={data.get('msg')}")
    return data.get("data", {})


def date_to_unix_ms(date_str: str) -> int | None:
    """YYYY-MM-DD → 当天 00:00:00 +08:00 的 unix 毫秒。"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=TZ_CN)
        return int(d.timestamp() * 1000)
    except Exception:
        return None


def fetch_all_feishu_records() -> list[dict]:
    print("[fetch] 拉飞书全表 ...", file=sys.stderr)
    out: list[dict] = []
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
        out.extend(data.get("items") or [])
        if not data.get("has_more"):
            break
        page_token = data.get("page_token") or ""
        if not page_token:
            break
        time.sleep(0.2)
    print(f"[fetch] 共 {len(out)} 行", file=sys.stderr)
    return out


def stringify(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, str): return v
    if isinstance(v, list):
        return "".join((it.get("text") or it.get("name") or "") if isinstance(it, dict) else str(it) for it in v)
    return str(v)


def index_by_wxid(records: list[dict]) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for r in records:
        wxid = stringify((r.get("fields") or {}).get(FIELD_WXID)).strip()
        if not wxid or wxid in idx:
            continue
        idx[wxid] = r
    return idx


def multiselect_names(value: Any) -> list[str]:
    """飞书多选字段当前值 → 选项名列表。"""
    if isinstance(value, list):
        names: list[str] = []
        for it in value:
            n = it.get("name") if isinstance(it, dict) else it
            if n:
                names.append(str(n))
        return names
    if isinstance(value, str) and value:
        return [value]
    return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--role", choices=["assistant", "zh2"], default="assistant",
                   help="数据源账号角色（决定默认 friend 源 + 添加微信标签）")
    p.add_argument("--friends", type=str, default="", help="显式指定 friend 源 json 路径（覆盖 role）")
    p.add_argument("--add-by", type=str, default="", help="显式指定 添加微信 选项名（覆盖 role）")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="只处理前 N 个（测试用）")
    args = p.parse_args()

    src, add_by = resolve_role(args.role, args.friends or None, args.add_by or None)
    print(f"[input] role={args.role} 源={src} 添加微信={add_by}", file=sys.stderr)
    if not src.exists():
        print(f"[ERROR] friend 源不存在：{src}\n  （zh2 需先跑 sync_groups.js 生成 friends_zh2.json）", file=sys.stderr)
        sys.exit(1)

    all_friends = load_friend_index(src)
    staff_wxids = {s["wxid"] for s in json.loads(STAFF_EXCLUDE_FILE.read_text(encoding="utf-8")).get("staff", [])}
    friends = [f for f in all_friends if f["wxid"] not in staff_wxids]
    print(f"[input] {len(all_friends)} 好友 - {len(all_friends) - len(friends)} staff = {len(friends)} 待处理")
    if args.limit:
        friends = friends[:args.limit]

    feishu_records = fetch_all_feishu_records()
    feishu_idx = index_by_wxid(feishu_records)

    updates: list[dict] = []
    creates: list[dict] = []
    skip_no_change = 0

    for f in friends:
        wxid = f["wxid"]
        alias = f["alias"]
        nick = f["nick_name"]
        remark = f.get("remark") or ""
        weixin_name = nick or alias or wxid   # 微信名称 = 昵称；空 → alias → wxid
        # 备注及其他名称 = 昵称 | 备注 (拼非空部分)；用户能看到这个人 = 谁
        beizhu_combined = " | ".join(x for x in [nick, remark] if x)
        first_date_ms = date_to_unix_ms(f["first_chat_date"]) if f.get("first_chat_date") else None

        existing = feishu_idx.get(wxid)
        if existing:
            ex_fields = existing.get("fields") or {}
            patch: dict[str, Any] = {}
            # 微信名称：只填空
            if not stringify(ex_fields.get(FIELD_WEIXIN_NAME)).strip():
                patch[FIELD_WEIXIN_NAME] = weixin_name
            # 备注及其他名称：只填空（不覆盖手填）+ 我们能给出内容
            if beizhu_combined and not stringify(ex_fields.get(FIELD_BEIZHU)).strip():
                patch[FIELD_BEIZHU] = beizhu_combined
            # 加好友日期：只填空 + 我们有日期
            if first_date_ms and not ex_fields.get(FIELD_JIA_DATE):
                patch[FIELD_JIA_DATE] = first_date_ms
            # 添加微信：append（已含 add_by 则不动；保留其它已有选项）
            cur_names = multiselect_names(ex_fields.get(FIELD_ADD_BY))
            if add_by not in cur_names:
                patch[FIELD_ADD_BY] = cur_names + [add_by]
            if not patch:
                skip_no_change += 1
                continue
            updates.append({
                "record_id": existing.get("record_id"),
                "fields": patch,
                "_diag": {"wxid": wxid, "微信名称": weixin_name, "备注": beizhu_combined,
                          "first_date": f.get("first_chat_date"), "patch_keys": list(patch.keys())},
            })
        else:
            fields: dict[str, Any] = {
                FIELD_WXID: wxid,
                FIELD_WEIXIN_NAME: weixin_name,
                FIELD_ADD_BY: [add_by],
            }
            if beizhu_combined:
                fields[FIELD_BEIZHU] = beizhu_combined
            if first_date_ms:
                fields[FIELD_JIA_DATE] = first_date_ms
            creates.append({
                "fields": fields,
                "_diag": {"wxid": wxid, "微信名称": weixin_name, "备注": beizhu_combined,
                          "first_date": f.get("first_chat_date")},
            })

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    run_dir = RUN_DIR_BASE / f"{run_id}_{args.role}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # 写 plan
    (run_dir / "plan.json").write_text(json.dumps({
        "role": args.role,
        "add_by": add_by,
        "source": str(src),
        "updates": [u["_diag"] | {"fields_in_patch": list(u["fields"].keys())} for u in updates],
        "creates": [c["_diag"] for c in creates],
        "skip_no_change": skip_no_change,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# {args.role} 好友同步 plan ({mode}) — 添加微信={add_by}\n",
          f"- 源：{src}",
          f"- 输入好友：{len(friends)}",
          f"- 飞书已存在 wxid：{sum(1 for f in friends if f['wxid'] in feishu_idx)}",
          f"- 计划 UPDATE：{len(updates)}",
          f"- 计划 CREATE：{len(creates)}",
          f"- 已存在且无变化：{skip_no_change}",
          "",
          "## 前 20 条 UPDATE 示例",
          "| wxid | 微信名称 | 备注及其他名称 | 首聊日期 | patch 字段 |",
          "|---|---|---|---|---|"]
    for u in updates[:20]:
        d = u["_diag"]
        md.append(f"| {d['wxid']} | {d['微信名称']} | {d['备注']} | {d['first_date'] or '-'} | {','.join(d['patch_keys'])} |")
    md.append("\n## 前 20 条 CREATE 示例\n| wxid | 微信名称 | 备注及其他名称 | 首聊日期 |\n|---|---|---|---|")
    for c in creates[:20]:
        d = c["_diag"]
        md.append(f"| {d['wxid']} | {d['微信名称']} | {d['备注']} | {d['first_date'] or '-'} |")
    (run_dir / "plan.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\n[{mode}] role={args.role} update={len(updates)} create={len(creates)} skip_no_change={skip_no_change}")
    print(f"  → plan: {run_dir / 'plan.md'}")
    if creates:
        print(f"  ⚠️ {len(creates)} 个新建行；建议用 recipes.friends_sync（sync+audit+merge 三步合一）"
              f"而非单跑本脚本，避免漏查与空 wxid 老行的重复。"
              f"（单查/单合并：python3 -m recipes.health_check duplicate_creates --role {args.role}）")

    if not args.apply:
        print("[dry-run] 不真写。要真写：加 --apply")
        return

    # 真写：先 update，再 create
    log_path = run_dir / "sync.log"
    log_fh = log_path.open("w", encoding="utf-8")
    def log(msg): log_fh.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n"); log_fh.flush()

    t0 = time.time()
    ok_u, fail_u = 0, 0
    if updates:
        print(f"[apply] PATCH {len(updates)} ...")
        body_records = [{"record_id": u["record_id"], "fields": u["fields"]} for u in updates]
        for i in range(0, len(body_records), BATCH_SIZE):
            batch = body_records[i:i+BATCH_SIZE]
            try:
                run_lark(["api", "POST",
                    f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update",
                    "--data", json.dumps({"records": batch}, ensure_ascii=False)], timeout=120)
                ok_u += len(batch)
                log(f"PATCH batch {i//BATCH_SIZE+1} ok ({len(batch)})")
            except RuntimeError as e:
                fail_u += len(batch)
                log(f"PATCH batch {i//BATCH_SIZE+1} FAIL: {e}")
            time.sleep(0.5)

    ok_c, fail_c = 0, 0
    if creates:
        print(f"[apply] CREATE {len(creates)} ...")
        body_records = [{"fields": c["fields"]} for c in creates]
        for i in range(0, len(body_records), BATCH_SIZE):
            batch = body_records[i:i+BATCH_SIZE]
            try:
                run_lark(["api", "POST",
                    f"/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_create",
                    "--data", json.dumps({"records": batch}, ensure_ascii=False)], timeout=120)
                ok_c += len(batch)
                log(f"CREATE batch {i//BATCH_SIZE+1} ok ({len(batch)})")
            except RuntimeError as e:
                fail_c += len(batch)
                log(f"CREATE batch {i//BATCH_SIZE+1} FAIL: {e}")
            time.sleep(0.5)

    elapsed = time.time() - t0
    print(f"[apply done] update_ok={ok_u} update_fail={fail_u} create_ok={ok_c} create_fail={fail_c} elapsed={elapsed:.1f}s")
    (run_dir / "result.json").write_text(json.dumps({
        "run_id": run_id, "role": args.role, "mode": mode,
        "update_ok": ok_u, "update_fail": fail_u,
        "create_ok": ok_c, "create_fail": fail_c,
        "elapsed_seconds": round(elapsed, 1),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
