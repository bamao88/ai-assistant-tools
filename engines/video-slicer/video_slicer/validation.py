from __future__ import annotations

from pathlib import Path

from .models import ClipPlan, ensure_safe_clip_id
from .transcript import Cue, transcript_bounds


VALID_LAYOUTS = {"original", "vertical", "square"}
VALID_SUBTITLE_MODES = {"auto", "none", "soft", "burned", "bilingual"}


def validate_clip_plan(
    plan: ClipPlan,
    video_duration: float | None = None,
    cues: list[Cue] | None = None,
    min_duration: float = 0.1,
    max_duration: float = 3600,
) -> None:
    if plan.defaults.layout not in VALID_LAYOUTS:
        raise ValueError(f"Invalid layout: {plan.defaults.layout!r}")
    if plan.defaults.subtitle not in VALID_SUBTITLE_MODES:
        raise ValueError(f"Invalid subtitle mode: {plan.defaults.subtitle!r}")
    if not plan.clips:
        raise ValueError("Clip plan must include at least one clip.")

    transcript_start = transcript_end = None
    if cues:
        transcript_start, transcript_end = transcript_bounds(cues)

    seen_ids = set()
    for clip in plan.clips:
        ensure_safe_clip_id(clip.id)
        if clip.id in seen_ids:
            raise ValueError(f"Duplicate clip id: {clip.id!r}")
        seen_ids.add(clip.id)
        if clip.duration < min_duration:
            raise ValueError(f"Clip {clip.id!r} is too short: {clip.duration:.2f}s")
        if clip.duration > max_duration:
            raise ValueError(f"Clip {clip.id!r} is too long: {clip.duration:.2f}s")
        previous_end = None
        for segment in clip.segments:
            if segment.start >= segment.end:
                raise ValueError(f"Clip {clip.id!r} has a segment whose start is not before its end.")
            if previous_end is not None and segment.start < previous_end - 0.2:
                raise ValueError(f"Clip {clip.id!r} segments must be in non-overlapping play order.")
            previous_end = segment.end
            padded_start = segment.start - plan.defaults.padding_start_seconds
            padded_end = segment.end + plan.defaults.padding_end_seconds
            if padded_start < 0:
                raise ValueError(f"Clip {clip.id!r} padding pushes a segment start before 0.")
            if video_duration is not None and padded_end > video_duration + 0.2:
                raise ValueError(
                    f"Clip {clip.id!r} has a segment ending after video duration "
                    f"({padded_end:.2f}s > {video_duration:.2f}s)."
                )
            if transcript_start is not None and segment.start < transcript_start - 0.2:
                raise ValueError(f"Clip {clip.id!r} has a segment starting before transcript range.")
            if transcript_end is not None and segment.end > transcript_end + 0.2:
                raise ValueError(f"Clip {clip.id!r} has a segment ending after transcript range.")


def validate_input_file(path: str | None, label: str) -> None:
    if not path:
        raise ValueError(f"Missing {label} path.")
    if not Path(path).exists():
        raise ValueError(f"{label} file does not exist: {path}")

