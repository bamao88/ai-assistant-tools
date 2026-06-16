#!/usr/bin/env python3
"""run —— 组合层编排：按 recipe 解析能力链 → 跨引擎调原子。唯一对外入口，只指挥不产原子。

迁移计划 §3.4 ④：依赖单向 video-compose → 各引擎；各引擎互不依赖。
- --plan <recipe>：解析并打印有序步骤（每步原子 + 所属引擎 + entry），完全可验证。
- --run  <recipe> [--selection sel.json] [--profile zh_main]：执行。
    delegate 配方（zh_business）→ 执行已装配的 run_pipeline（过渡期，见 recipes.json note）。
    chain 配方 → 按 dispatch 逐原子调用（atom 级编排；部分原子 arg 由调用方补全）。

帧验证（G4）就绪后，zh_business 由 delegate 升级为 atom 级 chain（render=framework_reframe）。
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINES = HERE.parent  # engines/

# 原子 → 引擎执行入口（依赖单向 compose→各引擎）
DISPATCH = {
    "cut_sentence":   ("video-slicer", "python -m video_slicer.planner"),
    "cut_word":       ("video-slicer", "python -m video_slicer.twostage.pipeline"),
    "pages_gen":      ("video-slicer", "python -m video_slicer.pages_gen"),
    "srt_fix":        ("video-slicer", "python -m video_slicer.srt_fix"),
    "subtitle_ai_fix":("video-slicer", "python -m video_slicer.srt_fix"),
    "framework_reframe": ("video-framework-render", "python -m video_framework_render.render"),
    "raw":            ("video-framework-render", "(直出·不改造)"),
    "concat":         ("video-clip", "python atoms/concat.py"),
    "progress_bar":   ("video-clip", "python atoms/progress_bar.py"),
    "endcard":        ("video-clip", "python atoms/endcard.py"),
    "speed_adapt":    ("video-clip", "python atoms/speed_adapt.py"),
    "subtitle_burn":  ("video-clip", "python atoms/subtitle_burn.py"),
    "name_mask":      ("video-clip", "python atoms/name_mask.py"),
    "face_locate":    ("video-clip", "python atoms/face_locate.py"),
    "cover_frame":    ("video-clip", "python atoms/cover_frame.py"),
}


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def resolve(recipe_name):
    recipes = load("recipes.json")["recipes"]
    r = recipes.get(recipe_name)
    if not r:
        raise SystemExit(f"未知 recipe: {recipe_name}（见 select.py --list）")
    steps = r.get("chain") or r.get("steps") or []
    return r, steps


def plan(recipe_name):
    r, steps = resolve(recipe_name)
    print(f"# recipe: {recipe_name} ({r['kind']}) — {r['label']}")
    for i, s in enumerate(steps, 1):
        atom = s.split("(")[0].split("=")[0].split(":")[-1].strip()
        eng, entry = DISPATCH.get(atom, ("?", "?"))
        print(f"  {i}. {s:42} → [{eng}] {entry}")
    if r.get("kind") == "delegate":
        print(f"  ⇒ delegate: {r['delegate']}")


def run(recipe_name, selection, profile):
    r, steps = resolve(recipe_name)
    if r.get("kind") == "delegate":
        if recipe_name in ("zh_business", "landscape_business"):
            if not selection:
                raise SystemExit(f"{recipe_name} 需 --selection <sel.json>")
            cmd = [sys.executable,
                   str(ENGINES.parent.parent / "assistant_zh/workflow/video_framework_slicer/run_pipeline.py"),
                   selection, "--profile", profile or r.get("profile", "zh_main")]
            if r.get("layout"):                      # 横版配方把 layout 传给渲染（竖版默认不传）
                cmd += ["--layout", r["layout"]]
            print("⇒ delegate:", " ".join(cmd))
            return subprocess.run(cmd).returncode
        raise SystemExit(f"delegate 配方 {recipe_name} 暂无执行绑定")
    # chain：打印逐原子调用计划（atom arg 由调用方补全；端到端执行待帧验证就绪）
    print(f"chain 配方 {recipe_name}：")
    plan(recipe_name)
    print("注：chain 级端到端执行待 G4 帧验证就绪；当前可用 --plan 审链 + 各引擎原子单独调用。")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=None, help="解析并打印 recipe 的能力链")
    ap.add_argument("--run", dest="run_recipe", default=None)
    ap.add_argument("--selection", default=None)
    ap.add_argument("--profile", default=None)
    a = ap.parse_args()
    if a.plan:
        plan(a.plan)
    elif a.run_recipe:
        sys.exit(run(a.run_recipe, a.selection, a.profile))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
