"""两阶段选段编排：minutes JSON → {选题 + 切片脚本}。止于脚本，不渲染。

用法：
  python -m video_slicer.twostage.pipeline <minutes.json> --persona zh_main \\
      --out cand.json [--md cand.md] [--host 张和] [--providers kimi,minimax] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..cli import _discover_env_file, load_env_file
from .index import Sentence, load_indexed_sentences
from .stage1_topics import load_persona, select_topics
from .stage2_script import select_script


def assemble_script(keep_sids: list[list[int]], sentences: list[Sentence]) -> dict:
    """keep_sids → 脚本文本 + 句级时间段 + 估时（句级；字级精修是后续 resolver 的事）。"""
    by_sid = {s.sid: s for s in sentences}
    parts: list[str] = []
    spans_time: list[list[float]] = []
    dur = 0.0
    for a, b in keep_sids:
        seg = [by_sid[sid] for sid in range(a, b + 1) if sid in by_sid and by_sid[sid].is_host]
        if not seg:
            continue
        parts.append("".join(s.text for s in seg))
        spans_time.append([round(seg[0].start, 2), round(seg[-1].end, 2)])
        dur += seg[-1].end - seg[0].start
    return {"script": "\n".join(parts), "sentence_time_spans": spans_time, "est_duration": round(dur, 1)}


def run(
    minutes_path: str,
    persona: str,
    host: str = "张和",
    providers: list[str] | None = None,
    limit: int | None = None,
) -> dict:
    sentences = load_indexed_sentences(minutes_path, host=host)
    persona_text = load_persona(persona)

    print(f"[stage1] 选题中…（{len(sentences)} 句逐字稿）", file=sys.stderr)
    topics = select_topics(sentences, persona=persona, providers=providers)
    if limit:
        topics = topics[:limit]
    print(f"[stage1] 出 {len(topics)} 条选题", file=sys.stderr)

    clips = []
    for i, clip in enumerate(topics, 1):
        print(f"[stage2] ({i}/{len(topics)}) 定脚本：{clip.get('title','')[:24]}…", file=sys.stderr)
        keep = []
        for attempt in (1, 2):  # 一条失败不拖累整批：重试一次，仍失败则跳过
            try:
                keep = select_script(clip, sentences, persona_text, providers=providers)
                break
            except Exception as ex:  # noqa: BLE001
                print(f"         ↳ 第{attempt}次失败：{str(ex)[:120]}", file=sys.stderr)
        if not keep:
            print("         ↳ 无可用句/调用失败，跳过", file=sys.stderr)
            continue
        asm = assemble_script(keep, sentences)
        if not asm["script"].strip():
            continue
        clips.append({**{k: clip.get(k) for k in
                         ("title", "one_argument", "hook_line", "audience", "mainstream", "why")},
                      "keep_sids": keep, **asm,
                      "备注": ""})  # 留空，供人工审查填写
    return {"source": minutes_path, "persona": persona, "host": host, "clips": clips}


def to_markdown(result: dict) -> str:
    out = [f"# 方案B 选段结果（{len(result['clips'])} 条） · persona={result['persona']}", ""]
    for i, c in enumerate(result["clips"], 1):
        out.append(f"## {i}. {c['title']}")
        out.append(f"- 论点：{c['one_argument']}")
        out.append(f"- 受众：{c.get('audience','')} ｜ 流量：{c.get('mainstream','')} ｜ 估时：{c['est_duration']}s")
        out.append(f"- 句号：{c['keep_sids']} ｜ 时间段：{c['sentence_time_spans']}")
        out.append(f"- 脚本：")
        for line in c["script"].split("\n"):
            out.append(f"  > {line}")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(prog="twostage")
    ap.add_argument("minutes")
    ap.add_argument("--persona", default="zh_main")
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 条选题（调试省钱用）")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    result = run(a.minutes, persona=a.persona, host=a.host, providers=providers, limit=a.limit)
    blob = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(blob + "\n", encoding="utf-8")
        print(f"写出 {len(result['clips'])} 条 → {a.out}", file=sys.stderr)
    else:
        print(blob)
    if a.md:
        Path(a.md).write_text(to_markdown(result) + "\n", encoding="utf-8")
        print(f"可读版 → {a.md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
