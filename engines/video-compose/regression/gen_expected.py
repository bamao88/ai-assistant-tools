#!/usr/bin/env python3
"""gen_expected —— 从冻结的金标准(golden)算出期望值，写 expected.json（回归断言口径·入库跟踪）。

金标准大媒体在 var/zh_main/0619test/golden/（gitignored）；本脚本把它们的【小期望值】
（时长/hash/条数/账本 keeps/G4 页 hash）抽出来存成可入库的 JSON，断言口径才有版本控制。
金标准变了就重跑：python gen_expected.py
"""
from __future__ import annotations
import hashlib, json, os, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GOLDEN = Path(os.environ.get("REGRESSION_GOLDEN", REPO / "var/zh_main/0619test/golden"))
G4 = REPO / "var/zh_main/baseline/_g4_replay/g4_v2_c02_CloudCode是足以载入"


def dur(p):
    return round(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                       "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0), 3)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def srt_cues(p):
    return sum(1 for b in Path(p).read_text(encoding="utf-8").strip().split("\n\n") if "-->" in b)


def main():
    man = json.loads((GOLDEN / "cut_manifest.json").read_text(encoding="utf-8"))
    ops = {o["op"]: o for o in man["ops"]}
    cat = json.loads((HERE.parent / "catalog.json").read_text(encoding="utf-8"))["atoms_index"]
    n_atoms = len(cat); n_staged = sum(1 for m in cat.values() if m.get("stage"))
    exp = {
        "_doc": "回归期望值·从 golden 计算·gen_expected.py 重建。tol 为允许偏差。",
        "golden_dir": str(GOLDEN.relative_to(REPO)),
        "tol": {"dur": 0.12, "ssim_min": 0.98},
        "durations": {
            "body": dur(GOLDEN / "body.mp4"),
            "trimmed": dur(GOLDEN / "trimmed.mp4"),
            "final": dur(GOLDEN / "final.mp4"),
            "vocals": dur(GOLDEN / "vocals.wav"),
            "成片": dur(GOLDEN / "成片.mp4"),
        },
        "manifest": {
            "ops": [o["op"] for o in man["ops"]],
            "rough_cut_keeps": ops["rough_cut"]["keeps"],
            "trim_silence_n_keeps": len(ops["trim_silence"]["keeps"]),
            "trim_removed_sec": ops["trim_silence"].get("removed_sec"),
            "speed_factor": ops["speed"]["factor"],
            "durations": man["durations"],
        },
        "subtitle": {
            "clip_srt_cues": srt_cues(GOLDEN / "clip.srt"),
            "clip_srt_sha": sha(GOLDEN / "clip.srt"),
            "zh_ass_sha": sha(GOLDEN / "zh.ass"),
            "final_protected_sha": sha(GOLDEN / "final_protected.srt"),
        },
        "catalog": {"n_atoms": n_atoms, "all_staged": n_staged == n_atoms, "planned_in_plan": 0},
        "gates": {"len_tol": 0.15, "align_seam_pct_min": 100, "align_drift_ok": True},
    }
    if G4.exists():
        exp["g4"] = {
            "page_sha": [sha(G4 / f"page_{i}.png") for i in range(5)],
            "zh_ass_sha": sha(G4 / "zh.ass"),
            "accel_dur": dur(G4 / "accel.mp4"),
            "dims": "720x1280",
        }
    (HERE / "expected.json").write_text(json.dumps(exp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"expected.json 重建：final={exp['durations']['final']}s, srt={exp['subtitle']['clip_srt_cues']}条, "
          f"manifest ops={exp['manifest']['ops']}" + (f", G4 {len(exp['g4']['page_sha'])} 页" if "g4" in exp else ""))


if __name__ == "__main__":
    main()
