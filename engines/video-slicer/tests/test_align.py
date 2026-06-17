"""align.py 合成单测：句级带标点 ITN 文本 ↔ 字级词 的对齐 + 去口水后投影。

不需要真实火山数据：手搓字级词 + 对应带标点 ITN 句，覆盖普通字 / ITN 数字块 / 标点 /
删词投影 / 对不齐降级。真实火山效果在 fixture 落地后另验（计划验证3，待 key）。
"""
from __future__ import annotations

import pytest

from video_slicer.transcribe import align


def _words(spec: list[tuple[str, float, float]]) -> list[dict]:
    """[(字, start, end)] → [{text,start,end}]（秒）。"""
    return [{"text": t, "start": s, "end": e} for t, s, e in spec]


def test_map_sentence_plain_chars_carry_time():
    # "我们好" 三个普通字，标点并入前一 token
    words = _words([("我", 0.0, 0.2), ("们", 0.2, 0.4), ("好", 0.4, 0.6)])
    toks = align.map_sentence("我们好。", words)
    assert [t["text"] for t in toks] == ["我", "们", "好。"]      # 句号并入"好"
    assert toks[0]["start"] == 0.0 and toks[2]["end"] == 0.6
    assert all(t["kind"] == "char" for t in toks)


def test_map_sentence_itn_block_binds_numeral_span():
    # 文本 "90%" 对应字级"百分之九十"5 个字，整块绑定其时间
    words = _words([("增", 0.0, 0.2), ("长", 0.2, 0.4),
                    ("百", 0.4, 0.5), ("分", 0.5, 0.6), ("之", 0.6, 0.7),
                    ("九", 0.7, 0.8), ("十", 0.8, 0.9), ("了", 0.9, 1.1)])
    toks = align.map_sentence("增长90%了", words)
    texts = [t["text"] for t in toks]
    assert texts == ["增", "长", "90%", "了"]
    itn = next(t for t in toks if t["kind"] == "itn")
    assert itn["text"] == "90%"
    assert itn["start"] == 0.4 and itn["end"] == 0.9             # 起=百, 止=十


def test_map_sentence_itn_at_end_consumes_rest():
    # 数字在句末："五倍"→"5倍" 里 "5" 在末尾的退化情形：数字段后无锚字 → 吃光剩余字
    words = _words([("差", 0.0, 0.2), ("五", 0.2, 0.4), ("十", 0.4, 0.6)])
    toks = align.map_sentence("差50", words)
    assert [t["text"] for t in toks] == ["差", "50"]
    assert toks[1]["start"] == 0.2 and toks[1]["end"] == 0.6


def test_map_sentence_mismatch_raises():
    words = _words([("我", 0.0, 0.2), ("们", 0.2, 0.4)])
    with pytest.raises(align.AlignError):
        align.map_sentence("你们", words)                        # 首字对不上


def test_project_cleaned_keeps_surviving_tokens_with_punct_and_itn():
    words = _words([("真", 0.0, 0.1), ("的", 0.1, 0.2), ("嗯", 0.2, 0.3),
                    ("增", 0.3, 0.4), ("长", 0.4, 0.5),
                    ("百", 0.5, 0.6), ("分", 0.6, 0.7), ("之", 0.7, 0.8),
                    ("九", 0.8, 0.9), ("十", 0.9, 1.0)])
    toks = align.map_sentence("真的，嗯增长90%", words)
    kept = align.project_cleaned("真的，增长90%", toks)           # 删了"嗯"
    assert align.rich_text(kept) == "真的，增长90%"
    assert "嗯" not in align.rich_text(kept)
    # ITN 块整块保留，时间正确
    itn = next(t for t in kept if t["kind"] == "itn")
    assert itn["text"] == "90%" and itn["start"] == 0.5 and itn["end"] == 1.0


def test_project_cleaned_drops_trailing_when_deleted():
    words = _words([("好", 0.0, 0.1), ("的", 0.1, 0.2), ("呀", 0.2, 0.3)])
    toks = align.map_sentence("好的呀", words)
    kept = align.project_cleaned("好的", toks)                   # 删了句尾"呀"
    assert align.rich_text(kept) == "好的"


def test_map_clip_concats_sentences():
    class _S:
        def __init__(self, text, wi, wj):
            self.text, self.wi, self.wj, self.sid = text, wi, wj, 0
    words = _words([("我", 0.0, 0.2), ("好", 0.2, 0.4), ("你", 0.4, 0.6), ("行", 0.6, 0.8)])
    sents = [_S("我好。", 0, 1), _S("你行！", 2, 3)]
    toks = align.map_clip(sents, words)
    assert align.rich_text(toks) == "我好。你行！"
