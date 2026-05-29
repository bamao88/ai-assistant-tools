import pytest

from video_slicer.models import build_manual_plan, clip_plan_from_dict
from video_slicer.transcript import Cue
from video_slicer.validation import validate_clip_plan


def test_manual_plan_round_trip_validation():
    plan = build_manual_plan(
        video="input.mp4",
        transcript="sample.en.vtt",
        language="en",
        ranges=[(1, 3)],
    )

    validate_clip_plan(plan, video_duration=5, cues=[Cue(1, 0, 5, "hello")])


def test_reject_invalid_clip_id():
    plan = clip_plan_from_dict(
        {
            "version": 1,
            "clips": [{"id": "../bad", "start": "00:00:01.000", "end": "00:00:02.000"}],
        }
    )

    with pytest.raises(ValueError, match="filename-safe"):
        validate_clip_plan(plan, video_duration=5, cues=[Cue(1, 0, 5, "hello")])


def test_reject_out_of_range_clip():
    plan = build_manual_plan(
        video="input.mp4",
        transcript="sample.en.vtt",
        language="en",
        ranges=[(1, 8)],
    )

    with pytest.raises(ValueError, match="ends after video duration"):
        validate_clip_plan(plan, video_duration=5, cues=[Cue(1, 0, 10, "hello")])

