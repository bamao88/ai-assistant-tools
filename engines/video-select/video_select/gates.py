"""门禁（Gates）—— ②选片的机器可判红线。不过就挡，不让进下一轮。

把原来手工跑的 `_merge_segments.py` 收成正式门禁，分两块：

1. `merge_segments(segments, sents)` —— **精选合并原则**的确定性变换（去重叠 + 合并
   列表相邻且中间 ≤2 句的刀）。Runner 在总编出口调它，把碎段先合并干净。

2. `check_*` / `check_clip` / `check_golden` —— 纯检查，返回违规列表（不改数据）：
   - 无重叠（同条内两段不能时间/句号重叠）
   - 无「列表相邻 gap ≤2」（该合并的没合并 = 切太碎）
   - 正文时长 ≥ 阈值（默认 60s）
   - 零编造（每个 sid 落在 words.json 真实句号范围内）
   - 字级去口水决策可执行（每个 deletion.text 是该句原话的真子串）

设计真源：doc/plan/视频剪辑skill-第二环选片-plan.md §5 / §7 / §9。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import _deps  # noqa: F401  挂 video-slicer 到 sys.path
from video_slicer.transcribe import segment  # noqa: E402

GAP_THR = 2            # 列表相邻、中间 ≤ 这么多句 → 该合并
MIN_BODY_DUR = 60.0    # 正文最短秒数
BODY_ROLES = {"argument", "evidence", "closing"}


# ───────────────────────── 精选合并（确定性变换） ─────────────────────────
def _contains(a, b) -> bool:           # b 完全包含 a
    return b[0] <= a[0] and a[1] <= b[1]


def _size(s) -> int:
    return s[1] - s[0]


def merge_segments(segments: list[dict], sents) -> list[dict]:
    """精选合并原则：去重叠 + 合并「列表相邻且中间 ≤GAP_THR 句」的刀。

    sents 用来回填合并后区间的 text / span（秒）。保留编辑顺序，不按时间拉平。
    """
    segs = [{"role": s.get("role", "evidence"), "sids": [int(s["sids"][0]), int(s["sids"][-1])],
             "reason": (s.get("reason") or "")} for s in segments if s.get("sids")]

    # 4) 去重叠/重复：丢被更大段完全包含的；完全相同的只留首个
    kept = []
    for i, s in enumerate(segs):
        sid = s["sids"]
        if any(j != i and _contains(sid, segs[j]["sids"]) and _size(segs[j]["sids"]) > _size(sid)
               for j in range(len(segs))):
            continue
        if any(j < i and segs[j]["sids"] == sid for j in range(len(segs))):
            continue
        kept.append(s)

    # 2) 合并列表相邻、中间 ≤GAP_THR 句（含重叠/乱序相邻对）
    groups: list[dict] = []
    for s in kept:
        lo0, hi0 = s["sids"]
        if groups:
            p = groups[-1]
            overlap = lo0 <= p["hi"] and p["lo"] <= hi0
            neargap = (lo0 - p["hi"] - 1) if lo0 > p["hi"] else (p["lo"] - hi0 - 1)
            if overlap or 0 <= neargap <= GAP_THR:
                p["lo"], p["hi"] = min(p["lo"], lo0), max(p["hi"], hi0)
                p["members"].append(s)
                continue
        groups.append({"lo": lo0, "hi": hi0, "members": [s]})

    # 3) 组装合并后的 segment（role 优先级 argument>closing>evidence；reason 去重拼接）
    max_sid = sents[-1].sid if sents else -1
    out = []
    for g in groups:
        lo, hi = max(0, g["lo"]), min(max_sid, g["hi"])
        if lo > hi:
            continue
        roles = [m["role"] for m in g["members"]]
        role = "argument" if "argument" in roles else ("closing" if "closing" in roles else "evidence")
        reasons, seen = [], set()
        for m in g["members"]:
            r = m["reason"].strip()
            if r and r not in seen:
                seen.add(r)
                reasons.append(r)
        out.append({"role": role, "sids": [lo, hi],
                    "span": [round(sents[lo].start, 2), round(sents[hi].end, 2)],
                    "text": "".join(sents[i].text for i in range(lo, hi + 1)),
                    "reason": " ｜ ".join(reasons)})
    return out


# ───────────────────────── 门禁检查（不改数据） ─────────────────────────
def check_clip(clip: dict, sents) -> list[str]:
    """对一条 clip 跑全部红线，返回违规描述列表（空 = 全绿）。"""
    title = clip.get("title", "?")
    issues: list[str] = []
    max_sid = sents[-1].sid if sents else -1
    segs = [list(s["sids"]) for s in clip.get("segments", [])]

    # 零编造：每个 sid 落在真实范围
    for s in segs:
        if not (0 <= s[0] <= s[1] <= max_sid):
            issues.append(f"[{title}] 编造/越界句号 {s}（合法 0..{max_sid}）")

    # 无重叠
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            a1, b1 = segs[i]
            a2, b2 = segs[j]
            if a1 <= b2 and a2 <= b1:
                issues.append(f"[{title}] 段重叠 {segs[i]} ∩ {segs[j]}")

    # 无「列表相邻 gap≤2」（该合并未合并）
    for i in range(len(segs) - 1):
        a1, b1 = segs[i]
        a2, b2 = segs[i + 1]
        ng = (a2 - b1 - 1) if a2 > b1 else (a1 - b2 - 1)
        if 0 <= ng <= GAP_THR:
            issues.append(f"[{title}] 相邻段未合并 {segs[i]}→{segs[i+1]} gap={ng}（≤{GAP_THR}）")

    # 正文时长 ≥ 阈值
    dur = sum(e - s for s, e in (sg.get("span", [0, 0]) for sg in clip.get("segments", [])))
    if dur < MIN_BODY_DUR:
        issues.append(f"[{title}] 正文时长 {dur:.1f}s < {MIN_BODY_DUR}s")

    # 字级去口水决策可执行：每个 deletion.text 是该句真子串
    for d in clip.get("deletions", []) or []:
        sid = d.get("sid")
        text = (d.get("text") or "").strip()
        if not isinstance(sid, int) or not (0 <= sid <= max_sid):
            issues.append(f"[{title}] 去口水决策 sid 非法：{sid}")
            continue
        if text and text not in sents[sid].text and text.replace(" ", "") not in sents[sid].text.replace(" ", ""):
            issues.append(f"[{title}] 去口水决策不可执行（非原话子串）#{sid}「{text}」")

    return issues


def check_golden(golden_path: str | Path, words_json: str | Path, host: str = "张和") -> dict:
    """对整份 golden_candidate / golden 跑门禁，返回 {pass, total, clips_failed, issues}。"""
    data = json.loads(Path(golden_path).read_text(encoding="utf-8"))
    _, sents = segment.sentences_from_wordfile(words_json, host=host)
    all_issues: list[str] = []
    failed = 0
    clips = data.get("clips", [])
    for c in clips:
        iss = check_clip(c, sents)
        if iss:
            failed += 1
            all_issues.extend(iss)
    return {"pass": not all_issues, "total": len(clips),
            "clips_failed": failed, "issues": all_issues}


def main() -> int:
    ap = argparse.ArgumentParser(prog="gates", description="②选片门禁：精选合并红线 + 时长 + 可执行 + 零编造")
    ap.add_argument("--golden", required=True, help="golden_candidate.json / golden.json")
    ap.add_argument("--words", required=True, help="words.json（句号↔时间真源）")
    ap.add_argument("--host", default="张和")
    ap.add_argument("--out", default=None, help="把门禁报告写成 JSON")
    a = ap.parse_args()
    rep = check_golden(a.golden, a.words, host=a.host)
    print(f"[gates] {'✅ PASS' if rep['pass'] else '❌ FAIL'} "
          f"— {rep['clips_failed']}/{rep['total']} 条有违规，共 {len(rep['issues'])} 项")
    for s in rep["issues"]:
        print(f"  · {s}")
    if a.out:
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[gates] 报告 → {a.out}")
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
