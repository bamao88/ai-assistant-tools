from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
from typing import Any

from .timecode import format_timecode, parse_timecode


SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


@dataclass
class Segment:
    """One continuous host-only span. A published clip ("视频") is the ordered
    concatenation of its segments — non-contiguous moments stitched by theme,
    with other speakers' speech cut out in between."""

    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Clip:
    id: str
    start: float = 0.0
    end: float = 0.0
    title: str = ""
    reason: str = ""
    tags: list[str] = field(default_factory=list)
    subtitle_mode: str | None = None
    segments: list[Segment] = field(default_factory=list)

    def __post_init__(self) -> None:
        # A clip is always expressed as segments internally. Callers that pass a
        # single (start,end) span get a one-segment clip for free; multi-segment
        # callers pass segments and we derive the envelope from them.
        if not self.segments:
            self.segments = [Segment(self.start, self.end)]
        self.start = self.segments[0].start
        self.end = self.segments[-1].end

    @property
    def duration(self) -> float:
        """Playable length = sum of segment durations (not the envelope), since
        the gaps between stitched segments are cut out."""
        return sum(segment.duration for segment in self.segments)


@dataclass
class ClipDefaults:
    layout: str = "original"
    subtitle: str = "auto"
    join: bool = False
    padding_start_seconds: float = 0
    padding_end_seconds: float = 0


@dataclass
class ClipPlan:
    version: int
    source_video: str | None
    source_transcript: str | None
    source_language: str | None
    defaults: ClipDefaults
    clips: list[Clip]
    selection_note: str = ""  # model's rationale for what it dropped (selective mode)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source": {
                "video": self.source_video,
                "transcript": self.source_transcript,
                "language": self.source_language,
            },
            "defaults": {
                "layout": self.defaults.layout,
                "subtitle": self.defaults.subtitle,
                "join": self.defaults.join,
                "padding_start_seconds": self.defaults.padding_start_seconds,
                "padding_end_seconds": self.defaults.padding_end_seconds,
            },
            "clips": [
                {
                    "id": clip.id,
                    "title": clip.title,
                    "start": format_timecode(clip.start),
                    "end": format_timecode(clip.end),
                    "segments": [
                        {"start": format_timecode(segment.start), "end": format_timecode(segment.end)}
                        for segment in clip.segments
                    ],
                    "reason": clip.reason,
                    "tags": clip.tags,
                    "subtitle": {"mode": clip.subtitle_mode} if clip.subtitle_mode else {},
                }
                for clip in self.clips
            ],
        }


def load_clip_plan(path: str | Path) -> ClipPlan:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return clip_plan_from_dict(data)


def write_clip_plan(plan: ClipPlan, path: str | Path) -> None:
    Path(path).write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clip_plan_from_dict(data: dict[str, Any]) -> ClipPlan:
    if not isinstance(data, dict):
        raise ValueError("Clip plan must be a JSON object.")
    version = data.get("version")
    if version != 1:
        raise ValueError(f"Unsupported clip plan version: {version!r}")

    source = data.get("source") or {}
    if not isinstance(source, dict):
        raise ValueError("Clip plan source must be an object.")

    defaults_data = data.get("defaults") or {}
    if not isinstance(defaults_data, dict):
        raise ValueError("Clip plan defaults must be an object.")
    # Models sometimes emit subtitle as {"mode": "..."} instead of a bare string.
    raw_subtitle = defaults_data.get("subtitle", "auto")
    if isinstance(raw_subtitle, dict):
        raw_subtitle = raw_subtitle.get("mode", "auto")
    defaults = ClipDefaults(
        layout=str(defaults_data.get("layout", "original")),
        subtitle=str(raw_subtitle),
        join=bool(defaults_data.get("join", False)),
        padding_start_seconds=float(defaults_data.get("padding_start_seconds", 0) or 0),
        padding_end_seconds=float(defaults_data.get("padding_end_seconds", 0) or 0),
    )

    raw_clips = data.get("clips")
    if not isinstance(raw_clips, list) or not raw_clips:
        raise ValueError("Clip plan must include at least one clip.")

    clips = []
    for index, raw_clip in enumerate(raw_clips, start=1):
        if not isinstance(raw_clip, dict):
            raise ValueError(f"Clip #{index} must be an object.")
        clip_id = str(raw_clip.get("id") or f"clip-{index:02d}")
        subtitle = raw_clip.get("subtitle") or {}
        subtitle_mode = None
        if isinstance(subtitle, dict) and subtitle.get("mode"):
            subtitle_mode = str(subtitle["mode"])
        segments = _parse_segments(raw_clip, index)
        clips.append(
            Clip(
                id=clip_id,
                title=str(raw_clip.get("title") or clip_id),
                reason=str(raw_clip.get("reason") or ""),
                tags=[str(tag) for tag in raw_clip.get("tags", [])],
                subtitle_mode=subtitle_mode,
                segments=segments,
            )
        )

    return ClipPlan(
        version=1,
        source_video=source.get("video"),
        source_transcript=source.get("transcript"),
        source_language=source.get("language"),
        defaults=defaults,
        clips=clips,
    )


def _parse_segments(raw_clip: dict[str, Any], index: int) -> list[Segment]:
    """A clip may stitch several non-contiguous spans. Accept an explicit
    `segments` list; fall back to a single (start,end) span for the simple case
    and for older plans that predate stitching."""
    raw_segments = raw_clip.get("segments")
    if isinstance(raw_segments, list) and raw_segments:
        segments = []
        for raw in raw_segments:
            if not isinstance(raw, dict) or "start" not in raw or "end" not in raw:
                raise ValueError(f"Clip #{index} has a malformed segment: {raw!r}")
            segments.append(
                Segment(start=parse_timecode(str(raw["start"])), end=parse_timecode(str(raw["end"])))
            )
        return segments
    if "start" in raw_clip and "end" in raw_clip:
        return [Segment(start=parse_timecode(str(raw_clip["start"])), end=parse_timecode(str(raw_clip["end"])))]
    raise ValueError(f"Clip #{index} must include either segments or start/end.")


def build_manual_plan(
    video: str | None,
    transcript: str | None,
    language: str | None,
    ranges: list[tuple[float, float]],
    layout: str = "original",
    subtitle: str = "auto",
    join: bool = False,
) -> ClipPlan:
    clips = [
        Clip(id=f"clip-{index:02d}", title=f"Clip {index:02d}", start=start, end=end)
        for index, (start, end) in enumerate(ranges, start=1)
    ]
    return ClipPlan(
        version=1,
        source_video=video,
        source_transcript=transcript,
        source_language=language,
        defaults=ClipDefaults(layout=layout, subtitle=subtitle, join=join),
        clips=clips,
    )


def ensure_safe_clip_id(value: str) -> str:
    if not SAFE_ID_RE.match(value):
        raise ValueError(
            f"Clip id {value!r} is not filename-safe. Use letters, numbers, dot, underscore, or dash."
        )
    return value

