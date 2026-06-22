#!/usr/bin/env python3
"""③ 去口水 评分器 —— 候选删除的字 vs 金标准删除的字，字符级 P/R/F1（+子串硬规则）。

契约：eval/contracts/3_refine_deduct.md。**纯代码自动评**：把「删掉的字符」当多重集，按
(idx, sid) 对齐算 P/R/F1——该删的删了吗（召回）、误删了吗（精确）。

判分：
  · 字符 P/R/F1（micro，按 sid 对齐求和）：主指标。               ← 纯代码
  · 子串硬规则（需 --input）：每个候选 deletion.text 必须是该句原话一字不差子串，
    否则记为「不可执行」违规（gates 同款红线）。
  · 承接句误删（最大的坑）属主观维度 → 交 LLM 评委（judge.py），本器不判。

金标准/候选格式：{items|clips}[].deletions[{sid,text,kind}]。
用法:
  python3 3_refine_deduct.py --golden g.json --candidate c.json [--input stage3/input.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

STAGE = "3_refine_deduct"


def _del_by_sid(item: dict) -> dict[int, str]:
    """该 clip 每个 sid 删掉的字（拼起来；同 sid 多段删除合并）。"""
    out: dict[int, str] = {}
    for d in item.get("deletions", []) or []:
        sid = d.get("sid")
        if not isinstance(sid, int):
            continue
        out[sid] = out.get(sid, "") + (d.get("text") or "")
    return out


def _src_by_idx(input_path: str | None) -> dict[int, dict[int, str]]:
    """从 input.json 取每条 clip 每句原话（子串硬规则用）。"""
    if not input_path:
        return {}
    data = C.load_json(input_path)
    out: dict[int, dict[int, str]] = {}
    for c in data.get("clips", []):
        idx = c.get("idx")
        out[idx] = {ln["sid"]: ln.get("text", "") for ln in c.get("body_lines", []) if "sid" in ln}
    return out


def score(golden_path: str, candidate_path: str, input_path: str | None = None) -> dict:
    gold = C.by_idx(C.load_items(golden_path))
    cand = C.by_idx(C.load_items(candidate_path))
    src = _src_by_idx(input_path)

    tp = g_chars = c_chars = 0
    clip_f1s, rows, violations = [], [], []
    for idx in sorted(gold):
        g = _del_by_sid(gold[idx])
        m = _del_by_sid(cand.get(idx, {}))
        sids = set(g) | set(m)
        ctp = cg = cc = 0
        for sid in sids:
            gm, cm = C.char_multiset(g.get(sid, "")), C.char_multiset(m.get(sid, ""))
            r = C.multiset_prf(gm, cm)
            ctp += r["tp"]; cg += r["gold_chars"]; cc += r["cand_chars"]
        cprec = ctp / cc if cc else (1.0 if cg == 0 else 0.0)
        crec = ctp / cg if cg else 1.0
        cf1 = (2 * cprec * crec / (cprec + crec)) if (cprec + crec) else 0.0
        clip_f1s.append(cf1)
        rows.append({"idx": idx, "matched": idx in cand, "char_f1": round(cf1, 3),
                     "char_recall": round(crec, 3), "char_precision": round(cprec, 3),
                     "gold_chars": cg, "cand_chars": cc})
        tp += ctp; g_chars += cg; c_chars += cc
        # 子串硬规则
        if src.get(idx):
            for d in cand.get(idx, {}).get("deletions", []) or []:
                sid, txt = d.get("sid"), (d.get("text") or "")
                s = src[idx].get(sid, "")
                if txt and C.norm(txt) not in C.norm(s):
                    violations.append(f"idx={idx} #{sid} 删「{txt}」非原话子串")

    mprec = tp / c_chars if c_chars else 1.0
    mrec = tp / g_chars if g_chars else 1.0
    mf1 = (2 * mprec * mrec / (mprec + mrec)) if (mprec + mrec) else 0.0
    summary = {"char_f1_micro": round(mf1, 3), "char_recall_micro": round(mrec, 3),
               "char_precision_micro": round(mprec, 3), "char_f1_macro": C.mean(clip_f1s),
               "clips_total": len(gold), "substring_violations": len(violations)}
    return {"stage": STAGE, "golden": str(golden_path), "candidate": str(candidate_path),
            "summary": summary, "per_clip": rows, "violations": violations}


def main() -> int:
    ap = argparse.ArgumentParser(prog="score:3_refine_deduct")
    ap.add_argument("--golden", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--input", default=None, help="stage3 input.json：开子串硬规则")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not C.is_filled(a.golden):
        print(f"[score:{STAGE}] ⚠ 金标准未填（{a.golden}）—— ③去口水金标准待 owner 重建，跳过。")
        return 0
    rep = score(a.golden, a.candidate, a.input)
    print(C.banner(STAGE, rep["summary"]))
    for v in rep["violations"][:20]:
        print(f"  ✗ {v}", file=sys.stderr)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
