"""字幕抓取 + Whisper 兜底。

策略：
1. yt-dlp 先试人工字幕 → 再试自动生成字幕（按 --lang 顺序优先级）
2. 都没有（或 --force-whisper）时，下载音频跑 faster-whisper
3. 输出 transcript.srt（带时间戳） + transcript.txt（纯文本）
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

import yt_dlp

from .info import fetch_info
from .storage import video_dir_from_url
from .ydl import merge_ydl_opts

logger = logging.getLogger(__name__)


def fetch_transcript(
    url: str,
    langs: list[str],
    force_whisper: bool = False,
    whisper_model: str = "base",
) -> dict:
    """抓字幕或 Whisper 转写。

    Args:
        url: 视频 URL
        langs: 优先语言列表，如 ["zh", "en"]
        force_whisper: True 时跳过字幕抓取直接用 Whisper
        whisper_model: faster-whisper 模型 (tiny/base/small/medium/large-v3)

    Returns:
        dict with source ("manual"|"auto"|"whisper"|"none"), srt_path, txt_path
    """
    meta = fetch_info(url, download_thumbnail=False)
    d = video_dir_from_url(url, meta["video_id"])

    srt_path = d / "transcript.srt"
    txt_path = d / "transcript.txt"

    if not force_whisper:
        source = _try_ytdlp_subs(url, langs, d, srt_path)
        if source:
            _srt_to_txt(srt_path, txt_path)
            return {
                "success": True,
                "source": source,
                "srt_path": str(srt_path),
                "txt_path": str(txt_path),
                "video_id": meta["video_id"],
                "platform": meta["platform"],
            }

    # Whisper 兜底
    try:
        _whisper_transcribe(url, langs, d, whisper_model, srt_path)
        _srt_to_txt(srt_path, txt_path)
        return {
            "success": True,
            "source": "whisper",
            "whisper_model": whisper_model,
            "srt_path": str(srt_path),
            "txt_path": str(txt_path),
            "video_id": meta["video_id"],
            "platform": meta["platform"],
        }
    except FasterWhisperNotAvailable as e:
        return {
            "success": False,
            "source": "none",
            "error": str(e),
            "video_id": meta["video_id"],
            "platform": meta["platform"],
            "available_subtitles": meta.get("subtitles", []),
            "available_auto_captions": meta.get("automatic_captions", []),
        }


def _try_ytdlp_subs(url: str, langs: list[str], d: Path, srt_out: Path) -> str | None:
    """尝试用 yt-dlp 拉字幕，优先人工再自动。成功返回 source，失败返回 None。"""
    tmpdir = Path(tempfile.mkdtemp(prefix="vr_subs_"))
    outtmpl = str(tmpdir / "%(id)s.%(ext)s")

    # 先试人工字幕
    for auto_mode, source in [(False, "manual"), (True, "auto")]:
        ydl_opts = merge_ydl_opts({
            "skip_download": True,
            "writesubtitles": not auto_mode,
            "writeautomaticsub": auto_mode,
            "subtitleslangs": langs,
            "subtitlesformat": "vtt",
            "outtmpl": outtmpl,
        })
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            logger.warning("yt-dlp %s 字幕抓取失败: %s", source, e)
            continue

        vtt_files = list(tmpdir.glob("*.vtt"))
        if not vtt_files:
            continue

        # 按 langs 顺序挑选
        chosen = _pick_vtt_by_lang(vtt_files, langs) or vtt_files[0]
        _vtt_to_srt(chosen, srt_out)
        logger.info("字幕来源: %s（%s）", source, chosen.name)
        _cleanup_dir(tmpdir)
        return source

    _cleanup_dir(tmpdir)
    return None


def _pick_vtt_by_lang(files: list[Path], langs: list[str]) -> Path | None:
    """按语言优先级挑 vtt。文件名形如 xxx.zh.vtt / xxx.en.vtt。"""
    for lang in langs:
        for f in files:
            if f".{lang}." in f.name or f.stem.endswith(f".{lang}"):
                return f
    return None


def _cleanup_dir(d: Path) -> None:
    for f in d.iterdir():
        f.unlink()
    d.rmdir()


# ---------- vtt / srt 格式转换 ----------

_VTT_HEADER_RE = re.compile(r"^WEBVTT.*?\n\n", re.DOTALL)
_VTT_TS_RE = re.compile(r"(\d{2}:\d{2}:\d{2})\.(\d{3})")
_TAG_RE = re.compile(r"<[^>]+>")


def _vtt_to_srt(vtt_path: Path, srt_out: Path) -> None:
    """粗暴但够用的 vtt → srt 转换。"""
    content = vtt_path.read_text(encoding="utf-8")
    content = _VTT_HEADER_RE.sub("", content, count=1)
    # vtt 用 . 作毫秒分隔，srt 用 ,
    content = _VTT_TS_RE.sub(r"\1,\2", content)
    # 去掉 "NOTE" 段
    lines = []
    skip_block = False
    block_num = 1
    current_block: list[str] = []

    def flush():
        nonlocal block_num, current_block
        if current_block:
            # 找时间轴行
            has_ts = any("-->" in l for l in current_block)
            if has_ts:
                lines.append(str(block_num))
                lines.extend(current_block)
                lines.append("")
                block_num += 1
            current_block = []

    for raw in content.splitlines():
        line = raw.rstrip()
        if line.upper().startswith("NOTE"):
            skip_block = True
            continue
        if line == "":
            if not skip_block:
                flush()
            skip_block = False
            continue
        if skip_block:
            continue
        # 去 HTML 标签
        line = _TAG_RE.sub("", line)
        # 跳过纯序号行（vtt 有些实现会带）
        if line.isdigit() and not current_block:
            continue
        current_block.append(line)
    flush()

    srt_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _srt_to_txt(srt_path: Path, txt_out: Path) -> None:
    """srt → 清洗后的纯文本（去时间戳、去编号、合并短句）。"""
    content = srt_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\n+", content.strip())
    texts: list[str] = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        # 第一行是编号、第二行是时间戳（或首行已经是时间戳）
        body_start = 2 if lines[0].strip().isdigit() else 1
        body_lines = [l.strip() for l in lines[body_start:] if l.strip()]
        if not body_lines:
            continue
        # 连接为单句（有些 srt 一条字幕拆成两行）
        texts.append(" ".join(body_lines))
    # 去连续重复（auto caption 常见滚动重复）
    deduped: list[str] = []
    for t in texts:
        if not deduped or deduped[-1] != t:
            deduped.append(t)
    txt_out.write_text("\n".join(deduped) + "\n", encoding="utf-8")


# ---------- Whisper 兜底 ----------


class FasterWhisperNotAvailable(Exception):
    pass


def _whisper_transcribe(
    url: str, langs: list[str], d: Path, model_size: str, srt_out: Path
) -> None:
    """下载音频 → faster-whisper 转写 → 写 srt。"""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise FasterWhisperNotAvailable(
            "字幕抓取失败且 faster-whisper 未安装；运行 `uv sync` 安装依赖"
        ) from e

    # 1. 用 yt-dlp 下最佳音频
    with tempfile.TemporaryDirectory(prefix="vr_audio_") as tmp:
        tmp_path = Path(tmp)
        outtmpl = str(tmp_path / "%(id)s.%(ext)s")
        ydl_opts = merge_ydl_opts({
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "0",
                }
            ],
        })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        audio_files = list(tmp_path.glob("*.wav"))
        if not audio_files:
            # 退而求其次找任何音频
            audio_files = [
                f for f in tmp_path.iterdir() if f.suffix.lower() in {".m4a", ".mp3", ".opus"}
            ]
        if not audio_files:
            raise RuntimeError("音频下载失败：未找到输出文件")
        audio = audio_files[0]

        # 2. faster-whisper 转写
        logger.info("正在加载 Whisper 模型 %s（首次会下载）…", model_size)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        lang = langs[0] if langs else None
        segments, _info = model.transcribe(
            str(audio), language=lang, vad_filter=True
        )

        # 3. 写 srt
        with open(srt_out, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                f.write(f"{i}\n")
                f.write(f"{_fmt_srt_ts(seg.start)} --> {_fmt_srt_ts(seg.end)}\n")
                f.write(f"{seg.text.strip()}\n\n")


def _fmt_srt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------- search ----------


def search_transcript(video_key: str, keyword: str, context_chars: int = 60) -> dict:
    """在 data/{key}/transcript.srt 里搜关键词，返回时间戳列表。"""
    from .storage import video_dir_from_key

    d = video_dir_from_key(video_key, create=False)
    srt = d / "transcript.srt"
    if not srt.exists():
        return {"success": False, "error": f"未找到 transcript.srt：{srt}"}

    content = srt.read_text(encoding="utf-8")
    blocks = re.split(r"\n\n+", content.strip())
    matches: list[dict] = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        ts_line = lines[1]
        body = " ".join(l.strip() for l in lines[2:])
        if keyword.lower() not in body.lower():
            continue
        m = re.match(r"(\d{2}:\d{2}:\d{2})", ts_line)
        if not m:
            continue
        start_ts = m.group(1)
        # 截上下文
        idx = body.lower().find(keyword.lower())
        left = max(0, idx - context_chars)
        right = min(len(body), idx + len(keyword) + context_chars)
        snippet = body[left:right]
        matches.append({"timestamp": start_ts, "snippet": snippet})

    return {
        "success": True,
        "video_id": video_key,
        "keyword": keyword,
        "match_count": len(matches),
        "matches": matches,
    }
