from video_slicer.ffmpeg import build_video_filter
from video_slicer.subtitles import split_long_cues
from video_slicer.transcript import Cue


def test_split_long_cue_breaks_at_punctuation_and_keeps_timespan():
    cue = Cue(index=1, start=0.0, end=12.0, text="第一句话很长。第二句也不短，需要再切一刀；第三句收尾。")
    pieces = split_long_cues([cue], max_chars=10)

    assert len(pieces) > 1
    # Re-indexed monotonically and the original span is preserved end to end.
    assert [p.index for p in pieces] == list(range(1, len(pieces) + 1))
    assert pieces[0].start == 0.0
    assert abs(pieces[-1].end - 12.0) < 1e-6
    # Every piece stays within the character budget.
    assert all(len(p.text) <= 10 for p in pieces)


def test_split_leaves_short_and_bilingual_cues_untouched():
    short = Cue(index=1, start=0.0, end=2.0, text="短句")
    bilingual = Cue(index=2, start=2.0, end=4.0, text="这是中文\nThis is English and quite long")
    result = split_long_cues([short, bilingual], max_chars=8)

    assert [c.text for c in result] == ["短句", "这是中文\nThis is English and quite long"]


def test_vertical_filter_is_blur_pad_not_center_crop():
    graph = build_video_filter("vertical")
    assert graph is not None
    # Fit (decrease) the foreground, cover (increase)+blur the background, overlay.
    assert "force_original_aspect_ratio=decrease" in graph
    assert "boxblur" in graph
    assert "overlay=(W-w)/2:(H-h)/2" in graph


def test_subtitle_appends_after_layout_graph():
    graph = build_video_filter("vertical", "/tmp/x.srt")
    assert graph is not None
    assert graph.endswith("subtitles='/tmp/x.srt'")
    assert "setsar=1,subtitles=" in graph
