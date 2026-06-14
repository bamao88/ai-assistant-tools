"""字级 resolver：把句级粗边界吸附到 paraformer 字级时间轴上的字间静音。

分工：腾讯句子定"选哪句"(粗边界，秒级/句级)，paraformer 定"那一刻的字边界"，
本模块用【时间对齐】把粗边界吸到最近的字间静音中点——不依赖文本匹配（两套转录文本不同）。

纯函数、无网络：输入 segments + words，输出吸附后的 segments。字级词表怎么来由调用方决定
（paraformer 整轨/窗口跑，见 wordsource）。
"""
from __future__ import annotations

import json
from pathlib import Path


def load_paraformer_words(path: str | Path, time_offset: float = 0.0) -> list[dict]:
    """读 spike 产出的 aliyun_words.json → [{text,start,end}]（秒）。

    time_offset：若词表是对源的某个窗口跑的（0 基），传窗口起点把它移回源绝对时间。
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    words = []
    for w in data.get("words", []):
        b, e = w.get("begin_time"), w.get("end_time")
        if b is None or e is None:
            continue
        words.append({"text": w.get("text", ""), "start": b / 1000 + time_offset, "end": e / 1000 + time_offset})
    words.sort(key=lambda x: x["start"])
    return words


def _snap_start(t: float, words: list[dict], gap_search: float, mode: str) -> float:
    """把 in 点吸到"应作为首字的那个字"的前一道静音。"""
    near = [w for w in words if abs(w["start"] - t) <= gap_search]
    if not near:
        return t
    w = min(near, key=lambda x: abs(x["start"] - t))  # 离 t 最近的字起点
    if mode == "word_edge":
        return w["start"]
    prev = [p for p in words if p["end"] <= w["start"]]
    if not prev:
        return w["start"]
    gap_lo = prev[-1]["end"]
    return (gap_lo + w["start"]) / 2 if w["start"] > gap_lo else w["start"]  # 静音中点


def _snap_end(t: float, words: list[dict], gap_search: float, mode: str) -> float:
    """把 out 点吸到"应作为末字的那个字"的后一道静音。"""
    near = [w for w in words if abs(w["end"] - t) <= gap_search]
    if not near:
        return t
    w = min(near, key=lambda x: abs(x["end"] - t))  # 离 t 最近的字终点
    if mode == "word_edge":
        return w["end"]
    nxt = [n for n in words if n["start"] >= w["end"]]
    if not nxt:
        return w["end"]
    gap_hi = nxt[0]["start"]
    return (w["end"] + gap_hi) / 2 if gap_hi > w["end"] else w["end"]


def snap_segments(
    segments: list[list[float]],
    words: list[dict],
    mode: str = "silence_mid",
    gap_search: float = 1.0,
) -> list[dict]:
    """逐段吸附。返回 [{rough:[s,e], snapped:[s,e], delta_start, delta_end}]。

    mode: "silence_mid"=吸到字间静音中点（更自然，默认）/ "word_edge"=紧贴字边。
    gap_search: 在粗边界 ±该秒数内找字边界；超出认为是静音、不动。
    """
    out = []
    for seg in segments:
        s, e = float(seg[0]), float(seg[-1])
        ss = _snap_start(s, words, gap_search, mode)
        se = _snap_end(e, words, gap_search, mode)
        if se <= ss:  # 兜底：吸附后非法则退回原值
            ss, se = s, e
        out.append({
            "rough": [round(s, 3), round(e, 3)],
            "snapped": [round(ss, 3), round(se, 3)],
            "delta_start": round(ss - s, 3),
            "delta_end": round(se - e, 3),
        })
    return out


def _main() -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="resolve", description="字级 resolver：句级边界 → 字级精确边界")
    ap.add_argument("--words", required=True, help="paraformer aliyun_words.json")
    ap.add_argument("--offset", type=float, default=0.0, help="词表窗口起点(秒)，移回源绝对时间")
    ap.add_argument("--segments", required=True, help='逗号分隔的 "start-end" 秒，如 610.36-615.42,617.02-629.34')
    ap.add_argument("--mode", default="silence_mid", choices=["silence_mid", "word_edge"])
    ap.add_argument("--gap-search", type=float, default=1.0)
    a = ap.parse_args()
    words = load_paraformer_words(a.words, time_offset=a.offset)
    segs = [[float(x) for x in part.split("-")] for part in a.segments.split(",") if part.strip()]
    rows = snap_segments(segs, words, mode=a.mode, gap_search=a.gap_search)
    print(f"词表 {len(words)} 字，覆盖 {words[0]['start']:.1f}–{words[-1]['end']:.1f}s" if words else "空词表")
    for r in rows:
        print(f"  粗 {r['rough']}  →  字级 {r['snapped']}   (Δin {r['delta_start']:+.3f}s, Δout {r['delta_end']:+.3f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
