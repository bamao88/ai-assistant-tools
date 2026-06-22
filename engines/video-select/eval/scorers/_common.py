#!/usr/bin/env python3
"""评分器公共库 —— 各阶段评分器共用的小工具。

设计真源：doc/plan/视频剪辑skill-第二环选片-分阶段评测-plan.md §4.2 / eval/README §5。

只放纯函数：集合 P/R/F1、字符集合、按 idx/标题对齐、读 golden/候选。
LLM 评委（主观维度）封装单独放 judge.py，本库不依赖网络。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PLACEHOLDER = "待填 · TODO_FILL_GOLDEN"


# ───────────────────────── 读文件 ─────────────────────────
def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def is_filled(path: str | Path) -> bool:
    """golden 是否已填（非占位、items/groups 非空）。"""
    p = Path(path)
    if not p.exists():
        return False
    txt = p.read_text(encoding="utf-8")
    if PLACEHOLDER in txt:
        return False
    d = json.loads(txt)
    return bool(d.get("items") or d.get("groups") or d.get("drop") or d.get("clips"))


def load_items(path: str | Path) -> list[dict]:
    """统一取「逐条记录」：golden 用 items；run 产物用 clips。"""
    d = load_json(path)
    return d.get("items") or d.get("clips") or []


def by_idx(items: list[dict]) -> dict[int, dict]:
    return {int(it["idx"]): it for it in items if it.get("idx") is not None}


# ───────────────────────── 指标 ─────────────────────────
def prf(gold: set, cand: set) -> dict:
    """集合 P/R/F1。gold=金标准该选的；cand=候选选的。"""
    if not gold and not cand:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0}
    tp = len(gold & cand)
    fp = len(cand - gold)
    fn = len(gold - cand)
    prec = tp / (tp + fp) if (tp + fp) else (1.0 if not gold else 0.0)
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    return {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
            "tp": tp, "fp": fp, "fn": fn}


def mean(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 3) if xs else 0.0


# ───────────────────────── 文本 ─────────────────────────
def norm(s: str) -> str:
    """归一化：去空白，用于子串/字符集合比较（口语转写空格不稳定）。"""
    return re.sub(r"\s+", "", s or "")


def char_multiset(s: str) -> dict[str, int]:
    """字符 → 计数（删除字符按多重集算，避免重复字相互抵消）。"""
    out: dict[str, int] = {}
    for ch in norm(s):
        out[ch] = out.get(ch, 0) + 1
    return out


def multiset_prf(gold_ms: dict[str, int], cand_ms: dict[str, int]) -> dict:
    """多重集 P/R/F1（字符级删除对比用）。"""
    tp = sum(min(gold_ms.get(k, 0), cand_ms.get(k, 0)) for k in set(gold_ms) | set(cand_ms))
    g = sum(gold_ms.values())
    c = sum(cand_ms.values())
    prec = tp / c if c else (1.0 if g == 0 else 0.0)
    rec = tp / g if g else 1.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    return {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
            "tp": tp, "gold_chars": g, "cand_chars": c}


def span_set(spans) -> set[int]:
    """[[a,b],...] / [a,b] → 句号集合（闭区间展开）。"""
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


# ───────────────────────── 报告 ─────────────────────────
def banner(stage: str, summary: dict) -> str:
    bits = " ".join(f"{k}={v}" for k, v in summary.items())
    return f"[score:{stage}] {bits}"
