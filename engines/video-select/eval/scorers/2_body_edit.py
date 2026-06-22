#!/usr/bin/env python3
"""② 总编 评分器 —— 候选正文 vs 金标准正文，句号 F1（+可选时间 IoU）。

契约：eval/contracts/2_body_edit.md。这是**纯代码自动评**：改 body-edit.md 提示词 → 单跑
② → 用本器对金标准，看句号 F1 涨没涨。按 idx 对齐（对不上的退化为同序号）。

判分：
  · 句号 P/R/F1：金标准选的句子被候选覆盖多少（召回）+ 候选有没有注水（精确）。   ← 主指标
  · 时间 IoU（可选 --words）：两版选段在时间轴上的重合比例。
金标准/候选都接受 {items|clips}[].segments[].sids 或 [].keep_sids 两种写法。

用法:
  python3 2_body_edit.py --golden <stage>/golden.json --candidate <run output|golden>
  python3 2_body_edit.py --golden g.json --candidate c.json --words words.json   # 加时间 IoU
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

STAGE = "2_body_edit"


def _sids(item: dict) -> set[int]:
    segs = item.get("segments")
    if segs:
        out: set[int] = set()
        for s in segs:
            out |= C.span_set([s.get("sids")])
        return out
    return C.span_set(item.get("keep_sids"))


def _intervals(item: dict, sid2time: dict[int, tuple[float, float]] | None):
    """秒区间：优先候选自带 time_spans/span；否则用 words 把 sids 换算成时间。"""
    spans = item.get("time_spans") or [s.get("span") for s in item.get("segments", []) if s.get("span")]
    iv = [(float(a), float(b)) for a, b in spans if a is not None and b is not None] if spans else []
    if iv:
        return sorted(iv)
    if sid2time:
        out = []
        for s in item.get("segments", []) or []:
            sids = s.get("sids")
            if not sids:
                continue
            a, b = int(sids[0]), int(sids[-1])
            if a in sid2time and b in sid2time:
                out.append((sid2time[a][0], sid2time[b][1]))
        return sorted(out)
    return []


def _iou(a, b) -> float:
    def total(iv):
        return sum(e - s for s, e in iv)
    i = j = 0
    ov = 0.0
    a, b = sorted(a), sorted(b)
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if hi > lo:
            ov += hi - lo
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    union = total(a) + total(b) - ov
    return ov / union if union else 0.0


def score(golden_path: str, candidate_path: str, words_json: str | None = None) -> dict:
    gold = C.by_idx(C.load_items(golden_path))
    cand = C.by_idx(C.load_items(candidate_path))
    sid2time = None
    if words_json:
        from video_select import _deps  # noqa: F401
        from video_slicer.transcribe import segment
        _, sents = segment.sentences_from_wordfile(words_json, host="张和")
        sid2time = {s.sid: (s.start, s.end) for s in sents}

    rows, f1s, recs, precs, ious = [], [], [], [], []
    for idx in sorted(gold):
        g = gold[idx]
        m = cand.get(idx)
        row = {"idx": idx, "matched": m is not None}
        if m is not None:
            r = C.prf(_sids(g), _sids(m))
            row.update(sid_recall=r["recall"], sid_precision=r["precision"], sid_f1=r["f1"])
            f1s.append(r["f1"]); recs.append(r["recall"]); precs.append(r["precision"])
            if sid2time is not None:
                gi, mi = _intervals(g, sid2time), _intervals(m, sid2time)
                if gi and mi:
                    iou = round(_iou(gi, mi), 3)
                    row["time_iou"] = iou
                    ious.append(iou)
        rows.append(row)
    summary = {"sid_f1": C.mean(f1s), "sid_recall": C.mean(recs), "sid_precision": C.mean(precs),
               "clips_matched": sum(1 for r in rows if r["matched"]), "clips_total": len(gold)}
    if ious:
        summary["time_iou"] = C.mean(ious)
    return {"stage": STAGE, "golden": str(golden_path), "candidate": str(candidate_path),
            "summary": summary, "per_clip": rows}


def main() -> int:
    ap = argparse.ArgumentParser(prog="score:2_body_edit")
    ap.add_argument("--golden", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--words", default=None, help="words.json：加算时间 IoU（可选）")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rep = score(a.golden, a.candidate, a.words)
    print(C.banner(STAGE, rep["summary"]))
    for r in rep["per_clip"]:
        if not r["matched"]:
            print(f"  idx={r['idx']}  ✗未匹配", file=sys.stderr)
        else:
            bits = " ".join(f"{k}={r[k]}" for k in ("sid_f1", "sid_recall", "sid_precision", "time_iou") if k in r)
            print(f"  idx={r['idx']:>2}  {bits}", file=sys.stderr)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
