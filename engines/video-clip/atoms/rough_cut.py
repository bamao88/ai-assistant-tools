#!/usr/bin/env python3
"""rough_cut —— ③3a 粗剪·拼身子：按②选片清单从源视频切段、按顺序硬切拼成一整条干净身子。

六环阶段化升级 WS-2（产品化 var/zh_main/0618test/assemble.py 的切段+按序拼接）。
承重墙：把「选段 keep + 顺序」记一笔进剪辑账本(cut manifest)，④ subtitle_align 照此重放字幕时间。
源适配：可选 --crop-vf（去录屏外框放大铺满）+ --mask-boxes（黑块盖 UI），与切段同一 ffmpeg 趟完成，
        整段录屏固定值。坐标=裁切后最终空间。WS-3 的 reframe_crop/name_mask 产出这两个参数。

跳接=块内硬切（concat 滤镜统一编码避免时间戳错位）。块间转场(xfade)属⑥组装(prepend_hook)，
本原子只产干净身子，keeps 为源时间轴上有序保留区间。

用法:
  rough_cut.py --spec clip_01_spec.json --out body.mp4 --manifest manifest.json
  rough_cut.py --source 源.mp4 --keeps "872.95,902.30 905.35,921.30" --out body.mp4 --manifest m.json \
               [--crop-vf "crop=894:1588:104:290,scale=1080:1920"] [--mask-boxes "0,0,1080,152"]
"""
from __future__ import annotations
import argparse, json, subprocess, tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _manifest  # noqa: E402

ENC_V = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30"]
ENC_A = ["-c:a", "aac", "-ar", "48000", "-ac", "2"]


def _run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：\n{' '.join(map(str, cmd))}\n{r.stderr[-800:]}")
    return r


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _boxes_vf(mask_boxes):
    if not mask_boxes:
        return ""
    return "".join(f"drawbox=x={b[0]}:y={b[1]}:w={b[2]}:h={b[3]}:color=black:t=fill,"
                   for b in mask_boxes)


def cut_seg(src, s, e, out, crop_vf=None, mask_boxes=None):
    """精确切一段并统一编码（-ss 前置：keyframe 快寻 + 重编到精确点）。"""
    vf = (crop_vf + "," if crop_vf else "") + _boxes_vf(mask_boxes) + "fps=30,format=yuv420p"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{s:.3f}", "-i", str(src),
          "-t", f"{e - s:.3f}", "-vf", vf, *ENC_V, *ENC_A, "-vsync", "cfr", str(out)])


def concat_hard(segs, out):
    if len(segs) == 1:
        Path(out).write_bytes(Path(segs[0]).read_bytes()); return
    inputs = []
    for s in segs:
        inputs += ["-i", str(s)]
    n = len(segs)
    fc = "".join(f"[{i}:v][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    _run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc,
          "-map", "[v]", "-map", "[a]", *ENC_V, *ENC_A, str(out)])


def build(source, keeps, out, manifest_path, crop_vf=None, mask_boxes=None):
    """keeps=源时间轴有序保留区间[[s,e],...]（已按输出顺序）。"""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        seg_files = []
        for i, (s, e) in enumerate(keeps):
            p = td / f"seg_{i:03d}.mp4"
            cut_seg(source, float(s), float(e), p, crop_vf, mask_boxes)
            seg_files.append(p)
        concat_hard(seg_files, out)
    body_dur = _dur(out)
    # 记账：rough_cut keep+顺序（源时间轴 → 拼好身子时间轴 assembled）
    man = _manifest.load(manifest_path) if Path(manifest_path).exists() else _manifest.new(source)
    man["source"] = str(source)
    _manifest.add_keep_op(man, "rough_cut", "source", "assembled", keeps,
                          n_segments=len(keeps),
                          source_kept_sec=round(sum(e - s for s, e in keeps), 3))
    man["durations"]["assembled"] = round(body_dur, 3)
    _manifest.save(man, manifest_path)
    print(f"DONE rough_cut  {out}  {len(keeps)}段 → 身子 {body_dur:.3f}s  | 账本 {manifest_path}")
    return body_dur


def _flatten_spec(spec):
    """clip_NN_spec.json：blocks[[ [s,e]... ]] → 扁平有序 keeps（块内硬切，块间也硬切；转场归⑥）。"""
    keeps = []
    for block in spec["blocks"]:
        for s, e in block:
            keeps.append([float(s), float(e)])
    return keeps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help="clip_NN_spec.json（source/blocks/crop_vf/mask_boxes）")
    ap.add_argument("--source")
    ap.add_argument("--keeps", help='"s1,e1 s2,e2 ..." 源秒，按输出顺序')
    ap.add_argument("--crop-vf", default=None)
    ap.add_argument("--mask-boxes", default=None, help='"x,y,w,h;x,y,w,h"')
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    a = ap.parse_args()

    if a.spec:
        spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
        source = spec["source"]; keeps = _flatten_spec(spec)
        crop_vf = a.crop_vf or spec.get("crop_vf")
        mask_boxes = spec.get("mask_boxes")
        if a.mask_boxes:
            mask_boxes = [[int(x) for x in g.split(",")] for g in a.mask_boxes.split(";")]
    else:
        if not (a.source and a.keeps):
            raise SystemExit("需 --spec，或 --source + --keeps")
        source = a.source
        keeps = [[float(x) for x in seg.split(",")] for seg in a.keeps.split()]
        crop_vf = a.crop_vf
        mask_boxes = [[int(x) for x in g.split(",")] for g in a.mask_boxes.split(";")] if a.mask_boxes else None

    build(source, keeps, a.out, a.manifest, crop_vf, mask_boxes)


if __name__ == "__main__":
    main()
