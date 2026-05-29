from pathlib import Path

import pytest

from video_slicer.transcript import clean_caption_text, detect_language, parse_transcript, parse_vtt


def test_parse_youtube_vtt_inline_word_tags(tmp_path: Path):
    path = tmp_path / "sample.en.vtt"
    path.write_text(
        """WEBVTT
Kind: captions
Language: en

00:00:00.080 --> 00:00:02.000 align:start position:0%
I<00:00:00.320><c> think</c><00:00:00.400><c> it</c><00:00:00.640><c> works</c>

00:00:02.000 --> 00:00:04.000 align:start position:0%
>> It<00:00:02.200><c> does</c><00:00:02.500><c> work</c>
""",
        encoding="utf-8",
    )

    cues = parse_transcript(path)

    assert len(cues) == 2
    assert cues[0].text == "I think it works"
    assert cues[1].text == ">> It does work"
    assert detect_language(cues, path) == "en"


def test_parse_srt(tmp_path: Path):
    path = tmp_path / "sample.zh.srt"
    path.write_text(
        """1
00:00:00,000 --> 00:00:01,500
你好

2
00:00:01,500 --> 00:00:03,000
世界
""",
        encoding="utf-8",
    )

    cues = parse_transcript(path)

    assert len(cues) == 2
    assert cues[0].text == "你好"
    assert detect_language(cues, path) == "zh"


def test_plain_text_is_rejected(tmp_path: Path):
    path = tmp_path / "plain.txt"
    path.write_text("No timestamps here.", encoding="utf-8")

    with pytest.raises(ValueError, match="Timestamped transcripts are required"):
        parse_transcript(path)


def test_clean_caption_text():
    assert clean_caption_text("A<00:00:00.100><c> B</c> &amp; C") == "A B & C"

