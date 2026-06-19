#!/usr/bin/env python3
"""subtitles_cli —— 把 make_subtitles(药丸 ASS 渲染) 暴露成独立入口，给裁剪版⑤铸造复用。

六环阶段化升级 WS-5：裁剪版要的不是整套框架页渲染，只是「定稿 SRT → 药丸 ASS」这一步。
本模块薄薄地 import render.make_subtitles（不改其几何/逻辑，G4 渲染管线零触碰），用 clip_cut 版式
(1080×1920，= vertical ×1.5)渲药丸——这就是计划「复用现成几何·弃 build_subs.py」。

用法:
  python -m video_framework_render.subtitles_cli --srt 定稿.srt --out-dir OUT [--layout clip_cut] [--profile zh_main]
  → 产 OUT/zh.ass（药丸字幕，再用 ffmpeg ass 滤镜烧到裁切身子）
"""
from __future__ import annotations
import argparse
from pathlib import Path

from .render import make_subtitles, load_layout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt", required=True)
    ap.add_argument("--out-dir", required=True, help="写 <out-dir>/zh.ass")
    ap.add_argument("--layout", default="clip_cut")
    ap.add_argument("--profile", default="zh_main")
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    L = load_layout(a.layout)
    make_subtitles(Path(a.srt), out, a.profile, L)
    print(f"DONE 药丸 ASS({a.layout} {L['canvas']['w']}×{L['canvas']['h']}) → {out / 'zh.ass'}")


if __name__ == "__main__":
    main()
