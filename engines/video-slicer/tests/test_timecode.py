from video_slicer.timecode import format_srt_timecode, format_timecode, parse_clip_range, parse_timecode


def test_parse_and_format_timecode():
    assert parse_timecode("00:01:02.345") == 62.345
    assert parse_timecode("01:02.345") == 62.345
    assert format_timecode(62.345) == "00:01:02.345"
    assert format_srt_timecode(62.345) == "00:01:02,345"


def test_parse_bare_seconds_from_llm():
    assert parse_timecode("468.855") == 468.855
    assert parse_timecode("468") == 468.0
    assert parse_timecode("90,5") == 90.5  # comma decimal


def test_parse_clip_range():
    assert parse_clip_range("00:00:01-00:00:03") == (1, 3)

