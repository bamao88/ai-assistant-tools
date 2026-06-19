#!/usr/bin/env python3
"""len_check —— ③自检门：身子时长核对，防「烧错身子」。

把成片身子时长和基准(数字或另一文件)比，超阈值非零退出当场停。
承重墙配套：身子若不等于基准，说明③链(rough_cut/trim_silence/speed)某步飘了或烧错了源。

用法:
  len_check.py 身子.mp4 --baseline 78.683 [--tol 0.15]
  len_check.py 身子.mp4 --baseline-file 基准.mp4 [--tol 0.15]
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path


def _dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media")
    ap.add_argument("--baseline", type=float, default=None)
    ap.add_argument("--baseline-file", default=None)
    ap.add_argument("--tol", type=float, default=0.15, help="允许偏差秒(默认0.15≈4帧)")
    a = ap.parse_args()

    if not Path(a.media).exists():
        raise SystemExit(f"不存在: {a.media}")
    got = _dur(a.media)
    base = a.baseline if a.baseline is not None else (_dur(a.baseline_file) if a.baseline_file else None)
    if base is None:
        raise SystemExit("需 --baseline 或 --baseline-file")
    diff = got - base
    ok = abs(diff) <= a.tol
    print(f"len_check: 身子={got:.3f}s 基准={base:.3f}s 偏差={diff:+.3f}s 阈值=±{a.tol}s → {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
