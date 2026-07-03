#!/usr/bin/env python3
"""底图抽帧工具（zh-video-cover 生命周期）。两步，中间由 AI 视觉筛：

  sample : 从口播原片某时间窗密集抽候选帧 + 拼联系表 → AI 按质量标准筛
  promote: 把 AI 选中的候选帧落进轮换池 covers/ 并回填账本

抽帧质量闸 = 张和正脸/睁眼/清晰/无叠字/口型自然/构图能裁(见 cover-kit-evc.json extraction.quality_gate)。
数量不封顶，合格就进；AI 逐张自渲染封面+Read 复核后再 promote。
base_videos.yaml 的 mined_ranges/exhausted 由 AI 自己 Edit（本脚本不碰 yaml）。

依赖：ffmpeg + PIL（跑在 video-clip venv）。零 yaml。
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSET_DIR = Path(__file__).resolve().parent
KIT_PATH = ASSET_DIR / "cover-kit-evc.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def load_kit() -> dict:
    return json.loads(KIT_PATH.read_text(encoding="utf-8"))


def covers_dir(kit: dict) -> Path:
    return Path(kit["shared_assets_dir"]) / kit.get("covers_dir", "covers")


def ledger_file(kit: dict) -> Path:
    return ASSET_DIR / kit.get("lifecycle", {}).get("ledger_file", "pool_ledger_evc.json")


# ---------- sample ----------

def cmd_sample(a) -> int:
    video = Path(a.video).expanduser()
    if not video.exists():
        print(f"error: video not found: {video}", file=sys.stderr)
        return 1
    every = a.every
    out = Path(a.out).expanduser() if a.out else (ASSET_DIR / "generated" /
          f"extract_{video.stem}_{int(a.start)}_{int(a.end)}")
    out.mkdir(parents=True, exist_ok=True)

    # 单趟 ffmpeg 抽帧(每 every 秒一张)，再按时间戳重命名
    tmp_pat = str(out / "raw_%04d.jpg")
    cmd = ["ffmpeg", "-v", "error", "-ss", str(a.start), "-to", str(a.end),
           "-i", str(video), "-vf", f"fps=1/{every}", "-qscale:v", "2", tmp_pat]
    subprocess.run(cmd, check=True)
    raws = sorted(out.glob("raw_*.jpg"))
    cands = []
    for i, r in enumerate(raws):
        t = int(round(a.start + i * every))
        dst = out / f"cand_t{t}s.jpg"
        r.rename(dst)
        cands.append(dst)
    if not cands:
        print(f"error: 没抽到帧(检查时间窗 {a.start}-{a.end} 是否在时长内)", file=sys.stderr)
        return 1

    # 联系表
    sheet = out / "contact_sheet.jpg"
    _contact_sheet(cands, sheet)
    print(json.dumps({
        "candidate_dir": str(out), "contact_sheet": str(sheet), "count": len(cands),
        "candidates": [p.name for p in cands],
        "next": "AI 看 contact_sheet 按质量标准筛→逐张自渲染自检→promote --files 选中的",
    }, ensure_ascii=False, indent=2))
    return 0


def _contact_sheet(cands, out_path: Path) -> None:
    tw = 150
    cols = 8
    rows = (len(cands) + cols - 1) // cols
    im0 = Image.open(cands[0])
    th = int(tw * im0.height / im0.width)
    lab = 22
    sheet = Image.new("RGB", (tw * cols, (th + lab) * rows), "white")
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 15)
    except OSError:
        f = ImageFont.load_default()
    for i, p in enumerate(cands):
        im = Image.open(p).convert("RGB").resize((tw, th))
        x, y = (i % cols) * tw, (i // cols) * (th + lab)
        sheet.paste(im, (x, y))
        d.text((x + 3, y + th + 3), p.stem.replace("cand_", ""), fill=(0, 0, 0), font=f)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=90)


# ---------- promote ----------

def _next_frame_index(cov: Path) -> int:
    mx = 0
    for p in cov.iterdir():
        m = re.match(r"frame-(\d+)\.", p.name)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx + 1


def cmd_promote(a) -> int:
    kit = load_kit()
    cov = covers_dir(kit)
    led_path = ledger_file(kit)
    ledger = json.loads(led_path.read_text(encoding="utf-8")) if led_path.exists() else {}

    cdir = Path(a.candidate_dir).expanduser() if a.candidate_dir else None
    files = [s.strip() for s in a.files.split(",") if s.strip()]
    idx = _next_frame_index(cov)
    added = []
    for fn in files:
        src = Path(fn)
        if not src.is_absolute():
            src = (cdir / fn) if cdir else (ASSET_DIR / fn)
        if not src.exists():
            print(f"error: candidate not found: {src}", file=sys.stderr)
            return 1
        ext = src.suffix.lower() if src.suffix.lower() in IMAGE_EXTS else ".jpg"
        dst = cov / f"frame-{idx:02d}{ext}"
        shutil.copy2(src, dst)
        m = re.search(r"_t(\d+)s", src.name)
        t = int(m.group(1)) if m else None
        ledger[dst.name] = {"source": a.source_id, "t": t, "uses": []}
        added.append({"candidate": src.name, "frame": dst.name, "t": t})
        idx += 1

    led_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "added": added, "pool_now": len([p for p in cov.iterdir()
                                         if p.suffix.lower() in IMAGE_EXTS]),
        "reminder": f"记得 Edit base_videos.yaml：把源 {a.source_id} 的这段时间窗并入 mined_ranges"
                    "（全时间轴覆盖或挑不出好帧则 exhausted:true）。新帧默认 lift 3/16，"
                    "若某张脸偏低/偏高在 kit base_crop.lift_overrides 设。",
    }, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="底图抽帧 sample/promote")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sample", help="从原片时间窗抽候选帧+联系表")
    s.add_argument("--video", required=True, help="口播原片绝对路径(从 base_videos.yaml 取)")
    s.add_argument("--start", type=float, required=True, help="起始秒")
    s.add_argument("--end", type=float, required=True, help="结束秒")
    s.add_argument("--every", type=float, default=2.5, help="每几秒抽一帧(默认2.5)")
    s.add_argument("--out", help="候选输出目录(默认 generated/extract_*)")
    s.set_defaults(func=cmd_sample)

    p = sub.add_parser("promote", help="把选中候选帧落池+记账")
    p.add_argument("--source-id", required=True, help="base_videos.yaml 里的源 id")
    p.add_argument("--files", required=True, help="选中候选帧文件名,逗号分隔(如 cand_t120s.jpg,cand_t145s.jpg)")
    p.add_argument("--candidate-dir", help="候选帧所在目录(sample 输出的 candidate_dir)")
    p.set_defaults(func=cmd_promote)

    a = ap.parse_args(argv)
    try:
        return a.func(a)
    except subprocess.CalledProcessError as e:
        print(f"error: ffmpeg 失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
