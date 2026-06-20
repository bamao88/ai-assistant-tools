"""字级转写模块（字级剪辑线的地基）：音频/视频 → 归一化字级词表 JSON。

供方案B（twostage）字级吸附用，输出 schema 与 twostage/resolve.py 的
load_paraformer_words 对齐：{"model","source_url","full_text","words":[{text,begin_time,end_time}]}（毫秒）。

编排策略（用户拍板）：
- 后端：火山 seedasr v3（主）→ 阿里 paraformer-v2（兜底，火山额度用尽/失败自动切）。
- 上传：公网托管（默认）→ 阿里 OSS（代码写好、默认不用，公网出问题再 --uploader oss）。
- 句级线（腾讯会议 minutes）不调用本模块。

公开 API：
    transcribe_audio(audio=..., backend="volc", fallback="aliyun", uploader="public") -> dict
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from .backends import BackendError, resolve_backend
from .upload import resolve_uploader

# engines/video-slicer/video_slicer/transcribe/ -> 上溯 4 层到 tools 根
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ENV = REPO_ROOT / "var" / "credentials" / "aliyun.env"

_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def _log(m: str) -> None:
    print(m, file=sys.stderr, flush=True)


def _media_dur(p: Path) -> float:
    """媒体时长（秒）；读不到返回 0。"""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or 0)


def load_env_file(path: str | Path) -> None:
    """读 KEY=VALUE 注入 os.environ（已存在的不覆盖）。火山 key 也放这里。"""
    import os

    path = Path(path)
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _fmt_from_name(name: str) -> str:
    ext = Path(name.split("?")[0]).suffix.lower().lstrip(".")
    return ext or "mp3"


def ensure_audio(src: Path) -> tuple[Path, str, Callable[[], None] | None]:
    """非音频（视频）→ ffmpeg 抽 mono/16k mp3（够 ASR、文件小）。返回 (路径, 格式, cleanup)。"""
    src = Path(src).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"音频/视频不存在：{src}")
    if src.suffix.lower() in _AUDIO_EXT:
        return src, _fmt_from_name(src.name), None

    tmp = Path(tempfile.mkdtemp(prefix="videocut-asr-")) / "audio.mp3"
    _log(f"[transcribe] ffmpeg 抽音频 {src.name} → {tmp.name}（mono 16k mp3）")
    # ★ aresample=async=1:first_pts=0 ——把源音频里的细碎空隙按时间线补回静音，
    #   抽出来的音频严格贴源时长。否则「带空隙」的素材会被抽短（声音前移），
    #   转写时间戳整体偏早、越往后越偏，最终字幕领先声音（详见 doc/bug/字幕音频5秒错位-words时间漂移）。
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-vn", "-af", "aresample=async=1:first_pts=0",
         "-ac", "1", "-ar", "16000", "-b:a", "48k", str(tmp)],
        check=True,
    )
    # 自检：抽出音频时长须贴源时长（差 >0.3s 说明仍有空隙没补上 → 转写会漂，告警）
    try:
        sd = _media_dur(src)
        ad = _media_dur(tmp)
        if sd > 0 and abs(sd - ad) > 0.3:
            _log(f"[transcribe] ⚠ 抽出音频({ad:.2f}s) 与源({sd:.2f}s) 差 {ad - sd:+.2f}s>0.3s——"
                 f"转写时间戳可能与视频漂移，请检查源音频空隙")
    except Exception as e:  # noqa: BLE001
        _log(f"[transcribe] 时长自检跳过：{e}")

    def cleanup() -> None:
        try:
            tmp.unlink(missing_ok=True)
            tmp.parent.rmdir()
        except OSError:
            pass

    return tmp, "mp3", cleanup


def transcribe_audio(
    audio: str | Path | None = None,
    audio_url: str | None = None,
    *,
    backend: str = "volc",
    fallback: str | None = "aliyun",
    uploader: str = "public",
    env_file: str | Path = DEFAULT_ENV,
    out_dir: str | Path | None = None,
) -> dict:
    """音频/视频 → 归一化字级词表 dict。给 audio_url 则跳过抽音频+上传。

    backend 主用，fallback 失败时自动切（传 None/"none" 关兜底）。
    out_dir 给定则落 words.json（可直接喂 twostage/resolve.load_paraformer_words）。
    """
    load_env_file(env_file)
    cleanups: list[Callable[[], None]] = []

    if audio_url:
        url, fmt = audio_url, _fmt_from_name(audio_url)
    elif audio:
        apath, fmt, acleanup = ensure_audio(Path(audio))
        if acleanup:
            cleanups.append(acleanup)
        url, ucleanup = resolve_uploader(uploader)(apath)
        if ucleanup:
            cleanups.append(ucleanup)
    else:
        raise ValueError("必须给 audio 或 audio_url 之一")

    chain = [backend] + ([fallback] if fallback and fallback != "none" else [])
    result: dict | None = None
    last_err: Exception | None = None
    try:
        for b in chain:
            try:
                fn = resolve_backend(b)
                result = fn(url, fmt=fmt) if b == "volc" else fn(url)
                break
            except BackendError as e:
                last_err = e
                _log(f"[transcribe] 后端 {b} 失败：{e} → 切下一个")
        if result is None:
            raise BackendError(f"全部后端失败：{last_err}")
    finally:
        for c in cleanups:  # 转写结束后才清 URL/临时音频
            c()

    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "words.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _log(f"[transcribe] 写 {out / 'words.json'}（{len(result['words'])} 字）")

    return result
