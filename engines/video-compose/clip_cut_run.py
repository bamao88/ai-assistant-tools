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


# 阶段顺序（resumable 边界，对齐六环）；--from 跳过它之前的阶段、复用已落盘产物
STAGES = ["rough_cut", "trim", "subtitle", "cast", "assemble"]
# 真源（小·有它们+源就能确定性重生一切，永远留） vs 缓存（大视频·可清后重生）
TRUTH = ["cut_manifest.json", "clip.srt", "clip.aifix.srt", "clip.final.srt"]
CACHE = ["body.mp4", "trimmed.mp4", "final.mp4", "vocals.wav", "vocals_trimmed.wav",
         "body_subbed.mp4", "titled.mp4"]   # 成片.mp4 是交付物，不当缓存清


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job", help="job 规格 JSON")
    ap.add_argument("--from", dest="from_stage", default="rough_cut", choices=STAGES,
                    help="从某阶段重跑，复用上游已落盘产物（改字幕→--from cast；只改组装→--from assemble）")
    ap.add_argument("--cleanup-cache", action="store_true", help="成功后删大视频缓存，只留真源(账本+srt)+成片")
    a = ap.parse_args()
    job = json.loads(Path(a.job).read_text(encoding="utf-8"))

    out = Path(job["out_dir"]).resolve(); out.mkdir(parents=True, exist_ok=True)
    profile = job.get("profile", "zh_main")
    speed = float(job.get("speed", 1.2))
    manifest = out / "cut_manifest.json"
    body, trimmed, final = out / "body.mp4", out / "trimmed.mp4", out / "final.mp4"
    vocals, vocals_t = out / "vocals.wav", out / "vocals_trimmed.wav"
    srt = out / "clip.srt"
    from_idx = STAGES.index(a.from_stage)

    def do(stage):
        return STAGES.index(stage) >= from_idx

    def need(path, stage):
        if not Path(path).exists():
            raise SystemExit(f"--from {a.from_stage} 需要上游产物 {Path(path).name}（来自 {stage} 阶段），但不存在；请先跑该阶段")

    # ── ③3a 粗剪 ──
    if do("rough_cut"):
        print("③ 裁剪 3a 粗剪·拼身子（源适配 crop/mask 同趟）")
        if job.get("spec"):
            sh([sys.executable, CLIP / "rough_cut.py", "--spec", job["spec"], "--out", body, "--manifest", manifest])
        else:
            sh([sys.executable, CLIP / "rough_cut.py", "--source", job["source"], "--keeps", job["keeps"],
                "--out", body, "--manifest", manifest] +
               (["--crop-vf", job["crop_vf"]] if job.get("crop_vf") else []) +
               (["--mask-boxes", job["mask_boxes"]] if job.get("mask_boxes") else []))
    else:
        need(body, "rough_cut"); print(f"复用 {body.name}（--from {a.from_stage}）")

    # ── ③ 去噪 + 去静音 + 变速（trim 阶段）──
    if do("trim"):
        if job.get("vocals"):
            print("用 job 提供的现成干净人声 REF")
            sh(["ffmpeg", "-y", "-loglevel", "error", "-i", job["vocals"],
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", vocals])
        else:
            print("源适配·带噪 denoise_voice（demucs·缺失优雅跳过抽原音轨）")
            sh([sys.executable, CLIP / "denoise_voice.py", "--in", body, "--out", vocals])
        print("③ 裁剪 3c 去长静音（吐区间记账·同步裁人声）")
        sh([sys.executable, CLIP / "trim_silence.py", "--ref", vocals, "--in", body, "--out", trimmed,
            "--apply-to", f"{vocals}:{vocals_t}", "--manifest", manifest])
        print("③ 裁剪 3d 固定变速 + 换干净轨（factor 记账）")
        sh([sys.executable, CLIP / "speed_adapt.py", str(trimmed), str(final),
            "--fixed", str(speed), "--replace-audio", str(vocals_t), "--manifest", str(manifest)])
    else:
        need(final, "trim"); need(manifest, "trim"); print(f"复用 {final.name} + 账本（--from {a.from_stage}）")

    # ── ④ 字幕(文字) ──
    if do("subtitle"):
        print("④ 字幕 subtitle_align（照账本重放搬时间）")
        sh([sys.executable, "-m", "video_slicer.subtitle_align", "--manifest", manifest,
            "--words", job["words"], "--out", srt] + (["--fixes", job["fixes"]] if job.get("fixes") else []),
           cwd=SLICER)
        final_srt = srt
        if job.get("ai_fix"):
            print("④ 字幕 subtitle_ai_fix(LLM 1:1) + subtitle_protect(别动清单钉回)")
            aifix = out / "clip.aifix.srt"
            sh([sys.executable, CLIP / "subtitle_ai_fix.py", str(srt), str(aifix)])
            final_srt = out / "clip.final.srt"
            sh([sys.executable, "-m", "video_slicer.subtitle_protect", "--pre", srt, "--post", aifix,
                "--out", final_srt] + (["--keeplist", job["keeplist"]] if job.get("keeplist") else []), cwd=SLICER)
    else:
        # 复用已定稿字幕：优先 protect 产物，否则 clip.srt（可手动编辑后 --from cast 重渲）
        final_srt = out / "clip.final.srt" if (out / "clip.final.srt").exists() else srt
        need(final_srt, "subtitle"); print(f"复用字幕 {Path(final_srt).name}（--from {a.from_stage}）")

    # ── ⑤ 铸造(裁剪版药丸) ──
    cast = out / "cast"; subbed = out / "body_subbed.mp4"
    if do("cast"):
        print("⑤ 铸造 subtitles(药丸·clip_cut 版式·复用 framework 几何) + 烧")
        cast.mkdir(exist_ok=True)
        sh([FRAMEWORK_PY, "-m", "video_framework_render.subtitles_cli", "--srt", final_srt,
            "--out-dir", cast, "--layout", "clip_cut", "--profile", profile], cwd=FRAMEWORK)
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", final, "-vf", f"ass={cast / 'zh.ass'}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", subbed])
    else:
        need(subbed, "cast"); print(f"复用 {subbed.name}（--from {a.from_stage}）")

    # ── ⑥ 组装 ──
    cur = subbed
    if do("assemble"):
        if job.get("title"):
            print("⑥ 组装 title_bar（顶部标题条）")
            titled = out / "titled.mp4"
            sh([sys.executable, CLIP / "title_bar.py", str(cur), str(titled), "--text", job["title"], "--style", "label"])
            cur = titled
        if job.get("hook"):
            print("⑥ 组装 prepend_hook（钩子+翻页转场·片段画音整体）")
            chengpian = out / "成片.mp4"
            sh([sys.executable, CLIP / "prepend_hook.py", job["hook"], str(cur), str(chengpian),
                "--flip", "0.30", "--trans", "slideleft"])
            cur = chengpian

    # ── 自检门（含门S 画音流时长一致）──
    print("自检门 len_check + align_check（门A/D/S）")
    if job.get("baseline"):
        subprocess.run([sys.executable, str(CLIP / "len_check.py"), str(final), "--baseline", str(job["baseline"])])
    subprocess.run([sys.executable, str(CLIP / "align_check.py"), "--body", str(final),
                    "--srt", str(final_srt), "--manifest", str(manifest)])
    if (out / "成片.mp4").exists():   # 成片画音整体红线（防转场/组装错位）
        subprocess.run([sys.executable, str(CLIP / "align_check.py"), "--body", str(out / "成片.mp4")])

    if a.cleanup_cache:
        for f in CACHE:
            (out / f).unlink(missing_ok=True)
        print("已清大视频缓存（保留真源 账本+srt + 成片；要重生跑 --from rough_cut）")

    print(f"\n✅ DONE zh_clip_cut → {cur}\n   真源: 账本={manifest.name} + 字幕={Path(final_srt).name}（小·永留）"
          f"\n   缓存: body/trimmed/final…（大·可 --cleanup-cache 清，--from 重跑）")


if __name__ == "__main__":
    main()
