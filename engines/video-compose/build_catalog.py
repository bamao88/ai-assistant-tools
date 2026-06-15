#!/usr/bin/env python3
"""build_catalog —— 从各积木厂引擎的 capabilities.json 汇总成 video-compose/catalog.json（总能力表·真源）。

迁移计划 §3.4：catalog 是跨引擎聚合的真源；新增原子只需在所属引擎 capabilities.json 声明，
重跑本脚本即并入。依赖单向：video-compose → 各引擎（只读各引擎声明，不反向）。

用法：python build_catalog.py
"""
from __future__ import annotations
import json
from pathlib import Path

ENGINES = ["video-slicer", "video-framework-render", "video-clip"]
ROOT = Path(__file__).resolve().parent.parent  # engines/


def build() -> dict:
    catalog = {
        "_schema": "video-catalog/v1",
        "_doc": "总能力表（真源·跨引擎聚合，从各引擎 capabilities.json 汇总）。重建：python build_catalog.py。",
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
            catalog["atoms_index"][name] = {
                "engine": e, "kind": meta.get("kind"), "tier": meta.get("tier"),
                "desc": meta.get("desc") or meta.get("sig"),
            }
    return catalog


if __name__ == "__main__":
    cat = build()
    out = Path(__file__).resolve().parent / "catalog.json"
    out.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"catalog: {len(cat['atoms_index'])} atoms across {len(cat['engines'])} engines -> {out.name}")
