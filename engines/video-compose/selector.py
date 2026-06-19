#!/usr/bin/env python3
"""select —— 组合层选择器：列出能力/配方，或按描述选一条 recipe（AI 读视频 → 选组合）。

迁移计划 §3.4 ③选择层：AI 读视频 → 选 recipe，或自由组合 catalog 原子。
本模块给规则化默认 + LLM 钩子（可选走 video-slicer 引擎 LLM）。

v2（六环阶段化升级 WS-1）：--list 按六环阶段(transcribe→assemble)分组主链原子，
横切层(source_adapt 源适配 / self_check 自检门)单列。

用法：
  python select.py --list                       # 按六环分组列出 catalog 原子 + recipes
  python select.py --describe "口播切片框架页"   # → 选中的 recipe 名
  python select.py --atoms-of zh_business        # 展开某 recipe 的原子链
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 六环主链顺序 + 人读标签
STAGE_ORDER = [
    ("transcribe", "① 转写"),
    ("select",     "② 选片"),
    ("trim",       "③ 裁剪(时间轴)★"),
    ("subtitle",   "④ 字幕(文字)★"),
    ("cast",       "⑤ 铸造(风格化)"),
    ("assemble",   "⑥ 组装成片"),
]
STAGE_LABELS = dict(STAGE_ORDER)


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def pick_recipe(desc: str, recipes: dict) -> str:
    """规则化选择（默认 zh_business）。关键词命中优先；可替换为 LLM 选择。"""
    d = (desc or "").lower()
    rules = [
        (("裁剪版", "录屏", "裁切", "clip_cut", "去静音", "药丸"), "zh_clip_cut"),
        (("快剪", "词级", "quickcut", "raw", "不框架"), "raw_quickcut"),
        (("拼接", "concat", "合并"), "simple_concat"),
        (("成长", "章节", "进度条", "growth"), "chaptered_growth"),
        (("框架", "切片", "口播", "竖版", "张和", "business"), "zh_business"),
    ]
    for kws, r in rules:
        if any(k in d for k in kws) and r in recipes:
            return r
    return "zh_business"  # 默认线上主路径


def _fmt(name, m):
    req = (m.get("required") or "")
    req_cn = {"required": "必须", "optional": "可选"}.get(req, "")
    sub = f" ·{m['substep']}" if m.get("substep") else ""
    src = f" ·{'/'.join(m['source_types'])}" if m.get("source_types") else ""
    tier = f" {m['tier']}" if m.get("tier") else ""
    return f"    {name:18} [{m['engine']}] {req_cn}{sub}{src}{tier}"


def list_catalog(catalog):
    idx = catalog["atoms_index"]
    backbone = {s: [] for s, _ in STAGE_ORDER}
    source_adapt, self_check, untagged = [], [], []
    for name, m in idx.items():
        layer = m.get("layer")
        if layer == "source_adapt":
            source_adapt.append((name, m))
        elif layer == "self_check":
            self_check.append((name, m))
        elif m.get("stage") in backbone:
            backbone[m["stage"]].append((name, m))
        else:
            untagged.append((name, m))

    print("== 骨干主链·六环（线性必经）==")
    for stage, label in STAGE_ORDER:
        rows = backbone[stage]
        print(f"{label}  [{stage}]")
        if not rows:
            print("    (本阶段暂无原子)")
        for name, m in rows:
            print(_fmt(name, m))
    print("== 横切层·源适配 (source_adapt — 按源类型挂载，主要挂③) ==")
    for name, m in source_adapt or []:
        print(_fmt(name, m))
    if not source_adapt:
        print("    (暂无)")
    print("== 横切层·自检门 (self_check — 每阶段后报数) ==")
    for name, m in self_check or []:
        print(_fmt(name, m))
    if not self_check:
        print("    (暂无；WS-2 落 align_check/len_check)")
    if untagged:
        print("== 未标六环 stage ==")
        for name, m in untagged:
            print(_fmt(name, m))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--describe", default=None)
    ap.add_argument("--atoms-of", default=None)
    a = ap.parse_args()
    catalog = load("catalog.json"); recipes = load("recipes.json")["recipes"]

    if a.list:
        list_catalog(catalog)
        print("== 配方 (recipes) ==")
        for name, r in recipes.items():
            print(f"  {name:16} {r['label']}  ({r['kind']})")
        return
    if a.atoms_of:
        r = recipes.get(a.atoms_of)
        if not r:
            raise SystemExit(f"未知 recipe: {a.atoms_of}")
        print(json.dumps(r.get("chain") or r.get("stages") or r.get("steps"), ensure_ascii=False))
        return
    if a.describe is not None:
        print(pick_recipe(a.describe, recipes))
        return
    ap.print_help()


if __name__ == "__main__":
    main()
