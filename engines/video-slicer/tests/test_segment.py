"""segment.py + clean_to_keep 富 token 路径的固化测试（纯本地，不联网）。

固化需求里"已测未固化"的两条分句路径：有原生句 → 用语义句；无 → 退回按停顿切。
并用打桩 LLM 验证去口水富 token 路径产出带标点 ITN 文案（无需真火山/真 provider）。
"""
from __future__ import annotations

import json
from pathlib import Path

from video_slicer import script_clean
from video_slicer.transcribe import segment


def _wordsfile(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "words.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


def test_sentences_from_wordfile_uses_native_when_present(tmp_path: Path):
    # 有 sentences[] → 走 segment_native（语义句），句界由原生句决定
    payload = {
        "words": [
            {"text": "我", "begin_time": 0, "end_time": 200},
            {"text": "好", "begin_time": 200, "end_time": 400},
            {"text": "你", "begin_time": 1000, "end_time": 1200},
            {"text": "行", "begin_time": 1200, "end_time": 1400},
        ],
        "sentences": [
            {"text": "我好。", "begin_time": 0, "end_time": 400},
            {"text": "你行！", "begin_time": 1000, "end_time": 1400},
        ],
    }
    words, sents = segment.sentences_from_wordfile(_wordsfile(tmp_path, payload))
    assert [s.text for s in sents] == ["我好。", "你行！"]          # 用原生句文本(带标点)
    assert sents[0].wi == 0 and sents[0].wj == 1                   # 字索引按时间落入
    assert sents[1].wi == 2 and sents[1].wj == 3


def test_sentences_from_wordfile_falls_back_to_gap_split(tmp_path: Path):
    # 无 sentences[] → 退回按字间停顿(≥0.5s)切句
    payload = {
        "words": [
            {"text": "我", "begin_time": 0, "end_time": 200},
            {"text": "好", "begin_time": 200, "end_time": 400},
            {"text": "你", "begin_time": 1000, "end_time": 1200},   # 距上字 0.6s>0.5s → 断句
            {"text": "行", "begin_time": 1200, "end_time": 1400},
        ],
    }
    words, sents = segment.sentences_from_wordfile(_wordsfile(tmp_path, payload))
    assert [s.text for s in sents] == ["我好", "你行"]              # 裸拼无标点
    assert len(sents) == 2


def test_clean_to_keep_rich_path_yields_punctuated_itn_text(monkeypatch):
    # 打桩 LLM：去口水删掉"嗯"，保留带标点 ITN 文本
    rich = [
        {"text": "真", "start": 0.0, "end": 0.1, "kind": "char"},
        {"text": "的", "start": 0.1, "end": 0.2, "kind": "char"},
        {"text": "嗯", "start": 0.2, "end": 0.3, "kind": "char"},
        {"text": "增长", "start": 0.3, "end": 0.5, "kind": "char"},
        {"text": "90%", "start": 0.5, "end": 1.0, "kind": "itn"},
        {"text": "。", "start": 1.0, "end": 1.0, "kind": "char"},
    ]

    class _StubClient:
        def __init__(self, *a, **k):
            pass

        def chat(self, *a, **k):
            return "真的增长90%。"                                 # AI 删口水后的带标点 ITN 文本

    monkeypatch.setattr(script_clean, "OpenAICompatibleClient", _StubClient)
    seg_words = [{"text": t["text"], "start": t["start"], "end": t["end"]} for t in rich]
    ck = script_clean.clean_to_keep(seg_words, rich_tokens=rich)
    assert ck["kept_text_rich"] == "真的增长90%。"                 # 带标点 + 书面数字
    assert "嗯" not in ck["kept_text"]
    assert ck["keep_spans"]                                        # 有可切的时间区间
    # 富路径下 kept_words 即富 token，喂 relative_srt 能出带标点字幕
    assert any(w["text"] == "90%" for w in ck["kept_words"])
