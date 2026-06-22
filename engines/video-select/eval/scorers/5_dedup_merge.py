#!/usr/bin/env python3
"""⑤ 批量去重 评分器 —— 候选合并分组 vs 金标准分组，pairwise P/R/F1（+drop 命中 + 硬规则）。

契约：eval/contracts/5_dedup_merge.md。合并是聚类问题：把「哪两条该合在一组」列成无序
配对集合，候选 vs 金标准算 pairwise P/R/F1（该合的合了吗、误合了吗）。

判分：
  · pairwise P/R/F1：主指标（合并对）。                                  ← 纯代码
  · drop 命中：金标准该删的 idx，候选删了多少（recall/precision）。
  · 硬规则（需 --input）：只操作真实 idx；每个 idx 只出现在 groups/drop/keep 之一。

金标准/候选规范形：{groups:[[3,9],...], drop:[14], keep:[1,2,...]}。
候选也接受 dedup 跑分产物（golden_dedup.json，含 clips[].dedup_merged_from）：用 --from-run
把它转成规范形（groups 可靠；drop 靠标题回原批次 best-effort）。
用法:
  python3 5_dedup_merge.py --golden g.json --candidate c.json [--input stage5/input.json]
  python3 5_dedup_merge.py --golden g.json --candidate golden_dedup.json --from-run --input in.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

STAGE = "5_dedup_merge"


def _pairs(groups) -> set[frozenset]:
    out: set[frozenset] = set()
    for grp in groups or []:
        for a, b in itertools.combinations(sorted(set(grp)), 2):
            out.add(frozenset((a, b)))
    return out


def canonical_from_run(run_path: str, input_path: str | None) -> dict:
    """dedup 跑分产物 → {groups,drop,keep} 规范形（best-effort）。"""
    data = C.load_json(run_path)
    clips = data.get("clips", [])
    groups = [list(c["dedup_merged_from"]) for c in clips
              if isinstance(c.get("dedup_merged_from"), list) and len(c["dedup_merged_from"]) >= 2]
    merged = {i for grp in groups for i in grp}
    # 存活的非合并条：靠标题回到原批次拿原 idx（dedup 重编号丢了原 idx）
    survivors = set(merged)
    if input_path:
        title2idx = {c.get("title"): c.get("idx") for c in C.load_json(input_path).get("batch", [])}
        for c in clips:
            if c.get("dedup_merged_from"):
                continue
            oi = title2idx.get(c.get("title"))
            if oi is not None:
                survivors.add(oi)
        universe = {c.get("idx") for c in C.load_json(input_path).get("batch", [])}
        drop = sorted(universe - survivors)
        keep = sorted(survivors - merged)
    else:
        drop, keep = [], sorted(survivors - merged)
    return {"groups": groups, "drop": drop, "keep": keep}


def score(golden_path: str, candidate: dict, input_path: str | None = None) -> dict:
    g = C.load_json(golden_path)
    gp, cp = _pairs(g.get("groups")), _pairs(candidate.get("groups"))
    pair = C.prf(gp, cp)
    gd, cd = set(g.get("drop", [])), set(candidate.get("drop", []))
    drop = C.prf(gd, cd)

    violations = []
    if input_path:
        universe = {c.get("idx") for c in C.load_json(input_path).get("batch", [])}
        seen: dict[int, int] = {}
        for bucket in (candidate.get("groups", []),
                       [[i] for i in candidate.get("drop", [])],
                       [[i] for i in candidate.get("keep", [])]):
            for grp in bucket:
                for i in grp:
                    if i not in universe:
                        violations.append(f"idx={i} 不在真实批次")
                    seen[i] = seen.get(i, 0) + 1
        for i, n in seen.items():
            if n > 1:
                violations.append(f"idx={i} 出现在 {n} 个动作里（应唯一）")

    summary = {"pair_f1": pair["f1"], "pair_recall": pair["recall"], "pair_precision": pair["precision"],
               "drop_f1": drop["f1"], "drop_recall": drop["recall"], "drop_precision": drop["precision"],
               "gold_pairs": len(gp), "cand_pairs": len(cp), "violations": len(violations)}
    return {"stage": STAGE, "golden": str(golden_path), "summary": summary,
            "pair_detail": pair, "drop_detail": drop, "violations": violations}


def main() -> int:
    ap = argparse.ArgumentParser(prog="score:5_dedup_merge")
    ap.add_argument("--golden", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--input", default=None, help="stage5 input.json：开硬规则 + drop 回原批次")
    ap.add_argument("--from-run", action="store_true", help="候选是 dedup 跑分产物，需转规范形")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not C.is_filled(a.golden):
        print(f"[score:{STAGE}] ⚠ 金标准未填（{a.golden}）—— ⑤去重金标准待 owner 冻结，跳过。")
        return 0
    cand = canonical_from_run(a.candidate, a.input) if a.from_run else C.load_json(a.candidate)
    rep = score(a.golden, cand, a.input)
    print(C.banner(STAGE, rep["summary"]))
    for v in rep["violations"][:20]:
        print(f"  ✗ {v}", file=sys.stderr)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
