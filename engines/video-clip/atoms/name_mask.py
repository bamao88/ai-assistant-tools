#!/usr/bin/env python3
"""name-mask —— 遮学员名闪帧（原子能力）。

某区域(如圆形人像 PIP)里出现近黑帧时(腾讯活跃说话人切到没开摄像头的学员=黑底+白名)，
用一张定格画面盖住这些时间段，避免公开成片泄露学员姓名。
源自 make_publish.py，把写死的 PIP 几何改成 --region 参数。幂等、不改原片。

填充图来源(三选一，优先级从高到低)：--fill 指定 / 自动从干净帧抠该区域 / 失败则报错。
可选 --mask 给填充图加圆形等 alpha。可选 --trim 裁掉片头 N 秒。

用法:
  name_mask.py IN.mp4 OUT.mp4 --region 250x250+435+850
  name_mask.py IN.mp4 OUT.mp4 --region 250x250+435+850 --mask circle.png --trim 16.5
  name_mask.py IN.mp4 OUT.mp4 --region 250x250+435+850 --fill goodface.png
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import run, probe, ensure_parent, x264  # noqa: E402


def parse_region(s):
    m = re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", s.strip())
    if not m:
        raise SystemExit("--region 格式应为 WxH+X+Y，如 250x250+435+850")
    return tuple(int(g) for g in m.groups())  # w,h,x,y


def detect_black(src, region, pic_th, pix_th):
    w, h, x, y = region
    vf = f"crop={w}:{h}:{x}:{y},blackdetect=d=0.03:pic_th={pic_th}:pix_th={pix_th}"
    r = run(["ffmpeg", "-i", str(src), "-vf", vf, "-an", "-f", "null", "-"])
    return [(float(m.group(1)), float(m.group(2)))
            for m in re.finditer(r"black_start:([0-9.]+) black_end:([0-9.]+)", r.stderr)]


def good_ts(dur, intervals, lo=0.0):
    bad = lambda t: any(s - 0.3 <= t <= e + 0.3 for s, e in intervals)
    for t in (lo + 0.8, dur * 0.5, dur * 0.35, dur * 0.65, dur * 0.8):
        if lo < t < dur and not bad(t):
            return round(t, 2)
    t = lo + 0.1
    while t < dur:
        if not bad(t):
            return round(t, 2)
        t += 0.2
    return round(dur * 0.5, 2)


def main():
    ap = argparse.ArgumentParser(description="遮学员名闪帧(区域黑帧检测+定格覆盖)")
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--region", required=True, help="检测/覆盖区域 WxH+X+Y")
    ap.add_argument("--fill", help="覆盖用定格图(默认自动从干净帧抠该区域)")
    ap.add_argument("--mask", help="给覆盖图加 alpha 的灰度遮罩(如圆形)")
    ap.add_argument("--trim", type=float, default=0.0, help="裁掉片头 N 秒")
    ap.add_argument("--pic_th", type=float, default=0.65)
    ap.add_argument("--pix_th", type=float, default=0.10)
    a = ap.parse_args()

    src = Path(a.input)
    if not src.exists():
        raise SystemExit(f"输入不存在: {src}")
    out = ensure_parent(a.output)
    _w, _h, dur, has_audio = probe(src)
    rw, rh, rx, ry = parse_region(a.region)

    intervals = detect_black(src, (rw, rh, rx, ry), a.pic_th, a.pix_th)
    iv = [(s, e) for (s, e) in intervals if e > a.trim]   # 片头被裁掉的黑帧不用管
    need_overlay = bool(iv)
    need_trim = a.trim > 0.05

    if not need_overlay and not need_trim:
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-c", "copy", str(out)])
        if r.returncode != 0:
            raise SystemExit(f"ffmpeg 失败：{r.stderr[-400:]}")
        print(f"DONE(copy)  {out}  无黑帧/无裁剪")
        return

    inputs = ["-i", str(src)]
    fc_pre = ""
    if need_overlay:
        # 准备填充图：用户给的 --fill，或从干净帧抠该区域
        fill = Path(a.fill) if a.fill else out.with_suffix(".fill.png")
        if not a.fill:
            ts = good_ts(dur, intervals, a.trim)
            ex = ["ffmpeg", "-y", "-ss", str(ts), "-i", str(src),
                  "-vf", f"crop={rw}:{rh}:{rx}:{ry}", "-frames:v", "1", str(fill), "-loglevel", "error"]
            run(ex)
        # 可选给填充图加 alpha 遮罩
        if a.mask:
            inputs += ["-i", str(fill), "-i", str(a.mask)]
            fc_pre = "[1:v]format=rgba[fc];[fc][2:v]alphamerge[fill];"
            fillref = "[fill]"
        else:
            inputs += ["-i", str(fill)]
            fillref = "[1:v]"
        enable = "+".join(f"between(t,{max(0, s-0.05):.2f},{e+0.05:.2f})" for s, e in iv)
        base = f"[0:v]{fillref}overlay={rx}:{ry}:enable='{enable}'"
    else:
        base = "[0:v]null"

    vtrim = f"trim=start={a.trim}," if need_trim else ""
    atrim = f"atrim=start={a.trim},asetpts=PTS-STARTPTS," if need_trim else ""
    fc = f"{fc_pre}{base}[ov];[ov]{vtrim}setpts=PTS-STARTPTS[v]"
    maps = ["-map", "[v]"]
    if has_audio:
        fc += f";[0:a]{atrim}anull[a]"
        maps += ["-map", "[a]"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, *maps,
           *x264(audio=has_audio), "-movflags", "+faststart", str(out)]
    r = run(cmd)
    if not a.fill:
        Path(out.with_suffix(".fill.png")).unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败：{r.stderr[-600:]}")
    tags = []
    if need_overlay: tags.append(f"遮{len(iv)}段")
    if need_trim: tags.append(f"裁片头{a.trim}s")
    print(f"DONE  {out}  {' / '.join(tags)}")


if __name__ == "__main__":
    main()
