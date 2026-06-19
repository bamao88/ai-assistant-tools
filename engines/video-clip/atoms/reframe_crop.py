#!/usr/bin/env python3
"""reframe_crop —— 源适配·录屏：源级裁切去外框、放大铺满目标画幅。

六环阶段化升级 WS-3（源适配·录屏）。录屏画面=PPT内容 + 外层录屏 UI/边框；本原子把内容矩形裁出来
缩放铺满竖版目标(默认 1080×1920)，吐出 crop_vf 字符串给 rough_cut --crop-vf 同趟应用(省一次重编码)。

裁切框来源：
  · --crop W:H:X:Y 显式给（录屏 UI 版式固定，通常是 per-account/per-source 常量，建议存进 profile）。
  · --detect 用 ffmpeg cropdetect 自动探测黑边/内容矩形(仅对有黑边的源准；纯内容重定位需显式)。

用法:
  reframe_crop.py --source X --crop 894:1588:104:290 [--target 1080x1920]      # 吐 crop_vf
  reframe_crop.py --source X --detect                                          # 探测建议
  reframe_crop.py --source X --crop 894:1588:104:290 --apply OUT.mp4           # 直接出裁切片
"""
from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import run, probe, ensure_parent, x264  # noqa: E402


def cropdetect(src, sample_at=None):
    """cropdetect 探测内容矩形（取出现最多的建议）。返回 'W:H:X:Y' 或 None。"""
    cmd = ["ffmpeg", "-hide_banner"]
    if sample_at is not None:
        cmd += ["-ss", str(sample_at)]
    cmd += ["-i", str(src), "-t", "8", "-vf", "cropdetect=24:2:0", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    cnt = {}
    for m in re.finditer(r"crop=(\d+:\d+:\d+:\d+)", err):
        cnt[m.group(1)] = cnt.get(m.group(1), 0) + 1
    if not cnt:
        return None
    return max(cnt, key=lambda k: cnt[k])


def crop_vf(crop, target):
    tw, th = target
    return f"crop={crop.replace('x', ':') if 'x' in crop else crop},scale={tw}:{th}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--crop", default=None, help="W:H:X:Y 显式裁切框")
    ap.add_argument("--detect", action="store_true", help="cropdetect 自动探测建议")
    ap.add_argument("--target", default="1080x1920")
    ap.add_argument("--apply", default=None, help="直接产出裁切后视频到此路径")
    a = ap.parse_args()

    src = Path(a.source)
    if not src.exists():
        raise SystemExit(f"源不存在: {src}")
    tw, th = (int(x) for x in a.target.lower().split("x"))

    crop = a.crop
    if a.detect or not crop:
        _w, _h, dur, _ = probe(src)
        sug = cropdetect(src, sample_at=min(5.0, dur / 2))
        print(f"cropdetect 建议: crop={sug}" if sug else "cropdetect 无建议(可能无黑边·录屏内容重定位需 --crop 显式)")
        if not crop:
            if not sug:
                raise SystemExit("无 --crop 且 cropdetect 无建议；录屏内容重定位请显式 --crop W:H:X:Y")
            crop = sug

    vf = crop_vf(crop, (tw, th))
    print(f"crop_vf: {vf}")
    if a.apply:
        out = ensure_parent(a.apply)
        _w, _h, dur, has_audio = probe(src)
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", vf,
                 *x264(audio=has_audio), "-movflags", "+faststart", str(out)])
        if r.returncode != 0:
            raise SystemExit(f"ffmpeg 失败：{r.stderr[-500:]}")
        print(f"DONE reframe_crop  {out}")


if __name__ == "__main__":
    main()
