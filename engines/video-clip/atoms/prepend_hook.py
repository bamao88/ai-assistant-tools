#!/usr/bin/env python3
"""prepend-hook —— 开篇钩子片 + 快速翻页转场（翻页时正文定格）+ 正文（原子能力）。

钩子(打字卡) → 翻页(xfade slide，快) → 正文。翻页期间正文「定格在第一帧」(暂停)，
翻页结束后正文才真正开始播放——衔接更自然。两路自动统一到正文画幅/帧率，音频随之过渡。
不改原片、幂等；两路缺音轨时自动补静音轨，保证 acrossfade 可用。

用法:
  prepend_hook.py 钩子.mp4 正文.mp4 输出.mp4
  prepend_hook.py 钩子.mp4 正文.mp4 输出.mp4 --flip 0.30 --trans slideleft --fps 30
翻页可选 xfade: slideleft/wipeleft/smoothleft/squeezeh（slideleft 最像翻页）
"""
from __future__ import annotations
import argparse, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vutil import run, probe, ensure_parent  # noqa: E402

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-ar", "48000", "-ac", "2"]


def _run(cmd):
    r = run(cmd)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg 失败:\n{' '.join(map(str, cmd))}\n{r.stderr[-900:]}")


def _norm(src, dst, W, H, fps, has_audio):
    """统一到 W×H/fps、yuv420p，并把片段规整成「画音严格等长的整体」。

    ★片段画音整体原则：片段是不可分割的画音对象，转场/拼接必须按它「同一条时间线」摆。
    源素材常画音不等长（如钩子画 5.800s / 音 5.208s）；这里把音频补静音到视频时长
    （apad 无限补 + -shortest 锁到视频长度），让对象天生合格——之后 xfade(按视频)和
    acrossfade(按音频末尾)就落在同一个边界，正片不会被错位（这是 0619 正片声音超前 0.59s 的根因修复）。"""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    if has_audio:
        # 音频补齐到视频时长：apad 无限补静音，-shortest 让输出在视频流结束时收尾 → 画音等长
        cmd += ["-vf", vf, "-af", "apad", "-r", str(fps), "-shortest", *ENC, str(dst)]
    else:
        # 缺音轨：补一条与视频等长的静音轨（anullsrc 无限 + -shortest 锁到视频长）
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-vf", vf, "-r", str(fps), "-shortest", "-map", "0:v", "-map", "1:a", *ENC, str(dst)]
    _run(cmd)


def main():
    ap = argparse.ArgumentParser(description="开篇钩子 + 翻页转场(正文定格) + 正文")
    ap.add_argument("hook"); ap.add_argument("body"); ap.add_argument("out")
    ap.add_argument("--flip", type=float, default=0.30, help="翻页时长(秒)，越小越快(默认0.30)")
    ap.add_argument("--trans", default="slideleft", help="xfade 转场名(默认slideleft)")
    ap.add_argument("--fps", type=int, default=30, help="统一目标帧率(默认30)")
    a = ap.parse_args()

    for p in (a.hook, a.body):
        if not Path(p).exists():
            raise SystemExit(f"输入不存在: {p}")
    Wb, Hb, _bd, body_audio = probe(a.body)
    _wh, _hh, hook_dur, hook_audio = probe(a.hook)
    if Wb == 0 or hook_dur <= 0:
        raise SystemExit("读不到输入视频")
    out = ensure_parent(a.out)
    fps, flip = a.fps, a.flip

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        hook, body = td / "hook.mp4", td / "body.mp4"
        _norm(a.hook, hook, Wb, Hb, fps, hook_audio)
        _norm(a.body, body, Wb, Hb, fps, body_audio)
        # 正文第一帧 → 定格 flip 秒(静音)，作为翻页期间的「暂停」画面
        f1 = td / "f1.png"
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(body), "-frames:v", "1", str(f1)])
        freeze = td / "freeze.mp4"
        _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", f"{flip}", "-i", str(f1),
              "-f", "lavfi", "-t", f"{flip}", "-i", "anullsrc=r=48000:cl=stereo",
              "-vf", f"scale={Wb}:{Hb},setsar=1,fps={fps},format=yuv420p", "-r", str(fps),
              "-shortest", *ENC, str(freeze)])
        body2, cl = td / "body2.mp4", td / "cl.txt"
        cl.write_text(f"file '{freeze}'\nfile '{body}'\n")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
              "-i", str(cl), *ENC, str(body2)])
        off = max(0.0, hook_dur - flip)
        fc = (f"[0:v][1:v]xfade=transition={a.trans}:duration={flip}:offset={off:.3f}[v];"
              f"[0:a][1:a]acrossfade=d={flip}[a]")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(hook), "-i", str(body2),
              "-filter_complex", fc, "-map", "[v]", "-map", "[a]", *ENC,
              "-movflags", "+faststart", str(out)])
    w, h, dur, _a = probe(out)
    print(f"DONE  {out}  {w}x{h}  {dur:.1f}s  (钩子{hook_dur:.1f}s + 翻页{flip}s定格 + 正文)")


if __name__ == "__main__":
    main()
