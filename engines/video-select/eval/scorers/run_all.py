#!/usr/bin/env python3
"""分阶段评测 · 一键跑全部可评阶段（金标准已填的）。

对一个数据集，遍历 5 个阶段：金标准已填 → 调对应评分器；候选默认用同目录金标准做**自比对
冒烟**（golden vs golden 应满分，证明评分器接线正确），也可指定一份候选产出对照。

用法:
  python3 run_all.py --dataset agent_eval_0613                 # 自比对冒烟（全绿=接线对）
  python3 run_all.py --dataset agent_eval_0613 --candidate-dir <run>   # 拿真候选对照
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

SCORERS_DIR = Path(__file__).resolve().parent
EVAL_DIR = SCORERS_DIR.parent
STAGES = ["1_topic_select", "2_body_edit", "3_refine_deduct", "4_hook", "5_dedup_merge"]


def _load(stage: str):
    spec = importlib.util.spec_from_file_location(f"scorer_{stage}", SCORERS_DIR / f"{stage}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _filled(p: Path) -> bool:
    if not p.exists():
        return False
    txt = p.read_text(encoding="utf-8")
    if "待填 · TODO_FILL_GOLDEN" in txt:
        return False
    d = json.loads(txt)
    return bool(d.get("items") or d.get("groups") or d.get("drop"))


def run(dataset: str, candidate_dir: str | None) -> int:
    base = EVAL_DIR / "fixtures" / dataset / "stages"
    print(f"=== 分阶段评测 · {dataset} ===")
    any_run = False
    for stage in STAGES:
        sd = base / stage
        golden, inp = sd / "golden.json", sd / "input.json"
        if not _filled(golden):
            print(f"[{stage}] ⏭ 金标准未填，跳过")
            continue
        any_run = True
        cand = Path(candidate_dir) / f"{stage}.json" if candidate_dir else golden
        cand = cand if cand.exists() else golden
        tag = "自比对冒烟" if cand == golden else f"vs {cand}"
        mod = _load(stage)
        try:
            if stage == "1_topic_select":
                n = json.loads(inp.read_text(encoding="utf-8")).get("n_sentences") if inp.exists() else None
                rep = mod.score(str(cand), str(golden), n)
            elif stage == "2_body_edit":
                rep = mod.score(str(golden), str(cand))
            elif stage == "3_refine_deduct":
                rep = mod.score(str(golden), str(cand), str(inp) if inp.exists() else None)
            elif stage == "4_hook":
                rep = mod.score(str(cand), str(golden), str(inp) if inp.exists() else None)
            elif stage == "5_dedup_merge":
                rep = mod.score(str(golden), json.loads(Path(cand).read_text("utf-8")),
                                str(inp) if inp.exists() else None)
            bits = " ".join(f"{k}={v}" for k, v in rep["summary"].items())
            print(f"[{stage}] {tag}: {bits}")
        except Exception as e:  # noqa: BLE001
            print(f"[{stage}] ✗ 评分器报错：{e}")
    if not any_run:
        print("（无任何阶段金标准已填）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="run_all", description="一键跑全部可评阶段")
    ap.add_argument("--dataset", default="agent_eval_0613")
    ap.add_argument("--candidate-dir", default=None,
                    help="候选产出目录（每阶段 <stage>.json）；不给则自比对冒烟")
    a = ap.parse_args()
    return run(a.dataset, a.candidate_dir)


if __name__ == "__main__":
    raise SystemExit(main())
