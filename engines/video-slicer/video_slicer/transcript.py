from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from pathlib import Path
import re

from .timecode import parse_timecode


TIMING_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[\.,]\d{1,3}|\d{1,2}:\d{2}[\.,]\d{1,3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[\.,]\d{1,3}|\d{1,2}:\d{2}[\.,]\d{1,3})"
)
INLINE_TIMESTAMP_RE = re.compile(r"<\d{1,2}:\d{2}:\d{2}[\.,]\d{1,3}>")
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str
    speaker: str | None = None
    language: str | None = None


def parse_transcript(path: str | Path) -> list[Cue]:
    transcript_path = Path(path)
    text = transcript_path.read_text(encoding="utf-8-sig")
    suffix = transcript_path.suffix.lower()
    if suffix == ".vtt" or text.lstrip().startswith("WEBVTT"):
        return parse_vtt(text)
    if suffix == ".srt" or "-->" in text:
        return parse_srt(text)
    raise ValueError(
        f"{transcript_path} does not look like VTT/SRT. Timestamped transcripts are required."
    )


def parse_vtt(text: str) -> list[Cue]:
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = [line.strip("\ufeff") for line in block.splitlines() if line.strip()]
        if not lines or lines[0].strip() == "WEBVTT":
            continue
        timing_idx = _find_timing_line(lines)
        if timing_idx is None:
            continue
        timing = TIMING_RE.search(lines[timing_idx])
        if not timing:
            continue
        body = " ".join(lines[timing_idx + 1 :]).strip()
        clean = clean_caption_text(body)
        if not clean:
            continue
        cues.append(
            Cue(
                index=len(cues) + 1,
                start=parse_timecode(timing.group("start")),
                end=parse_timecode(timing.group("end")),
                text=clean,
            )
        )
    return cues


def parse_srt(text: str) -> list[Cue]:
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        timing_idx = _find_timing_line(lines)
        if timing_idx is None:
            continue
        timing = TIMING_RE.search(lines[timing_idx])
        if not timing:
            continue
        body = " ".join(line.strip() for line in lines[timing_idx + 1 :])
        clean = clean_caption_text(body)
        if not clean:
            continue
        cues.append(
            Cue(
                index=len(cues) + 1,
                start=parse_timecode(timing.group("start")),
                end=parse_timecode(timing.group("end")),
                text=clean,
            )
        )
    return cues


def clean_caption_text(text: str) -> str:
    text = INLINE_TIMESTAMP_RE.sub("", text)
    text = TAG_RE.sub("", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def transcript_bounds(cues: list[Cue]) -> tuple[float, float]:
    if not cues:
        raise ValueError("Transcript contains no timestamped cues.")
    return cues[0].start, max(cue.end for cue in cues)


def detect_language(cues: list[Cue], path: str | Path | None = None) -> str:
    if path is not None:
        name = Path(path).name.lower()
        if ".zh" in name or ".cn" in name:
            return "zh"
        if ".en" in name:
            return "en"
    sample = " ".join(cue.text for cue in cues[:200])
    if not sample:
        return "unknown"
    cjk = sum(1 for char in sample if "\u4e00" <= char <= "\u9fff")
    alpha = sum(1 for char in sample if char.isascii() and char.isalpha())
    if cjk >= max(6, alpha // 4):
        return "zh"
    if alpha:
        return "en"
    return "unknown"


def cues_to_prompt_lines(cues: list[Cue], limit: int = 500) -> str:
    lines = []
    for cue in cues[:limit]:
        lines.append(f"[{cue.index}] {cue.start:.3f}-{cue.end:.3f}: {cue.text}")
    if len(cues) > limit:
        lines.append(f"... {len(cues) - limit} more cues omitted ...")
    return "\n".join(lines)


def _find_timing_line(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if "-->" in line:
            return index
    return None

