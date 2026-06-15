#!/usr/bin/env python3
"""health_check.py — ★ 客户表数据体检/订正闭环（§5 ★ + §7）。

死脚本考古（§7）发现一组一次性脚本骨架完全相同：

    扫飞书表找某类毛病的行（缺wxid/填错列/重复/缺群序号）
      → 出人读候选清单(plan.md) → dry-run 确认 → --apply 幂等批量改 → 归档 run

本配方把这套**反复出现的任务**提炼成一等配方：一个「缺陷类（defect class）」注册表
+ 统一的 scan→plan→(dry-run|apply)→archive 闭环。新增一类体检 = 写一个找候选的纯
函数，不再复制整套 IO/写回骨架（那走 `capabilities.resolve.core`）。

吸收的死脚本 → 缺陷类（§7）
--------------------------
- `find_missing_wxid` + `update_existing_wxids`  → defect `missing_wxid`
    缺 wxid 且已是学员的行 → 从本地主数据/群产物反查候选 wxid（+ 带上群序号）。
- `fix_friends_column_misplacement`              → defect `friends_column_misplaced`
    sync_friends 把 nick 误填进「微信名称」列 → 纠成 alias/wxid，nick 落「备注及其他名称」。
- `fix_zh2_weixin_name_to_nick`                  → defect `weixin_name_to_nick`（按 role）
    把某 role CREATE 行的「微信名称」由 alias/wxid 改成 nick + append 角色标签。
- `audit_duplicate_creates` + `merge_duplicate_creates` → defect `duplicate_creates`
    sync_friends CREATE 行与「空 wxid 老行」的重复审计（+ 合并：PATCH 老行 wxid / DELETE 新行）。

读侧（找候选）默认走**本地只读镜像** `customer_management_mirror.json`，不碰 live Feishu
（与 ⚠️P3 事故防线一致：体检/确认全离线）。`--apply` 才经 resolve/core 真写飞书（授权门）。
`--source live` 可显式从 live Feishu 拉全表（仅在镜像过期、且你明确要最新时用）。

用法（默认 dry-run + 本地镜像，绝不写）：
  python3 -m recipes.health_check missing_wxid                 # 出缺 wxid 候选清单（dry-run）
  python3 -m recipes.health_check missing_wxid --loose         # 把 S5 成交时间也算学员信号
  python3 -m recipes.health_check friends_column_misplaced
  python3 -m recipes.health_check weixin_name_to_nick --role zh2
  python3 -m recipes.health_check duplicate_creates --role assistant
  python3 -m recipes.health_check missing_wxid --apply         # 授权门：真写飞书（幂等）
  python3 -m recipes.health_check missing_wxid --source live   # 从 live Feishu 拉（仍 dry-run）
  python3 -m recipes.health_check --list                       # 列出所有缺陷类
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

# engine 根（recipes/ → up 1）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from capabilities.resolve import core  # noqa: E402  lark-cli/fetch/run-archive/batch_update+delete
from capabilities.resolve.friend_index import load_friend_index, resolve_role  # noqa: E402

# 群序号字段（missing_wxid 补行序号用）
GROUP_FIELDS = ["群序号-四期", "群序号-核心", "群序号-4.5期"]


# --- 读侧：飞书表（默认本地镜像，--source live 才碰网络）---------------------

def load_feishu_rows(source: str) -> tuple[list[dict], str]:
    """返回 ([{record_id, fields}], 来源描述)。

    source='mirror'（默认）: 读 customer_management_mirror.json（只读，不碰网络）。
    source='live'         : 经 resolve/core.fetch_all_records 拉 live 全表（碰网络）。
    """
    if source == "live":
        rows = core.fetch_all_records()
        return rows, "live Feishu (fetch_all_records)"
    mirror = json.loads(config.MIRROR_FILE.read_text(encoding="utf-8"))
    rows = mirror.get("records", [])
    synced = (mirror.get("_meta") or {}).get("synced_at", "?")
    return rows, f"local mirror (synced_at={synced})"


# ============================================================================
# 缺陷类 1：missing_wxid（吸收 find_missing_wxid + update_existing_wxids）
# ============================================================================

_CLEAN_KEEP_RE = re.compile(r"[^一-鿿぀-ヿA-Za-z0-9_\- ]")
_CLEAN_SPLIT_RE = re.compile(r"[-—()（）/@\s]")


def _clean_name(s: str) -> str:
    if not s:
        return ""
    s = _CLEAN_KEEP_RE.sub(" ", s.strip())
    return _CLEAN_SPLIT_RE.split(s)[0].strip()


def _norm_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p or "")
    return digits[-11:] if len(digits) >= 11 else digits


def _is_student(fields: dict, strict: bool) -> tuple[bool, list[str]]:
    """学员信号 S1-S5（沿用 find_missing_wxid 口径）。strict=True 只看 S1-S4。"""
    signals = []
    if fields.get("几期学员"):
        signals.append("S1:几期学员")
    if fields.get("复训（陪跑和一期学员2次）"):
        signals.append("S2:复训")
    if fields.get("付定金"):
        signals.append("S3:付定金")
    shifu = core.stringify(fields.get("实付")).strip()
    if shifu and shifu not in ("0", "0.0", "0元"):
        signals.append("S4:实付")
    if not strict and fields.get("成交/首次权益时间"):
        signals.append("S5:成交时间")
    strict_signals = [s for s in signals if not s.startswith("S5")]
    return (len(strict_signals) > 0, strict_signals) if strict else (len(signals) > 0, signals)


def _build_reverse_indexes(staff_wxids: set[str]):
    """从 all_student.json + by_wxid.json 建反查索引（同 find_missing_wxid）。"""
    all_students = json.loads(config.STUDENT_FILE.read_text(encoding="utf-8"))
    by_wxid = {}
    if config.BY_WXID_FILE.exists():
        by_wxid = json.loads(config.BY_WXID_FILE.read_text(encoding="utf-8"))

    phone_to_wxid: dict[str, str] = {}
    weixinhao_to_wxid: dict[str, str] = {}
    nickname_to_wxids: dict[str, list[str]] = {}
    beizhu_head_to_wxids: dict[str, list[str]] = {}
    display_to_wxids: dict[str, list[str]] = {}

    for s in all_students:
        if not isinstance(s, dict):
            continue
        w = s.get("wxid")
        if not w or w in staff_wxids:
            continue
        ph = _norm_phone(s.get("手机号") or "")
        if ph and len(ph) == 11:
            phone_to_wxid.setdefault(ph, w)
        nick = (s.get("微信昵称") or "").strip()
        if nick:
            nickname_to_wxids.setdefault(nick, []).append(w)
        other = s.get("其他名称") or ""
        m = re.search(r"微信号:([^|]+?)(?:\s*\||$)", other)
        if m and m.group(1).strip():
            weixinhao_to_wxid.setdefault(m.group(1).strip(), w)
        m = re.search(r"备注:([^|]+?)(?:\s*\||$)", other)
        if m:
            head = _clean_name(m.group(1))
            if head:
                beizhu_head_to_wxids.setdefault(head, []).append(w)

    for wxid, info in by_wxid.items():
        if wxid in staff_wxids:
            continue
        head = _clean_name(info.get("display_seen") or "")
        if head:
            display_to_wxids.setdefault(head, []).append(wxid)

    return {
        "by_wxid": by_wxid,
        "phone_to_wxid": phone_to_wxid,
        "weixinhao_to_wxid": weixinhao_to_wxid,
        "nickname_to_wxids": nickname_to_wxids,
        "beizhu_head_to_wxids": beizhu_head_to_wxids,
        "display_to_wxids": display_to_wxids,
    }


def scan_missing_wxid(rows: list[dict], args) -> dict:
    """找飞书表里 wxid 空 + 是学员的行，反查候选 wxid（同 find_missing_wxid 逻辑）。

    返回 plan dict：{candidates, stats}。候选含 guesses（按置信度降序）。
    """
    strict = not args.loose
    staff_wxids: set[str] = set()
    if config.STAFF_EXCLUDE_FILE.exists():
        staff_wxids = {s["wxid"] for s in
                       json.loads(config.STAFF_EXCLUDE_FILE.read_text(encoding="utf-8")).get("staff", [])}
    idx = _build_reverse_indexes(staff_wxids)
    by_wxid = idx["by_wxid"]

    candidates: list[dict] = []
    for row in rows:
        fields = row.get("fields", {}) or {}
        if core.stringify(fields.get("wxid")).strip():
            continue
        is_stu, signals = _is_student(fields, strict)
        if not is_stu:
            continue

        姓名 = core.stringify(fields.get("姓名")).strip()
        客户名 = core.stringify(fields.get("客户名称（微信号）")).strip()
        手机号 = core.stringify(fields.get("手机号")).strip()
        几期 = core.stringify(fields.get("几期学员")).strip()
        备注 = core.stringify(fields.get("备注")).strip()

        guesses: list[dict] = []

        def add(method: str, wxid: str, conf: str, evi: str):
            if wxid in staff_wxids or any(g["wxid"] == wxid for g in guesses):
                return
            guesses.append({"method": method, "wxid": wxid, "confidence": conf, "evidence": evi})

        if 客户名 and 客户名 in by_wxid:
            add("M0-客户名即wxid", 客户名, "high", f"客户名称'{客户名}' 直接是有效 wxid")
        phone_norm = _norm_phone(手机号)
        if phone_norm and phone_norm in idx["phone_to_wxid"]:
            add("M1-手机号", idx["phone_to_wxid"][phone_norm], "high", f"手机号 {phone_norm} 在 all_student.json")
        if 客户名 and 客户名 in idx["weixinhao_to_wxid"]:
            add("M2-微信号", idx["weixinhao_to_wxid"][客户名], "high", f"客户名'{客户名}' = all_student 微信号")
        for nm in [姓名, 客户名]:
            if nm and nm in idx["nickname_to_wxids"]:
                for w in idx["nickname_to_wxids"][nm]:
                    add("M3-微信昵称", w, "high", f"'{nm}' = all_student 微信昵称")
        for nm in [姓名, 客户名]:
            head = _clean_name(nm)
            if head and head in idx["beizhu_head_to_wxids"]:
                for w in idx["beizhu_head_to_wxids"][head]:
                    add("M4-备注头部", w, "medium", f"clean_name('{nm}')='{head}' = all_student 备注头部")
        for nm in [姓名, 客户名]:
            head = _clean_name(nm)
            if head and head in idx["display_to_wxids"]:
                for w in idx["display_to_wxids"][head]:
                    add("M5-群昵称头部", w, "medium", f"clean_name('{nm}')='{head}' 命中群昵称")

        candidates.append({
            "record_id": row.get("record_id"), "signals": signals,
            "姓名": 姓名, "客户名称": 客户名, "手机号": 手机号,
            "几期学员": 几期, "备注": 备注[:80], "guesses": guesses,
        })

    def sort_key(c):
        if not c["guesses"]:
            return (3, c["姓名"])
        return ({"high": 0, "medium": 1, "low": 2}.get(c["guesses"][0]["confidence"], 3), c["姓名"])
    candidates.sort(key=sort_key)

    have = sum(1 for c in candidates if c["guesses"])
    high = sum(1 for c in candidates if c["guesses"] and c["guesses"][0]["confidence"] == "high")
    medium = sum(1 for c in candidates if c["guesses"] and c["guesses"][0]["confidence"] == "medium")
    return {
        "candidates": candidates,
        "stats": {"total": len(candidates), "have_guess": have, "high": high,
                  "medium": medium, "no_guess": len(candidates) - have},
    }


def updates_missing_wxid(plan: dict) -> list[dict]:
    """从候选生成幂等 updates（只取 high/medium 头部候选 + 带群序号），同 update_existing_wxids。"""
    by_wxid = {}
    if config.BY_WXID_FILE.exists():
        by_wxid = json.loads(config.BY_WXID_FILE.read_text(encoding="utf-8"))
    updates = []
    for c in plan["candidates"]:
        if not c["guesses"]:
            continue
        best = c["guesses"][0]
        if best["confidence"] not in ("high", "medium"):
            continue
        wxid = best["wxid"]
        fields: dict[str, Any] = {"wxid": wxid}
        orders = by_wxid.get(wxid, {})
        for f in GROUP_FIELDS:
            if f in orders:
                fields[f] = int(orders[f])
        updates.append({"record_id": c["record_id"], "fields": fields})
    return updates


def render_missing_wxid_md(plan: dict) -> str:
    st = plan["stats"]
    lines = ["# 飞书客户管理表 wxid 空 + 已是学员 反查清单", "",
             f"- 候选行总数：{st['total']}",
             f"- 找到候选 wxid：{st['have_guess']}（高 {st['high']} / 中 {st['medium']}）",
             f"- 无任何候选（需人工）：{st['no_guess']}", ""]
    for title, conf in [("高置信候选", "high"), ("中置信候选", "medium")]:
        items = [c for c in plan["candidates"] if c["guesses"] and c["guesses"][0]["confidence"] == conf]
        if not items:
            continue
        lines += [f"## {title}（{len(items)} 条）", "",
                  "| 姓名 | 客户名称 | 手机号 | 几期 | 信号 | 候选 wxid | 方法 |",
                  "|---|---|---|---|---|---|---|"]
        for c in items:
            g = c["guesses"][0]
            lines.append(f"| {c['姓名']} | {c['客户名称']} | {c['手机号']} | {c['几期学员']} | "
                         f"{','.join(c['signals'])} | {g['wxid']} | {g['method']} |")
        lines.append("")
    return "\n".join(lines)


# ============================================================================
# 缺陷类 2：friends_column_misplaced（吸收 fix_friends_column_misplacement）
# ============================================================================

def _latest_sync_friends_plan(role: str | None = None) -> Path | None:
    runs = sorted([p for p in config.FRIENDS_SYNC_RUNS_DIR.iterdir() if p.is_dir()], reverse=True) \
        if config.FRIENDS_SYNC_RUNS_DIR.exists() else []
    for r in runs:
        if role and f"_{role}_" not in r.name:
            continue
        plan = r / "plan.json"
        if plan.exists():
            d = json.loads(plan.read_text(encoding="utf-8"))
            if d.get("creates"):
                return plan
    return None


def scan_friends_column_misplaced(rows: list[dict], args) -> dict:
    """sync_friends CREATE 行里「微信名称」被误填成 nick → 纠成 alias/wxid，nick 落「备注及其他名称」。"""
    plan_path = _latest_sync_friends_plan()
    if not plan_path:
        return {"candidates": [], "stats": {"total": 0, "note": "没找到 sync_friends plan.json（含 creates）"}}
    create_wxids = [c["wxid"] for c in json.loads(plan_path.read_text())["creates"]]
    friends = {}
    if config.FRIENDS_INDEX_FILE.exists():
        friends = {f["wxid"]: f for f in json.loads(config.FRIENDS_INDEX_FILE.read_text())["friends"]}

    by_wxid = {core.stringify((r.get("fields") or {}).get("wxid")).strip(): r for r in rows
               if core.stringify((r.get("fields") or {}).get("wxid")).strip() in set(create_wxids)}

    candidates = []
    for wxid in create_wxids:
        rec = by_wxid.get(wxid)
        if not rec:
            continue
        f = rec.get("fields") or {}
        cur_weixin = core.stringify(f.get("微信名称")).strip()
        cur_beizhu = core.stringify(f.get("备注及其他名称")).strip()
        meta = friends.get(wxid) or {}
        alias = (meta.get("alias") or "").strip()
        nick = (meta.get("nick_name") or "").strip()
        correct_weixin = alias or wxid
        patch: dict[str, Any] = {}
        if cur_weixin == nick and nick and cur_weixin != correct_weixin:
            patch["微信名称"] = correct_weixin
        if not cur_beizhu and nick:
            patch["备注及其他名称"] = nick
        if patch:
            candidates.append({"record_id": rec.get("record_id"), "wxid": wxid,
                               "before_微信名称": cur_weixin, "patch": patch})
    return {"candidates": candidates, "stats": {"total": len(candidates),
            "plan_source": plan_path.name, "create_scope": len(create_wxids)}}


def updates_friends_column_misplaced(plan: dict) -> list[dict]:
    return [{"record_id": c["record_id"], "fields": c["patch"]} for c in plan["candidates"]]


def render_friends_column_md(plan: dict) -> str:
    st = plan["stats"]
    lines = [f"# 列错位修复 plan（缺陷类 friends_column_misplaced）", "",
             f"- 待修复：{st['total']}", f"- 范围：{st.get('plan_source','?')} ({st.get('create_scope','?')} CREATE)", "",
             "| wxid | before 微信名称 | patch |", "|---|---|---|"]
    for c in plan["candidates"][:30]:
        lines.append(f"| {c['wxid']} | {c['before_微信名称']} | {','.join(c['patch'].keys())} |")
    return "\n".join(lines)


# ============================================================================
# 缺陷类 3：weixin_name_to_nick（吸收 fix_zh2_weixin_name_to_nick，按 role）
# ============================================================================

ROLE_PLAN_FILES = {
    "zh2": "20260526_175515_zh2_apply",
    "assistant": "20260519_160713_apply",
}


def scan_weixin_name_to_nick(rows: list[dict], args) -> dict:
    role = args.role or "zh2"
    src, role_tag = resolve_role(role, None, None)
    run_name = ROLE_PLAN_FILES.get(role)
    plan_file = config.FRIENDS_SYNC_RUNS_DIR / (run_name or "") / "plan.json"
    if not run_name or not plan_file.exists():
        # 兜底：取该 role 最新含 creates 的 plan
        p = _latest_sync_friends_plan(role)
        if not p:
            return {"candidates": [], "stats": {"total": 0, "note": f"没找到 role={role} 的 sync plan"}}
        plan_file = p
    create_wxids = {c["wxid"] for c in json.loads(plan_file.read_text())["creates"]}
    friends = load_friend_index(src)
    wxid_to_nick = {f["wxid"]: (f.get("nick_name") or "").strip()
                    for f in friends if f.get("wxid") in create_wxids}

    candidates = []
    for r in rows:
        f = r.get("fields") or {}
        wxid = core.stringify(f.get("wxid")).strip()
        if not wxid or wxid not in create_wxids:
            continue
        nick = wxid_to_nick.get(wxid, "")
        if not nick:
            continue
        patch: dict[str, Any] = {}
        cur_weixin = core.stringify(f.get("微信名称")).strip()
        if cur_weixin != nick:
            patch["微信名称"] = nick
        cur_tags = core.multiselect_names(f.get("添加微信"))
        if role_tag not in cur_tags:
            patch["添加微信"] = cur_tags + [role_tag]
        if patch:
            candidates.append({"record_id": r.get("record_id"), "wxid": wxid,
                               "before_微信名称": cur_weixin, "after_微信名称": nick, "patch": patch})
    return {"candidates": candidates, "stats": {"total": len(candidates), "role": role,
            "role_tag": role_tag, "plan_source": plan_file.parent.name, "scope": len(create_wxids)}}


def updates_weixin_name_to_nick(plan: dict) -> list[dict]:
    return [{"record_id": c["record_id"], "fields": c["patch"]} for c in plan["candidates"]]


def render_weixin_name_md(plan: dict) -> str:
    st = plan["stats"]
    lines = [f"# {st.get('role_tag','?')} 微信名称→昵称 修复 plan（缺陷类 weixin_name_to_nick）", "",
             f"- role={st.get('role')} 范围={st.get('scope','?')} CREATE (plan={st.get('plan_source','?')})",
             f"- 待修复：{st['total']}", "",
             "| wxid | before 微信名称 | after 微信名称 | patch |", "|---|---|---|---|"]
    for c in plan["candidates"][:30]:
        lines.append(f"| {c['wxid']} | {c['before_微信名称']} | {c['after_微信名称']} | {','.join(c['patch'].keys())} |")
    return "\n".join(lines)


# ============================================================================
# 缺陷类 4：duplicate_creates（吸收 audit_duplicate_creates + merge_duplicate_creates）
# ============================================================================

HIGH_COLLISION_NICKS = {"ss", "十一", "流浪猫", "克柔", "Dustinn", "Thor"}


def scan_duplicate_creates(rows: list[dict], args) -> dict:
    """sync_friends CREATE 行与「空 wxid + 有业务字段」老行的重复审计 + 合并计划。"""
    role = args.role or "assistant"
    src, _ = resolve_role(role, None, None)
    plan_file = _latest_sync_friends_plan(role) or _latest_sync_friends_plan()
    if not plan_file:
        return {"candidates": [], "merge_auto": [], "merge_manual": [],
                "stats": {"total": 0, "note": f"没找到 role={role} sync plan"}}
    create_wxids = [c["wxid"] for c in json.loads(plan_file.read_text())["creates"]]
    wxid_to_friend = {f["wxid"]: f for f in load_friend_index(src)}

    empty_wxid_rows = []
    our_new_rows: dict[str, str] = {}
    for r in rows:
        f = r.get("fields") or {}
        w = core.stringify(f.get("wxid")).strip()
        if w in create_wxids:
            our_new_rows[w] = r.get("record_id")
            continue
        if w:
            continue
        has_biz = any(core.stringify(f.get(k)).strip() for k in
                      ["微信名称", "备注及其他名称", "手机号", "几期学员",
                       "复训（陪跑和一期学员2次）", "付定金", "实付"])
        if has_biz:
            empty_wxid_rows.append({
                "record_id": r.get("record_id"),
                "微信名称": core.stringify(f.get("微信名称")).strip(),
                "备注及其他名称": core.stringify(f.get("备注及其他名称")).strip(),
                "几期学员": core.stringify(f.get("几期学员")).strip(),
            })

    suspects = []
    for wxid in create_wxids:
        friend = wxid_to_friend.get(wxid) or {}
        alias = (friend.get("alias") or "").strip()
        nick = (friend.get("nick_name") or "").strip()
        remark_head = _clean_name((friend.get("remark") or "").strip())
        matches = []
        for row in empty_wxid_rows:
            kmm = row["微信名称"]
            bz = row["备注及其他名称"]
            bz_head = _clean_name(bz)
            rules = []
            if alias and kmm == alias:
                rules.append(("HIGH", f"alias={alias}==微信名称"))
            if alias and bz == alias:
                rules.append(("HIGH", f"alias={alias}==备注及其他名称"))
            if nick and kmm == nick:
                rules.append(("MID", f"nick={nick}==微信名称"))
            if nick and bz == nick:
                rules.append(("MID", f"nick={nick}==备注及其他名称"))
            if remark_head and bz_head and remark_head == bz_head:
                rules.append(("LOW", f"remark_head={remark_head}==备注头部"))
            if rules:
                matches.append({"row": row, "rules": rules})
        if matches:
            best = ("HIGH" if any(r[0] == "HIGH" for m in matches for r in m["rules"])
                    else "MID" if any(r[0] == "MID" for m in matches for r in m["rules"]) else "LOW")
            suspects.append({"wxid": wxid, "our_record_id": our_new_rows.get(wxid),
                             "alias": alias, "nick": nick, "confidence": best, "matches": matches})
    suspects.sort(key=lambda x: {"HIGH": 0, "MID": 1, "LOW": 2}[x["confidence"]])

    # 合并计划（同 merge_duplicate_creates）：单候选 + 非高重名 → 自动；否则人工
    merge_auto, merge_manual = [], []
    for s in suspects:
        if len(s["matches"]) > 1:
            merge_manual.append({**s, "_reason": f"{len(s['matches'])} 候选"})
            continue
        if s["nick"] in HIGH_COLLISION_NICKS:
            merge_manual.append({**s, "_reason": f"高重名 nick: {s['nick']}"})
            continue
        cand = s["matches"][0]["row"]
        new_weixin = s["alias"] or s["wxid"]
        old_patch: dict[str, Any] = {"wxid": s["wxid"]}
        if cand["微信名称"] == s["nick"] and s["nick"]:
            old_patch["微信名称"] = new_weixin
        if not cand["备注及其他名称"] and s["nick"]:
            old_patch["备注及其他名称"] = s["nick"]
        merge_auto.append({"wxid": s["wxid"], "old_record_id": cand["record_id"],
                           "old_patch": old_patch, "delete_record_id": s["our_record_id"]})

    return {
        "candidates": suspects, "merge_auto": merge_auto, "merge_manual": merge_manual,
        "stats": {"total": len(suspects),
                  "high": sum(1 for s in suspects if s["confidence"] == "HIGH"),
                  "mid": sum(1 for s in suspects if s["confidence"] == "MID"),
                  "low": sum(1 for s in suspects if s["confidence"] == "LOW"),
                  "auto": len(merge_auto), "manual": len(merge_manual),
                  "role": role, "scope": len(create_wxids)},
    }


def updates_duplicate_creates(plan: dict) -> dict:
    """duplicate_creates 是双操作（PATCH 老行 + DELETE 新行）。返回 {updates, deletes}。"""
    updates = [{"record_id": m["old_record_id"], "fields": m["old_patch"]} for m in plan["merge_auto"]]
    deletes = [m["delete_record_id"] for m in plan["merge_auto"] if m["delete_record_id"]]
    return {"updates": updates, "deletes": deletes}


def render_duplicate_md(plan: dict) -> str:
    st = plan["stats"]
    lines = [f"# sync_friends CREATE 重复审计 + 合并 plan（缺陷类 duplicate_creates）", "",
             f"- role={st.get('role')} 范围={st.get('scope','?')} CREATE",
             f"- 嫌疑重复：{st['total']}（高 {st['high']} / 中 {st['mid']} / 低 {st['low']}）",
             f"- 可自动合并：{st['auto']} | 需人工：{st['manual']}", "",
             "## 自动合并预览（前 20）", "| wxid | alias | nick | 老行 record | 删新行 |", "|---|---|---|---|---|"]
    for m in plan["merge_auto"][:20]:
        lines.append(f"| {m['wxid']} | {m['old_patch'].get('微信名称','-')} | - | "
                     f"{m['old_record_id']} | {m['delete_record_id']} |")
    return "\n".join(lines)


# ============================================================================
# 缺陷类注册表
# ============================================================================

# defect → (scan_fn, updates_fn, render_md_fn, archive_base_dir)
DEFECTS: dict[str, dict[str, Any]] = {
    "missing_wxid": {
        "scan": scan_missing_wxid, "updates": updates_missing_wxid,
        "render": render_missing_wxid_md, "archive": "GROUP_ORDER_WXID_FILLS_DIR",
        "desc": "缺 wxid 且已是学员的行 → 反查候选 wxid（+群序号）",
    },
    "friends_column_misplaced": {
        "scan": scan_friends_column_misplaced, "updates": updates_friends_column_misplaced,
        "render": render_friends_column_md, "archive": "FRIENDS_COLUMN_FIX_DIR",
        "desc": "sync_friends 把 nick 误填进「微信名称」→ 纠正",
    },
    "weixin_name_to_nick": {
        "scan": scan_weixin_name_to_nick, "updates": updates_weixin_name_to_nick,
        "render": render_weixin_name_md, "archive": "FRIENDS_COLUMN_FIX_DIR",
        "desc": "把某 role CREATE 行「微信名称」改成 nick + 加角色标签",
    },
    "duplicate_creates": {
        "scan": scan_duplicate_creates, "updates": updates_duplicate_creates,
        "render": render_duplicate_md, "archive": "FRIENDS_MERGE_DIR",
        "desc": "sync_friends CREATE 行与空 wxid 老行的重复审计 + 合并",
    },
}


def run_defect(defect: str, args) -> int:
    spec = DEFECTS[defect]
    rows, source_desc = load_feishu_rows(args.source)
    print(f"[health_check:{defect}] 读侧来源 = {source_desc}（{len(rows)} 行）", file=sys.stderr)

    plan = spec["scan"](rows, args)
    plan_md = spec["render"](plan)

    archive_base = getattr(config, spec["archive"])
    run_dir, run_id, mode = core.make_run_dir(archive_base, apply=args.apply, suffix=defect)
    core.write_plan(run_dir, plan, plan_md)
    print(plan_md)
    print(f"\n[{mode}] plan → {run_dir / 'plan.md'}", file=sys.stderr)

    if not args.apply:
        print(f"[dry-run] 不写飞书。确认 plan 后加 --apply（授权门）。", file=sys.stderr)
        return 0

    # --apply 真写（授权门 + 幂等 batch；走 resolve/core）
    upd = spec["updates"](plan)
    if defect == "duplicate_creates":
        ok_u, fail_u = core.batch_update(upd["updates"]) if upd["updates"] else (0, 0)
        ok_d, fail_d = core.batch_delete(upd["deletes"]) if upd["deletes"] else (0, 0)
        result = {"run_id": run_id, "update_ok": ok_u, "update_fail": fail_u,
                  "delete_ok": ok_d, "delete_fail": fail_d}
    else:
        ok, fail = core.batch_update(upd) if upd else (0, 0)
        result = {"run_id": run_id, "ok": ok, "fail": fail}
    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[apply done] {result}", file=sys.stderr)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="health_check — 客户表数据体检/订正闭环（scan→plan→dry-run→apply→archive）")
    p.add_argument("defect", nargs="?", choices=list(DEFECTS),
                   help="缺陷类（见 --list）")
    p.add_argument("--list", action="store_true", help="列出所有缺陷类")
    p.add_argument("--apply", action="store_true", help="授权门：真写飞书（默认 dry-run）")
    p.add_argument("--source", choices=["mirror", "live"], default="mirror",
                   help="读侧来源：mirror=本地只读镜像（默认，不碰网络）| live=拉 live Feishu")
    p.add_argument("--role", choices=["assistant", "zh2"], default=None,
                   help="role-scoped 缺陷类（weixin_name_to_nick / duplicate_creates）用")
    p.add_argument("--loose", action="store_true", help="missing_wxid：把 S5 成交时间也算学员信号")
    args = p.parse_args()

    if args.list or not args.defect:
        print("可用缺陷类（defect class）：")
        for name, spec in DEFECTS.items():
            print(f"  {name:28} {spec['desc']}")
        return 0

    return run_defect(args.defect, args)


if __name__ == "__main__":
    sys.exit(main())
