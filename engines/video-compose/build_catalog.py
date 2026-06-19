#!/usr/bin/env python3
"""build_catalog —— 从各积木厂引擎的 capabilities.json 汇总成 video-compose/catalog.json（总能力表·真源）。

迁移计划 §3.4：catalog 是跨引擎聚合的真源；新增原子只需在所属引擎 capabilities.json 声明，
重跑本脚本即并入。依赖单向：video-compose → 各引擎（只读各引擎声明，不反向）。

v2（六环阶段化升级 WS-1）：
- 透传六环阶段标签 stage/layer/required/substep/source_types 到 atoms_index。
- atoms 与 also_provides 都索引（① transcribe、④ srt_fix 等住 also_provides，stage 视图需要它们）。
- atoms_index 每条加 group=atoms|also_provides 区分主原子 vs 兼供能力。

用法：python build_catalog.py
"""
from __future__ import annotations
import json
from pathlib import Path

ENGINES = ["video-slicer", "video-framework-render", "video-clip"]
ROOT = Path(__file__).resolve().parent.parent  # engines/

# 透传到 atoms_index 的六环阶段字段（缺省则不写入该条）
STAGE_FIELDS = ("stage", "layer", "required", "substep", "source_types")


def _index_entry(engine: str, group: str, meta: dict) -> dict:
    entry = {
        "engine": engine, "group": group,
        "kind": meta.get("kind"), "tier": meta.get("tier"),
        "desc": meta.get("desc") or meta.get("sig"),
    }
    for f in STAGE_FIELDS:
        if f in meta:
            entry[f] = meta[f]
    return entry


def build() -> dict:
    catalog = {
        "_schema": "video-catalog/v2",
        "_doc": "总能力表（真源·跨引擎聚合，从各引擎 capabilities.json 汇总）。重建：python build_catalog.py。六环阶段字段 stage/layer/required/substep/source_types 透传自各引擎。",
        "engines": {}, "atoms_index": {},
    }
    for e in ENGINES:
        p = ROOT / e / "capabilities.json"
        if not p.exists():
            continue
        cap = json.loads(p.read_text(encoding="utf-8"))
        catalog["engines"][e] = {
            "role": cap.get("role"),
            "atoms": list(cap.get("atoms", {}).keys()),
            "also_provides": list(cap.get("also_provides", {}).keys()),
        }
        for name, meta in cap.get("atoms", {}).items():
            catalog["atoms_index"][name] = _index_entry(e, "atoms", meta)
        for name, meta in cap.get("also_provides", {}).items():
            # 不覆盖已有主原子同名条目
            catalog["atoms_index"].setdefault(name, _index_entry(e, "also_provides", meta))
    return catalog


if __name__ == "__main__":
    cat = build()
    out = Path(__file__).resolve().parent / "catalog.json"
    out.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged = sum(1 for m in cat["atoms_index"].values() if m.get("stage"))
    print(f"catalog: {len(cat['atoms_index'])} atoms ({staged} 带六环 stage) across {len(cat['engines'])} engines -> {out.name}")
