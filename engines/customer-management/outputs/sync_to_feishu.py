"""
学员就业情况追踪 — 飞书 sync 脚本

把 student_manage/state/student_employment_tracking_latest.json 同步到飞书
"客户管理"表 (app_token=YTcFbyGS4arILPseQJscA6J7nqb, table=tblfCYoeornDw0XF)。

匹配键: wxid

合并策略:
- 拿到offer (Checkbox) → 直接覆盖
- 客户画像 (Text) → 如果飞书现内容含 "AI回访分析" 标记 → 跳过该字段（已 sync 过，幂等）；
                    否则把 latest.customer_profile_full 整段 append 到现内容末尾（保留手填）
- 备注 (Text) → 同上

跑两次是幂等的。默认 dry-run，--apply 真写。

用法（迁移后从 engine 根跑）:
    python3 -m outputs.sync_to_feishu              # 默认 dry-run
    python3 -m outputs.sync_to_feishu --apply      # 真写
    python3 -m outputs.sync_to_feishu --wxid <id>  # 单人
    python3 -m outputs.sync_to_feishu --limit 5    # 控制范围
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

# engine 根（outputs/ → up 1）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

PROJECT_ROOT = config.PROJECT_ROOT
LATEST_FILE = config.EMPLOYMENT_LATEST_FILE
ANALYTICS_DIR = config.EMPLOYMENT_ANALYTICS_DIR
SYNC_RUNS_DIR = config.EMPLOYMENT_SYNC_RUNS_DIR

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"

# 飞书字段名（中文，跟 PATCH 接口对接）
FIELD_HUAXIANG = "客户画像"
FIELD_BEIZHU = "备注"
FIELD_OFFER = "拿到offer"
FIELD_WXID = "wxid"

# 判断字段是否已 sync 过的标记串（latest stub/LLM 模板里都会有）
AI_STAMP = "AI回访分析"

# 飞书 batch update 限制
BATCH_SIZE = 100


def run_lark(args: list[str], timeout: int = 60) -> dict:
    """跑 lark-cli，返回解析后的 JSON data 字段。"""
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"lark-cli failed: {' '.join(args[:6])}... stderr={res.stderr[:300]}")
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"lark-cli non-JSON: {e} stdout_head={res.stdout[:200]}")
    if data.get("code") != 0:
        raise RuntimeError(f"feishu error code={data.get('code')} msg={data.get('msg')}")
    return data.get("data", {})


def fetch_all_feishu_records() -> list[dict]:
    """拉飞书全表，返回 [{record_id, fields:{...}}]"""
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
        items = data.get("items") or []
        all_items.extend(items)
        if not data.get("has_more"):
            break
        page_token = data.get("page_token") or ""
        if not page_token:
            break
        time.sleep(0.2)
    print(f"[sync] 共拉到 {len(all_items)} 行", file=sys.stderr)
    return all_items


def index_by_wxid(records: list[dict]) -> dict[str, dict]:
    """飞书行按 wxid 字段索引。空 wxid 行跳过。"""
    idx: dict[str, dict] = {}
    for r in records:
        wxid = (r.get("fields", {}).get(FIELD_WXID) or "").strip() if isinstance(r.get("fields", {}).get(FIELD_WXID), str) else ""
        if not wxid:
            continue
        if wxid in idx:
            # 重复 wxid → 用第一行（飞书表里如果有重复是数据质量问题，不处理）
            continue
        idx[wxid] = r
    return idx


def build_update_payload(latest_entry: dict, feishu_fields: dict) -> tuple[dict, list[str]]:
    """计算给一行飞书的 update payload + 触发原因列表。

    返回 (fields_to_update, reasons). fields_to_update 空 → 这行不需要 update。
    """
    payload: dict[str, Any] = {}
    reasons: list[str] = []

    # got_offer → 拿到offer Checkbox
    latest_offer = bool(latest_entry.get("got_offer"))
    current_offer = feishu_fields.get(FIELD_OFFER)
    if bool(current_offer) != latest_offer:
        payload[FIELD_OFFER] = latest_offer
        reasons.append(f"offer:{current_offer!r}→{latest_offer}")

    # 客户画像 → append（飞书已有 AI 标记则跳过，保持幂等；保留手填）
    profile_text = latest_entry.get("customer_profile_full") or ""
    if profile_text.strip():
        current_huaxiang = feishu_fields.get(FIELD_HUAXIANG)
        # 飞书 text 字段可能是 list[{type,text}] 富文本，转成纯文本
        current_str = stringify_text(current_huaxiang)
        if AI_STAMP in current_str:
            pass  # 已 sync 过，跳过
        else:
            new_value = (current_str + ("\n\n" if current_str.strip() else "") + profile_text).strip()
            payload[FIELD_HUAXIANG] = new_value
            reasons.append(f"画像:append(+{len(profile_text)}字)")

    # 备注 → append（同上）
    remark_text = latest_entry.get("remark_full") or ""
    if remark_text.strip():
        current_beizhu = feishu_fields.get(FIELD_BEIZHU)
        current_str = stringify_text(current_beizhu)
        if AI_STAMP in current_str:
            pass
        else:
            new_value = (current_str + ("\n\n" if current_str.strip() else "") + remark_text).strip()
            payload[FIELD_BEIZHU] = new_value
            reasons.append(f"备注:append(+{len(remark_text)}字)")

    return payload, reasons


def stringify_text(value: Any) -> str:
    """飞书 Text 字段可能是 str、或 list[{type,text}] 富文本片段，统一返回纯文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for it in value:
            if isinstance(it, dict):
                parts.append(it.get("text") or "")
            else:
                parts.append(str(it))
        return "".join(parts)
    return str(value)


def batch_update_records(updates: list[dict], apply: bool, logger) -> tuple[int, int]:
    """updates: [{record_id, fields:{...}}]. apply=False 时只打印。
    返回 (success_count, fail_count)."""
    if not updates:
        return 0, 0
    if not apply:
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
    p = argparse.ArgumentParser(description="把 latest.json 同步到飞书客户管理表")
    p.add_argument("--apply", action="store_true", help="真写（默认 dry-run）")
    p.add_argument("--wxid", type=str, default="", help="只同步单个 wxid")
    p.add_argument("--limit", type=int, default=0, help="本轮最多处理 N 个 wxid")
    args = p.parse_args()

    latest = json.loads(LATEST_FILE.read_text(encoding="utf-8"))
    print(f"[sync] latest.json 共 {len(latest)} 学员", file=sys.stderr)

    feishu_records = fetch_all_feishu_records()
    feishu_idx = index_by_wxid(feishu_records)
    print(f"[sync] 飞书表 wxid-indexed {len(feishu_idx)} 行（共 {len(feishu_records)} 行）", file=sys.stderr)

    # 过滤目标
    target_wxids = list(latest.keys())
    if args.wxid:
        if args.wxid not in latest:
            print(f"[ERROR] {args.wxid} 不在 latest.json", file=sys.stderr)
            sys.exit(1)
        target_wxids = [args.wxid]
    if args.limit:
        target_wxids = target_wxids[:args.limit]

    # 准备 run dir
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if args.apply else "dryrun"
    run_dir = SYNC_RUNS_DIR / f"{run_id}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "sync.log"
    log_fh = log_path.open("w", encoding="utf-8")

    def logger(msg: str):
        log_fh.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
        log_fh.flush()

    # 算 diff
    updates: list[dict] = []  # 给 batch_update_records
    plan_rows: list[dict] = []  # 给 plan.json / plan.md
    no_match: list[str] = []

    for wxid in target_wxids:
        latest_entry = latest[wxid]
        feishu_row = feishu_idx.get(wxid)
        if not feishu_row:
            no_match.append(wxid)
            logger(f"NO_MATCH wxid={wxid} display={latest_entry.get('display_name','')}")
            continue
        record_id = feishu_row.get("record_id") or feishu_row.get("id")
        feishu_fields = feishu_row.get("fields", {})
        payload, reasons = build_update_payload(latest_entry, feishu_fields)
        if not payload:
            logger(f"SKIP_NO_CHANGE wxid={wxid} display={latest_entry.get('display_name','')}")
            continue
        plan_rows.append({
            "wxid": wxid,
            "display_name": latest_entry.get("display_name", ""),
            "record_id": record_id,
            "transition_outcome": latest_entry.get("transition_outcome"),
            "got_offer": latest_entry.get("got_offer"),
            "reasons": reasons,
            "fields": list(payload.keys()),
        })
        updates.append({"record_id": record_id, "fields": payload})
        logger(f"PLAN_UPDATE wxid={wxid} display={latest_entry.get('display_name','')} reasons={reasons}")

    # 写 plan
    (run_dir / "plan.json").write_text(
        json.dumps(plan_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "no_match.json").write_text(
        json.dumps(no_match, ensure_ascii=False, indent=2), encoding="utf-8")

    # plan.md（人读）
    plan_md = [
        f"# 飞书 sync {mode} — {run_id}",
        "",
        f"- latest 总数：{len(latest)}",
        f"- 飞书 wxid-indexed：{len(feishu_idx)}",
        f"- 目标 wxid：{len(target_wxids)}",
        f"- 计划更新行数：{len(updates)}",
        f"- 无匹配 wxid：{len(no_match)}",
        "",
        "## 字段更新统计",
        "",
    ]
    field_counter: dict[str, int] = {}
    for r in plan_rows:
        for f in r["fields"]:
            field_counter[f] = field_counter.get(f, 0) + 1
    for f, n in sorted(field_counter.items(), key=lambda x: -x[1]):
        plan_md.append(f"- {f}: {n} 行")
    plan_md.append("")

    plan_md.append("## 触发更新明细（前 30）")
    plan_md.append("")
    plan_md.append("| wxid | 姓名 | outcome | offer | 改动 |")
    plan_md.append("|---|---|---|---|---|")
    for r in plan_rows[:30]:
        plan_md.append(
            f"| `{r['wxid']}` | {r['display_name']} | {r['transition_outcome']} | "
            f"{r['got_offer']} | {'; '.join(r['reasons'])} |"
        )
    plan_md.append("")
    if no_match:
        plan_md.append(f"## 无匹配 wxid（{len(no_match)}）— 飞书表里找不到这些 wxid")
        plan_md.append("")
        for w in no_match[:50]:
            plan_md.append(f"- `{w}` {latest[w].get('display_name','')}")
        if len(no_match) > 50:
            plan_md.append(f"- …还有 {len(no_match) - 50} 个")
        plan_md.append("")
    (run_dir / "plan.md").write_text("\n".join(plan_md), encoding="utf-8")

    print(f"[{mode}] target={len(target_wxids)} updates={len(updates)} no_match={len(no_match)}")
    print(f"  → plan: {run_dir / 'plan.md'}")

    # 执行
    if not args.apply:
        print(f"[dry-run] 不真写。要真写：加 --apply", file=sys.stderr)
        logger("DRY_RUN_DONE")
        log_fh.close()
        return 0

    print(f"[apply] 开始真写 {len(updates)} 行 ...", file=sys.stderr)
    started = time.time()
    ok, fail = batch_update_records(updates, apply=True, logger=logger)
    elapsed = time.time() - started
    summary = {
        "run_id": run_id,
        "mode": mode,
        "target_count": len(target_wxids),
        "updated_ok": ok,
        "updated_fail": fail,
        "no_match": len(no_match),
        "elapsed_seconds": round(elapsed, 1),
    }
    (run_dir / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger(f"APPLY_DONE {summary}")
    log_fh.close()
    print(f"[apply done] ok={ok} fail={fail} elapsed={elapsed:.1f}s")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
