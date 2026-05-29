from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
from typing import Any

from .timecode import format_timecode, parse_timecode


SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


@dataclass
class Clip:
    id: str
    start: float
    end: float
    title: str = ""
    reason: str = ""
    tags: list[str] = field(default_factory=list)
    subtitle_mode: str | None = None

    @property
    def duration(self) -> float:
        return self.end - self.start


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
        clips.append(
            Clip(
                id=clip_id,
                start=parse_timecode(str(raw_clip["start"])),
                end=parse_timecode(str(raw_clip["end"])),
                title=str(raw_clip.get("title") or clip_id),
                reason=str(raw_clip.get("reason") or ""),
                tags=[str(tag) for tag in raw_clip.get("tags", [])],
                subtitle_mode=subtitle_mode,
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

