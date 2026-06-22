#!/usr/bin/env python3
"""分阶段评测 · 从「种子端到端 golden」派生各阶段 golden 的种子/草稿（可复现）。

设计真源：doc/plan/视频剪辑skill-第二环选片-分阶段评测-plan.md §5（P0/P4/P5）。
配套：build_inputs.py 派生各阶段 input.json；本脚本派生各阶段 golden.json 的种子。

派生口径（铁律：只把「能从已认可数据机械推导」的当正式金标准，其余只当草稿）：
  ② 总编 2_body_edit   ← 直接复用种子 golden 里每条 clip 的 segments（这是「已认可端到端
                          golden」的正文决策，原地复用即正式金标准）。   ✅ 正式
  ④ 钩子 4_hook        ← 用 hook_options 当「可接受集合」草稿；best_stitched 取首条、
                          must_keep_terms 留空 —— 这两项必须 owner 人工补，故标 draft。 ⚠ 草稿
  ① 选题 1_topic_select← 用 clip 的 title/论点/受众/orig_keep_sids 拼草稿；hit_dims/why
                          种子里没有，留空待补 —— 故标 draft，需 owner 拍板。        ⚠ 草稿
  ③ 去口水 3_refine    ← 种子 golden 的 deletions 已失效（refine_stale），无法派生 → 留 TODO。
  ⑤ 去重 5_dedup       ← 本数据集无冻结去重答案 → 留 TODO（需 owner 标 groups/drop/keep）。

安全：只覆盖「占位符」或「本脚本上次派生（带 _seeded）」的 golden，绝不覆盖 owner 已冻结
（即手工编辑过、去掉 _seeded 标记）的金标准。

用法:
  python3 seed_golden.py --dataset agent_eval_0613
  python3 seed_golden.py --dataset agent_eval_0613 --force   # 连 owner 冻结的也重派生（慎用）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PLACEHOLDER = "待填 · TODO_FILL_GOLDEN"


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _can_write(path: Path, force: bool) -> bool:
    """只在占位 / 本脚本派生 / --force 时落盘；owner 冻结过的不动。"""
    if force or not path.exists():
        return True
    txt = path.read_text(encoding="utf-8")
    if PLACEHOLDER in txt:
        return True
    try:
        return bool(json.loads(txt).get("_seeded"))
    except json.JSONDecodeError:
        return False


def _write(stage_dir: Path, payload: dict, force: bool, tag: str) -> bool:
    g = stage_dir / "golden.json"
    if not _can_write(g, force):
        print(f"    · {stage_dir.name}/golden.json 已被 owner 冻结，跳过（--force 可覆盖）",
              file=sys.stderr)
        return False
    _dump(g, payload)
    print(f"    ✓ {stage_dir.name}/golden.json ← {tag}", file=sys.stderr)
    return True


def seed(dataset: str, force: bool) -> None:
    ds = EVAL_DIR / "fixtures" / dataset
    seed_golden = ds / "golden.json"
    if not seed_golden.exists():
        print(f"[seed] 找不到种子 {seed_golden}", file=sys.stderr)
        raise SystemExit(2)
    clips = json.loads(seed_golden.read_text(encoding="utf-8")).get("clips", [])
    for i, c in enumerate(clips, 1):
        c.setdefault("idx", i)
    stages = ds / "stages"
    print(f"[seed] dataset={dataset} | {len(clips)} 条种子 clip", file=sys.stderr)

    # ② 总编 —— 正式金标准（原地复用 segments）────────────────────────────
    body_items = [{
        "idx": c["idx"],
        "segments": [{"role": s.get("role", "evidence"),
                      "sids": [int(s["sids"][0]), int(s["sids"][-1])],
                      "reason": s.get("reason", "")}
                     for s in c.get("segments", []) if s.get("sids")],
    } for c in clips]
    _write(stages / "2_body_edit", {
        "_status": "已派生 · 总编金标准原地复用（来自已认可端到端 golden 的 segments）",
        "_seeded": True,
        "_contract": "eval/contracts/2_body_edit.md",
        "_note": "这是正式金标准：segments 来自上一轮已认可的端到端 golden。owner 如需修订，"
                 "直接编辑本文件并删掉 _seeded 字段即可冻结（再跑 seed_golden 不会覆盖）。",
        "items": body_items,
    }, force, "种子 golden.segments（正式）")

    # ④ 钩子 —— 草稿（acceptable 来自 hook_options；best/must_keep 待人工）──────
    hook_items = []
    for c in clips:
        acceptable = [{
            "stitched": h.get("stitched", ""),
            "fragments": [{"sid": fr.get("sid"), "text": fr.get("text", "")}
                          for fr in h.get("fragments", [])],
            "strategy": h.get("strategy", ""),
        } for h in c.get("hook_options", [])]
        hook_items.append({
            "idx": c["idx"],
            "acceptable": acceptable,
            "best_stitched": acceptable[0]["stitched"] if acceptable else "",
            "must_keep_terms": [],
        })
    _write(stages / "4_hook", {
        "_status": "草稿 · 待 owner 核（acceptable 来自 AI hook_options；best/must_keep_terms 需人工）",
        "_seeded": True,
        "_contract": "eval/contracts/4_hook.md",
        "_note": "钩子无唯一答案：本草稿把 AI 跑出的 hook_options 当可接受集合种子。owner 需："
                 "①确认/增删 acceptable；②挑 best_stitched；③补 must_keep_terms（这条题不许丢的"
                 "限定词/数字）。改完删 _seeded 即冻结。",
        "items": hook_items,
    }, force, "种子 hook_options（草稿）")

    # ① 选题 —— 草稿（hit_dims/why 待人工补）───────────────────────────────
    topic_items = []
    for c in clips:
        rough = c.get("orig_keep_sids") or c.get("keep_sids") or []
        topic_items.append({
            "idx": c["idx"],
            "title": c.get("title", ""),
            "one_argument": c.get("one_argument", ""),
            "hook_line": c.get("hook_line", ""),
            "audience": c.get("audience", ""),
            "mainstream": c.get("mainstream", ""),
            "hit_dims": c.get("hit_dims") or [],
            "rough_sid_spans": [[int(s[0]), int(s[-1])] for s in rough
                                if isinstance(s, (list, tuple)) and len(s) >= 2],
            "why": c.get("why", ""),
        })
    _write(stages / "1_topic_select", {
        "_status": "草稿 · 待 owner 拍板（hit_dims/why 种子里没有，需人工补；条数/标题等可先自动评）",
        "_seeded": True,
        "_contract": "eval/contracts/1_topic_select.md",
        "_note": "选题该不该选要 owner 拍板。本草稿从种子 clip 拼出标题/论点/受众/rough_sid_spans，"
                 "但 hit_dims（命中富集维度·≥3）和 why 种子里没有 → 留空，硬规则评分会如实标红，"
                 "提示这些字段待补。补全并拍板后删 _seeded 冻结。",
        "items": topic_items,
    }, force, "种子 clip 字段（草稿）")

    # ③ 去口水 / ⑤ 去重 —— 无法机械派生，留 TODO 占位（不动 owner 已填的）───────
    for stage, why in (("3_refine_deduct", "种子 golden 的 deletions 已失效(refine_stale)，无法派生"),
                       ("5_dedup_merge", "本数据集无冻结去重答案，需 owner 标 groups/drop/keep")):
        g = stages / stage / "golden.json"
        if g.exists() and PLACEHOLDER not in g.read_text(encoding="utf-8"):
            try:
                if not json.loads(g.read_text(encoding="utf-8")).get("_seeded"):
                    print(f"    · {stage}/golden.json 已有 owner 内容，跳过", file=sys.stderr)
                    continue
            except json.JSONDecodeError:
                pass
        print(f"    ⏭ {stage}/golden.json 留 TODO（{why}）", file=sys.stderr)

    print("[seed] 完成。② 已是正式金标准；①④ 为草稿待补；③⑤ 待 owner 重建。", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="从种子端到端 golden 派生各阶段 golden 种子/草稿")
    ap.add_argument("--dataset", default="agent_eval_0613")
    ap.add_argument("--force", action="store_true", help="连 owner 冻结的也重派生（慎用）")
    a = ap.parse_args()
    seed(a.dataset, a.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
