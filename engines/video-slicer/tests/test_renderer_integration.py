from pathlib import Path
import subprocess

import pytest

from video_slicer.models import build_manual_plan
from video_slicer.renderer import render_plan
from video_slicer.subtitles import align_translation_cues
from video_slicer.transcript import parse_transcript
from video_slicer.transcript import Cue


def test_render_manual_clip_with_soft_subtitles(tmp_path: Path):
    video = tmp_path / "input.mp4"
    transcript = tmp_path / "sample.zh.srt"
    out_dir = tmp_path / "outputs"
    make_tiny_video(video)
    transcript.write_text(
        """1
00:00:00,000 --> 00:00:01,000
你好

2
00:00:01,000 --> 00:00:02,000
世界
""",
        encoding="utf-8",
    )
    cues = parse_transcript(transcript)
    plan = build_manual_plan(
        video=str(video),
        transcript=str(transcript),
        language="zh",
        ranges=[(0, 1.5)],
        subtitle="soft",
    )

    outputs = render_plan(str(video), plan, cues, out_dir=str(out_dir), source_language="zh")

    assert Path(outputs[0]).exists()
    assert (out_dir / "clip-01.source.srt").exists()


def test_align_translation_cues_with_mismatched_counts():
    source = [
        Cue(1, 0, 1, "hello"),
        Cue(2, 1, 2, "world"),
    ]
    translated = [
        Cue(1, 0, 0.6, "你"),
        Cue(2, 0.6, 1.4, "好世界"),
        Cue(3, 1.4, 2, "结束"),
    ]

    bilingual = align_translation_cues(source, translated)

    assert "你" in bilingual[0].text
    assert "好世界" in bilingual[0].text
    assert "好世界" in bilingual[1].text
    assert "结束" in bilingual[1].text


def make_tiny_video(path: Path):
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:d=2",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-shortest",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                str(path),
            ],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        pytest.skip(f"ffmpeg unavailable for integration test: {error}")
