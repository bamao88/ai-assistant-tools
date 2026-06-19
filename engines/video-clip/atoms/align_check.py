#!/usr/bin/env python3
"""align_check —— ③④自检门：对齐自检·出数字。承重墙的质检员。

门D(④后·字幕贴口型)：每条字幕的起点 vs 成片里最近的「人声起音点」偏差，报均值/中位/最大；
                      后半段(承重墙最易飘处)单独报最大偏差，超阈值非零退出。
门A(③后·切点准)：剪辑账本里 trim_silence 去静音造成的「接缝」映射到成片时间，检查每条接缝是否
                  落在成片音频的静音处(切在停顿=好)，报 接缝落静音比例。

不重转写、不依赖外部对齐——只用成片自身音频的能量包络(ffmpeg silencedetect)做证据，便宜可复跑。

用法:
  align_check.py --body 成片.mp4 --srt clip.srt [--manifest m.json] [--tol 0.2] [--noise -30dB]
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path


def _dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0)


def voiced_intervals(media, noise, min_sil=0.25):
    """成片音频 → 静音区间 → 取补集=人声(voiced)区间。"""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(media), "-af",
                          f"silencedetect=noise={noise}:d={min_sil}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    sils, s = [], None
    for m in re.finditer(r"silence_(start|end):\s*(-?[0-9.]+)", out):
        if m.group(1) == "start":
            s = max(0.0, float(m.group(2)))
        elif s is not None:
            sils.append((s, float(m.group(2)))); s = None
    dur = _dur(media)
    voiced, cur = [], 0.0
    for ss, se in sils:
        if ss > cur:
            voiced.append((cur, ss))
        cur = max(cur, se)
    if cur < dur:
        voiced.append((cur, dur))
    return voiced, sils, dur


def parse_srt(path):
    cues, t = [], path.read_text(encoding="utf-8")
    for blk in re.split(r"\n\s*\n", t.strip()):
        mm = re.search(r"(\d+):(\d+):(\d+[.,]\d+)\s*-->\s*(\d+):(\d+):(\d+[.,]\d+)", blk)
        if not mm:
            continue
        g = [x.replace(",", ".") for x in mm.groups()]
        s = int(g[0]) * 3600 + int(g[1]) * 60 + float(g[2])
        e = int(g[3]) * 3600 + int(g[4]) * 60 + float(g[5])
        cues.append((s, e))
    return cues


def nearest_voice_onset(t, voiced):
    """字幕起点 t 到最近人声区间起点的有符号偏差(s)；正=字幕早于起音。"""
    best = None
    for vs, ve in voiced:
        if vs <= t <= ve:
            return t - vs           # 落在人声内：到本区间起音的距离
        d = vs - t                  # 到后续区间起音
        if best is None or abs(d) < abs(best):
            best = d
        d2 = t - ve
        if abs(d2) < abs(best):
            best = d2
    return best if best is not None else 0.0


def final_seams(manifest):
    """trim_silence 去静音接缝映射到成片(final)时间：assembled keeps 的内部接缝 → trimmed → /speed。"""
    ops = manifest.get("ops", [])
    speed = 1.0
    for op in ops:
        if op["op"] == "speed":
            speed = op.get("factor", 1.0)
    seams = []
    for op in ops:
        if op["op"] == "trim_silence":
            off = 0.0; first = True
            for s, e in op["keeps"]:
                if not first:                  # 段与段在 trimmed 轴上的接缝点 = 累计保留时长
                    seams.append(off / speed)
                off += (e - s); first = False
    return seams


def in_silence(t, sils, margin=0.12):
    for ss, se in sils:
        if ss - margin <= t <= se + margin:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--tol", type=float, default=0.2, help="后半段最大允许偏差秒")
    ap.add_argument("--noise", default="-30dB")
    a = ap.parse_args()

    voiced, sils, dur = voiced_intervals(a.body, a.noise)
    cues = parse_srt(Path(a.srt))
    if not cues:
        raise SystemExit("SRT 无字幕条")

    offs = [nearest_voice_onset(s, voiced) for s, _ in cues]
    on_voice = sum(1 for s, _ in cues if any(vs <= s <= ve for vs, ve in voiced))
    abs_off = sorted(abs(o) for o in offs)
    mean = sum(abs_off) / len(abs_off)
    median = abs_off[len(abs_off) // 2]
    mx = abs_off[-1]
    half = dur / 2
    latter = [abs(o) for (s, _), o in zip(cues, offs) if s >= half]
    latter_max = max(latter) if latter else 0.0

    print("== 门D 字幕↔起音对齐 ==")
    print(f"  字幕{len(cues)}条 落人声内 {on_voice}/{len(cues)} ({100*on_voice//len(cues)}%)")
    print(f"  起音偏差 |mean|={mean:.3f}s |median|={median:.3f}s |max|={mx:.3f}s")
    print(f"  后半段(>{half:.1f}s) 最大偏差={latter_max:.3f}s  阈值±{a.tol}s → {'PASS' if latter_max <= a.tol else 'FAIL'}")

    seam_ok = None
    if a.manifest and Path(a.manifest).exists():
        man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
        seams = final_seams(man)
        if seams:
            in_sil = sum(1 for t in seams if in_silence(t, sils))
            seam_ok = in_sil == len(seams)
            print("== 门A 去静音接缝↔停顿 ==")
            print(f"  接缝{len(seams)}处 落静音处 {in_sil}/{len(seams)} ({100*in_sil//len(seams)}%) → {'PASS' if seam_ok else 'WARN'}")

    fail = latter_max > a.tol
    sys.exit(2 if fail else 0)


if __name__ == "__main__":
    main()
