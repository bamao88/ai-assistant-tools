"""video-clip 引擎共享工具。把散在各脚本里的 run()/ffprobe 探测去重成一份。

只放通用、无业务耦合的小工具。原子脚本 `from vutil import ...`。
"""
from __future__ import annotations
import subprocess
from pathlib import Path


def run(cmd, **kw):
    """跑命令，捕获输出（text）。返回 CompletedProcess。"""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def ffprobe_dur(path) -> float:
    """视频/音频时长（秒）。读不到返回 0。"""
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path])
    return float(r.stdout.strip() or 0)


def probe(video) -> tuple[int, int, float, bool]:
    """返回 (width, height, duration, has_audio)。"""
    v = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", video])
    parts = (v.stdout.strip().split("x") + ["0", "0"])[:2]
    w, h = int(parts[0] or 0), int(parts[1] or 0)
    dur = ffprobe_dur(video)
    a = run(["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=index", "-of", "csv=p=0", video]).stdout.strip()
    return w, h, dur, bool(a)


def ensure_parent(path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def x264(crf=18, preset="medium", audio=True):
    """统一的 x264 输出参数列表（原子间一致）。"""
    out = ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p"]
    if audio:
        out += ["-c:a", "aac", "-b:a", "128k"]
    return out


# ---- SRT 解析（speed-adapt / subtitle-burn 共用）----
def srt_secs(ts: str) -> float:
    """'HH:MM:SS,mmm' → 秒。"""
    h, m, rest = ts.strip().split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path) -> list[tuple[float, float, str]]:
    """SRT → [(t0, t1, text)]，text 为该 cue 各行合并。"""
    out = []
    for b in Path(path).read_text(encoding="utf-8").strip().split("\n\n"):
        L = [x for x in b.split("\n") if x.strip()]
        if len(L) < 3 or "-->" not in L[1]:
            continue
        t0, t1 = (srt_secs(x) for x in L[1].split("-->"))
        out.append((t0, t1, " ".join(L[2:]).strip()))
    return out


# ---- 人脸中心定位（face-locate / name-mask 共用；cv2 可选）----
def face_center(video, samples=40):
    """Haar 抽帧测脸，返回 (cx, cy, found)，cx/cy 为占宽高比例(0..1)；无 cv2 或没检到→(0.5,0.42,0)。"""
    try:
        import cv2, numpy as np, statistics
    except ImportError:
        return 0.5, 0.42, 0
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1
    base = cv2.data.haarcascades
    cas = [cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml"),
           cv2.CascadeClassifier(base + "haarcascade_frontalface_alt2.xml")]
    cxs, cys = [], []
    for i in np.linspace(0, max(total - 1, 0), samples).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        boxes = []
        for c in cas:
            boxes += [tuple(int(v) for v in f) for f in c.detectMultiScale(g, 1.1, 6, minSize=(80, 80))]
        if boxes:
            x, y, w, h = max(boxes, key=lambda f: f[2] * f[3])
            cxs.append((x + w / 2) / W); cys.append((y + h / 2) / H)
    cap.release()
    if not cxs:
        return 0.5, 0.42, 0
    return statistics.median(cxs), statistics.median(cys), len(cxs)
