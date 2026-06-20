#!/usr/bin/env python3
"""clip_cut_run —— zh_clip_cut 链式执行器：把六环原子按序串起来端到端出片，剪辑账本在原子间流转。

组合层编排（依赖单向 compose→各引擎；本文件只指挥，不产原子）。run.py --run zh_clip_cut 委派到这里。

WS-6 伴随轨重构（doc/bug/ws6_chain-clip01-音画字幕-诊断.md）：字幕全程走 .srt「便签」，谁切画面谁就
按同一把刀把便签一起裁/缩/偏移，像素只在最后一步烧一次。新顺序：

  ③a 粗剪 → ④字幕换算(源→assembled) → [④改字] → ③取人声 → ③c 去静音(画+音+字幕同刀)
  → ③d 变速(画+音+字幕同因子) → ⑥加标题 → ⑥拼钩子(画音整体·字幕+hook_dur) → ⑤末次烧字 → 硬门S/D/A

承重墙：③记账(rough_cut/trim/speed) 给门检；字幕便签随各原子的 --srt-in/--srt-out 同步裁缩，绝不事后另算。
门 align_check 升级为硬红线：FAIL 直接 raise 停管线，带病片(音画错位/字幕错位)出不了厂（INV-3）。

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


# 阶段顺序（resumable 边界）；--from 跳过它之前的阶段、复用已落盘产物
#   subtitle 提到 trim 之前：字幕便签先在 assembled 轴锁定，再随 trim/speed/hook 同刀裁缩
STAGES = ["rough_cut", "subtitle", "trim", "assemble"]
# 真源（小·有它们+源就能确定性重生一切，永远留） vs 缓存（大视频·可清后重生）
TRUTH = ["cut_manifest.json", "clip.srt", "clip.final.srt",
         "trimmed.srt", "final.srt", "final_shifted.srt"]
CACHE = ["body.mp4", "trimmed.mp4", "final.mp4", "vocals.wav", "vocals_trimmed.wav",
         "titled.mp4", "成片_nosub.mp4"]   # 成片.mp4 是交付物，不当缓存清


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job", help="job 规格 JSON")
    ap.add_argument("--from", dest="from_stage", default="rough_cut", choices=STAGES,
                    help="从某阶段重跑，复用上游已落盘产物（改字幕文本→编辑 clip.srt 后 --from trim；只改组装/烧字→--from assemble）")
    ap.add_argument("--cleanup-cache", action="store_true", help="成功后删大视频缓存，只留真源(账本+srt)+成片")
    ap.add_argument("--no-gate-raise", action="store_true", help="门 FAIL 不停管线（仅调试；默认硬红线 INV-3）")
    a = ap.parse_args()
    job = json.loads(Path(a.job).read_text(encoding="utf-8"))

    out = Path(job["out_dir"]).resolve(); out.mkdir(parents=True, exist_ok=True)
    profile = job.get("profile", "zh_main")
    speed = float(job.get("speed", 1.2))
    manifest = out / "cut_manifest.json"
    body, trimmed, final = out / "body.mp4", out / "trimmed.mp4", out / "final.mp4"
    vocals, vocals_t = out / "vocals.wav", out / "vocals_trimmed.wav"
    # 字幕便签链：assembled(clip→clip.final) → trimmed → final → 成片(final_shifted)
    srt_asm = out / "clip.srt"
    srt_asm_fixed = out / "clip.final.srt"
    srt_trimmed = out / "trimmed.srt"
    srt_final = out / "final.srt"
    srt_shifted = out / "final_shifted.srt"
    from_idx = STAGES.index(a.from_stage)

    def do(stage):
        return STAGES.index(stage) >= from_idx

    def need(path, stage):
        if not Path(path).exists():
            raise SystemExit(f"--from {a.from_stage} 需要上游产物 {Path(path).name}（来自 {stage} 阶段），但不存在；请先跑该阶段")

    def gate(media, srt=None, manifest_path=None, label=""):
        """硬门：align_check 跑门S(画音流等长)+门D(字幕↔人声)+门A(接缝↔停顿)，FAIL 即 raise 停管线。"""
        cmd = [sys.executable, str(CLIP / "align_check.py"), "--body", str(media)]
        if srt:
            cmd += ["--srt", str(srt)]
        if manifest_path:
            cmd += ["--manifest", str(manifest_path)]
        print(f"  自检门{(' '+label) if label else ''}: {' '.join(str(c) for c in cmd)}")
        r = subprocess.run([str(c) for c in cmd])
        if r.returncode != 0 and not a.no_gate_raise:
            raise SystemExit(f"❌ 自检门红线 FAIL（{Path(media).name}）— 带病片(音画/字幕错位)不出厂，管线停。"
                             f" 调试可加 --no-gate-raise。")
        return r.returncode

    # ── ③3a 粗剪（首环：重建干净账本，只记 rough_cut，源→assembled）──
    if do("rough_cut"):
        print("③ 裁剪 3a 粗剪·拼身子（源适配 crop/mask 同趟）")
        manifest.unlink(missing_ok=True)   # 全量重跑：账本从 rough_cut 重建，避免 op 叠加
        if job.get("spec"):
            sh([sys.executable, CLIP / "rough_cut.py", "--spec", job["spec"], "--out", body, "--manifest", manifest])
        else:
            sh([sys.executable, CLIP / "rough_cut.py", "--source", job["source"], "--keeps", job["keeps"],
                "--out", body, "--manifest", manifest] +
               (["--crop-vf", job["crop_vf"]] if job.get("crop_vf") else []) +
               (["--mask-boxes", job["mask_boxes"]] if job.get("mask_boxes") else []))
    else:
        need(body, "rough_cut"); print(f"复用 {body.name}（--from {a.from_stage}）")

    # ── ④ 字幕换算（源→assembled 一次）+ 可选改字（1:1 只改字）──
    if do("subtitle"):
        print("④ 字幕 subtitle_align（源→assembled 单次换算·便签锁定在拼好身子轴）")
        sh([sys.executable, "-m", "video_slicer.subtitle_align", "--manifest", manifest,
            "--words", job["words"], "--out", srt_asm] + (["--fixes", job["fixes"]] if job.get("fixes") else []),
           cwd=SLICER)
        sub_asm = srt_asm
        if job.get("ai_fix"):
            print("④ 字幕 subtitle_ai_fix(LLM 1:1) + subtitle_protect(别动清单钉回)")
            aifix = out / "clip.aifix.srt"
            sh([sys.executable, CLIP / "subtitle_ai_fix.py", str(srt_asm), str(aifix)])
            sh([sys.executable, "-m", "video_slicer.subtitle_protect", "--pre", srt_asm, "--post", aifix,
                "--out", srt_asm_fixed] + (["--keeplist", job["keeplist"]] if job.get("keeplist") else []), cwd=SLICER)
            sub_asm = srt_asm_fixed
    else:
        sub_asm = srt_asm_fixed if srt_asm_fixed.exists() else srt_asm
        need(sub_asm, "subtitle"); print(f"复用字幕便签 {sub_asm.name}（--from {a.from_stage}）")

    # ── ③ 取人声 → ③c 去静音(画+音+字幕同刀) → ③d 变速(画+音+字幕同因子) ──
    if do("trim"):
        if job.get("vocals"):
            print("用 job 提供的现成干净人声 REF")
            sh(["ffmpeg", "-y", "-loglevel", "error", "-i", job["vocals"],
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", vocals])
        else:
            print("源适配·带噪 denoise_voice（demucs·缺失优雅跳过抽原音轨）")
            sh([sys.executable, CLIP / "denoise_voice.py", "--in", body, "--out", vocals])
        print("③ 裁剪 3c 去长静音（画+音+字幕便签 同一份 keeps 一起裁）")
        sh([sys.executable, CLIP / "trim_silence.py", "--ref", vocals, "--in", body, "--out", trimmed,
            "--apply-to", f"{vocals}:{vocals_t}", "--srt-in", sub_asm, "--srt-out", srt_trimmed,
            "--manifest", manifest])
        gate(trimmed, label="③c后(门S)")
        print("③ 裁剪 3d 固定变速 + 换干净轨（画+音+字幕便签 同一 factor 一起缩）")
        sh([sys.executable, CLIP / "speed_adapt.py", str(trimmed), str(final),
            "--fixed", str(speed), "--replace-audio", str(vocals_t),
            "--srt-in", str(srt_trimmed), "--srt-out", str(srt_final), "--manifest", str(manifest)])
        # 正片(还没烧字)硬门：门S 画音等长 + 门D 字幕↔人声 + 门A 接缝↔停顿
        gate(final, srt=srt_final, manifest_path=manifest, label="正片(门S/D/A)")
    else:
        need(final, "trim"); need(manifest, "trim"); need(srt_final, "trim")
        print(f"复用 {final.name} + 账本 + {srt_final.name}（--from {a.from_stage}）")

    # ── ⑥ 组装：加标题 → 拼钩子(画音整体·字幕+hook_dur) → ⑤ 末次烧字 ──
    chengpian = out / "成片.mp4"
    if do("assemble"):
        cur_video = final
        cur_srt = srt_final
        if job.get("title"):
            print("⑥ 组装 title_bar（顶部标题条·不动时间·字幕便签透传）")
            titled = out / "titled.mp4"
            sh([sys.executable, CLIP / "title_bar.py", str(cur_video), str(titled),
                "--text", job["title"], "--style", "label"])
            cur_video = titled
        if job.get("hook"):
            print("⑥ 组装 prepend_hook（钩子+翻页转场·片段画音整体·字幕便签 +hook_dur）")
            nosub = out / "成片_nosub.mp4"
            sh([sys.executable, CLIP / "prepend_hook.py", job["hook"], str(cur_video), str(nosub),
                "--flip", "0.30", "--trans", "slideleft",
                "--srt-in", str(cur_srt), "--srt-out", str(srt_shifted)])
            cur_video = nosub
            cur_srt = srt_shifted
        print("⑤ 末次烧字（subtitles 渲药丸 clip_cut 版式 + ffmpeg 一次性烧·文字只过一道编码）")
        cast = out / "cast"; cast.mkdir(exist_ok=True)
        sh([FRAMEWORK_PY, "-m", "video_framework_render.subtitles_cli", "--srt", cur_srt,
            "--out-dir", cast, "--layout", "clip_cut", "--profile", profile], cwd=FRAMEWORK)
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(cur_video), "-vf", f"ass={cast / 'zh.ass'}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "copy", str(chengpian)])
    else:
        need(chengpian, "assemble"); print(f"复用 {chengpian.name}（--from {a.from_stage}）")

    # ── 末端硬门：成片画音整体红线 + 字幕↔人声（防转场/组装/烧字错位）──
    print("自检门 len_check（基线时长）+ align_check（成片 门S/D 硬红线）")
    if job.get("baseline"):
        subprocess.run([sys.executable, str(CLIP / "len_check.py"), str(final), "--baseline", str(job["baseline"])])
    burn_srt = srt_shifted if srt_shifted.exists() else srt_final
    gate(chengpian, srt=burn_srt, label="成片(门S/D)")

    if a.cleanup_cache:
        for f in CACHE:
            (out / f).unlink(missing_ok=True)
        print("已清大视频缓存（保留真源 账本+srt + 成片；要重生跑 --from rough_cut）")

    print(f"\n✅ DONE zh_clip_cut → {chengpian}\n   真源: 账本={manifest.name} + 字幕便签链(clip/trimmed/final/final_shifted.srt)（小·永留）"
          f"\n   缓存: body/trimmed/final/成片_nosub…（大·可 --cleanup-cache 清，--from 重跑）")


if __name__ == "__main__":
    main()
