#!/usr/bin/env python3
"""抽帧测脸 → 算竖屏裁切重心。

横屏放进竖屏视频条(默认 720x744)时，张和每条素材坐的位置不同，
不能写死裁切偏移。这里在整段里均匀抽帧、做人脸检测、取脸中心中位数，
再反推出让脸“水平居中、垂直略偏上”的裁切偏移。

输出同时给两种形式：
  - object_position: 喂给 HTML 样图(CSS object-fit:cover 的 object-position)
  - ffmpeg_scale / ffmpeg_crop: 喂给出片脚本
"""
from __future__ import annotations
import cv2
import json
import argparse
import statistics
import numpy as np


def _detect_faces(gray, cascades):
    boxes = []
    for c in cascades:
        found = c.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(80, 80))
        for f in found:
            boxes.append(tuple(int(v) for v in f))
    return boxes


def locate(video, tw=720, th=744, samples=40, face_y=0.42):
    cap = cv2.VideoCapture(video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    base = cv2.data.haarcascades
    cascades = [
        cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml"),
        cv2.CascadeClassifier(base + "haarcascade_frontalface_alt2.xml"),
    ]
    idxs = np.linspace(0, max(total - 1, 0), samples).astype(int)
    cxs, cys = [], []
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _detect_faces(gray, cascades)
        if not faces:
            continue
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])  # 最大脸=最靠近镜头的主体
        cxs.append((x + w / 2) / W)
        cys.append((y + h / 2) / H)
    cap.release()

    found = len(cxs)
    cx = statistics.median(cxs) if cxs else 0.5
    cy = statistics.median(cys) if cys else 0.42

    s = max(tw / W, th / H)            # cover 缩放
    SW, SH = W * s, H * s
    fx, fy = cx * SW, cy * SH
    x0 = min(max(fx - tw * 0.5, 0), SW - tw)       # 脸水平居中
    y0 = min(max(fy - th * face_y, 0), SH - th)    # 脸垂直略偏上(留头顶)
    posx = 50.0 if SW - tw <= 0 else x0 / (SW - tw) * 100
    posy = 50.0 if SH - th <= 0 else y0 / (SH - th) * 100

    return {
        "video": video,
        "src": [W, H],
        "target": [tw, th],
        "faces_found": found,
        "samples": len(idxs),
        "face_center_pct": [round(cx * 100, 1), round(cy * 100, 1)],
        "object_position": [round(posx, 1), round(posy, 1)],
        "ffmpeg_scale": f"scale={round(SW)}:{round(SH)}",
        "ffmpeg_crop": f"crop={tw}:{th}:{round(x0)}:{round(y0)}",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--tw", type=int, default=720)
    ap.add_argument("--th", type=int, default=744)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--face-y", type=float, default=0.42)
    a = ap.parse_args()
    print(json.dumps(locate(a.video, a.tw, a.th, a.samples, a.face_y), ensure_ascii=False, indent=2))
