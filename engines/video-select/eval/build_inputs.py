#!/usr/bin/env python3
"""分阶段评测 · 派生各阶段 input.json（可复现·可追溯）。

设计真源：doc/plan/视频剪辑skill-第二环选片-分阶段评测-plan.md
每阶段的输入契约：eval/contracts/<N_stage>.md

【数据血缘 · 铁律】每个阶段的输入 = 上一阶段「已认可的金标准」重塑而来：
  ① 选题   input ← 源 words.json（整场逐字稿）
  ② 总编   input ← ①金标准（选题清单）
  ③ 去口水 input ← ②金标准（正文 segments 展开成逐句）
  ④ 钩子   input ← ①金标准（选题）+ ②金标准（正文，决定候选池）
  ⑤ 去重   input ← ②③④金标准组装出的整批 clip 摘要
金标准没填好之前，本脚本用「种子」(--seed，默认 fixtures/<ds>/golden.json 这份旧端到端
金标准，含全部中间产物) 兜底派生，让 owner 先看到每阶段输入长什么样；金标准填好后
重跑本脚本即从认可的金标准派生（--chained），输入随之刷新——这就是可追溯：input 永远
是某个明确上游的函数，不是手�-写的孤儿数据。

输入忠实于真实提示词所见（对齐 video_select/generate.py 与 dedup.py 的取数逻辑）：
  ② = {title,one_argument,hook_line,audience,mainstream} + 全场句（共享 words.json）
  ③ = 【正文逐句】每行 #sid text（segments 的 sids 逐句展开）
  ④ = {title,one_argument,audience} + 候选池（正文±3 ∪ 原选段±2，= generate._hook_view）
  ⑤ = 整批 [{idx,title,one_argument,script_raw}]（= dedup._clip_summary 的结构化版）

用法:
  python3 build_inputs.py --dataset agent_eval_0613
  python3 build_inputs.py --dataset agent_eval_0613 --chained   # 金标准填好后，从金标准派生
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ENGINE_DIR = EVAL_DIR.parent
sys.path.insert(0, str(ENGINE_DIR / "video_select"))

from video_select import _deps  # noqa: E402,F401  挂 video-slicer 到 sys.path
from video_select import generate as gen  # noqa: E402  复用真实取数逻辑
from video_slicer.transcribe import segment  # noqa: E402

STAGES = ["1_topic_select", "2_body_edit", "3_refine_deduct", "4_hook", "5_dedup_merge"]
PLACEHOLDER = "待填 · TODO_FILL_GOLDEN"


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_golden_placeholder(stage_dir: Path, stage: str) -> None:
    """金标准占位：只在缺失时建，绝不覆盖 owner 已填的内容。"""
    g = stage_dir / "golden.json"
    if g.exists():
        txt = g.read_text(encoding="utf-8")
        if PLACEHOLDER not in txt:
            print(f"    · {stage}/golden.json 已有内容，跳过（不覆盖）", file=sys.stderr)
            return
    _dump(g, {
        "_status": PLACEHOLDER,
        "_contract": f"eval/contracts/{stage}.md",
        "_note": "金标准由 owner 整理后填入；字段与判分口径见 _contract。填好后重跑 build_inputs.py --chained。",
        "items": [],
    })


def build(dataset: str, chained: bool, seed_path: str | None) -> None:
    ds_dir = EVAL_DIR / "fixtures" / dataset
    words = ds_dir / "words.json"
    seed = Path(seed_path) if seed_path else ds_dir / "golden.json"
    stages_dir = ds_dir / "stages"

    _, sents = segment.sentences_from_wordfile(str(words), host="张和")
    sid_text = {s.sid: s.text for s in sents}

    # clips 来源：--chained 时优先各阶段已填金标准；否则用种子 golden.json 兜底
    seed_clips = json.loads(seed.read_text(encoding="utf-8")).get("clips", []) if seed.exists() else []
    for i, c in enumerate(seed_clips, 1):
        c.setdefault("idx", i)
    src_tag = "种子 golden.json（旧端到端·未认可）" if not chained else "上游金标准（--chained）"
    print(f"[build] dataset={dataset} | {len(sents)}句 | {len(seed_clips)}条候选 | 取数={src_tag}",
          file=sys.stderr)

    def upstream_clips(stage_golden: str) -> list[dict]:
        """chained 模式：从指定上游阶段的 golden 取 clips；没填好则回退种子。"""
        if chained:
            g = stages_dir / stage_golden / "golden.json"
            if g.exists():
                data = json.loads(g.read_text(encoding="utf-8"))
                if PLACEHOLDER not in g.read_text(encoding="utf-8") and data.get("items"):
                    return data["items"]
            print(f"    ⚠ {stage_golden}/golden.json 未填，回退种子派生", file=sys.stderr)
        return seed_clips

    # ── ① 选题：输入 = 整场逐字稿（指针 + 内联可读副本头部）────────────
    s1 = stages_dir / "1_topic_select"
    _dump(s1 / "input.json", {
        "_stage": "1_topic_select",
        "_desc": "选题吃整场编号逐字稿；输入就是源 words.json（每行 #sid [说话人] 文本）。",
        "source_words": "../../words.json",
        "host": "张和",
        "n_sentences": len(sents),
        "sample_head": [{"sid": s.sid, "speaker": s.speaker, "text": s.text}
                        for s in sents[:5]],
    })
    _write_golden_placeholder(s1, "1_topic_select")

    # ── ② 总编：每条选题 5 字段 + 共享全场句 ─────────────────────────
    topics = upstream_clips("1_topic_select")
    s2_items = [{
        "idx": c.get("idx"),
        "title": c.get("title", ""),
        "one_argument": c.get("one_argument", ""),
        "hook_line": c.get("hook_line", ""),
        "audience": c.get("audience", ""),
        "mainstream": c.get("mainstream", ""),
    } for c in topics]
    s2 = stages_dir / "2_body_edit"
    _dump(s2 / "input.json", {
        "_stage": "2_body_edit",
        "_desc": "每条选题独立喂总编：给这 5 个字段 + 全场编号句（共享 ../../words.json）。"
                 "逐条循环，每条一次 LLM 调用。",
        "shared_full_transcript": "../../words.json",
        "topics": s2_items,
    })
    _write_golden_placeholder(s2, "2_body_edit")

    # ── ③ 去口水：每条 clip 的【正文逐句】（segments 的 sids 逐句展开）──
    bodies = upstream_clips("2_body_edit")
    s3_items = []
    for c in bodies:
        lines = []
        for seg in c.get("segments", []):
            sids = seg.get("sids")
            if not sids:
                continue
            for sid in range(sids[0], sids[-1] + 1):
                if sid in sid_text:
                    lines.append({"sid": sid, "text": sid_text[sid]})
        s3_items.append({"idx": c.get("idx"), "title": c.get("title", ""), "body_lines": lines})
    s3 = stages_dir / "3_refine_deduct"
    _dump(s3 / "input.json", {
        "_stage": "3_refine_deduct",
        "_desc": "在冻结的正文逐句上做字级去口水决策；顺序/去留已由总编定死，只标删哪些字。",
        "clips": s3_items,
    })
    _write_golden_placeholder(s3, "3_refine_deduct")

    # ── ④ 钩子：{标题/论点/受众} + 候选池（= generate._hook_view）──────
    s4_items = []
    for c in bodies:
        body = [{"sids": seg["sids"], "span": seg.get("span", [0, 0])}
                for seg in c.get("segments", []) if seg.get("sids")]
        view = gen._hook_view(sents, body, extra_spans=c.get("orig_keep_sids"))
        pool = [{"sid": int(line.split(" ", 1)[0][1:]), "text": line.split(" ", 1)[1]}
                for line in view.splitlines() if line.startswith("#") and " " in line]
        s4_items.append({
            "idx": c.get("idx"),
            "title": c.get("title", ""),
            "one_argument": c.get("one_argument", ""),
            "audience": c.get("audience", ""),
            "candidate_pool": pool,
        })
    s4 = stages_dir / "4_hook"
    _dump(s4 / "input.json", {
        "_stage": "4_hook",
        "_desc": "给论点+受众+候选原话池，产 2-3 个开场钩子。候选池=正文覆盖句±3 ∪ 原选段±2。",
        "clips": s4_items,
    })
    _write_golden_placeholder(s4, "4_hook")

    # ── ⑤ 去重：整批 clip 摘要（idx/标题/论点/选段原文）────────────────
    batch = upstream_clips("2_body_edit")
    s5_items = [{
        "idx": c.get("idx"),
        "title": c.get("title", ""),
        "one_argument": c.get("one_argument", ""),
        "script_raw": (c.get("script_raw") or "").strip(),
    } for c in batch]
    s5 = stages_dir / "5_dedup_merge"
    _dump(s5 / "input.json", {
        "_stage": "5_dedup_merge",
        "_desc": "整批一次性喂去重器，找讲同一观点/高度重叠的，产 merge/drop/keep 动作。",
        "batch": s5_items,
    })
    _write_golden_placeholder(s5, "5_dedup_merge")

    print(f"[done] 5 阶段 input.json 已写入 {stages_dir}/ ；golden.json 占位已就位（不覆盖已填）。",
          file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="派生各阶段评测 input.json")
    ap.add_argument("--dataset", default="agent_eval_0613")
    ap.add_argument("--seed", default=None, help="种子 golden（默认 fixtures/<ds>/golden.json）")
    ap.add_argument("--chained", action="store_true",
                    help="从各阶段已填金标准派生下游输入（金标准填好后用）")
    a = ap.parse_args()
    build(a.dataset, a.chained, a.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
