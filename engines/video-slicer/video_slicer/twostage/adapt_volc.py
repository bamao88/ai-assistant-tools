"""火山转录 → twostage 句级输入 适配层。

把火山风格的字级词表 + 句级分句表，适配成 twostage 认的 `list[Sentence]`，
让字级线（火山转写 → 选片 → 去口水）端到端跑通，无需腾讯会议 minutes 格式。

输入两份（videocut-zh / 火山 transcribe_live 产出，或我们 transcribe 模块 + 分句后）：
- 字级词表：`[{text,start,end,isGap}]`（秒）—— videocut-zh subtitles_words.json
- 句级分句：每行 `句号|起词idx-止词idx|文本` —— videocut-zh sentences.txt（按静音切句）

口播/直播=单说话人，全部 is_host=True（host 名给 speaker 标签）。
"""
from __future__ import annotations

import json
from pathlib import Path

from .index import Sentence


def load_volc_sentences(
    words_json: str | Path,
    sentences_txt: str | Path,
    host: str = "张和",
) -> list[Sentence]:
    """火山字级词表 + 句级分句 → list[Sentence]（sid=原句号，便于与人工选片交叉对照）。"""
    words = json.loads(Path(words_json).read_text(encoding="utf-8"))
    n = len(words)
    out: list[Sentence] = []
    for raw in Path(sentences_txt).read_text(encoding="utf-8").splitlines():
        parts = raw.split("|", 2)
        if len(parts) != 3 or not parts[0].isdigit():
            continue
        sid = int(parts[0])
        idx_range, text = parts[1], parts[2].strip()
        if not text:
            continue
        try:
            si, ei = (int(x) for x in idx_range.split("-"))
        except ValueError:
            continue
        start = float(words[si]["start"]) if 0 <= si < n else 0.0
        end = float(words[ei]["end"]) if 0 <= ei < n else start
        out.append(Sentence(sid=sid, start=start, end=end, speaker=host, text=text, is_host=True))
    return out
