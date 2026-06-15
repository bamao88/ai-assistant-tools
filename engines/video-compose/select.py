#!/usr/bin/env python3
"""select —— 组合层选择器：列出能力/配方，或按描述选一条 recipe（AI 读视频 → 选组合）。

迁移计划 §3.4 ③选择层：AI 读视频 → 选 recipe，或自由组合 catalog 原子。
本模块给规则化默认 + LLM 钩子（可选走 video-slicer 引擎 LLM）。

用法：
  python select.py --list                       # 列出 catalog 原子 + recipes
  python select.py --describe "口播切片框架页"   # → 选中的 recipe 名
  python select.py --atoms-of zh_business        # 展开某 recipe 的原子链
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def pick_recipe(desc: str, recipes: dict) -> str:
    """规则化选择（默认 zh_business）。关键词命中优先；可替换为 LLM 选择。"""
    d = (desc or "").lower()
    rules = [
        (("快剪", "词级", "quickcut", "raw", "不框架"), "raw_quickcut"),
        (("拼接", "concat", "合并"), "simple_concat"),
        (("成长", "章节", "进度条", "growth"), "chaptered_growth"),
        (("框架", "切片", "口播", "竖版", "张和", "business"), "zh_business"),
    ]
    for kws, r in rules:
        if any(k in d for k in kws) and r in recipes:
            return r
    return "zh_business"  # 默认线上主路径


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--describe", default=None)
    ap.add_argument("--atoms-of", default=None)
    a = ap.parse_args()
    catalog = load("catalog.json"); recipes = load("recipes.json")["recipes"]

    if a.list:
        print("== 能力原子 (catalog) ==")
        for name, m in catalog["atoms_index"].items():
            print(f"  {name:18} [{m['engine']}] {m.get('kind') or ''} {m.get('tier') or ''}")
        print("== 配方 (recipes) ==")
        for name, r in recipes.items():
            print(f"  {name:16} {r['label']}  ({r['kind']})")
        return
    if a.atoms_of:
        r = recipes.get(a.atoms_of)
        if not r:
            raise SystemExit(f"未知 recipe: {a.atoms_of}")
        print(json.dumps(r.get("chain") or r.get("steps"), ensure_ascii=False))
        return
    if a.describe is not None:
        print(pick_recipe(a.describe, recipes))
        return
    ap.print_help()


if __name__ == "__main__":
    main()
