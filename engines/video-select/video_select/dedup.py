#!/usr/bin/env python3
"""批量去重/合并（流程二之后）—— 对整批已生成切片做内容级去重。

思路来自 videocut-zh「多候选 → 去重合并」，但落点在流程二**之后**：等每条选题都
跑出了「实际切什么内容」，再让大模型对整批 clip 做内容级去重/合并，比基于粗区间判断更准。

流程：读 golden_candidate.json → 组装整批 clip 摘要（标题/论点/选段原文）→ 调
dedup-merge.md 拿动作表（merge/drop/keep）→ 应用动作（merge 取被合并 clip 的 segments
并集，复用 gates.merge_segments 精选合并重算）→ 写 golden_dedup.json + 重渲 candidates/。

用法:
  python -m video_select.dedup --golden <dir>/golden_candidate.json --words words.json --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import _deps  # noqa: F401  挂 video-slicer 到 sys.path
from ._deps import load_prompt
from . import gates
from . import generate as gen  # 复用 write_review_md

from video_slicer.transcribe import segment  # noqa: E402
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402


def _clip_summary(clips: list[dict]) -> str:
    """整批 clip 摘要喂给去重器：序号 + 标题 + 论点 + 实际选段原文。"""
    blocks = []
    for c in clips:
        idx = c.get("idx")
        body = (c.get("script_raw") or "").strip()
        blocks.append(
            f"### idx={idx}｜{c.get('title','')}\n"
            f"论点：{c.get('one_argument','')}\n"
            f"选段原文：\n{body}")
    return "\n\n".join(blocks)


def _merge_clip(members: list[dict], title: str, one_argument: str, sents) -> dict:
    """把几条 clip 合并成一条：segments 取并集 → gates.merge_segments 精选合并 → 重算派生字段。"""
    raw_segs = []
    for m in members:
        for s in m.get("segments", []):
            raw_segs.append({"role": s.get("role", "evidence"), "sids": s.get("sids", []),
                             "reason": s.get("reason", "")})
    body = gates.merge_segments(raw_segs, sents)
    keep_sids = [s["sids"] for s in body]
    time_spans = [s["span"] for s in body]
    est_dur = round(sum(e - s for s, e in time_spans), 1)
    script_raw = "\n".join(s["text"] for s in body)
    head = members[0]
    # 去口水决策合并（sid 是绝对句号，合并后仍有效）：按 (sid,text) 去重
    seen, deletions = set(), []
    for m in members:
        for d in m.get("deletions", []) or []:
            key = (d.get("sid"), d.get("text"))
            if key not in seen:
                seen.add(key)
                deletions.append(d)
    merged = dict(head)
    merged.update({
        "title": title or head.get("title", ""),
        "one_argument": one_argument or head.get("one_argument", ""),
        "segments": body, "keep_sids": keep_sids, "time_spans": time_spans,
        "est_dur": est_dur, "script_raw": script_raw, "deletions": deletions,
        "hook_options": head.get("hook_options", []),   # 沿用主条钩子（合并后可下一轮重跑）
        "dedup_merged_from": [m.get("idx") for m in members],
    })
    return merged


def apply_actions(clips: list[dict], actions: list[dict], sents) -> tuple[list[dict], dict]:
    """按动作表产出去重后的 clip 列表（保留原始顺序），并返回统计。"""
    by_idx = {c.get("idx"): c for c in clips if c.get("idx") is not None}
    drop_set: set[int] = set()
    group_of: dict[int, int] = {}          # idx -> 组号
    groups: list[dict] = []                # {idxs,title,one_argument}
    for a in actions or []:
        t = a.get("type")
        if t == "drop":
            i = a.get("idx")
            if i in by_idx:
                drop_set.add(i)
        elif t == "merge":
            idxs = [i for i in (a.get("idxs") or []) if i in by_idx]
            idxs = [i for i in idxs if i not in group_of and i not in drop_set]
            if len(idxs) < 2:
                continue
            g = len(groups)
            groups.append({"idxs": idxs, "title": a.get("title", ""),
                           "one_argument": a.get("one_argument", "")})
            for i in idxs:
                group_of[i] = g
        # keep: 无需登记，下面默认保留

    out, emitted, n_merged, n_dropped = [], set(), 0, 0
    for c in clips:
        i = c.get("idx")
        if i in drop_set:
            n_dropped += 1
            continue
        if i in group_of:
            g = group_of[i]
            if g in emitted:
                continue
            emitted.add(g)
            grp = groups[g]
            members = [by_idx[j] for j in grp["idxs"]]
            out.append(_merge_clip(members, grp["title"], grp["one_argument"], sents))
            n_merged += len(members)
        else:
            out.append(c)
    # 重新编号（顺序保留）
    for new_idx, c in enumerate(out, 1):
        c["idx"] = new_idx
    stats = {"before": len(clips), "after": len(out),
             "groups": len(groups), "merged_clips": n_merged, "dropped": n_dropped}
    return out, stats


def run(golden_path, words_json, out_dir, host="张和", providers=None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    src = json.loads(Path(golden_path).read_text(encoding="utf-8"))
    clips = src.get("clips", [])
    for pos, c in enumerate(clips, 1):
        c.setdefault("idx", pos)
    _, sents = segment.sentences_from_wordfile(words_json, host=host)

    client = OpenAICompatibleClient(providers=providers)
    print(f"[dedup] 送 {len(clips)} 条候选去重…", file=sys.stderr)
    data = client.chat_json([
        {"role": "system", "content": load_prompt("dedup-merge")},
        {"role": "user", "content": _clip_summary(clips)}], temperature=0.2)
    actions = data.get("actions", [])

    deduped, stats = apply_actions(clips, actions, sents)
    out_json = {**{k: v for k, v in src.items() if k != "clips"},
                "method": "video-select/dedup", "dedup_stats": stats, "clips": deduped}
    (out / "golden_dedup.json").write_text(
        json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8")
    # 重渲评审稿（去重后这批）
    for c in deduped:
        gen.write_review_md(out, c["idx"], c)
    (out / "_dedup.log").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    print(f"[dedup done] {stats['before']} → {stats['after']} 条 "
          f"（合并 {stats['merged_clips']} 条入 {stats['groups']} 组 / 删 {stats['dropped']}）"
          f" → {out / 'golden_dedup.json'}", file=sys.stderr)
    return out_json


def main() -> int:
    ap = argparse.ArgumentParser(prog="dedup", description="②选片·批量去重/合并（流程二之后）")
    ap.add_argument("--golden", required=True, help="golden_candidate.json（流程二产出）")
    ap.add_argument("--words", required=True, help="words.json（句号↔时间真源）")
    ap.add_argument("--out", required=True, help="输出目录（写 golden_dedup.json + candidates/）")
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    run(a.golden, a.words, a.out, host=a.host, providers=providers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
