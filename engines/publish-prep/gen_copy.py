#!/usr/bin/env python3
"""切片 → 正文 生成器（Kimi，干净上下文）。

SYSTEM/USER prompt 从 skill 的 prompts/body_video.md 读（config.BODY_VIDEO_PROMPT），
不再内联——口径（企业AI落地）改一处即可。复用 assistant_zh 的 knowledge_ingest/core.py LLM 客户端。

用法:
    python3 gen_copy.py <clip_dir> [--platform 小红书|视频号] [--provider kimi|minimax] [--title 主题]
"""
import sys
import os
import re
import json
import argparse
from pathlib import Path

import config

sys.path.insert(0, str(config.KNOWLEDGE_INGEST))
import core  # noqa: E402
core.load_env(config.ENV_FILE)


def load_prompt() -> tuple[str, str]:
    """从 body_video.md 抽 `## SYSTEM` 与 `## USER` 两段。"""
    md = config.BODY_VIDEO_PROMPT.read_text(encoding="utf-8")

    def section(name: str) -> str:
        m = re.search(rf"^## {name}\s*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
        return m.group(1).strip() if m else ""

    return section("SYSTEM"), section("USER")


def srt_to_text(srt_path: Path) -> str:
    """剥掉序号和时间轴，只留口播文字。"""
    lines = []
    for ln in srt_path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.isdigit() or "-->" in s:
            continue
        lines.append(s)
    return "".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_dir")
    ap.add_argument("--provider", choices=["auto", "kimi", "minimax"], default="auto",
                    help="auto=kimi→minimax 自动兜底（单个配额墙不卡死）")
    ap.add_argument("--platform", default="小红书")
    ap.add_argument("--title", default="（未提供，请你从逐字稿自行判断主题）")
    ap.add_argument("--temperature", type=float, default=0.7)
    args = ap.parse_args()

    clip_dir = Path(args.clip_dir)
    srt = clip_dir / "clip.fixed.srt"
    if not srt.exists():
        srt = clip_dir / "clip.srt"
    transcript = srt_to_text(srt)

    system, user_tmpl = load_prompt()
    os.environ["LLM_PROVIDER"] = args.provider
    user = user_tmpl.format(transcript=transcript, topic=args.title, platform=args.platform)

    raw = core.call_llm(system, user, temperature=args.temperature, json_mode=True)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"_raw": raw}
    data["_provider"] = args.provider
    data["_platform"] = args.platform
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
