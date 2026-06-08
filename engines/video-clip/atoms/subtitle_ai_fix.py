#!/usr/bin/env python3
"""subtitle-ai-fix —— 用 AI 加工字幕：ASR 纠错 + 术语订正 + 轻度口语清理（原子能力）。

输入一条 SRT，逐条丢给 LLM，**严格等长 1:1 返回**：只改文本，不动 cue 条数/时间戳，
不合并不拆分不总结。时间轴完全不变，下游 subtitle-burn / speed-adapt 照用。
源自 assistant_zh/workflow/video_framework_slicer/srt_fix.py，复用 video-slicer 引擎的 LLM 客户端。

用法:
  subtitle_ai_fix.py IN.srt OUT.srt [--hint "这条切片讲的核心"]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

# 复用 video-slicer 引擎的 LLM 客户端（同一份共享 .env / provider 链）
_ENGINE = "/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-slicer"
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402

SYSTEM_PROMPT = """你是中文口播视频的字幕校对员。输入是一条短视频切片里主讲人的逐字稿 cue 数组（机器语音识别 ASR 产出，按时间顺序）。语境是「AI 产品 / 编程 / AI 创业」播客式分享。你要逐条订正，**严格等长 1:1 返回**。

【只做两件事】
1. 订正 ASR 听错的词，重点是专有名词/技术术语（中文同音错字也要改）。常见错法举例（不限于此）：
   - honeystone / 哈尼森 / 哈里森 / 海纳斯  → Harness（如「Harness Engineering」）
   - cloud code / blood code / 克劳德 code → Claude Code
   - cloud agent sdk / cloud sgn sdk / agent sgk → Agent SDK / Claude Agent SDK
   - codecs / codex → Codex；克瑟 / cursor → Cursor；copilot 保持 Copilot
   - mcp / 而 cp → MCP；prd → PRD；token / 套кен → token；prompt → prompt
   - agent → agent；LLM / 大模型 保持；GPT / chat gpt → ChatGPT；gpt 4 → GPT-4
   - vibe coding / 外不 coding → vibe coding；context engineering → context engineering
   - rag → RAG；api → API；saas → SaaS；demo → demo；builder → builder
   - git / 鸡他 → git；repo → repo；debug → debug；deploy → deploy
   英文技术词统一规范大小写；中文里夹的英文术语保留英文。
2. 轻度清理口语：去掉紧邻的结巴重复（"你你懂"→"你懂"、"也也也学"→"也学"、"就能就能就能"→"就能"、"咱们咱们"→"咱们"），去掉无意义语气填充的冗余。

【绝对禁止】
- 不许改变 cue 条数、顺序；输入几条就输出几条，第 i 条对应第 i 条。
- 不许合并、拆分、总结、改写句意、翻译；不许补主讲人没说的内容。
- 不许动标点节奏到面目全非；保持口语自然，只是把错词改对、把结巴去掉。
- 拿不准的词就保持原样，别瞎猜成别的词。

【输出】严格 JSON，不要 markdown：
{"cues":["<第0条订正后>","<第1条订正后>", ...]}
cues 数组长度必须等于输入条数。"""


def parse_srt(srt_path):
    out = []
    for b in Path(srt_path).read_text(encoding="utf-8").strip().split("\n\n"):
        L = [x for x in b.split("\n") if x.strip()]
        if len(L) < 3 or "-->" not in L[1]:
            continue
        t0, t1 = (x.strip() for x in L[1].split("-->"))
        out.append({"t0": t0, "t1": t1, "text": " ".join(L[2:]).strip()})
    return out


def _call_llm(texts, hint, providers):
    payload = {"hint": hint or "", "cues": [{"i": i, "text": t} for i, t in enumerate(texts)]}
    client = OpenAICompatibleClient(providers=list(providers))
    data = client.chat_json(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        temperature=0.0)
    norm = []
    for x in data.get("cues") or []:
        if isinstance(x, str):
            norm.append(x)
        elif isinstance(x, dict):
            norm.append(str(x.get("text", "")))
    return norm


def correct_cues(texts, hint=None, providers=("kimi", "minimax")):
    """逐条订正，严格等长。单条返空用原文补位；条数不符重试一次；仍不符整条回退(绝不丢字幕)。"""
    if not texts:
        return texts
    load_env_file(_discover_env_file())
    for attempt in (1, 2):
        try:
            norm = _call_llm(texts, hint, providers)
        except Exception as ex:  # noqa: BLE001
            print(f"  [ai-fix] LLM 失败(第{attempt}次)：{str(ex)[:140]}", file=sys.stderr); continue
        if len(norm) == len(texts):
            out, empties = [], 0
            for orig, nw in zip(texts, norm):
                nw = re.sub(r"\s{2,}", " ", nw).strip()
                out.append(nw if nw else orig); empties += 0 if nw else 1
            if empties:
                print(f"  [ai-fix] {empties} 条返空，已用原文补位", file=sys.stderr)
            return out
        print(f"  [ai-fix] 条数不符(in={len(texts)} out={len(norm)})，第{attempt}次", file=sys.stderr)
    print("  [ai-fix] 重试后仍不符，回退原文", file=sys.stderr)
    return texts


def main():
    ap = argparse.ArgumentParser(description="用 AI 加工字幕(纠错+口语清理),时间轴1:1")
    ap.add_argument("input", help="输入 SRT")
    ap.add_argument("output", help="输出 SRT")
    ap.add_argument("--hint", default=None)
    a = ap.parse_args()
    if not Path(a.input).exists():
        raise SystemExit(f"输入不存在: {a.input}")
    cues = parse_srt(a.input)
    fixed = correct_cues([c["text"] for c in cues], hint=a.hint)
    lines = []
    for i, (c, t) in enumerate(zip(cues, fixed), start=1):
        lines += [str(i), f"{c['t0']} --> {c['t1']}", t, ""]
    Path(a.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"DONE  {a.output}  AI 订正 {len(cues)} 条")


if __name__ == "__main__":
    main()
