from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import re

from .timecode import format_srt_timecode
from .transcript import Cue, parse_transcript


# Break preferentially after CJK/ASCII sentence and clause punctuation, keeping
# the punctuation attached to the preceding chunk.
_CLAUSE_BREAK_RE = re.compile(r"(?<=[。！？!?；;，,、])")


def split_long_cues(cues: list[Cue], max_chars: int = 16) -> list[Cue]:
    """Split over-long single-line cues into shorter ones for burned captions.

    Tencent transcripts arrive at sentence granularity, so one cue can be 100+
    characters and dominate a 9:16 frame. We re-segment such cues at clause
    punctuation (falling back to a hard wrap) and divide the cue's time span
    proportionally to each piece's length. Multi-line cues (e.g. bilingual
    zh/en) are left untouched so their two-line structure survives.
    """
    out: list[Cue] = []
    for cue in cues:
        if "\n" in cue.text or len(cue.text) <= max_chars:
            out.append(cue)
            continue
        pieces = _segment_text(cue.text, max_chars)
        total = sum(len(piece) for piece in pieces) or 1
        span = cue.end - cue.start
        cursor = cue.start
        for piece in pieces:
            piece_span = span * (len(piece) / total)
            out.append(
                Cue(
                    index=len(out) + 1,
                    start=cursor,
                    end=cursor + piece_span,
                    text=piece,
                    speaker=cue.speaker,
                    language=cue.language,
                )
            )
            cursor += piece_span
    return [
        Cue(index=index, start=cue.start, end=cue.end, text=cue.text, speaker=cue.speaker, language=cue.language)
        for index, cue in enumerate(out, start=1)
    ]


def _segment_text(text: str, max_chars: int) -> list[str]:
    clauses = [clause.strip() for clause in _CLAUSE_BREAK_RE.split(text) if clause.strip()]
    pieces: list[str] = []
    buffer = ""
    for clause in clauses:
        while len(clause) > max_chars:
            if buffer:
                pieces.append(buffer)
                buffer = ""
            pieces.append(clause[:max_chars])
            clause = clause[max_chars:]
        if not buffer:
            buffer = clause
        elif len(buffer) + len(clause) <= max_chars:
            buffer += clause
        else:
            pieces.append(buffer)
            buffer = clause
    if buffer:
        pieces.append(buffer)
    return pieces or [text]


def extract_cues(cues: list[Cue], start: float, end: float) -> list[Cue]:
    selected = []
    for cue in cues:
        if cue.end <= start or cue.start >= end:
            continue
        selected.append(
            Cue(
                index=len(selected) + 1,
                start=max(cue.start, start) - start,
                end=min(cue.end, end) - start,
                text=cue.text,
                speaker=cue.speaker,
                language=cue.language,
            )
        )
    return selected


def offset_cues(cues: list[Cue], offset: float) -> list[Cue]:
    return [
        Cue(
            index=index,
            start=cue.start + offset,
            end=cue.end + offset,
            text=cue.text,
            speaker=cue.speaker,
            language=cue.language,
        )
        for index, cue in enumerate(cues, start=1)
    ]


def write_srt(cues: list[Cue], path: str | Path) -> None:
    lines: list[str] = []
    for index, cue in enumerate(cues, start=1):
        lines.append(str(index))
        lines.append(f"{format_srt_timecode(cue.start)} --> {format_srt_timecode(cue.end)}")
        lines.append(cue.text)
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def make_bilingual_cues(source_cues: list[Cue], translated_texts: list[str], zh_first: bool = True) -> list[Cue]:
    if len(source_cues) != len(translated_texts):
        raise ValueError("Translated cue count does not match source cue count.")
    bilingual = []
    for index, (cue, zh_text) in enumerate(zip(source_cues, translated_texts, strict=True), start=1):
        text = f"{zh_text}\n{cue.text}" if zh_first else f"{cue.text}\n{zh_text}"
        bilingual.append(Cue(index=index, start=cue.start, end=cue.end, text=text))
    return bilingual


def align_translation_cues(source_cues: list[Cue], translated_cues: list[Cue], zh_first: bool = True) -> list[Cue]:
    bilingual = []
    for index, cue in enumerate(source_cues, start=1):
        overlaps = [
            translated.text
            for translated in translated_cues
            if min(cue.end, translated.end) - max(cue.start, translated.start) > 0.05
        ]
        translated_text = " ".join(dict.fromkeys(overlaps)).strip()
        if not translated_text:
            translated_text = ""
        text = f"{translated_text}\n{cue.text}" if zh_first and translated_text else cue.text
        if not zh_first and translated_text:
            text = f"{cue.text}\n{translated_text}"
        bilingual.append(Cue(index=index, start=cue.start, end=cue.end, text=text))
    return bilingual


def load_optional_zh_cues(path: str | None) -> list[Cue] | None:
    if not path:
        return None
    return parse_transcript(path)


class SubtitleTempFile:
    def __init__(self, cues: list[Cue]) -> None:
        self.cues = cues
        self._temp_dir: TemporaryDirectory[str] | None = None
        self.path: str | None = None

    def __enter__(self) -> str:
        self._temp_dir = TemporaryDirectory()
        path = Path(self._temp_dir.name) / "subtitles.srt"
        write_srt(self.cues, path)
        self.path = str(path)
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
