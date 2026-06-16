"""字级词表 → 按字间静音分句（让字级线自给自足，不再依赖外部 sentences.txt）。

搬 videocut-zh `transcribe_live.py` 的 gen_readable 静音切句逻辑：相邻字之间静音 ≥0.5s 断句。
我们的 words.json 没有 isGap 占位，从相邻字的 (下一字.start - 上一字.end) 直接算静音。

兼容两种字级词表 schema：
- 我们 transcribe：`{"words":[{text,begin_time(ms),end_time(ms)}]}`
- videocut-zh   ：`[{text,start(sec),end(sec),isGap}]`
"""
from __future__ import annotations

import json
from pathlib import Path

from ..twostage.index import Sentence


def load_words(path: str | Path) -> list[dict]:
    """读字级词表 → 归一化 `[{text,start,end}]`（秒，去静音占位，按时间排序）。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: list[dict] = []
    if isinstance(data, dict) and "words" in data:                  # 我们 transcribe（毫秒）
        for w in data["words"]:
            b, e = w.get("begin_time"), w.get("end_time")
            t = (w.get("text") or "").strip()
            if b is None or e is None or not t:
                continue
            out.append({"text": t, "start": b / 1000, "end": e / 1000})
    elif isinstance(data, list):                                    # videocut-zh（秒 + isGap）
        for w in data:
            if w.get("isGap"):
                continue
            s, e = w.get("start"), w.get("end")
            t = (w.get("text") or "").strip()
            if s is None or e is None or not t:
                continue
            out.append({"text": t, "start": float(s), "end": float(e)})
    else:
        raise ValueError(f"无法识别的字级词表 schema：{type(data)}")
    out.sort(key=lambda x: x["start"])
    return out


def segment_to_sentences(words: list[dict], gap_sec: float = 0.5, host: str = "张和") -> list[Sentence]:
    """归一化词表 → Sentence 列表（字间静音 ≥gap_sec 断句）。每句记录词索引范围 wi/wj。"""
    sents: list[Sentence] = []
    cur: list[tuple[int, dict]] = []

    def flush() -> None:
        if not cur:
            return
        wi, wj = cur[0][0], cur[-1][0]
        text = "".join(w["text"] for _, w in cur)
        sents.append(Sentence(sid=len(sents), start=cur[0][1]["start"], end=cur[-1][1]["end"],
                              speaker=host, text=text, is_host=True, wi=wi, wj=wj))
        cur.clear()

    for i, w in enumerate(words):
        if cur and w["start"] - cur[-1][1]["end"] >= gap_sec:
            flush()
        cur.append((i, w))
    flush()
    return sents


def sentences_from_wordfile(path: str | Path, gap_sec: float = 0.5, host: str = "张和"):
    """便捷：字级词表文件 → (words 归一化列表, Sentence 列表)。字级线端到端入口用。"""
    words = load_words(path)
    return words, segment_to_sentences(words, gap_sec=gap_sec, host=host)
