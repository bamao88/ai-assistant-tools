#!/usr/bin/env python3
"""read_chat.py — 只读 / 0-LLM 的 ad-hoc「读聊天 / 找人」能力（补回迁移丢失的 agent 入口）。

迁移前 agent 有 `llm_enrich --wxid` / `analyze --wxid` 可读某人解码聊天;迁移后解码逻辑被收进
`capabilities/analyze/core.py`,只在 employment/profile 流程内部可达,7 个命令里没有"读聊天"入口
→ 干净 agent 退回直接读 raw JSON、撞上 zstd hex、误判"加密卡住"。本模块补回这个入口。

经 __main__ 以两个 dispatch key 进入,靠 sys.argv[0]（原命令名）区分:
  read-chat   --wxid X     读某人解码+分层聊天 + 信息地图
  search-chat --any kw…    跨全部人按关键词/日期/方向找候选 wxid + 解码片段

全程只读:仅 core.load_messages_raw（读）+ normalize_messages/text_layer/build_info_map（纯函数）
+ 打印到 stdout。不调 LLM、不写盘、不联网。数据现实见 skills/.../references/ad-hoc-chat-read.md。
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# engine 根（recipes/ → up 1）入 sys.path，统一经 config 读路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from capabilities.analyze import core  # noqa: E402


def _fmt(m: dict) -> str:
    role = "助理" if m["is_staff"] else "对方"
    dt = datetime.fromtimestamp(m["createTime"]).strftime("%Y-%m-%d %H:%M")
    tag = "" if m["kind"] == "text" else f"<{m['kind']}>"
    return f"[{dt}] [{role}] {tag}{m['content']}"


def _date_ts(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d").timestamp())


def _load_norm(wxid: str, staff: set[str], min_ts: int = 0):
    raw = core.load_messages_raw(config.DATA_DIR / f"messages_user_{wxid}.json")
    if not raw:
        return None, []
    norm = core.normalize_messages(raw.get("messages") or [], wxid, staff, min_ts=min_ts)
    return raw, norm


def cmd_read(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="read-chat",
                                 description="读某人解码+分层聊天 + 信息地图（只读 / 0-LLM）")
    ap.add_argument("--wxid", required=True)
    ap.add_argument("--layer", choices=["text", "all"], default="text",
                    help="text=L0 文字层（默认,旧行为）; all=全部层（含图片/语音/系统事件标记）")
    ap.add_argument("--since", help="起始日期 YYYY-MM-DD")
    ap.add_argument("--until", help="截止日期 YYYY-MM-DD")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--no-info-map", action="store_true", help="不前置信息地图")
    a = ap.parse_args(argv)

    staff = core.load_staff_wxids()
    raw, norm = _load_norm(a.wxid, staff, _date_ts(a.since) if a.since else 0)
    if raw is None:
        print(f"无聊天文件: messages_user_{a.wxid}.json", file=sys.stderr)
        return 1
    if a.until:
        u = _date_ts(a.until) + 86400
        norm = [m for m in norm if m["createTime"] < u]
    msgs = norm if a.layer == "all" else core.text_layer(norm)

    if a.format == "json":
        print(json.dumps({
            "wxid": a.wxid, "display_name": raw.get("userName"),
            "info_map": core.build_info_map(norm),
            "messages": [{k: m[k] for k in ("ts_str", "is_staff", "kind", "layer", "content")} for m in msgs],
        }, ensure_ascii=False, indent=1))
    else:
        if not a.no_info_map:
            print(core.build_info_map(norm))
            print("\n---\n")
        for m in msgs:
            print(_fmt(m))
    return 0


def cmd_search(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="search-chat",
                                 description="跨全部人找私聊候选 + 解码片段（只读 / 0-LLM）")
    ap.add_argument("--any", nargs="+", default=[], help="关键词（OR 匹配,子串）")
    ap.add_argument("--regex", help="正则（替代 --any）")
    ap.add_argument("--side", choices=["any", "from-them", "from-staff"], default="any",
                    help="from-them=只看对方发的; from-staff=只看助理发的")
    ap.add_argument("--since", help="起始日期 YYYY-MM-DD")
    ap.add_argument("--until", help="截止日期 YYYY-MM-DD")
    ap.add_argument("--layer", choices=["text", "all"], default="all",
                    help="all=含解压出的 zstd 真消息（默认,找回放/退差价建议用 all）")
    ap.add_argument("--context", type=int, default=1, help="每条命中前后保留 N 条上下文")
    ap.add_argument("--limit-people", type=int, default=200)
    ap.add_argument("--max-hits-per-person", type=int, default=5)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    a = ap.parse_args(argv)
    if not a.any and not a.regex:
        ap.error("需要 --any 或 --regex")

    pat = re.compile(a.regex) if a.regex else None
    kws = a.any

    def hit(c: str) -> bool:
        return bool(pat.search(c)) if pat else any(k in c for k in kws)

    staff = core.load_staff_wxids()
    min_ts = _date_ts(a.since) if a.since else 0
    until = _date_ts(a.until) + 86400 if a.until else None

    results = []
    for f in sorted(glob.glob(str(config.DATA_DIR / "messages_user_*.json"))):
        # 廉价预筛：明文关键词不在原文、且无 zstd 压缩行 → 不可能命中,跳过（省去 normalize）。
        try:
            raw_txt = Path(f).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if kws and not pat:
            if not any(k in raw_txt for k in kws) and "28b52ffd" not in raw_txt:
                continue
        wxid = re.sub(r"^.*messages_user_|\.json$", "", f)
        raw, norm = _load_norm(wxid, staff, min_ts)
        if not norm:
            continue
        if until:
            norm = [m for m in norm if m["createTime"] < until]
        pool = norm if a.layer == "all" else core.text_layer(norm)
        hits = []
        for i, m in enumerate(pool):
            if a.side == "from-them" and m["is_staff"]:
                continue
            if a.side == "from-staff" and not m["is_staff"]:
                continue
            if hit(m["content"]):
                ctx = pool[max(0, i - a.context): i + a.context + 1]
                hits.append({"ts": m["ts_str"][:16], "role": "助理" if m["is_staff"] else "对方",
                             "content": m["content"][:100], "context": [_fmt(x) for x in ctx]})
                if len(hits) >= a.max_hits_per_person:
                    break
        if hits:
            results.append({"wxid": wxid, "display_name": (raw or {}).get("userName") or wxid, "hits": hits})
            if len(results) >= a.limit_people:
                break

    if a.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        print(f"命中 {len(results)} 人:\n")
        for r in results:
            print(f"● {r['display_name']} ({r['wxid']})")
            for h in r["hits"]:
                print(f"    [{h['ts']}][{h['role']}] {h['content']}")
    return 0


def main() -> int:
    cmd = sys.argv[0]
    argv = sys.argv[1:]
    if cmd == "search-chat":
        return cmd_search(argv)
    return cmd_read(argv)


if __name__ == "__main__":
    raise SystemExit(main())
