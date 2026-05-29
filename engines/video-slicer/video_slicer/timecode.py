from __future__ import annotations

import re


TIMECODE_RE = re.compile(
    r"^(?:(?P<hours>\d{1,2}):)?(?P<minutes>\d{1,2}):(?P<seconds>\d{1,2})(?P<fraction>[\.,]\d{1,3})?$"
)
# LLMs frequently emit timestamps as bare seconds (e.g. "468.855" or "468").
BARE_SECONDS_RE = re.compile(r"^\d+(?:[\.,]\d+)?$")


def parse_timecode(value: str) -> float:
    text = value.strip()
    if BARE_SECONDS_RE.match(text):
        return float(text.replace(",", "."))
    match = TIMECODE_RE.match(text)
    if not match:
        raise ValueError(f"Invalid timecode: {value!r}")
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    fraction = match.group("fraction") or ""
    millis = 0
    if fraction:
        millis = int(fraction[1:].ljust(3, "0")[:3])
    if minutes > 59 or seconds > 59:
        raise ValueError(f"Invalid timecode: {value!r}")
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def format_timecode(seconds: float, separator: str = ".") -> str:
    if seconds < 0:
        seconds = 0
    millis_total = int(round(seconds * 1000))
    hours, remainder = divmod(millis_total, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def format_srt_timecode(seconds: float) -> str:
    return format_timecode(seconds, separator=",")


def parse_clip_range(value: str) -> tuple[float, float]:
    if "-" not in value:
        raise ValueError(f"Clip range must use START-END format: {value!r}")
    start_text, end_text = value.split("-", 1)
    start = parse_timecode(start_text)
    end = parse_timecode(end_text)
    if start >= end:
        raise ValueError(f"Clip start must be before end: {value!r}")
    return start, end

