#!/usr/bin/env python3
"""④ 钩子 评分器 —— 硬规则（纯代码）+ 打分卡 rubric（LLM 评委，可选）。

契约：eval/contracts/4_hook.md。钩子开放生成、无唯一答案，金标准是「可接受集合 + 人工首选 +
must_keep_terms（不许丢的限定词/数字）」。分两层：
  · 硬规则（代码·自动）：每个片段是原话子串（需 --input 候选池）；must_keep_terms 一个不丢；
    stitched 字数 ≤ 片段和×1.2；整条 ≤30 字；strategy 已标。本器只跑这层。
  · 打分卡 rubric（LLM 评委）：戳点/中受众/露答案 三要素 → judge.py，默认不跑（留接口）。

候选格式：{items|clips}[]，每条 hooks/acceptable/hook_options 任一键给候选钩子
（[{stitched, fragments:[{sid,text}], strategy}]）。must_keep_terms 取自金标准同 idx。
用法:
  python3 4_hook.py --candidate <run|golden> --golden g.json [--input stage4/input.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

STAGE = "4_hook"
STITCH_MAX = 30
FRAG_RATIO = 1.2


def _hooks(item: dict) -> list[dict]:
    return item.get("hooks") or item.get("acceptable") or item.get("hook_options") or []


def _pool(input_path: str | None) -> dict[int, dict[int, str]]:
    if not input_path:
        return {}
    out: dict[int, dict[int, str]] = {}
    for c in C.load_json(input_path).get("clips", []):
        out[c.get("idx")] = {p["sid"]: p.get("text", "") for p in c.get("candidate_pool", []) if "sid" in p}
    return out


def _src_for_sid(pool: dict[int, str], sid) -> str:
    """sid 可能是 'a-b' 区间，拼回原话。"""
    if isinstance(sid, int):
        return pool.get(sid, "")
    s = str(sid)
    if "-" in s:
        try:
            a, b = (int(x) for x in s.split("-", 1))
            return "".join(pool.get(i, "") for i in range(a, b + 1))
        except ValueError:
            return ""
    try:
        return pool.get(int(s), "")
    except ValueError:
        return ""


def check_hook(h: dict, must_keep: list[str], pool: dict[int, str]) -> list[str]:
    bad = []
    stitched = h.get("stitched", "")
    if len(stitched) > STITCH_MAX:
        bad.append(f"整条 {len(stitched)}字 >{STITCH_MAX}")
    frags = h.get("fragments") or []
    frag_total = sum(len(C.norm(f.get("text", ""))) for f in frags)
    if frag_total and len(C.norm(stitched)) > frag_total * FRAG_RATIO:
        bad.append(f"拼接注水：stitched {len(C.norm(stitched))}字 > 片段和{frag_total}×{FRAG_RATIO}")
    if not h.get("strategy"):
        bad.append("缺 strategy 标注")
    if pool:
        for f in frags:
            txt, src = C.norm(f.get("text", "")), C.norm(_src_for_sid(pool, f.get("sid")))
            if txt and src and txt not in src:
                bad.append(f"片段 #{f.get('sid')}「{f.get('text')}」非候选池原话子串")
    for term in must_keep:
        if C.norm(term) not in C.norm(stitched):
            bad.append(f"丢了 must_keep_term「{term}」")
    return bad


def score(candidate_path: str, golden_path: str | None, input_path: str | None) -> dict:
    cand = C.by_idx(C.load_items(candidate_path))
    gold = C.by_idx(C.load_items(golden_path)) if golden_path and C.is_filled(golden_path) else {}
    pools = _pool(input_path)

    rows, clean_hooks, total_hooks = [], 0, 0
    for idx in sorted(cand):
        hooks = _hooks(cand[idx])
        must_keep = (gold.get(idx, {}) or {}).get("must_keep_terms", [])
        pool = pools.get(idx, {})
        hrows = []
        for h in hooks:
            bad = check_hook(h, must_keep, pool)
            hrows.append({"stitched": h.get("stitched", "")[:30], "violations": bad})
            total_hooks += 1
            if not bad:
                clean_hooks += 1
        rows.append({"idx": idx, "n_hooks": len(hooks), "hooks": hrows,
                     "must_keep_terms": must_keep})
    summary = {"clips": len(cand), "hooks_total": total_hooks, "hooks_clean": clean_hooks,
               "hard_rule_pass_rate": round(clean_hooks / total_hooks, 3) if total_hooks else 0.0,
               "must_keep_terms_set": sum(1 for r in rows if r["must_keep_terms"])}
    return {"stage": STAGE, "candidate": str(candidate_path), "summary": summary, "per_clip": rows}


def main() -> int:
    ap = argparse.ArgumentParser(prog="score:4_hook")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--golden", default=None, help="金标准（取 must_keep_terms）")
    ap.add_argument("--input", default=None, help="stage4 input.json：开候选池子串硬规则")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rep = score(a.candidate, a.golden, a.input)
    print(C.banner(STAGE, rep["summary"]))
    for r in rep["per_clip"]:
        for h in r["hooks"]:
            if h["violations"]:
                print(f"  ✗ idx={r['idx']}「{h['stitched']}」: {'; '.join(h['violations'])}", file=sys.stderr)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
