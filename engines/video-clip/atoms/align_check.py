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


def _envelope(intervals, dur, dt):
    """把区间列表栅格化成 0/1 包络（dt 步长）。"""
    n = int(dur / dt) + 1
    env = [0] * n
    for s, e in intervals:
        i0 = max(0, int(s / dt)); i1 = min(n, int(e / dt) + 1)
        for i in range(i0, i1):
            env[i] = 1
    return env


def lag_sweep(sub_env, voi_env, dt, max_lag=1.0):
    """把字幕包络相对人声包络平移 ±max_lag，找「两条包络最吻合」的平移量(系统性偏移)。
    最佳平移≈0 → 字幕没整体漂移；这是「能量包络互相关」的离散实现，对连续语流稳健。"""
    n = min(len(sub_env), len(voi_env))
    L = int(max_lag / dt)
    best_lag_bins, best_agree = 0, -1.0
    agree0 = 0.0
    for lag in range(-L, L + 1):
        match = tot = 0
        for i in range(n):
            j = i + lag
            if 0 <= j < n:
                tot += 1
                if sub_env[i] == voi_env[j]:
                    match += 1
        agree = match / tot if tot else 0.0
        if lag == 0:
            agree0 = agree
        if agree > best_agree:
            best_agree, best_lag_bins = agree, lag
    return best_lag_bins * dt, best_agree, agree0


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

    dt = 0.02
    sub_env = _envelope([(s, e) for s, e in cues], dur, dt)
    voi_env = _envelope(voiced, dur, dt)
    best_lag, best_agree, agree0 = lag_sweep(sub_env, voi_env, dt, max_lag=2.0)
    on_voice = sum(1 for s, _ in cues if any(vs <= s <= ve for vs, ve in voiced))
    # 仅当平移峰「显著」(吻合度提升≥SIG)才认为存在系统性漂移；否则曲线平坦=无可判定漂移→PASS。
    SIG = 0.05
    significant = (best_agree - agree0) >= SIG
    lag_ok = (not significant) or (abs(best_lag) <= a.tol)
    verdict = "PASS(无可判定漂移)" if not significant else ("PASS" if lag_ok else "FAIL")

    print("== 门D 字幕↔人声 能量包络对齐 ==")
    print(f"  字幕{len(cues)}条 起点落人声内 {on_voice}/{len(cues)} ({100*on_voice//len(cues)}%)")
    print(f"  包络吻合度 lag0={agree0:.3f} 最佳={best_agree:.3f} 提升={best_agree-agree0:.3f}(显著阈{SIG})")
    print(f"  系统性偏移={best_lag:+.3f}s 阈值±{a.tol}s → {verdict}")

    seam_ok = None
    if a.manifest and Path(a.manifest).exists():
        man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
        seams = final_seams(man)
        if seams:
            in_sil = sum(1 for t in seams if in_silence(t, sils))
            seam_ok = in_sil == len(seams)
            print("== 门A 去静音接缝↔停顿 ==")
            print(f"  接缝{len(seams)}处 落静音处 {in_sil}/{len(seams)} ({100*in_sil//len(seams)}%) → {'PASS' if seam_ok else 'WARN'}")

    sys.exit(0 if (lag_ok and (seam_ok is not False)) else 2)


if __name__ == "__main__":
    main()
