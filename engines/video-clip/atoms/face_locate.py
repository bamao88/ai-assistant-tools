#!/usr/bin/env python3
"""face-locate —— 抽帧测脸，给出脸中心 + 竖屏裁切重心（原子能力，只读不改片）。

Haar 抽帧检测取脸中心中位数。两个用途：
  1) 圆形 PIP 水平居中（取 face_cx）；
  2) 横屏→竖屏裁切偏移（给 --target WxH，反推 cover 缩放 + crop，让脸水平居中、垂直略偏上）。
合并自 slicer.py::locate_face_cx 与 video_vertical/reframe_locate.py。输出 JSON 到 stdout。

用法:
  face_locate.py IN.mp4
  face_locate.py IN.mp4 --target 720x744 --samples 40 --face-y 0.42
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import probe, face_center  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="抽帧测脸 → 脸中心 / 竖屏裁切重心")
    ap.add_argument("input")
    ap.add_argument("--target", help="竖屏目标尺寸 WxH，给了才算裁切参数")
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--face-y", type=float, default=0.42, help="脸垂直落点(占目标高,默认0.42略偏上)")
    a = ap.parse_args()

    if not Path(a.input).exists():
        raise SystemExit(f"输入不存在: {a.input}")
    W, Hh, _dur, _ = probe(a.input)
    cx, cy, found = face_center(a.input, a.samples)
    res = {"input": a.input, "src": [W, Hh], "faces_found": found, "samples": a.samples,
           "face_center_pct": [round(cx * 100, 1), round(cy * 100, 1)]}

    if a.target:
        tw, th = (int(x) for x in a.target.lower().split("x"))
        s = max(tw / W, th / Hh) if W and Hh else 1.0
        SW, SH = W * s, Hh * s
        x0 = min(max(cx * SW - tw * 0.5, 0), max(SW - tw, 0))
        y0 = min(max(cy * SH - th * a.face_y, 0), max(SH - th, 0))
        posx = 50.0 if SW - tw <= 0 else x0 / (SW - tw) * 100
        posy = 50.0 if SH - th <= 0 else y0 / (SH - th) * 100
        res.update({
            "target": [tw, th],
            "object_position": [round(posx, 1), round(posy, 1)],
            "ffmpeg_scale": f"scale={round(SW)}:{round(SH)}",
            "ffmpeg_crop": f"crop={tw}:{th}:{round(x0)}:{round(y0)}",
        })
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
