"""从源视频按 keep 时间区间 trim+concat 切出干净片段。搬 videocut-zh `cut_clip.py`。

输入：源视频 + keep_spans `[[start_sec,end_sec],...]`（已去口水的保留区间）。
输出：clip.mp4（按区间拼接，跳切掉口水/静音）+ 可选 clip 相对 SRT。
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _ass_t(sec: float) -> str:
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def cut_clip(video: str | Path, keep_spans: list[list[float]], out_mp4: str | Path,
             crop: str | None = None, crf: int = 20, preset: str = "veryfast") -> Path:
    """源视频 + keep_spans → clip.mp4（trim 每段 + concat）。crop 如 'crop=1080:800:0:1120' 裁下半。"""
    keep = [(float(s), float(e)) for s, e in keep_spans if float(e) - float(s) > 0.05]
    if not keep:
        raise ValueError("无有效保留区间")
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    vf = f",{crop}" if crop else ""
    lines = []
    for i, (s, e) in enumerate(keep):
        lines.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS{vf}[v{i}];")
        lines.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
    lines.append("".join(f"[v{i}][a{i}]" for i in range(len(keep))) +
                 f"concat=n={len(keep)}:v=1:a=1[outv][outa]")
    flt = out_mp4.with_suffix(".filter.txt")
    flt.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-filter_complex_script", str(flt),
         "-map", "[outv]", "-map", "[outa]", "-r", "25", "-c:v", "libx264", "-preset", "medium",
         "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(out_mp4)],
        check=True,
    )
    return out_mp4


def relative_srt(kept_words: list[dict], keep_spans: list[list[float]], out_srt: str | Path,
                 max_chars: float = 14.0) -> Path:
    """保留字 + keep_spans → clip 相对时间轴 SRT（搬 cut_build out_time 重映射）。"""
    def out_time(src: float) -> float:
        t = 0.0
        for s, e in keep_spans:
            if src >= e:
                t += e - s
            elif src > s:
                return t + (src - s)
            else:
                return t
        return t

    def w_width(c: str) -> float:
        return 0.5 if c.isascii() and (c.isalnum()) else 1.0

    subs = []
    line: list[dict] = []
    width = 0.0

    def emit() -> None:
        if not line:
            return
        a = out_time(line[0]["start"]); b = out_time(line[-1]["end"])
        txt = "".join(w["text"] for w in line).strip()
        if b > a + 0.05 and txt:
            subs.append((a, b, txt))

    for w in kept_words:
        tw = sum(w_width(c) for c in w["text"])
        if line and width + tw > max_chars:
            emit(); line = []; width = 0.0
        line.append(w); width += tw
    emit()

    out_srt = Path(out_srt)
    with out_srt.open("w", encoding="utf-8") as f:
        for k, (a, b, t) in enumerate(subs, 1):
            f.write(f"{k}\n{_ass_t(a)} --> {_ass_t(b)}\n{t}\n\n")
    return out_srt


def main() -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="按 keep 区间从源视频切干净片段")
    ap.add_argument("video")
    ap.add_argument("keep_json", help="keep.json: [[start,end],...]（秒）")
    ap.add_argument("out")
    ap.add_argument("--crop", default=None, help="如 crop=1080:800:0:1120 裁下半摄像头")
    a = ap.parse_args()
    spans = json.loads(Path(a.keep_json).read_text(encoding="utf-8"))
    out = cut_clip(a.video, spans, a.out, crop=a.crop)
    dur = sum(e - s for s, e in spans)
    print(f"[OK] {out} (keep {len(spans)}seg/{dur:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
