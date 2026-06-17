#!/usr/bin/env python3
"""选段打分器 —— 任意一版切片产出 vs 金标准，给出"逼近度"分数（评测基准这条线）。

用途：金标准定稿后，以后每改一版选段 prompt → 重跑产出 → 用本脚本跟金标准对照，看分有没有涨。
这就是"评测这一块逻辑"的闭环（生成器 global_evidence.py 产基准，本脚本量逼近度）。

两套指标（按候选文件里有什么自动算哪个）：
  · 句号集合（keep_sids）  → 召回/精确/F1：金标准选的句子被候选覆盖了多少 + 候选有没有注水。
  · 时间区间（time_spans / keep_spans 秒） → 时间 IoU：两版选段在时间轴上的重合比例。
按 clip 标题对齐（对不上退化为同序号对齐）。

支持的候选/金标准文件格式（同一函数自适应）：
  · 本基准 golden.json / golden_candidate.json：clips[].keep_sids(句号) + time_spans(秒)
  · 生产 _selection.json：clips[].keep_sids(句号)
  · 人工筛选版 .json：[{title, keep_spans(秒)}]（无句号，走时间 IoU）

用法:
  python score.py --golden <golden.json> --candidate <_selection.json|人工筛选版.json|...> \\
      [--out score_report.json]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def _sid_set(spans) -> set[int]:
    out: set[int] = set()
    for sp in spans or []:
        if isinstance(sp, (list, tuple)) and len(sp) >= 2:
            try:
                a, b = int(sp[0]), int(sp[-1])
            except (TypeError, ValueError):
                continue
            if a > b:
                a, b = b, a
            out.update(range(a, b + 1))
    return out


def _merge_intervals(spans) -> list[tuple[float, float]]:
    iv = sorted((float(s), float(e)) for s, e in (spans or []) if e is not None and s is not None)
    merged: list[tuple[float, float]] = []
    for s, e in iv:
        if s > e:
            s, e = e, s
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def _total(iv) -> float:
    return sum(e - s for s, e in iv)


def _overlap(a, b) -> float:
    tot, i, j = 0.0, 0, 0
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if hi > lo:
            tot += hi - lo
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return tot


def normalize_clips(path: str | Path) -> list[dict]:
    """任意支持格式 → [{title, sids:set, intervals:[(s,e)]}]（缺哪套就空哪套）。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = data["clips"] if isinstance(data, dict) and "clips" in data else data
    out = []
    for c in raw:
        sid_spans = c.get("keep_sids") or []
        time_spans = c.get("time_spans") or c.get("keep_spans") or []
        out.append({
            "title": (c.get("title") or "").replace("（✅ 剪辑）", "").strip(),
            "sids": _sid_set(sid_spans),
            "intervals": _merge_intervals(time_spans),
        })
    return out


def _match(gold: list[dict], cand: list[dict]) -> list[tuple[dict, dict | None]]:
    """按标题对齐；标题对不上的退化为同序号对齐。"""
    by_title = {c["title"]: c for c in cand if c["title"]}
    used, pairs = set(), []
    for i, g in enumerate(gold):
        m = by_title.get(g["title"])
        if m is None and i < len(cand) and cand[i]["title"] not in by_title.keys() - {None}:
            m = cand[i]  # 同序号兜底
        if m is not None:
            used.add(id(m))
        pairs.append((g, m))
    return pairs


def score(golden_path: str, candidate_path: str) -> dict:
    gold = normalize_clips(golden_path)
    cand = normalize_clips(candidate_path)
    rows, agg = [], {"sid_recall": [], "sid_precision": [], "sid_f1": [], "time_iou": []}
    for g, m in _match(gold, cand):
        row = {"title": g["title"], "matched": m is not None}
        if m is not None:
            # 句号集合指标
            if g["sids"] and m["sids"]:
                inter = len(g["sids"] & m["sids"])
                rec = inter / len(g["sids"])
                prec = inter / len(m["sids"])
                f1 = (2 * rec * prec / (rec + prec)) if (rec + prec) else 0.0
                row.update(sid_recall=round(rec, 3), sid_precision=round(prec, 3), sid_f1=round(f1, 3))
                agg["sid_recall"].append(rec); agg["sid_precision"].append(prec); agg["sid_f1"].append(f1)
            # 时间 IoU
            if g["intervals"] and m["intervals"]:
                ov = _overlap(g["intervals"], m["intervals"])
                union = _total(g["intervals"]) + _total(m["intervals"]) - ov
                iou = ov / union if union else 0.0
                row["time_iou"] = round(iou, 3)
                agg["time_iou"].append(iou)
        rows.append(row)
    summary = {k: round(sum(v) / len(v), 3) for k, v in agg.items() if v}
    summary["clips_matched"] = sum(1 for r in rows if r["matched"])
    summary["clips_total"] = len(gold)
    return {"golden": str(golden_path), "candidate": str(candidate_path),
            "summary": summary, "per_clip": rows}


def main() -> int:
    ap = argparse.ArgumentParser(prog="score", description="选段产出 vs 金标准 逼近度打分")
    ap.add_argument("--golden", required=True, help="金标准 golden.json（或候选 golden_candidate.json）")
    ap.add_argument("--candidate", required=True, help="待评切片产出（_selection.json / 人工筛选版.json / 另一版 golden）")
    ap.add_argument("--out", default=None, help="把报告写成 JSON（默认只打印摘要）")
    a = ap.parse_args()
    rep = score(a.golden, a.candidate)
    print(json.dumps(rep["summary"], ensure_ascii=False, indent=2))
    for r in rep["per_clip"]:
        bits = [f"{k}={r[k]}" for k in ("sid_recall", "sid_precision", "sid_f1", "time_iou") if k in r]
        flag = "" if r["matched"] else "  ✗未匹配"
        print(f"  {r['title'][:30]:30}  {' '.join(bits)}{flag}", file=sys.stderr)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[done] 报告 → {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
