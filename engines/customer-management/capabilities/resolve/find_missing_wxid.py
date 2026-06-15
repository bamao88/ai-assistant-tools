"""
找飞书客户管理表里 wxid 字段空 + 已是学员的行，反查候选 wxid。

判定"是学员"的信号（满足任一即视为学员，按强度降序）：
  S1. 几期学员 非空（最强）
  S2. 复训 非空
  S3. 付定金 = True
  S4. 实付 非空且非"0"
  S5. 成交/首次权益时间 非空

反查策略（按置信度降序）：
  M1. 飞书"客户名称（微信号）"字段 == 群成员的微信号（注意：是 weixinhao，不是 wxid）
      —— 这种最准；微信号在群 protobuf 里没有，但在 student_manage/all_student.json 里有
  M2. 飞书"姓名" 字段出现在 by_wxid.json 的 display_seen（群昵称）头部
  M3. 飞书"客户名称（微信号）" 字段出现在 display_seen 头部
  M4. 飞书"备注" 字段里包含某 wxid 的姓名

输出：
  analytics/group_member_order/missing_wxid_review.md — 候选清单，人工 review 用
  analytics/group_member_order/missing_wxid_candidates.json — 结构化数据
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# engine 根（capabilities/resolve/ → up 2）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

PROJECT_ROOT = config.PROJECT_ROOT
BY_WXID_FILE = config.BY_WXID_FILE
ALL_STUDENT_FILE = config.STUDENT_FILE
STAFF_EXCLUDE_FILE = config.STAFF_EXCLUDE_FILE
OUTPUT_DIR = config.GROUP_MEMBER_ORDER_DIR

APP_TOKEN = "YTcFbyGS4arILPseQJscA6J7nqb"
TABLE_ID = "tblfCYoeornDw0XF"
LARK_PROFILE = "zhanghe"


def run_lark(args: list[str], timeout: int = 60) -> dict:
    cmd = ["lark-cli", "--as", "bot", "--profile", LARK_PROFILE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"lark-cli failed: stderr={res.stderr[:300]}")
    data = json.loads(res.stdout)
    if data.get("code") != 0:
        raise RuntimeError(f"feishu error: code={data.get('code')} msg={data.get('msg')}")
    return data.get("data", {})


def fetch_all() -> list[dict]:
    print("[fetch] 拉飞书全表 ...", file=sys.stderr)
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
    print(f"[fetch] 共 {len(all_items)} 行", file=sys.stderr)
    return all_items


def stringify(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        out = []
        for it in v:
            if isinstance(it, dict):
                out.append(it.get("text") or it.get("name") or "")
            else:
                out.append(str(it))
        return "".join(out)
    return str(v)


def is_student(fields: dict, strict: bool = True) -> tuple[bool, list[str]]:
    """strict=True：只看 S1-S4（明确学员）；strict=False：含 S5（首次权益时间，可能潜客）。"""
    signals = []
    if fields.get("几期学员"):
        signals.append("S1:几期学员")
    if fields.get("复训（陪跑和一期学员2次）"):
        signals.append("S2:复训")
    if fields.get("付定金"):
        signals.append("S3:付定金")
    shifu = stringify(fields.get("实付")).strip()
    if shifu and shifu not in ("0", "0.0", "0元"):
        signals.append("S4:实付")
    s5_hit = bool(fields.get("成交/首次权益时间"))
    if not strict and s5_hit:
        signals.append("S5:成交时间")
    strict_signals = [s for s in signals if not s.startswith("S5")]
    if strict:
        return (len(strict_signals) > 0, strict_signals)
    return (len(signals) > 0, signals)


def clean_name(s: str) -> str:
    """从昵称里抽出"看起来像真名"的部分：去掉期数、emoji、英文角色后缀等。"""
    if not s:
        return ""
    s = s.strip()
    # 去 emoji 简单方案：保留 ASCII + 中日韩
    s = re.sub(r"[^一-鿿぀-ヿA-Za-z0-9_\- ]", " ", s)
    # 截断到第一个分隔符
    head = re.split(r"[-—()（）/@\s]", s)[0]
    return head.strip()


def main():
    p = argparse.ArgumentParser(description="反查飞书表里 wxid 空 + 是学员的行")
    p.add_argument("--loose", action="store_true",
                   help="宽松模式：把 S5(成交/首次权益时间) 也算学员信号；默认严格(S1-S4)")
    args = p.parse_args()
    strict = not args.loose

    by_wxid = json.loads(BY_WXID_FILE.read_text(encoding="utf-8"))
    all_students = json.loads(ALL_STUDENT_FILE.read_text(encoding="utf-8"))
    staff_data = json.loads(STAFF_EXCLUDE_FILE.read_text(encoding="utf-8"))
    staff_wxids = {s["wxid"] for s in staff_data.get("staff", [])}

    # 学员主数据反查（按真实 schema：手机号 / 微信昵称 / 其他名称）
    phone_to_wxid: dict[str, str] = {}
    weixinhao_to_wxid: dict[str, str] = {}
    nickname_to_wxids: dict[str, list[str]] = {}
    beizhu_head_to_wxids: dict[str, list[str]] = {}
    qunnick_head_to_wxids: dict[str, list[str]] = {}

    def norm_phone(p: str) -> str:
        digits = re.sub(r"\D", "", p or "")
        return digits[-11:] if len(digits) >= 11 else digits

    for s in all_students:
        if not isinstance(s, dict):
            continue
        w = s.get("wxid")
        if not w or w in staff_wxids:
            continue

        ph = norm_phone(s.get("手机号") or "")
        if ph and len(ph) == 11:
            phone_to_wxid.setdefault(ph, w)

        nick = (s.get("微信昵称") or "").strip()
        if nick:
            nickname_to_wxids.setdefault(nick, []).append(w)

        # 其他名称: "备注:XXX-YY期 | 微信号:Cool_Like_Michelle | 群昵称:A.Little..."
        other = s.get("其他名称") or ""
        m = re.search(r"微信号:([^|]+?)(?:\s*\||$)", other)
        if m:
            wh = m.group(1).strip()
            if wh:
                weixinhao_to_wxid.setdefault(wh, w)
        m = re.search(r"备注:([^|]+?)(?:\s*\||$)", other)
        if m:
            head = clean_name(m.group(1))
            if head:
                beizhu_head_to_wxids.setdefault(head, []).append(w)
        m = re.search(r"群昵称:([^|]+?)(?:\s*\||$)", other)
        if m:
            head = clean_name(m.group(1))
            if head:
                qunnick_head_to_wxids.setdefault(head, []).append(w)

    # 群 by_wxid: 加一个 display->wxid 反查（短名前缀匹配）
    display_to_wxids: dict[str, list[str]] = {}
    for wxid, info in by_wxid.items():
        if wxid in staff_wxids:
            continue
        d = info.get("display_seen") or ""
        head = clean_name(d)
        if head:
            display_to_wxids.setdefault(head, []).append(wxid)

    feishu_rows = fetch_all()

    # 找候选行
    candidates = []
    for row in feishu_rows:
        fields = row.get("fields", {}) or {}
        wxid_val = stringify(fields.get("wxid")).strip()
        if wxid_val:
            continue
        is_stu, signals = is_student(fields, strict=strict)
        if not is_stu:
            continue

        姓名 = stringify(fields.get("姓名")).strip()
        客户名 = stringify(fields.get("客户名称（微信号）")).strip()
        手机号 = stringify(fields.get("手机号")).strip()
        几期 = stringify(fields.get("几期学员")).strip()
        备注 = stringify(fields.get("备注")).strip()

        guesses: list[dict] = []

        def add(method: str, wxid: str, conf: str, evi: str):
            if wxid in staff_wxids:
                return
            if any(g["wxid"] == wxid for g in guesses):
                return
            guesses.append({"method": method, "wxid": wxid, "confidence": conf, "evidence": evi})

        # M0: 客户名称直接是 wxid（飞书 wxid 误填在了"客户名称"字段）
        if 客户名 and 客户名 in by_wxid:
            add("M0-客户名即wxid", 客户名, "high",
                f"客户名称'{客户名}' 直接是有效 wxid")

        # M1: 手机号精确匹配（最强）
        phone_norm = norm_phone(手机号)
        if phone_norm and phone_norm in phone_to_wxid:
            add("M1-手机号", phone_to_wxid[phone_norm], "high",
                f"手机号 {phone_norm} 在 all_student.json")

        # M2: 客户名 == all_student 提取的微信号（精确）
        if 客户名 and 客户名 in weixinhao_to_wxid:
            add("M2-微信号", weixinhao_to_wxid[客户名], "high",
                f"客户名'{客户名}' = all_student 微信号")

        # M3: 姓名 == all_student 微信昵称（精确字符串）
        for nm_field in [姓名, 客户名]:
            if nm_field and nm_field in nickname_to_wxids:
                for w in nickname_to_wxids[nm_field]:
                    add("M3-微信昵称", w, "high",
                        f"'{nm_field}' = all_student 微信昵称")

        # M4: 姓名头部 == all_student 备注头部
        for nm_field in [姓名, 客户名]:
            head = clean_name(nm_field)
            if head and head in beizhu_head_to_wxids:
                for w in beizhu_head_to_wxids[head]:
                    add("M4-备注头部", w, "medium",
                        f"clean_name('{nm_field}')='{head}' = all_student 备注头部")

        # M5: 姓名头部 == 群 by_wxid display 头部
        display_to_wxids: dict[str, list[str]] = {}
        for wxid_, info in by_wxid.items():
            if wxid_ in staff_wxids:
                continue
            d = info.get("display_seen") or ""
            head_ = clean_name(d)
            if head_:
                display_to_wxids.setdefault(head_, []).append(wxid_)
        for nm_field in [姓名, 客户名]:
            head = clean_name(nm_field)
            if head and head in display_to_wxids:
                for w in display_to_wxids[head]:
                    add("M5-群昵称头部", w, "medium",
                        f"clean_name('{nm_field}')='{head}' 命中群昵称")

        candidates.append({
            "record_id": row.get("record_id"),
            "signals": signals,
            "姓名": 姓名, "客户名称": 客户名,
            "手机号": 手机号, "几期学员": 几期, "备注": 备注[:80],
            "guesses": guesses,
        })

    # 排序：先按是否有候选 + 候选置信度（无候选放最后，给人工补）
    def sort_key(c):
        if not c["guesses"]:
            return (3, c["姓名"])
        best = c["guesses"][0]["confidence"]
        return ({"high": 0, "medium": 1, "low": 2}.get(best, 3), c["姓名"])
    candidates.sort(key=sort_key)

    # 落盘
    out_json = OUTPUT_DIR / "missing_wxid_candidates.json"
    out_json.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    # markdown for human review
    lines = ["# 飞书客户管理表 wxid 空 + 已是学员 反查清单", ""]
    lines.append(f"- 候选行总数：{len(candidates)}")
    have_guess = sum(1 for c in candidates if c["guesses"])
    high = sum(1 for c in candidates if c["guesses"] and c["guesses"][0]["confidence"] == "high")
    medium = sum(1 for c in candidates if c["guesses"] and c["guesses"][0]["confidence"] == "medium")
    lines.append(f"- 找到候选 wxid：{have_guess}（高置信 {high}，中置信 {medium}）")
    lines.append(f"- **无任何候选**（需人工查群成员对照）：{len(candidates) - have_guess}")
    lines.append("")
    lines.append("`确认` 列你填 ✓ 表示这个候选 wxid 对，✗ 表示错；不确定留空让我跳过。")
    lines.append("")

    # 分组：high → medium → no_guess
    def block(title, filt):
        items = [c for c in candidates if filt(c)]
        if not items:
            return
        lines.append(f"## {title}（{len(items)} 条）\n")
        lines.append("| 确认 | 姓名 | 客户名称 | 手机号 | 几期 | 信号 | 候选 wxid | 方法 | 证据 |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for c in items:
            g = c["guesses"][0] if c["guesses"] else {"wxid": "（无）", "method": "", "evidence": ""}
            sig = ",".join(c["signals"])
            lines.append(f"|  | {c['姓名']} | {c['客户名称']} | {c['手机号']} | {c['几期学员']} | {sig} | {g['wxid']} | {g.get('method','')} | {g.get('evidence','')[:60]} |")
        lines.append("")

    block("高置信候选", lambda c: c["guesses"] and c["guesses"][0]["confidence"] == "high")
    block("中置信候选", lambda c: c["guesses"] and c["guesses"][0]["confidence"] == "medium")
    block("无候选 - 需人工查", lambda c: not c["guesses"])

    out_md = OUTPUT_DIR / "missing_wxid_review.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n候选行总数：{len(candidates)}")
    print(f"找到候选：{have_guess}（高 {high} / 中 {medium}）")
    print(f"无候选：{len(candidates) - have_guess}")
    print(f"\n人工 review：{out_md}")
    print(f"结构化数据：{out_json}")


if __name__ == "__main__":
    main()
