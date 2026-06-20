#!/usr/bin/env python3
"""方案A · 单阶段选段（备用对照）—— 整场逐字稿 → 切片候选（选题层）。一次 LLM 同时定选题 + 选段。

留作 Harness 里「方案A vs 方案B(twostage) vs 金标准」的脚本级对照真源。日常 Runner 走
topics.py(选题) + generate.py(总编/去口水/钩子) 两段式；本脚本不渲染、不切片，只出候选 JSON。

输入：腾讯 minutes JSON（paragraphs[] 带 ms 时间戳）。

用法:
  python -m video_select.select_clips_a <minutes.json> [--out cand.json] [--providers kimi,minimax]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import _deps  # noqa: F401  挂 video-slicer 到 sys.path
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402

SELECT_SYSTEM_PROMPT = """你是短视频切片选题官。输入是主讲一场口播/答疑的完整逐字稿(带 mm:ss 时间戳)。你的任务：从中挑出**少而精**的、能在社交平台上钩住陌生人的切片候选。宁缺毋滥，挑不出就少挑。只输出严格 JSON，不要 markdown。

【根本认知】
切片不是"把逐字稿按话题分块"，而是"用主讲的原话当素材，重新立一条短视频选题"。判断标准永远是"陌生人刷到会不会停下来、看完记不记得住"，不是"主讲讲到了什么"。

【选题闸：每条候选必须同时过这 5 关】
1. 独立可懂：抽掉课堂内部语境后，零背景陌生人能看懂吗？
2. 单一论点：这条只讲一个观点。
3. 值不值得切 = 看「反认知度」，不看「内不内行」。专有名词/权威人物/机构自带流量，是资产不是负债。
4. 价值一句话说清：能用一句话说出"观众看完得到什么"。
5. 炸点可前置：有没有一句主讲原话能当 0-3 秒钩子。

【in/out 点纪律】
in 点切到 hook_line 那句之前，丢掉软开场；out 点论点说完就收；允许跳接(中间砍废话、按时间先后)。

【输出 JSON】
{"clips":[{"title":"...","one_argument":"...","segments":[{"start":"09:50","end":"10:44"}],"hook_line":"...","mainstream":"高","audience":"...","why":"...","duration_sec":84}]}
只输出这个 JSON 对象。"""


def transcript_from_minutes(mj_path: str | Path) -> str:
    data = json.loads(Path(mj_path).read_text(encoding="utf-8"))
    paras = data["minutes"]["paragraphs"]
    lines = []
    for p in paras:
        ms = p.get("start_time", 0)
        mm, ss = divmod(int(ms) // 1000, 60)
        txt = "".join(w.get("text", "") for s in p.get("sentences", []) for w in s.get("words", []))
        if txt.strip():
            lines.append(f"[{mm:02d}:{ss:02d}] {txt.strip()}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(prog="select_clips_a", description="方案A·单阶段选段（备用对照）")
    ap.add_argument("minutes")
    ap.add_argument("--out", default=None)
    ap.add_argument("--providers", default="kimi,minimax")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    transcript = transcript_from_minutes(a.minutes)
    client = OpenAICompatibleClient(providers=a.providers.split(","))
    data = client.chat_json(
        [{"role": "system", "content": SELECT_SYSTEM_PROMPT},
         {"role": "user", "content": transcript}],
        temperature=0.2,
    )
    clips = data.get("clips", [])
    blob = json.dumps({"clips": clips}, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(blob + "\n", encoding="utf-8")
        print(f"写出 {len(clips)} 条候选 → {a.out}")
    else:
        print(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
