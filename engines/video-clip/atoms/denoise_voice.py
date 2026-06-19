#!/usr/bin/env python3
"""denoise_voice —— 源适配·带噪：demucs 人声分离去噪（换干净人声轨）。可选能力·缺失优雅跳过。

六环阶段化升级 WS-3（源适配·带噪：录屏带"叮"提示音/底噪）。用 demucs 把人声从背景音里分离出来，
产出干净人声 wav，供 trim_silence 当 REF + speed_adapt --replace-audio 换轨。

demucs 是重依赖(torch)，装在可选 audio venv 里。找不到 demucs 时【优雅跳过】：
抽原始音轨当 out(标记"未降噪")并以 exit 0 返回，配方照常往下走(用原音)，绝不因可选能力缺失而崩。

用法:
  denoise_voice.py --in 身子.mp4 --out 人声.wav [--venv engines/video-clip/.venv-audio] [--model htdemucs]
"""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys, tempfile
from pathlib import Path


_REPO = Path(__file__).resolve().parents[3]   # tools/


def _demucs_python(venv):
    """返回能跑 demucs 的 python 解释器；按序探测多个已知位置，找不到返回 None。"""
    cands = []
    if venv:
        cands.append(Path(venv) / "bin" / "python")
    env = os.environ.get("VIDEO_AUDIO_VENV")
    if env:
        cands.append(Path(env) / "bin" / "python")
    # 已知安装位置：video-clip 规范 audio venv + 6-18 既有 .audio_venv（demucs 已装在此）
    cands.append(_REPO / "engines" / "video-clip" / ".venv-audio" / "bin" / "python")
    cands.append(_REPO / "var" / "zh_main" / "0618test" / ".audio_venv" / "bin" / "python")
    cands.append(Path(sys.executable))
    seen = set()
    for py in cands:
        sp = str(py)
        if sp in seen or not Path(py).exists():
            continue
        seen.add(sp)
        if subprocess.run([sp, "-c", "import demucs"], capture_output=True).returncode == 0:
            return sp
    return None


def _extract_audio(src, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-vn", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--venv", default=os.environ.get("VIDEO_AUDIO_VENV", "engines/video-clip/.venv-audio"))
    ap.add_argument("--model", default="htdemucs")
    a = ap.parse_args()

    src = Path(a.inp); out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise SystemExit(f"输入不存在: {src}")

    py = _demucs_python(a.venv)
    if not py:
        _extract_audio(src, out)
        print(f"SKIP denoise_voice(demucs 不可用·优雅跳过)  {out}  ← 原音轨(未降噪)")
        print(f"  装 demucs 启用降噪: python -m venv {a.venv} && {a.venv}/bin/pip install demucs")
        return

    with tempfile.TemporaryDirectory() as td:
        # demucs 抽人声(two-stems)；先抽音轨成 wav 再分离更稳
        wav = Path(td) / "in.wav"; _extract_audio(src, wav)
        r = subprocess.run([py, "-m", "demucs", "--two-stems=vocals", "-n", a.model,
                            "-o", td, str(wav)], capture_output=True, text=True)
        if r.returncode != 0:
            _extract_audio(src, out)
            print(f"WARN demucs 失败·优雅跳过用原音: {r.stderr[-300:]}\nDONE  {out}(未降噪)")
            return
        voc = next(Path(td).rglob("vocals.wav"), None)
        if not voc:
            _extract_audio(src, out); print(f"WARN demucs 无 vocals 输出·用原音  {out}"); return
        # 统一成 48k 立体声 wav
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voc),
                        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(out)], check=True)
        shutil.rmtree(td, ignore_errors=True)
    print(f"DONE denoise_voice(demucs {a.model})  {out}  ← 干净人声")


if __name__ == "__main__":
    main()
