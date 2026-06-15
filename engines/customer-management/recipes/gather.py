#!/usr/bin/env python3
"""gather.py — ★ 读取侧 Facade（§5/§10 + v1 §4）。

一句话：把一个人/一群人散在四处的客户数据**一把抓全**成一个稳定的 bundle，
并算出「本地有、飞书缺」的 diff + 回填建议，给 agent 做判断用。

设计红线（§10/§12/§13）
----------------------
* **默认只读、0-LLM、不碰飞书网络**：读 all_student.json（本地主数据）+
  customer_management_mirror.json（飞书表的**本地只读镜像**，NOT live Feishu）+
  群成员/好友名单产物。`--analyze` 才调 analyze（LLM）；本配方自身永不写任何文件。
* 飞书真源永远是 tblfCYoeornDw0XF；镜像可能过期，bundle 里带 `mirror_synced_at`
  让调用方知道新鲜度。要刷新镜像请单独跑 `capabilities.acquire.mirror`（那才碰网络）。

bundle schema（稳定契约，调用方/skill 依赖）
-------------------------------------------
gather 返回 `{"_meta": {...}, "people": [ <PersonBundle>, ... ]}`。

PersonBundle = {
  "wxid": str,                       # 主键（可能为空：镜像里有行但没填 wxid）
  "display_name": str,               # 最佳展示名（昵称/微信名称/备注头部）
  "local":  <LocalHit | null>,       # all_student.json 命中（本地主数据）
  "feishu": <FeishuHit | null>,      # 飞书镜像命中（本地 mirror，非 live）
  "wechat": <WechatPresence>,        # 微信现场（昵称/备注/群可达账号/所在群）
  "payment": <PaymentHit | null>,    # 付款（镜像 实付/付款方式/凭证 有无）
  "analysis": <Analysis | null>,     # 仅 --analyze；就业 latest 快照（不调 LLM 时为 null）
  "diff": <Diff>,                    # 本地→飞书的差异（hero）
}

LocalHit   = all_student.json 该 wxid 的整条记录（原样字段）。
FeishuHit  = {"record_id": str, "fields": {飞书原始字段子集（已 stringify 的可读值）}}。
WechatPresence = {
  "nickname": str, "remark": str,
  "group_accounts": [str],          # 「添加微信」可达账号标签（小助理/张和2号）
  "groups": [str],                  # 所在群名
  "in_group_roster": bool,          # 是否出现在群成员产物里
}
PaymentHit = {"实付": str, "付款方式": str, "has_proof": bool} 或 null。
Analysis   = {"got_offer": bool, "transition_outcome": str, "confidence": float,
              "last_analyzed_at": str} 或 null（仅 --analyze 且 latest 有该 wxid）。
Diff       = {
  "in_local": bool, "in_feishu": bool,
  "missing_in_feishu": bool,        # 本地有 + 飞书镜像无该 wxid 行
  "conflicts": [ {"field": str, "local": str, "feishu": str} ],
  "suggested_fill": { <feishu字段> : <拟填值> },   # 7 字段口径，仅「飞书空 + 本地有」时给
}

suggested_fill 的 7 字段（§10 本地→飞书回写口径）= 本地源 → 飞书字段：
  wxid          ← local.wxid
  微信名称       ← local.微信昵称（飞书第一眼看人名）
  备注           ← local.其他名称
  客户画像       ← local.自我介绍（本地侧能给的画像原料）
  拿到offer      ← analysis.got_offer（仅 --analyze 命中）
  添加微信       ← local.添加微信（多选；建议「并集补齐」）
  加好友日期      ← （本地主数据不持有；留空，由 friends_sync 的 first_chat_date 负责）

用法（迁移后从 engine 根跑；全部只读）：
  python3 -m recipes.gather --wxid <wxid>           # 单人 bundle
  python3 -m recipes.gather --wxid <a> <b> ...      # 多人
  python3 -m recipes.gather --new                   # 本地有但飞书镜像缺的人（missing_in_feishu）
  python3 -m recipes.gather --group "4.5期-AI实战训练营！"   # 某群成员
  python3 -m recipes.gather --wxid <wxid> --analyze # 额外带就业 analysis 快照
  python3 -m recipes.gather --wxid <wxid> --pretty  # 人读摘要而非纯 JSON
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# engine 根（recipes/ → up 1）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

# 群名 → 群成员产物文件（recognize 用的同一映射）
GROUP_NAME_TO_CHATROOM = {
    "四期-AI实战训练营-无所畏惧！": "members_54388823635_chatroom.json",
    "AI产品训练营核心交流群": "members_56738408970_chatroom.json",
    "4.5期-AI实战训练营！": "members_57069021254_chatroom.json",
}

# 飞书镜像字段名（与 customer_management_mirror.json 一致）
F_WXID = "wxid"
F_WEIXIN_NAME = "微信名称"
F_BEIZHU = "备注"
F_BEIZHU_OTHER = "备注及其他名称"
F_HUAXIANG = "客户画像"
F_OFFER = "拿到offer"
F_ADD_BY = "添加微信"
F_JIA_DATE = "加好友日期"
F_SHIFU = "实付"
F_FANGSHI = "付款方式"
F_PINGZHENG = "截图附件"
F_JIQI = "几期学员"

# suggested_fill 的 7 字段（§10）。映射：飞书字段 → 取本地哪个字段（None=非本地源）。
# 注：§10 口径写「备注」；飞书表里「备注」是 AI 回访分析的 append 目标（见 sync_to_feishu），
# 而姓名/昵称类备注的真实落点是「备注及其他名称」（见 sync_friends）。本地「其他名称」是
# 姓名元数据，故回填到「备注及其他名称」，不污染 AI 分析的「备注」列。
SUGGESTED_FILL_FIELDS = [F_WXID, F_WEIXIN_NAME, F_BEIZHU_OTHER, F_HUAXIANG, F_OFFER, F_ADD_BY, F_JIA_DATE]


# --- 字段值规约（飞书各类字段值 → 可读字符串）-------------------------------

def stringify(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "✓" if v else ""
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        parts = []
        for it in v:
            if isinstance(it, dict):
                parts.append(it.get("text") or it.get("name") or "")
            else:
                parts.append(str(it))
        return " ".join(p for p in parts if p)
    if isinstance(v, dict):
        return v.get("text") or v.get("name") or ""
    return str(v)


def multiselect_names(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(it.get("name") if isinstance(it, dict) else it)
                for it in value if (it.get("name") if isinstance(it, dict) else it)]
    if isinstance(value, str) and value:
        return [value]
    return []


# --- 数据源加载（全只读）----------------------------------------------------

def load_local_students() -> dict[str, dict]:
    """all_student.json → {wxid: record}（+ 其他名称.微信号 别名）。"""
    students = json.loads(config.STUDENT_FILE.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for s in students:
        if not isinstance(s, dict):
            continue
        w = s.get("wxid")
        if w:
            out[w] = s
    return out


def load_mirror() -> tuple[dict[str, dict], str, dict[str, dict]]:
    """飞书本地镜像 → ({wxid: record}, synced_at, {record_id: record})。

    空 wxid 的镜像行不进 wxid 索引（但仍可被 missing/conflict 逻辑参考）。
    """
    mirror = json.loads(config.MIRROR_FILE.read_text(encoding="utf-8"))
    synced_at = (mirror.get("_meta") or {}).get("synced_at", "")
    by_wxid: dict[str, dict] = {}
    for r in mirror.get("records", []):
        w = stringify((r.get("fields") or {}).get(F_WXID)).strip()
        if w and w not in by_wxid:
            by_wxid[w] = r
    return by_wxid, synced_at, mirror


def load_group_rosters() -> dict[str, dict]:
    """群成员产物 → {wxid: {昵称,备注名,微信号,群昵称,所在群:[...]}}（聚合多群）。"""
    roster: dict[str, dict] = {}
    for gname, fname in GROUP_NAME_TO_CHATROOM.items():
        path = config.DATA_DIR / fname
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for m in data.get("members", []):
            w = m.get("wxid", "")
            if not w:
                continue
            entry = roster.setdefault(w, {
                "昵称": m.get("昵称", ""), "备注名": m.get("备注名", ""),
                "微信号": m.get("微信号", ""), "群昵称": m.get("群昵称", ""),
                "所在群": [],
            })
            if gname not in entry["所在群"]:
                entry["所在群"].append(gname)
    return roster


def load_employment_latest() -> dict[str, dict]:
    """就业 latest.json → {wxid: snapshot}（--analyze 用；不调 LLM，只读已有产物）。"""
    p = config.EMPLOYMENT_LATEST_FILE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


# --- bundle 组装 ------------------------------------------------------------

def _best_display_name(local: dict | None, feishu_fields: dict | None, wechat: dict) -> str:
    if local and local.get("微信昵称"):
        return local["微信昵称"]
    if wechat.get("nickname"):
        return wechat["nickname"]
    if feishu_fields:
        for f in (F_WEIXIN_NAME, F_BEIZHU, F_BEIZHU_OTHER):
            v = stringify(feishu_fields.get(f)).strip()
            if v:
                return v
    if local and local.get("wxid"):
        return local["wxid"]
    return ""


def _wechat_presence(local: dict | None, roster_entry: dict | None) -> dict:
    nickname = ""
    remark = ""
    groups: list[str] = []
    group_accounts: list[str] = []
    if local:
        nickname = local.get("微信昵称", "") or ""
        groups = list(local.get("所在群") or [])
        group_accounts = list(local.get("添加微信") or [])
        # 备注：从 其他名称 抽「备注:...」头
        other = local.get("其他名称") or ""
        m = re.search(r"备注[:：]([^|]+)", other)
        if m:
            remark = m.group(1).strip()
    if roster_entry:
        nickname = nickname or roster_entry.get("昵称", "")
        remark = remark or roster_entry.get("备注名", "")
        for g in roster_entry.get("所在群", []):
            if g not in groups:
                groups.append(g)
    return {
        "nickname": nickname,
        "remark": remark,
        "group_accounts": sorted(set(group_accounts)),
        "groups": groups,
        "in_group_roster": roster_entry is not None,
    }


def _payment_hit(feishu_fields: dict | None) -> dict | None:
    if not feishu_fields:
        return None
    shifu = stringify(feishu_fields.get(F_SHIFU)).strip()
    fangshi = stringify(feishu_fields.get(F_FANGSHI)).strip()
    has_proof = bool(feishu_fields.get(F_PINGZHENG))
    if not (shifu or fangshi or has_proof):
        return None
    return {"实付": shifu, "付款方式": fangshi, "has_proof": has_proof}


def _compute_diff(local: dict | None, feishu_row: dict | None,
                  analysis: dict | None) -> dict:
    """算本地→飞书 diff：missing_in_feishu + conflicts + suggested_fill（7 字段）。"""
    in_local = local is not None
    in_feishu = feishu_row is not None
    feishu_fields = (feishu_row or {}).get("fields") or {}

    conflicts: list[dict] = []
    suggested_fill: dict[str, Any] = {}

    if in_local:
        # 本地源 → 飞书字段 拟填值
        local_to_feishu: dict[str, Any] = {
            F_WXID: (local.get("wxid") or "").strip(),
            F_WEIXIN_NAME: (local.get("微信昵称") or "").strip(),
            F_BEIZHU: (local.get("其他名称") or "").strip(),
            F_HUAXIANG: (local.get("自我介绍") or "").strip(),
            F_ADD_BY: sorted(set(local.get("添加微信") or [])),
            # 加好友日期 本地不持有 → 永远不建议（由 friends_sync 负责）
        }
        if analysis is not None and analysis.get("got_offer") is not None:
            local_to_feishu[F_OFFER] = bool(analysis.get("got_offer"))

        for f, local_val in local_to_feishu.items():
            if f not in SUGGESTED_FILL_FIELDS:
                continue
            empty_local = local_val in (None, "", [])
            if empty_local:
                continue
            if not in_feishu:
                # 飞书整行都没有 → 全部建议（建行）
                suggested_fill[f] = local_val
                continue
            cur = feishu_fields.get(f)
            cur_str = stringify(cur).strip()
            # 多选字段：算并集补齐
            if f == F_ADD_BY:
                cur_names = set(multiselect_names(cur))
                want = set(local_val)
                missing = sorted(want - cur_names)
                if missing:
                    suggested_fill[f] = sorted(cur_names | want)
                continue
            if f == F_OFFER:
                if bool(cur) != bool(local_val):
                    # offer 是状态字段：本地(analysis) 与飞书不一致 → conflict + 建议
                    conflicts.append({"field": f, "local": str(local_val), "feishu": str(bool(cur))})
                    suggested_fill[f] = bool(local_val)
                continue
            # 文本字段：飞书空 → 建议填；飞书非空且不同 → 记 conflict（不强行覆盖）
            if not cur_str:
                suggested_fill[f] = local_val
            elif cur_str != str(local_val):
                conflicts.append({"field": f, "local": str(local_val), "feishu": cur_str})

    return {
        "in_local": in_local,
        "in_feishu": in_feishu,
        "missing_in_feishu": in_local and not in_feishu,
        "conflicts": conflicts,
        "suggested_fill": suggested_fill,
    }


def build_person_bundle(wxid: str, *, local: dict | None, feishu_row: dict | None,
                        roster_entry: dict | None, latest: dict[str, dict],
                        with_analyze: bool) -> dict:
    feishu_fields = (feishu_row or {}).get("fields") or {}
    wechat = _wechat_presence(local, roster_entry)

    analysis = None
    if with_analyze:
        snap = latest.get(wxid)
        if snap:
            analysis = {
                "got_offer": snap.get("got_offer"),
                "transition_outcome": snap.get("transition_outcome"),
                "confidence": snap.get("confidence"),
                "last_analyzed_at": snap.get("last_analyzed_at"),
            }

    diff = _compute_diff(local, feishu_row, analysis)

    feishu_hit = None
    if feishu_row is not None:
        # 只回可读字段子集（避免把 2103 行 ×40 字段全量原始结构吐出来）
        readable = {k: stringify(v) for k, v in feishu_fields.items()
                    if stringify(v).strip()}
        feishu_hit = {"record_id": feishu_row.get("record_id"), "fields": readable}

    return {
        "wxid": wxid,
        "display_name": _best_display_name(local, feishu_fields, wechat),
        "local": local,
        "feishu": feishu_hit,
        "wechat": wechat,
        "payment": _payment_hit(feishu_fields),
        "analysis": analysis,
        "diff": diff,
    }


# --- 目标选择 ---------------------------------------------------------------

def select_targets(args, local_idx: dict[str, dict], mirror_idx: dict[str, dict],
                   roster: dict[str, dict]) -> list[str]:
    """根据 --wxid / --new / --group 选 wxid 列表。"""
    if args.wxid:
        return list(args.wxid)
    if args.new:
        # 本地有 + 飞书镜像缺 → missing_in_feishu 候选
        return [w for w in local_idx if w not in mirror_idx]
    if args.group:
        fname = GROUP_NAME_TO_CHATROOM.get(args.group)
        if not fname:
            print(f"[ERROR] 未知群名: {args.group}\n  可选: {list(GROUP_NAME_TO_CHATROOM)}",
                  file=sys.stderr)
            return []
        path = config.DATA_DIR / fname
        if not path.exists():
            print(f"[ERROR] 群成员产物不存在: {path}", file=sys.stderr)
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [m["wxid"] for m in data.get("members", []) if m.get("wxid")]
    return []


def render_pretty(bundle: dict) -> str:
    lines = [f"# gather bundle — {bundle['_meta']['count']} 人 "
             f"(镜像 synced_at={bundle['_meta']['mirror_synced_at']})", ""]
    for p in bundle["people"]:
        d = p["diff"]
        flags = []
        if d["missing_in_feishu"]:
            flags.append("⚠飞书缺行")
        if d["conflicts"]:
            flags.append(f"{len(d['conflicts'])}冲突")
        if d["suggested_fill"]:
            flags.append(f"{len(d['suggested_fill'])}待填")
        lines.append(f"## {p['display_name']}  `{p['wxid']}`  {' '.join(flags) or '✓一致'}")
        lines.append(f"  本地: {'有' if d['in_local'] else '无'} | 飞书镜像: {'有' if d['in_feishu'] else '无'}"
                     f" | 群可达: {','.join(p['wechat']['group_accounts']) or '-'}")
        if p.get("analysis"):
            a = p["analysis"]
            lines.append(f"  就业: offer={a.get('got_offer')} outcome={a.get('transition_outcome')}")
        if d["suggested_fill"]:
            lines.append(f"  建议回填: {json.dumps(d['suggested_fill'], ensure_ascii=False)}")
        if d["conflicts"]:
            for c in d["conflicts"]:
                lines.append(f"  冲突[{c['field']}]: 本地={c['local']!r} 飞书={c['feishu']!r}")
        lines.append("")
    return "\n".join(lines)


def gather(args) -> dict:
    """组装 bundle（纯读、纯函数；不写任何文件）。"""
    local_idx = load_local_students()
    mirror_idx, synced_at, _mirror = load_mirror()
    roster = load_group_rosters()
    latest = load_employment_latest() if args.analyze else {}

    targets = select_targets(args, local_idx, mirror_idx, roster)

    people = []
    for wxid in targets:
        people.append(build_person_bundle(
            wxid,
            local=local_idx.get(wxid),
            feishu_row=mirror_idx.get(wxid),
            roster_entry=roster.get(wxid),
            latest=latest,
            with_analyze=args.analyze,
        ))

    return {
        "_meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "mode": "wxid" if args.wxid else "new" if args.new else "group" if args.group else "none",
            "readonly": True,
            "analyze": bool(args.analyze),
            "mirror_synced_at": synced_at,
            "mirror_note": "飞书表的本地只读镜像（非 live）。刷新请跑 capabilities.acquire.mirror。",
            "count": len(people),
            "local_total": len(local_idx),
            "feishu_mirror_total": len(mirror_idx),
        },
        "people": people,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="gather — 读取侧 Facade（本地+飞书镜像+微信+付款+diff/建议回填，默认只读 0-LLM）")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--wxid", nargs="+", help="一个或多个 wxid")
    g.add_argument("--new", action="store_true", help="本地有但飞书镜像缺的人（missing_in_feishu）")
    g.add_argument("--group", type=str, help="某群成员（群名）")
    p.add_argument("--analyze", action="store_true",
                   help="额外带就业 analysis 快照（读 latest.json，仍不调 LLM）")
    p.add_argument("--pretty", action="store_true", help="人读摘要而非纯 JSON")
    p.add_argument("--limit", type=int, default=0, help="只取前 N 人")
    args = p.parse_args()

    bundle = gather(args)
    if args.limit and len(bundle["people"]) > args.limit:
        bundle["people"] = bundle["people"][:args.limit]
        bundle["_meta"]["count"] = len(bundle["people"])
        bundle["_meta"]["truncated_to"] = args.limit

    if args.pretty:
        print(render_pretty(bundle))
    else:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
