#!/usr/bin/env python3
"""clip_cut_run —— zh_clip_cut 链式执行器：把六环原子按序串起来端到端出片，剪辑账本在原子间流转。

组合层编排（依赖单向 compose→各引擎；本文件只指挥，不产原子）。run.py --run zh_clip_cut 委派到这里。
按 job 规格跑：③裁剪(rough_cut→[denoise]→trim_silence→speed_adapt 固定档) → ④字幕(subtitle_align→
[subtitle_ai_fix]→subtitle_protect) → ⑤铸造(subtitles 药丸 clip_cut 版式 → 烧) → ⑥组装([title_bar]→
[prepend_hook]) → 自检(len_check/align_check)。承重墙：③记账，④照账本重放。

job 规格 JSON（见 --help 示例）：
  {"spec":"clip_NN_spec.json", "words":"words.json", "profile":"zh_main",
   "fixes":"fixes.json", "keeplist":"keeplist.json", "title":"标题", "hook":"钩子.mp4",
   "speed":1.2, "denoise":false, "ai_fix":false, "baseline":78.683, "out_dir":"out/clip_NN"}

用法: clip_cut_run.py job.json
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINES = HERE.parent                          # engines/
CLIP = ENGINES / "video-clip" / "atoms"
SLICER = ENGINES / "video-slicer"
FRAMEWORK = ENGINES / "video-framework-render"
FRAMEWORK_PY = os.environ.get("VIDEO_FRAMEWORK_PY", str(FRAMEWORK / ".venv" / "bin" / "python"))


def sh(cmd, cwd=None):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run([str(c) for c in cmd], cwd=cwd)
    if r.returncode != 0:
        raise SystemExit(f"步骤失败(exit {r.returncode}): {cmd[0]} ...")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job", help="job 规格 JSON")
    a = ap.parse_args()
    job = json.loads(Path(a.job).read_text(encoding="utf-8"))

    out = Path(job["out_dir"]).resolve(); out.mkdir(parents=True, exist_ok=True)
    profile = job.get("profile", "zh_main")
    speed = float(job.get("speed", 1.2))
    manifest = out / "cut_manifest.json"
    body = out / "body.mp4"

    # ── ③ 裁剪(时间轴) ──
    print("③ 裁剪 3a 粗剪·拼身子（源适配 crop/mask 同趟）")
    if job.get("spec"):
        sh([sys.executable, CLIP / "rough_cut.py", "--spec", job["spec"], "--out", body, "--manifest", manifest])
    else:
        sh([sys.executable, CLIP / "rough_cut.py", "--source", job["source"], "--keeps", job["keeps"],
            "--out", body, "--manifest", manifest] +
           (["--crop-vf", job["crop_vf"]] if job.get("crop_vf") else []) +
           (["--mask-boxes", job["mask_boxes"]] if job.get("mask_boxes") else []))

    # 干净人声：denoise(可选·缺失优雅跳过) 否则抽原音轨
    vocals = out / "vocals.wav"
    print("源适配·带噪 denoise_voice（可选）" if job.get("denoise") else "抽原音轨当人声 REF")
    if job.get("denoise"):
        sh([sys.executable, CLIP / "denoise_voice.py", "--in", body, "--out", vocals])
    else:
        sh([sys.executable, CLIP / "denoise_voice.py", "--in", body, "--out", vocals])  # 无 demucs 自动抽原音

    print("③ 裁剪 3c 去长静音（吐区间记账·同步裁人声）")
    trimmed = out / "trimmed.mp4"; vocals_t = out / "vocals_trimmed.wav"
    sh([sys.executable, CLIP / "trim_silence.py", "--ref", vocals, "--in", body, "--out", trimmed,
        "--apply-to", f"{vocals}:{vocals_t}", "--manifest", manifest])

    print("③ 裁剪 3d 固定变速 + 换干净轨（factor 记账）")
    final = out / "final.mp4"
    sh([sys.executable, CLIP / "speed_adapt.py", str(trimmed), str(final),
        "--fixed", str(speed), "--replace-audio", str(vocals_t), "--manifest", str(manifest)])

    # ── ④ 字幕(文字) ──
    print("④ 字幕 subtitle_align（照账本重放搬时间）")
    srt = out / "clip.srt"
    sh([sys.executable, "-m", "video_slicer.subtitle_align", "--manifest", manifest,
        "--words", job["words"], "--out", srt] + (["--fixes", job["fixes"]] if job.get("fixes") else []),
       cwd=SLICER)

    final_srt = srt
    if job.get("ai_fix"):
        print("④ 字幕 subtitle_ai_fix(LLM 1:1) + subtitle_protect(别动清单钉回)")
        aifix = out / "clip.aifix.srt"
        sh([sys.executable, CLIP / "subtitle_ai_fix.py", str(srt), str(aifix)])
        protected = out / "clip.final.srt"
        sh([sys.executable, "-m", "video_slicer.subtitle_protect", "--pre", srt, "--post", aifix,
            "--out", protected] + (["--keeplist", job["keeplist"]] if job.get("keeplist") else []), cwd=SLICER)
        final_srt = protected

    # ── ⑤ 铸造(裁剪版药丸) ──
    print("⑤ 铸造 subtitles(药丸·clip_cut 版式·复用 framework 几何) + 烧")
    cast = out / "cast"; cast.mkdir(exist_ok=True)
    sh([FRAMEWORK_PY, "-m", "video_framework_render.subtitles_cli", "--srt", final_srt,
        "--out-dir", cast, "--layout", "clip_cut", "--profile", profile], cwd=FRAMEWORK)
    subbed = out / "body_subbed.mp4"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", final, "-vf", f"ass={cast / 'zh.ass'}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", subbed])

    # ── ⑥ 组装 ──
    cur = subbed
    if job.get("title"):
        print("⑥ 组装 title_bar（顶部标题条）")
        titled = out / "titled.mp4"
        sh([sys.executable, CLIP / "title_bar.py", str(cur), str(titled), "--text", job["title"], "--style", "label"])
        cur = titled
    if job.get("hook"):
        print("⑥ 组装 prepend_hook（钩子+翻页转场）")
        chengpian = out / "成片.mp4"
        sh([sys.executable, CLIP / "prepend_hook.py", job["hook"], str(cur), str(chengpian),
            "--flip", "0.30", "--trans", "slideleft"])
        cur = chengpian

    # ── 自检门 ──
    print("自检门 len_check + align_check")
    if job.get("baseline"):
        subprocess.run([sys.executable, str(CLIP / "len_check.py"), str(final), "--baseline", str(job["baseline"])])
    subprocess.run([sys.executable, str(CLIP / "align_check.py"), "--body", str(final),
                    "--srt", str(final_srt), "--manifest", str(manifest)])

    print(f"\n✅ DONE zh_clip_cut → {cur}\n   身子={final}  账本={manifest}")


if __name__ == "__main__":
    main()
