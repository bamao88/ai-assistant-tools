#!/usr/bin/env python3
"""视频帧截图：从 YouTube 演讲/视频抠帧，可裁出画面里的某区域（如 PPT）。

find-images skill 的「方式三：视频帧截图」配套工具。封装机械操作
（下视频轨 / 截帧 / 批量裁区域），布局判断和选图交给 AI。

位置：tools/engines/screenshot/video_frame.py

用法（两步）：

  1) probe —— 下视频轨 + 截均匀分布的整帧，供 AI 看画面布局、定 crop 区域
     python3 video_frame.py probe <youtube_url> [--n 6] [--outdir /tmp/ppt_probe]

  2) grab —— 给定时间点 + crop 区域，批量截帧并裁出目标区域（PPT/画面）
     python3 video_frame.py grab <youtube_url> \
         --crop 1418:783:472:30 \
         --at 00:09:42=results,00:11:22=pareto,00:08:50=recursion \
         --outdir content/personas/<...>/assets

  不传 --crop 则裁整帧（截视频画面本身，非合成画面里的子区域）。

crop 格式 = W:H:X:Y（ffmpeg crop 语法：宽:高:左上x:左上y）。
--at 格式 = 逗号分隔的 `时间=名字`；时间 HH:MM:SS，名字可省（省则用序号）。

已知布局预设（crop 直接抄，省去 probe）：
  AI Engineer 大会录制（1920x1080，PPT 在右上，含 mac 菜单栏+讲者小窗+底部横幅）：
    --crop 1418:783:472:30

依赖：系统 yt-dlp（/Users/xpw/.local/bin）、ffmpeg。视频轨缓存在 /Volumes/ExtSSD2601/media/。
绕 YouTube bot 墙：--cookies-from-browser chrome + player_client=web_embedded（见记忆 reference_youtube_transcript_bot_bypass）。
"""
import argparse
import os
import re
import subprocess
import sys

MEDIA_DIR = "/Volumes/ExtSSD2601/media"
# 1080p mp4 视频轨；若 299 不可用 yt-dlp 会回退到 -f 中指定的备选
VIDEO_FORMAT = "299/137/bestvideo[height<=1080][ext=mp4]"
YTDLP_BYPASS = ["--cookies-from-browser", "chrome",
                "--extractor-args", "youtube:player_client=web_embedded"]


def video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", url)
    if not m:
        sys.exit(f"无法从 URL 解析 video id: {url}")
    return m.group(1)


def ensure_video(url: str) -> str:
    """下载视频轨（仅视频，无音轨）到 media/，已存在则复用。返回路径。"""
    vid = video_id(url)
    path = os.path.join(MEDIA_DIR, f"yt_{vid}_video.mp4")
    if os.path.exists(path):
        print(f"[cache] 视频轨已存在：{path}")
        return path
    os.makedirs(MEDIA_DIR, exist_ok=True)
    print(f"[download] 下载视频轨 {vid} → {path}")
    cmd = ["yt-dlp", *YTDLP_BYPASS, "-f", VIDEO_FORMAT, url, "-o", path]
    r = subprocess.run(cmd)
    if r.returncode != 0 or not os.path.exists(path):
        sys.exit("视频轨下载失败（检查 cookies / 网络 / 下载权限）")
    return path


def duration_seconds(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def frame_at(video: str, ts: str, out: str, crop: str | None):
    vf = ["-vf", f"crop={crop}"] if crop else []
    cmd = ["ffmpeg", "-ss", ts, "-i", video, "-frames:v", "1",
           *vf, "-q:v", "2", out, "-y"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cmd_probe(args):
    video = ensure_video(args.url)
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    dur = duration_seconds(video)
    if dur <= 0:
        sys.exit("无法读取时长")
    # 均匀分布 n 张整帧（跳过头尾各 5%）
    n = args.n
    start, end = dur * 0.05, dur * 0.95
    step = (end - start) / max(n - 1, 1)
    print(f"[probe] 时长 {int(dur)}s，截 {n} 张整帧 → {outdir}")
    for i in range(n):
        sec = start + step * i
        ts = f"{int(sec//3600):02d}:{int(sec%3600//60):02d}:{int(sec%60):02d}"
        out = os.path.join(outdir, f"probe_{i:02d}_{ts.replace(':','-')}.jpg")
        frame_at(video, ts, out, crop=None)
        print(f"  {ts} → {out}")
    print("\n下一步：Read 这些整帧看 PPT 在画面什么位置，定出 crop=W:H:X:Y，再跑 grab。")


def cmd_grab(args):
    video = ensure_video(args.url)
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    specs = []
    for i, item in enumerate(args.at.split(",")):
        item = item.strip()
        if "=" in item:
            ts, name = item.split("=", 1)
        else:
            ts, name = item, f"slide{i+1}"
        specs.append((ts.strip(), name.strip()))
    print(f"[grab] crop={args.crop}，裁 {len(specs)} 张 → {outdir}")
    for ts, name in specs:
        out = os.path.join(outdir, f"ppt_{name}.jpg")
        frame_at(video, ts, out, crop=args.crop)
        ok = "✓" if os.path.exists(out) else "✗"
        print(f"  {ok} {ts} → {out}")


def main():
    p = argparse.ArgumentParser(description="从 YouTube 演讲视频抠 PPT 帧")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("probe", help="下视频轨 + 截整帧供看布局")
    pp.add_argument("url")
    pp.add_argument("--n", type=int, default=6, help="截几张整帧（默认 6）")
    pp.add_argument("--outdir", default="/tmp/ppt_probe")
    pp.set_defaults(func=cmd_probe)

    pg = sub.add_parser("grab", help="按时间点+crop 批量裁 PPT")
    pg.add_argument("url")
    pg.add_argument("--crop", required=True, help="W:H:X:Y（ffmpeg crop 语法）")
    pg.add_argument("--at", required=True,
                    help="逗号分隔 时间=名字，如 00:09:42=results,00:11:22=pareto")
    pg.add_argument("--outdir", required=True)
    pg.set_defaults(func=cmd_grab)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
