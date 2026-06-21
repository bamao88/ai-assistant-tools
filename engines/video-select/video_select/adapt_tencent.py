#!/usr/bin/env python3
"""腾讯会议逐字稿（minutes 格式）→ 我们的 words.json（选片输入）。

输入：`fetch_tencent_meeting_transcripts_stable.py` 下载的逐字稿 JSON，结构是
`{"minutes":{"paragraphs":[{speaker,sentences:[{start_time,end_time,words:[...]}]}]}}`
（毫秒时间戳，多说话人）。

输出：`{"words":[{text,begin_time,end_time}], "sentences":[{text,begin_time,end_time,speaker,is_host}]}`
——即 `video_slicer.transcribe.segment.sentences_from_wordfile` 能直接吃的格式。
**保留每句说话人**：`is_host = (speaker == host)`，让选题能区分主讲 vs 学员（答疑场景需要）。

用法:
  python -m video_select.adapt_tencent --in <腾讯逐字稿.json> --out <words.json> [--host 张和]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _para_speaker(para: dict) -> str:
    sp = para.get("speaker")
    if isinstance(sp, dict):
        return sp.get("user_name", "") or ""
    return str(sp or "")


def adapt(minutes_json: dict, host: str = "张和") -> dict:
    """腾讯 minutes dict → 我们的 words.json dict（保留说话人）。"""
    paras = minutes_json.get("minutes", {}).get("paragraphs", [])
    words: list[dict] = []
    sentences: list[dict] = []
    for para in paras:
        speaker = _para_speaker(para)
        is_host = speaker == host
        for s in para.get("sentences", []):
            ws = s.get("words", []) or []
            text = "".join((w.get("text") or "") for w in ws).strip()
            if not text:
                continue
            for w in ws:
                t = (w.get("text") or "").strip()
                b, e = w.get("start_time"), w.get("end_time")
                if t and b is not None and e is not None:
                    words.append({"text": t, "begin_time": int(b), "end_time": int(e)})
            sentences.append({"text": text, "begin_time": int(s["start_time"]),
                              "end_time": int(s["end_time"]), "speaker": speaker, "is_host": is_host})
    words.sort(key=lambda x: x["begin_time"])
    sentences.sort(key=lambda x: x["begin_time"])
    return {"model": "tencent.minutes", "host": host,
            "source_url": minutes_json.get("entry", {}).get("url", ""),
            "words": words, "sentences": sentences}


def run(in_path: str | Path, out_path: str | Path, host: str = "张和") -> dict:
    data = json.loads(Path(in_path).read_text(encoding="utf-8"))
    out = adapt(data, host=host)
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n_host = sum(1 for s in out["sentences"] if s["is_host"])
    print(f"[adapt-tencent] {len(out['sentences'])} 句（主讲 {n_host} / 学员 {len(out['sentences'])-n_host}）"
          f"、{len(out['words'])} 词 → {out_path}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(prog="adapt_tencent", description="腾讯会议逐字稿 → words.json（选片输入）")
    ap.add_argument("--in", dest="inp", required=True, help="腾讯逐字稿 JSON（minutes 格式）")
    ap.add_argument("--out", required=True, help="输出 words.json")
    ap.add_argument("--host", default="张和", help="主讲名（用于 is_host 判定）")
    a = ap.parse_args()
    run(a.inp, a.out, host=a.host)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
