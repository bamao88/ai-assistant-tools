"""腾讯会议 minutes JSON → 全局编号的句子表（两阶段共用的「文本查找表」）。

句号(sid)是我们自己的 0 基连续编号，作为 AI 选择和代码回查时间的稳定锚点。
（不复用原始 sid 字段：它不保证全局唯一/连续。）
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Sentence:
    sid: int        # 我们的全局 0 基编号
    start: float    # 秒
    end: float      # 秒
    speaker: str
    text: str
    is_host: bool
    wi: int = -1    # 句首字在归一化词表中的索引（字级去口水/切片用；-1=未知）
    wj: int = -1    # 句尾字索引（含）


def load_indexed_sentences(minutes_path: str | Path, host: str = "张和") -> list[Sentence]:
    data = json.loads(Path(minutes_path).read_text(encoding="utf-8"))
    out: list[Sentence] = []
    sid = 0
    for para in data["minutes"]["paragraphs"]:
        speaker = (para.get("speaker") or {}).get("user_name", "")
        for s in para.get("sentences", []):
            text = "".join(w.get("text", "") for w in s.get("words", [])).strip()
            if not text:
                continue
            out.append(
                Sentence(
                    sid=sid,
                    start=s["start_time"] / 1000,
                    end=s["end_time"] / 1000,
                    speaker=speaker,
                    text=text,
                    is_host=(speaker == host),
                )
            )
            sid += 1
    return out


def render_numbered(sentences: list[Sentence], host_label: str = "张和", guest_label: str = "学员") -> str:
    """整场编号逐字稿（喂阶段一）。说话人压成 张和/学员 两类，省 token、聚焦主讲。"""
    lines = []
    for s in sentences:
        who = host_label if s.is_host else guest_label
        lines.append(f"#{s.sid} [{who}] {s.text}")
    return "\n".join(lines)


def render_window(sentences: list[Sentence], sids: list[int]) -> str:
    """给阶段二的候选句窗口（只列 host 句，逐句编号）。"""
    by_sid = {s.sid: s for s in sentences}
    lines = []
    for sid in sids:
        s = by_sid.get(sid)
        if s is not None:
            lines.append(f"#{s.sid} {s.text}")
    return "\n".join(lines)
