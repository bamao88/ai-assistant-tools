"""纯文字端到端固化测试：火山原生 fixture → 文案/字幕 都带标点 ITN（不切视频、不联网）。

用 `tests/fixtures/volc_native_words.json`（带 sentences[] 的火山风格转写）跑通
segment → map_clip → 去口水(打桩) → 文案 + 字幕(.srt)，断言标点和书面数字一路保留。
真去口水(KIMI/MiniMax)实跑见 var/output/native-text-e2e/（需 key，本测试不依赖）。
"""
from __future__ import annotations

from pathlib import Path

from video_slicer import script_clean
from video_slicer.transcribe import align, segment
from video_slicer.twostage import cut_video

_FX = Path(__file__).parent / "fixtures" / "volc_native_words.json"


def test_native_words_to_punctuated_text_files(monkeypatch, tmp_path):
    words, sents = segment.sentences_from_wordfile(_FX)
    assert [s.text for s in sents][0].endswith("。")          # 用了原生句(带标点)
    seg_words = words[sents[0].wi: sents[-1].wj + 1]
    rich = align.map_clip(list(sents), words)
    assert "30%、20%甚至10%" in align.rich_text(rich)          # 相邻 ITN 块对齐不丢

    # 打桩去口水：删口水、保留带标点 ITN（即真模型在 var/output 里产出的同款）
    cleaned = ("真的不要做低代码了，不要做工作流了，完全干不过Agent。今天用Codex能解决的问题，"
               "如果用低代码只能解决30%、20%甚至10%，水平能差5到10倍。除了极少数场景，比如外呼客服。")

    class _Stub:
        def __init__(self, *a, **k): ...
        def chat(self, *a, **k): return cleaned

    monkeypatch.setattr(script_clean, "OpenAICompatibleClient", _Stub)
    ck = script_clean.clean_to_keep(seg_words, rich_tokens=rich)

    # 文案：带标点 + 书面数字，且口水已删
    assert "30%、20%甚至10%" in ck["kept_text_rich"]
    assert "5到10倍" in ck["kept_text_rich"]
    assert "嗯" not in ck["kept_text_rich"] and "那个" not in ck["kept_text_rich"]

    # 字幕：.srt 落盘且带标点 ITN
    srt = cut_video.relative_srt(ck["kept_words"], ck["keep_spans"], tmp_path / "c.srt")
    body = srt.read_text(encoding="utf-8")
    assert "%" in body and "。" in body
