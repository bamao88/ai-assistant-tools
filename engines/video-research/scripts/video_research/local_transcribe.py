"""Local media transcription.

This module handles already-downloaded audio/video files. It keeps URL fetching
out of the path and produces reusable transcript artifacts for downstream
research, title generation, and clipping workflows.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from .storage import DATA_ROOT
from .transcript import FasterWhisperNotAvailable, _fmt_srt_ts

logger = logging.getLogger(__name__)


def transcribe_local_media(
    inputs: list[str],
    output_dir: str | None,
    language: str | None = "zh",
    whisper_model: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    cpu_threads: int = 0,
    vad_filter: bool = True,
    initial_prompt: str | None = None,
    glossary: list[str] | None = None,
    replacements: dict[str, str] | None = None,
) -> dict:
    """Transcribe local audio/video files and write transcript artifacts."""
    media_paths = [Path(p).expanduser().resolve() for p in inputs]
    missing = [str(p) for p in media_paths if not p.exists()]
    if missing:
        return {"success": False, "error": "输入文件不存在", "missing": missing}

    out_dir = _resolve_output_dir(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = _build_prompt(initial_prompt, glossary)
    replacements = replacements or {}

    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise FasterWhisperNotAvailable(
            "faster-whisper 未安装；运行 `uv sync` 安装 video-research 依赖"
        ) from e

    model_kwargs: dict = {"device": device, "compute_type": compute_type}
    if cpu_threads > 0:
        model_kwargs["cpu_threads"] = cpu_threads

    logger.info("正在加载 Whisper 模型 %s", whisper_model)
    model = WhisperModel(whisper_model, **model_kwargs)

    results: list[dict] = []
    used_stems: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="vr_local_audio_") as tmp:
        tmp_dir = Path(tmp)
        for media_path in media_paths:
            stem = _unique_stem(_safe_stem(media_path.stem), used_stems)
            audio_path = tmp_dir / f"{stem}.wav"
            logger.info("抽取音频: %s", media_path)
            _extract_wav(media_path, audio_path)
            result = _transcribe_one(
                model=model,
                media_path=media_path,
                audio_path=audio_path,
                out_dir=out_dir,
                stem=stem,
                language=language,
                vad_filter=vad_filter,
                initial_prompt=prompt,
                glossary=glossary or [],
                replacements=replacements,
                model_name=whisper_model,
            )
            results.append(result)

    combined_path = out_dir / "combined.md"
    combined_path.write_text(_render_combined_md(results), encoding="utf-8")

    return {
        "success": True,
        "output_dir": str(out_dir),
        "combined_md": str(combined_path),
        "count": len(results),
        "items": results,
    }


def _transcribe_one(
    *,
    model,
    media_path: Path,
    audio_path: Path,
    out_dir: Path,
    stem: str,
    language: str | None,
    vad_filter: bool,
    initial_prompt: str | None,
    glossary: list[str],
    replacements: dict[str, str],
    model_name: str,
) -> dict:
    kwargs: dict = {
        "language": language or None,
        "vad_filter": vad_filter,
        "initial_prompt": initial_prompt,
    }
    if glossary:
        kwargs["hotwords"] = ", ".join(glossary)

    duration = _ffprobe_duration(media_path)
    segments_iter, info = model.transcribe(str(audio_path), **kwargs)
    segments = []
    for seg in segments_iter:
        start = seg.start
        end = seg.end
        if duration is not None:
            if start >= duration:
                continue
            end = min(end, duration)
            if end <= start:
                continue
        text = _apply_replacements(seg.text.strip(), replacements)
        if not text:
            continue
        segments.append({"start": start, "end": end, "text": text})

    json_path = out_dir / f"{stem}.json"
    srt_path = out_dir / f"{stem}.srt"
    txt_path = out_dir / f"{stem}.txt"
    md_path = out_dir / f"{stem}.md"

    payload = {
        "source": str(media_path),
        "duration": duration,
        "language": info.language,
        "language_probability": info.language_probability,
        "whisper_model": model_name,
        "segments": segments,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    srt_path.write_text(_render_srt(segments), encoding="utf-8")
    txt_path.write_text(_render_plain_text(segments) + "\n", encoding="utf-8")
    md_path.write_text(_render_transcript_md(stem, payload), encoding="utf-8")

    return {
        "source": str(media_path),
        "stem": stem,
        "duration": duration,
        "language": info.language,
        "language_probability": info.language_probability,
        "segment_count": len(segments),
        "json_path": str(json_path),
        "srt_path": str(srt_path),
        "txt_path": str(txt_path),
        "md_path": str(md_path),
    }


def _resolve_output_dir(output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir).expanduser().resolve()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_ROOT / "local_transcripts" / stamp


def _build_prompt(initial_prompt: str | None, glossary: list[str] | None) -> str | None:
    parts = []
    if initial_prompt:
        parts.append(initial_prompt.strip())
    if glossary:
        terms = "、".join(term.strip() for term in glossary if term.strip())
        if terms:
            parts.append(f"请优先准确识别这些术语：{terms}。")
    return "\n".join(parts) if parts else None


def _extract_wav(media_path: Path, audio_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True)


def _ffprobe_duration(path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.SubprocessError:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def _render_srt(segments: list[dict]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{_fmt_srt_ts(segment['start'])} --> {_fmt_srt_ts(segment['end'])}",
                    segment["text"],
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _render_plain_text(segments: list[dict]) -> str:
    return "".join(segment["text"] for segment in segments)


def _render_transcript_md(stem: str, payload: dict) -> str:
    lines = [f"# {stem} 逐字稿", ""]
    language = payload.get("language") or "unknown"
    prob = payload.get("language_probability")
    if isinstance(prob, float):
        lines.append(f"- 识别语言：{language}（置信度 {prob:.2f}）")
    else:
        lines.append(f"- 识别语言：{language}")
    duration = payload.get("duration")
    if isinstance(duration, float):
        lines.append(f"- 时长：{duration:.1f} 秒")
    lines.extend(["", "## 带时间轴", ""])
    for segment in payload["segments"]:
        lines.append(
            f"[{_fmt_md_ts(segment['start'])}-{_fmt_md_ts(segment['end'])}] {segment['text']}"
        )
    lines.extend(["", "## 连贯文本", "", _render_plain_text(payload["segments"]), ""])
    return "\n".join(lines)


def _render_combined_md(results: list[dict]) -> str:
    lines = ["# 本地视频逐字稿汇总", ""]
    for result in results:
        txt_path = Path(result["txt_path"])
        text = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
        lines.extend([f"## {result['stem']}", "", text, ""])
    return "\n".join(lines)


def _fmt_md_ts(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _safe_stem(stem: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "-", stem).strip(".-")
    return cleaned or "media"


def _unique_stem(stem: str, used: set[str]) -> str:
    if stem not in used:
        used.add(stem)
        return stem
    index = 2
    while f"{stem}-{index}" in used:
        index += 1
    unique = f"{stem}-{index}"
    used.add(unique)
    return unique


def _apply_replacements(text: str, replacements: dict[str, str]) -> str:
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
