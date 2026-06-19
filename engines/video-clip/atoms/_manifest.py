#!/usr/bin/env python3
"""_manifest —— 剪辑账本(cut manifest)：③裁剪的承重墙数据模型。

不是原子，是 rough_cut / trim_silence / speed_adapt 共用的账本读写 + 时间重放助手。
六环阶段化升级 WS-2 §三：③裁剪每个时间操作记一笔进账本，④ subtitle_align 照账本重放，
把「逐字账本里每个选中字的源时间」依次套上同一串操作 → 它在成片里的时间。
字幕时间永远 == 画音被同一把剪刀剪过后的时间，从不另算。

账本 schema (cut-manifest/v1)：
  {
    "_schema": "cut-manifest/v1",
    "source": "/path/源视频.mp4",
    "ops": [                                  # 有序：源 → 成片，依次套用
      {"op": "rough_cut",    "in": "source",    "out": "assembled", "keeps": [[s,e],...]},
      {"op": "trim_silence", "in": "assembled", "out": "trimmed",   "keeps": [[s,e],...], "removed_sec": 13.4},
      {"op": "speed",        "in": "trimmed",   "out": "final",     "factor": 1.2}
    ],
    "durations": {"assembled": 107.766, "trimmed": 94.4, "final": 78.683}
  }

重放算法（subtitle_align 在 video-slicer 侧复制同一份·schema 是引擎间唯一接口）：
  keeps 类 op = 分段线性映射：落在某保留区间→偏移到累计保留时长里；落在被删处→返回 None(该字被剪掉)。
  speed op   = 除以 factor。
"""
from __future__ import annotations
import json
from pathlib import Path

SCHEMA = "cut-manifest/v1"
KEEP_OPS = ("rough_cut", "trim_silence", "script_clean")   # 用 keeps 区间映射的 op


def new(source: str) -> dict:
    return {"_schema": SCHEMA, "source": str(source), "ops": [], "durations": {}}


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(manifest: dict, path) -> None:
    Path(path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_keep_op(manifest: dict, op: str, in_tl: str, out_tl: str, keeps, **extra) -> dict:
    """记一笔保留区间类操作（rough_cut/trim_silence/script_clean）。keeps=in_tl 时间轴上的保留区间。"""
    entry = {"op": op, "in": in_tl, "out": out_tl, "keeps": [[round(s, 3), round(e, 3)] for s, e in keeps]}
    entry.update(extra)
    manifest["ops"].append(entry)
    return manifest


def add_speed_op(manifest: dict, in_tl: str, out_tl: str, factor: float, **extra) -> dict:
    entry = {"op": "speed", "in": in_tl, "out": out_tl, "factor": float(factor)}
    entry.update(extra)
    manifest["ops"].append(entry)
    return manifest


def _through_keeps(t: float, keeps) -> float | None:
    """分段线性映射：t 落在某保留区间[s,e)→偏移到累计保留时长；落在被删处→None。"""
    off = 0.0
    for s, e in keeps:
        if s <= t < e:
            return off + (t - s)
        off += (e - s)
    return None


def remap_time(ops, t: float, *, is_end: bool = False) -> float | None:
    """把源时间 t 依次套用所有 op → 成片时间。被剪掉的时间返回 None。
    is_end=True：句末时间若正好落在某保留区间右边界(切点)，回退一个微小量夹回段内，
    避免「句末=切点」被判 None 而字幕提前消失（build_subs 的 pe-0.03 坑沉淀）。"""
    for op in ops:
        if op["op"] in KEEP_OPS or "keeps" in op:
            nt = _through_keeps(t, op["keeps"])
            if nt is None and is_end:
                nt = _through_keeps(t - 0.03, op["keeps"])
            if nt is None:
                return None
            t = nt
        elif op["op"] == "speed":
            t = t / op["factor"]
    return t
