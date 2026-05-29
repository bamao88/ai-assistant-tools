from __future__ import annotations

import json
import re

from .llm import OpenAICompatibleClient, parse_json_response
from .models import ClipPlan, clip_plan_from_dict
from .transcript import Cue, cues_to_prompt_lines, detect_language


# Clip-length budget. Kept below validation's 180s hard cap so the model has
# headroom — it tends to overshoot slightly, and we clamp rather than reject.
MIN_CLIP_SECONDS = 8
MAX_CLIP_SECONDS = 150


def generate_ai_clip_plan(
    video: str,
    transcript: str,
    cues: list[Cue],
    mode: str,
    query: str | None = None,
    max_clips: int = 6,
    client: OpenAICompatibleClient | None = None,
    layout: str | None = None,
    subtitle: str | None = None,
    join: bool | None = None,
) -> ClipPlan:
    if mode not in {"query", "auto"}:
        raise ValueError("AI planning mode must be query or auto.")
    if mode == "query" and not query:
        raise ValueError("--query is required for query mode.")
    client = client or OpenAICompatibleClient()
    language = detect_language(cues, transcript)
    transcript_lines = cues_to_prompt_lines(cues, limit=900)
    user_goal = query or "Recommend standalone short video clips with high insight density."
    payload = {
        "video": video,
        "transcript": transcript,
        "language": language,
        "mode": mode,
        "max_clips": max_clips,
        "min_clip_seconds": MIN_CLIP_SECONDS,
        "max_clip_seconds": MAX_CLIP_SECONDS,
        "goal": user_goal,
        "transcript_cues": transcript_lines,
    }
    raw = client.chat(
        [
            {
                "role": "system",
                "content": (
                    "You select video clips from timestamped transcript cues. "
                    "Return strict JSON only. Use only timestamps present in the cues; "
                    "express start/end as HH:MM:SS.mmm. Do not invent transcript content. "
                    "Prefer complete semantic moments. Each clip MUST last between "
                    "min_clip_seconds and max_clip_seconds; split longer moments into "
                    "multiple clips. Avoid intros, sponsor reads, outros, "
                    "and transitions unless requested. Choose ONLY the clips — do not set "
                    "layout, subtitle, or join; rendering is controlled by the operator. "
                    "The JSON schema is: version=1, "
                    "clips[{id,title,start,end,reason,tags}]."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.2,
        json_mode=True,
    )
    result = _coerce_plan_json(raw)
    result.setdefault("version", 1)
    result.setdefault("source", {"video": video, "transcript": transcript, "language": language})
    plan = clip_plan_from_dict(result)
    # Rendering settings are operator choices, not the model's — override whatever
    # the model may have emitted with the values passed on the CLI.
    if layout is not None:
        plan.defaults.layout = layout
    if subtitle is not None:
        plan.defaults.subtitle = subtitle
    if join is not None:
        plan.defaults.join = join
    plan.clips = _enforce_clip_lengths(plan.clips)
    return plan


def _coerce_plan_json(content: str) -> dict:
    """Accept either {"clips": [...]} or a bare top-level [...] array — models
    drift between the two, especially as max_clips grows."""
    try:
        return parse_json_response(content)
    except ValueError:
        pass
    match = re.search(r"\[.*\]", content, flags=re.DOTALL)
    if match:
        array = json.loads(match.group(0))
        if isinstance(array, list):
            return {"clips": array}
    raise ValueError("Could not parse a clip plan from the model response.")


def _enforce_clip_lengths(clips: list) -> list:
    """Drop clips below the floor and clamp those above the ceiling. The model
    overshoots the budget often enough that rejecting the whole plan is hostile;
    the resulting JSON is written for the operator to review and tweak anyway."""
    kept = []
    for clip in clips:
        if clip.duration < MIN_CLIP_SECONDS:
            continue
        if clip.duration > MAX_CLIP_SECONDS:
            clip.end = clip.start + MAX_CLIP_SECONDS
        kept.append(clip)
    if not kept:
        raise ValueError("Model returned no clips within the allowed length range.")
    return kept

