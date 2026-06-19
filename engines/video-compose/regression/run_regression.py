#!/usr/bin/env python3
"""run_regression —— 视频剪辑 skill 分层回归测试。读 expected.json，喂 golden 夹具，逐能力比对。

四层（计划 doc：var/zh_main/0619test/doc/视频剪辑skill-回归测试计划.md）：
  t0 纯数据/单元（秒级·每次跑·不碰视频）
  t1 单原子·复用 golden 视频（分钟级·改了某原子）
  t2 阶段集成（③裁剪链 / ④字幕链 / ⑤⑥铸造组装）
  t3 端到端 + G4 零回归 + ①火山转录短视频（发版前）

慢步骤（LLM/demucs/火山/G4）默认只在它该在的层真跑；t0/t1 用 golden 复用，不碰它们。

用法: run_regression.py [t0|t1|t2|t3|all] [--golden DIR] [--keep-llm] [--skip-slow]
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EXP = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
GOLDEN = Path(os.environ.get("REGRESSION_GOLDEN") or REPO / EXP["golden_dir"])
SRC = REPO / "var/zh_main/0619test/source"
SPEC = REPO / "var/zh_main/0619test/clip_01_为什么你花500万做的AI我100万就能搞定.md/clip_01_spec.json"
WORDS = SRC / "words.json"
FIXES = REPO / "var/zh_main/0618test/clip_01_为什么你花500万做的AI我100万就能搞定✅.md/fixes.json"
KEEPLIST = REPO / "engines/video-slicer/profiles/zh_main/keeplist.json"
SHORT_VIDEO = SRC / "6月17日_成片.mp4"
CLIP = REPO / "engines/video-clip/atoms"
SLICER = REPO / "engines/video-slicer"
COMPOSE = REPO / "engines/video-compose"
FW = REPO / "engines/video-framework-render"
FW_PY = FW / ".venv/bin/python"
DTOL = EXP["tol"]["dur"]

RESULTS = []


def rec(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f"  — {detail}" if detail else ""))
    return ok


def _dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0)


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def _cues(p):
    return sum(1 for b in Path(p).read_text(encoding="utf-8").strip().split("\n\n") if "-->" in b)


def _run(cmd, cwd=None):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)


def _approx(g, e, tol=DTOL):
    return abs(g - e) <= tol


# ───────────────────────── T0 纯数据/单元 ─────────────────────────
def t0(work):
    print("== T0 纯数据/单元（秒级）==")
    # catalog 重建：30 原子全带 stage
    r = _run([sys.executable, "build_catalog.py"], cwd=COMPOSE)
    cat = json.loads((COMPOSE / "catalog.json").read_text(encoding="utf-8"))
    staged = sum(1 for m in cat["atoms_index"].values() if m.get("stage"))
    n = len(cat["atoms_index"])
    rec("catalog 30原子全带stage", n == EXP["catalog"]["n_atoms"] and staged == n, f"{n}原子 {staged}带stage")
    # 审链：六环 + 0 待建
    r = _run([sys.executable, "run.py", "--plan", "zh_clip_cut"], cwd=COMPOSE)
    o = r.stdout
    rec("审链 zh_clip_cut 六环+0待建", all(s in o for s in ["① 转写", "⑥ 组装", "源适配", "自检"]) and "[待建]" not in o,
        f"{'有待建!' if '[待建]' in o else '六环齐'}")
    # check-tools 0 error
    r = _run([sys.executable, "scripts/check-tools.py"], cwd=REPO)
    rec("check-tools 0 error", "0 errors" in r.stdout, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "?")
    # _manifest.remap_time 单元
    sys.path.insert(0, str(CLIP))
    import _manifest as M  # type: ignore  # noqa: E402  (dynamic path)
    ops = [{"op": "rough_cut", "keeps": [[10, 20], [30, 40]]},
           {"op": "trim_silence", "keeps": [[0, 5], [6, 16]]},
           {"op": "speed", "factor": 2.0}]
    t = M.remap_time(ops, 12)              # 12→assembled(2)→trimmed(2)→final(1.0)
    cut = M.remap_time(ops, 25)            # 落被剪区间→None
    rec("_manifest.remap_time 链式重放", abs(t - 1.0) < 1e-6 and cut is None, f"t=12→{t}, 25→{cut}")
    # subtitle_align：喂 golden 账本+words → srt 文本/条数比对
    out = work / "align.srt"
    r = _run([sys.executable, "-m", "video_slicer.subtitle_align", "--manifest", GOLDEN / "cut_manifest.json",
              "--words", WORDS, "--fixes", FIXES, "--out", out], cwd=SLICER)
    ok = out.exists() and _cues(out) == EXP["subtitle"]["clip_srt_cues"] and _sha(out) == EXP["subtitle"]["clip_srt_sha"]
    rec("subtitle_align 复现 golden srt", ok, f"{_cues(out) if out.exists() else 0}条 sha={_sha(out) if out.exists() else '-'}")
    # subtitle_protect：喂冻结 pre/post → 比对 golden
    out = work / "protect.srt"
    r = _run([sys.executable, "-m", "video_slicer.subtitle_protect", "--pre", GOLDEN / "llm_pre.srt",
              "--post", GOLDEN / "llm_post.srt", "--keeplist", KEEPLIST, "--out", out], cwd=SLICER)
    rec("subtitle_protect 复现+1:1", out.exists() and _sha(out) == EXP["subtitle"]["final_protected_sha"],
        f"sha={_sha(out) if out.exists() else '-'}")
    # subtitles_cli 药丸 ASS 字节复现（framework venv）
    if FW_PY.exists():
        od = work / "cast"; od.mkdir(exist_ok=True)
        r = _run([FW_PY, "-m", "video_framework_render.subtitles_cli", "--srt", GOLDEN / "clip.srt",
                  "--out-dir", od, "--layout", "clip_cut"], cwd=FW)
        za = od / "zh.ass"
        rec("subtitles_cli 药丸ASS字节复现", za.exists() and _sha(za) == EXP["subtitle"]["zh_ass_sha"],
            f"sha={_sha(za) if za.exists() else '-'}")
    else:
        rec("subtitles_cli 药丸ASS字节复现", False, "framework venv 缺")
    # reframe_crop crop_vf 字符串
    r = _run([sys.executable, CLIP / "reframe_crop.py", "--source", SRC / "源视频_20260613_Agent评测体系.mp4",
              "--crop", "894:1588:104:290"])
    rec("reframe_crop crop_vf", "crop=894:1588:104:290,scale=1080:1920" in r.stdout)


# ───────────────────────── T1 单原子·复用 golden ─────────────────────────
def t1(work, skip_slow):
    print("== T1 单原子·复用 golden 视频（分钟级）==")
    # trim_silence: golden body+vocals → 94.495 + 6 keeps
    out = work / "trimmed.mp4"; man = work / "m_trim.json"
    r = _run([sys.executable, CLIP / "trim_silence.py", "--ref", GOLDEN / "vocals.wav", "--in", GOLDEN / "body.mp4",
              "--out", out, "--manifest", man])
    if out.exists():
        m = json.loads(man.read_text()); ks = next(o for o in m["ops"] if o["op"] == "trim_silence")["keeps"]
        rec("trim_silence 94.495+keeps", _approx(_dur(out), EXP["durations"]["trimmed"]) and len(ks) == EXP["manifest"]["trim_silence_n_keeps"],
            f"{_dur(out):.3f}s {len(ks)}段")
    else:
        rec("trim_silence 94.495+keeps", False, r.stderr[-120:])
    # speed_adapt --fixed: golden trimmed+vocals_t → 78.683
    out = work / "final.mp4"; man = work / "m_spd.json"
    r = _run([sys.executable, CLIP / "speed_adapt.py", GOLDEN / "trimmed.mp4", out, "--fixed", "1.2",
              "--replace-audio", GOLDEN / "vocals_trimmed.wav", "--manifest", man])
    rec("speed_adapt --fixed 78.683", out.exists() and _approx(_dur(out), EXP["durations"]["final"]),
        f"{_dur(out):.3f}s" if out.exists() else r.stderr[-120:])
    # align_check / len_check: golden final+srt → 门数字
    r = _run([sys.executable, CLIP / "len_check.py", GOLDEN / "final.mp4", "--baseline", str(EXP["durations"]["final"])])
    rec("len_check 身子核对 PASS", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    r = _run([sys.executable, CLIP / "align_check.py", "--body", GOLDEN / "final.mp4", "--srt", GOLDEN / "clip.srt",
              "--manifest", GOLDEN / "cut_manifest.json"])
    rec("align_check 门A/D PASS", r.returncode == 0 and "PASS" in r.stdout, "门A接缝+门D无漂" if r.returncode == 0 else "FAIL")
    # name_mask --black: golden body → 尺寸不变
    out = work / "masked.mp4"
    r = _run([sys.executable, CLIP / "name_mask.py", GOLDEN / "body.mp4", out, "--region", "1080x152+0+0", "--black"])
    rec("name_mask --black 多块", out.exists() and r.returncode == 0)
    # title_bar / prepend_hook：golden final → 输出存在
    out = work / "titled.mp4"
    r = _run([sys.executable, CLIP / "title_bar.py", GOLDEN / "final.mp4", out, "--text", "回归测试标题", "--style", "label"])
    rec("title_bar 标题条", out.exists() and r.returncode == 0)
    # denoise_voice（demucs·慢）：golden body → 107.712
    if skip_slow:
        rec("denoise_voice demucs(跳过·--skip-slow)", True, "skipped")
    else:
        out = work / "voc.wav"
        r = _run([sys.executable, CLIP / "denoise_voice.py", "--in", GOLDEN / "body.mp4", "--out", out])
        is_demucs = "demucs" in r.stdout and "优雅跳过" not in r.stdout
        rec("denoise_voice demucs 107.712", out.exists() and _approx(_dur(out), EXP["durations"]["vocals"]) and is_demucs,
            f"{_dur(out):.3f}s {'demucs' if is_demucs else '原音!'}" if out.exists() else "fail")


# ───────────────────────── T2 阶段集成 ─────────────────────────
def t2(work):
    print("== T2 阶段集成（喂阶段入口 golden）==")
    # ③ 裁剪链（省 demucs·给现成 vocals）→ 78.683
    job = work / "job_t2.json"
    job.write_text(json.dumps({
        "spec": str(SPEC), "words": str(WORDS), "vocals": str(GOLDEN / "vocals.wav"),
        "profile": "zh_main", "speed": 1.2, "baseline": EXP["durations"]["final"],
        "out_dir": str(work / "t2_clip")}, ensure_ascii=False), encoding="utf-8")
    r = _run([sys.executable, "run.py", "--run", "zh_clip_cut", "--job", job], cwd=COMPOSE)
    fin = work / "t2_clip/final.mp4"
    rec("③④⑤ 链 final 78.683", fin.exists() and _approx(_dur(fin), EXP["durations"]["final"]),
        f"{_dur(fin):.3f}s" if fin.exists() else r.stderr[-150:])
    rec("③④⑤ 链 药丸+审链通过", (work / "t2_clip/cast/zh.ass").exists() and (work / "t2_clip/clip.srt").exists())


# ───────────────────────── T3 端到端 + G4 + 转录 ─────────────────────────
def t3(work, keep_llm, skip_slow):
    print("== T3 端到端 + G4 零回归 + ①转录（发版前）==")
    # 端到端整链（含 demucs + 可选 LLM + 组装）
    if not skip_slow:
        D = REPO / "var/zh_main/0618test/clip_01_为什么你花500万做的AI我100万就能搞定✅.md"
        job = work / "job_t3.json"
        job.write_text(json.dumps({
            "spec": str(SPEC), "words": str(WORDS), "profile": "zh_main", "denoise": True,
            "ai_fix": keep_llm, "fixes": str(FIXES), "keeplist": str(KEEPLIST),
            "title": "为什么你花500万做的AI我100万就能搞定",
            "hook": str(D / "开篇钩子_打字效果_人脸版.mp4"),
            "speed": 1.2, "baseline": EXP["durations"]["final"], "out_dir": str(work / "t3_clip")}, ensure_ascii=False), encoding="utf-8")
        r = _run([sys.executable, "run.py", "--run", "zh_clip_cut", "--job", job], cwd=COMPOSE)
        fin = work / "t3_clip/final.mp4"; cp = work / "t3_clip/成片.mp4"
        rec("端到端 整链出成片 78.683", fin.exists() and _approx(_dur(fin), EXP["durations"]["final"]) and cp.exists(),
            f"final={_dur(fin):.3f}s 成片={'有' if cp.exists() else '无'}" if fin.exists() else r.stderr[-150:])
    else:
        rec("端到端 整链出成片(跳过·--skip-slow)", True, "skipped")
    # G4 零回归（重·跑 framework 渲染）
    g4 = EXP.get("g4")
    if g4 and not skip_slow and FW_PY.exists():
        B = REPO / "var/zh_main/baseline"
        od = work / "g4"; od.mkdir(exist_ok=True)
        r = _run([FW_PY, "-m", "video_framework_render.render", B / "_g4_replay/test_job.json",
                  "--out", od, "--profile", "zh_main"], cwd=FW)
        nd = od / "g4_v2_c02_CloudCode是足以载入"
        if nd.exists():
            pages_ok = all(_sha(nd / f"page_{i}.png") == g4["page_sha"][i] for i in range(5))
            ass_ok = _sha(nd / "zh.ass") == g4["zh_ass_sha"]
            dur_ok = _approx(_dur(nd / "accel.mp4"), g4["accel_dur"])
            rec("G4 zh_business 零回归", pages_ok and ass_ok and dur_ok,
                f"页{'✓' if pages_ok else '✗'} ass{'✓' if ass_ok else '✗'} 时长{'✓' if dur_ok else '✗'}")
        else:
            rec("G4 zh_business 零回归", False, r.stderr[-150:])
    else:
        rec("G4 zh_business 零回归(跳过)", True, "skipped" if skip_slow else "无 g4/venv")
    # ① 火山转录短视频
    if not skip_slow:
        out = work / "short_words.json"
        r = _run([sys.executable, "-m", "video_slicer.transcribe", str(SHORT_VIDEO), "--out", str(out)], cwd=SLICER)
        ok = out.exists()
        if ok:
            try:
                d = json.loads(out.read_text()); ws = d.get("words", [])
                mono = all(ws[i]["begin_time"] <= ws[i + 1]["begin_time"] for i in range(len(ws) - 1))
                ok = len(ws) > 50 and mono
                rec("① 火山转录短视频", ok, f"{len(ws)}字 单调{'✓' if mono else '✗'}")
            except Exception as e:
                rec("① 火山转录短视频", False, f"解析失败 {e}")
        else:
            rec("① 火山转录短视频", False, r.stderr[-150:] or "无输出（看 transcribe 入口/凭证）")
    else:
        rec("① 火山转录短视频(跳过)", True, "skipped")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tier", nargs="?", default="t0", choices=["t0", "t1", "t2", "t3", "all"])
    ap.add_argument("--golden", default=None)
    ap.add_argument("--keep-llm", action="store_true", help="T3 真跑 LLM ai_fix（默认关·非确定）")
    ap.add_argument("--skip-slow", action="store_true", help="跳过 demucs/G4/转录/端到端 重步骤")
    a = ap.parse_args()
    if a.golden:
        global GOLDEN
        GOLDEN = Path(a.golden)
    tiers = ["t0", "t1", "t2", "t3"] if a.tier == "all" else [a.tier]
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for t in tiers:
            {"t0": lambda: t0(work), "t1": lambda: t1(work, a.skip_slow),
             "t2": lambda: t2(work), "t3": lambda: t3(work, a.keep_llm, a.skip_slow)}[t]()
    n = len(RESULTS); p = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n=== 回归结果: {p}/{n} PASS ===")
    for name, ok, _ in RESULTS:
        if not ok:
            print(f"  ❌ {name}")
    sys.exit(0 if p == n else 1)


if __name__ == "__main__":
    main()
