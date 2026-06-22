#!/usr/bin/env python3
"""① 选题 评分器 —— 硬规则（纯代码）+ 覆盖率（LLM 评委，可选）。

契约：eval/contracts/1_topic_select.md。选题「该不该选」无唯一答案，分两层：
  · 硬规则（代码·自动）：标题 ≤20 字且含 AI/产品名；hit_dims≥3 且在 5 维集合内；
    rough_sid_spans 落在 [0,n)；条数 18–25。本器只跑这层（秒出、可回归）。
  · 覆盖率（LLM 评委 + 人工抽检）：候选 vs 金标准按语义对齐算召回/精确。需 --judge 且配好
    评委（judge.py），默认不跑（留接口）。

注意：金标准本身也会过硬规则——若金标准缺 hit_dims（草稿态），这层会如实标红，提示该字段
待 owner 补全，这是正确信号而非 bug。

用法:
  python3 1_topic_select.py --candidate <run topics.json|golden>   # 只硬规则自检
  python3 1_topic_select.py --golden g.json --candidate c.json     # 加金标准对照（条数/覆盖留待评委）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

STAGE = "1_topic_select"
DIMS = {"数据", "转变故事", "金句", "权威背书", "戳痛点"}
# 标题须含的「AI/产品名」线索（命中其一即算）
AI_HINTS = re.compile(r"(AI|Agent|GPT|大模型|模型|Codex|Cursor|Claude|MCP|Excel|低代码|"
                      r"自动驾驶|评测|多轮|skill|prompt|DeepSeek|工作流|算法|智能)", re.I)
TITLE_MAX = 20
COUNT_LO, COUNT_HI = 18, 25


def check_item(it: dict, n_sentences: int | None) -> list[str]:
    bad = []
    title = it.get("title", "")
    if len(title) > TITLE_MAX:
        bad.append(f"标题 {len(title)}字 >{TITLE_MAX}")
    if not AI_HINTS.search(title):
        bad.append("标题缺 AI/产品名线索")
    dims = it.get("hit_dims") or []
    if len(dims) < 3:
        bad.append(f"hit_dims={len(dims)}<3")
    bad_dims = [d for d in dims if d not in DIMS]
    if bad_dims:
        bad.append(f"hit_dims 越界 {bad_dims}")
    if n_sentences:
        for sp in it.get("rough_sid_spans") or []:
            if isinstance(sp, (list, tuple)) and len(sp) >= 2:
                if not (0 <= int(sp[0]) <= int(sp[-1]) < n_sentences):
                    bad.append(f"rough_sid_spans 越界 {sp}（合法 0..{n_sentences-1}）")
    return bad


def score(candidate_path: str, golden_path: str | None = None,
          n_sentences: int | None = None) -> dict:
    items = C.load_items(candidate_path)
    # 若给了 stage1 input.json，从中读 n_sentences
    rows, n_clean = [], 0
    for i, it in enumerate(items):
        bad = check_item(it, n_sentences)
        rows.append({"idx": it.get("idx", i + 1), "title": it.get("title", "")[:24],
                     "violations": bad})
        if not bad:
            n_clean += 1
    count_ok = COUNT_LO <= len(items) <= COUNT_HI
    summary = {"n_topics": len(items), "count_in_range": count_ok,
               "hard_rule_clean": n_clean, "hard_rule_total": len(items),
               "hard_rule_pass_rate": C.mean([1.0 if not r["violations"] else 0.0 for r in rows])}
    rep = {"stage": STAGE, "candidate": str(candidate_path), "summary": summary, "per_topic": rows}
    if golden_path and C.is_filled(golden_path):
        rep["coverage"] = {"_note": "语义覆盖率需 LLM 评委（judge.py），见 contracts §覆盖率；本器未跑。",
                           "golden_topics": len(C.load_items(golden_path))}
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(prog="score:1_topic_select")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--golden", default=None)
    ap.add_argument("--input", default=None, help="stage1 input.json：取 n_sentences 做越界检查")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    n = None
    if a.input:
        n = C.load_json(a.input).get("n_sentences")
    rep = score(a.candidate, a.golden, n)
    print(C.banner(STAGE, rep["summary"]))
    for r in rep["per_topic"]:
        if r["violations"]:
            print(f"  ✗ idx={r['idx']} {r['title']}: {'; '.join(r['violations'])}", file=sys.stderr)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
