"""流程一 · 选题（Runner 第 1 段）。

输入：整场编号逐字稿（带说话人）。输出：少而精的选题候选，每条带「粗句号区间」
（`rough_sid_spans`）。AI 只做编辑判断 + 指出大概在哪几句，**不吐时间戳、不定段**
（原 stage2 定段已停用，精确边界交流程二·总编）。

提示词从 `prompts/topic-select.md` 读（不再拼接 persona 文件）。
逐字稿→句的核心 import 自 video-slicer（单向依赖）。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import _deps  # noqa: F401  挂 video-slicer 到 sys.path
from ._deps import load_prompt

from video_slicer.transcribe import segment  # noqa: E402
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402


def _render_numbered(sents, host_label: str = "主讲", guest_label: str = "学员") -> str:
    """整场编号逐字稿（喂选题）。说话人压成两类，省 token、聚焦主讲。"""
    lines = []
    for s in sents:
        who = host_label if s.is_host else guest_label
        lines.append(f"#{s.sid} [{who}] {s.text}")
    return "\n".join(lines)


def select_topics(sents, providers: list[str] | None = None,
                  temperature: float = 0.2) -> list[dict]:
    """整场逐字稿 → 选题候选（只保留给了 rough_sid_spans 的）。"""
    transcript = _render_numbered(sents)
    client = OpenAICompatibleClient(providers=providers)
    msgs = [{"role": "system", "content": load_prompt("topic-select")},
            {"role": "user", "content": transcript}]
    data = None
    for _ in (1, 2):  # 整场长稿一次性吐 JSON 偶发截断/超时/返回非对象，重试一次
        try:
            r = client.chat_json(msgs, temperature=temperature)
            if isinstance(r, dict):
                data = r
                break
        except Exception:  # noqa: BLE001
            continue
    clips = (data or {}).get("clips", [])
    return [c for c in clips if c.get("rough_sid_spans")]


def run(words_json: str | Path, out_path: str | Path, host: str = "张和",
        providers: list[str] | None = None) -> dict:
    """words.json → _selection.json（选题清单）。"""
    _, sents = segment.sentences_from_wordfile(words_json, host=host)
    clips = select_topics(sents, providers=providers)
    out = {"source": str(words_json), "host": host, "method": "topic-select", "clips": clips}
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(prog="topics", description="流程一·选题 Runner")
    ap.add_argument("--words", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    res = run(a.words, a.out, host=a.host, providers=providers)
    print(f"[topics] {len(res['clips'])} 条选题 → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
