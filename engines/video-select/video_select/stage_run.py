#!/usr/bin/env python3
"""单阶段测试口（stage runner）—— 从冻结 input.json 单跑某一个中间阶段，输出落盘。

为什么要它：generate.py 把②总编→③去口水→④钩子在一次内存里连跑，中间产物不落盘、不可
单独喂输入，所以没法「单测某一道工序」。本模块在不破坏一条龙的前提下，额外开 3 个测试口：
喂一份冻结的上游金标准（input.json），只跑这一阶段，产出对齐评分器的 <stage>.json。
①选题用 topics.py、⑤去重用 dedup.py 本就能单跑，不在此处。

落盘格式（对齐 eval/scorers/<stage>.py 期望）：
  body_edit    → {"items":[{idx, segments:[{role,sids,reason}]}]}
  refine_deduct→ {"items":[{idx, deletions:[{sid,text,kind,verbatim}]}]}
  hook         → {"items":[{idx, hooks:[{stitched,fragments,strategy,why}]}]}

设计真源：doc/plan/视频剪辑skill-第二环选片-分阶段评测-plan.md §4.1。
注意：要真调 LLM。按 memory「发布/转录走本地出口」，跑前请确保出口已就位（route-bypass）。

用法:
  python3 -m video_select.stage_run --stage body_edit \\
      --input eval/fixtures/agent_eval_0613/stages/2_body_edit/input.json \\
      --words words.json --out runs/<x>/2_body_edit.json [--providers kimi,minimax] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import _deps  # noqa: F401  挂 video-slicer
from ._deps import load_prompt
from . import generate as gen

from video_slicer.transcribe import segment  # noqa: E402
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402


def _runs(sids: list[int]) -> list[list[int]]:
    """把一串 sid 压成连续闭区间 [[a,b],...]（去口水/钩子从逐句还原正文段用）。"""
    if not sids:
        return []
    sids = sorted(set(sids))
    out, lo, prev = [], sids[0], sids[0]
    for s in sids[1:]:
        if s == prev + 1:
            prev = s
            continue
        out.append([lo, prev]); lo = prev = s
    out.append([lo, prev])
    return out


def _body_from_sids(sids: list[int], sents) -> list[dict]:
    return [{"role": "evidence", "sids": [a, b],
             "span": [round(sents[a].start, 2), round(sents[b].end, 2)]}
            for a, b in _runs(sids)]


# ───────────────────────── ② 总编 ─────────────────────────
def run_body_edit(inp: dict, sents, full_view: str, providers, limit) -> list[dict]:
    items = []
    topics = inp.get("topics", [])[: limit or None]
    for t in topics:
        body, _ = gen.select_body(t, sents, full_view, providers=providers)
        items.append({"idx": t.get("idx"),
                      "segments": [{"role": s["role"], "sids": s["sids"], "reason": s.get("reason", "")}
                                   for s in body]})
        print(f"  ② idx={t.get('idx')} → {len(body)}段", file=sys.stderr)
    return items


# ───────────────────────── ③ 去口水 ─────────────────────────
def run_refine_deduct(inp: dict, sents, providers, limit) -> list[dict]:
    items = []
    for c in inp.get("clips", [])[: limit or None]:
        sids = [ln["sid"] for ln in c.get("body_lines", []) if "sid" in ln]
        body = _body_from_sids(sids, sents)
        deletions, _ = gen.deduct_disfluency(body, sents, providers=providers)
        items.append({"idx": c.get("idx"), "deletions": deletions})
        print(f"  ③ idx={c.get('idx')} → 删 {len(deletions)} 处", file=sys.stderr)
    return items


# ───────────────────────── ④ 钩子 ─────────────────────────
def run_hook(inp: dict, sents, providers, limit) -> list[dict]:
    """从冻结候选池直接产钩子（faithful：不重算 _hook_view，用 input 里冻结的 candidate_pool）。"""
    items = []
    for c in inp.get("clips", [])[: limit or None]:
        pool = c.get("candidate_pool", [])
        view = "\n".join(f"#{p['sid']} {p.get('text','')}" for p in pool if "sid" in p)
        user = (f"标题：{c.get('title','')}\n论点：{c.get('one_argument','')}\n"
                f"目标受众：{c.get('audience','')}\n\n【候选原话句】\n{view}")
        client = OpenAICompatibleClient(providers=providers)
        data = gen._chat_json_retry(client, [
            {"role": "system", "content": load_prompt("hook")},
            {"role": "user", "content": user}], 0.4)
        pool_text = {p["sid"]: p.get("text", "") for p in pool if "sid" in p}
        hooks = []
        for h in data.get("hooks", []) or []:
            frags = []
            for fr in h.get("fragments", []) or []:
                txt = (fr.get("text") or "").strip()
                rng = gen._parse_sid_range(fr.get("sid"))
                if not txt or rng is None:
                    continue
                a, b = rng
                src = "".join(pool_text.get(i, "") for i in range(a, b + 1))
                verbatim = txt in src or re.sub(r"\s", "", txt) in re.sub(r"\s", "", src)
                frags.append({"sid": a if a == b else f"{a}-{b}", "text": txt, "verbatim": verbatim})
            if not frags:
                continue
            stitched = (h.get("stitched") or "".join(f["text"] for f in frags)).strip()
            hooks.append({"stitched": stitched, "fragments": frags,
                          "strategy": str(h.get("strategy", ""))[:20], "why": str(h.get("why", ""))[:200]})
        items.append({"idx": c.get("idx"), "hooks": hooks})
        print(f"  ④ idx={c.get('idx')} → {len(hooks)} 个钩子", file=sys.stderr)
    return items


STAGES = {"body_edit": run_body_edit, "refine_deduct": run_refine_deduct, "hook": run_hook}


def main() -> int:
    ap = argparse.ArgumentParser(prog="stage_run", description="单阶段测试口：从冻结 input 单跑某阶段")
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--input", required=True, help="该阶段冻结 input.json")
    ap.add_argument("--words", required=True, help="words.json（句号↔时间/原文真源）")
    ap.add_argument("--out", required=True, help="输出 <stage>.json")
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    inp = json.loads(Path(a.input).read_text(encoding="utf-8"))
    _, sents = segment.sentences_from_wordfile(a.words, host=a.host)
    print(f"[stage_run] {a.stage} | {len(sents)}句", file=sys.stderr)
    if a.stage == "body_edit":
        items = run_body_edit(inp, sents, gen.render_full(sents), providers, a.limit)
    else:
        items = STAGES[a.stage](inp, sents, providers, a.limit)
    out = {"_stage": a.stage, "_input": a.input, "items": items}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] {len(items)} 条 → {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
