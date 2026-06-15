#!/usr/bin/env python3
"""srt_fix —— clip 字幕 LLM 纠错（术语订正 + 轻度口语清理），保留时间轴 1:1。

腾讯 ASR 原声字幕在 AI/编程/创业语境下系统性错术语（Harness→honeystone、
Claude Agent SDK→cloud agent sdk、Codex/Cursor/MCP 等），口语还带大量即时重复
（"你你懂"/"也也也"/"就能就能"）。本模块把一条 clip 的 cue 文本逐条丢给 LLM 纠错，
**严格等长 1:1 返回**：只改文本，不动 cue 条数、不动时间戳、不合并不拆分不总结。
渲染层(slicer.make_subtitles / accelerate)读修正后的 SRT，时间轴完全不变。

复用 video-slicer 引擎的 LLM 客户端（同一套 .env / provider 链、temp=0、json_mode、
think 块剥离、重试），套路同 pages_gen.py。

【迁移说明（video-tools-migration 阶段2）】
  原住 assistant_zh/workflow/video_framework_slicer/，靠 sys.path 反向依赖本引擎。
  现迁入 video_slicer 包，改正常包内相对导入。张和术语表/纠错 prompt 抽到定制层
  profiles/<profile>/srt_fix_system_prompt.txt（默认 zh_main），引擎不再内嵌账号术语。

用法：
  python -m video_slicer.srt_fix <clip.srt> [--hint "核心"] [--profile zh_main] [--out clip.fixed.srt]
  # 不带 --out 时把修正后的 SRT 打到 stdout
程序化：
  from video_slicer.srt_fix import correct_srt
  correct_srt("clip.srt", "clip.fixed.srt", hint="...")
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

from .llm import OpenAICompatibleClient
from .cli import load_env_file, _discover_env_file

_ENGINE_ROOT = Path(__file__).resolve().parent.parent  # engines/video-slicer


def _load_system_prompt(profile: str = "zh_main") -> str:
    """从定制层读纠错 system prompt（含账号术语表，迁移计划 §3.2 定制层①）。"""
    p = _ENGINE_ROOT / "profiles" / profile / "srt_fix_system_prompt.txt"
    if not p.exists():
        raise FileNotFoundError(f"srt_fix: 缺定制层 prompt {p}（profile={profile}）")
    return p.read_text(encoding="utf-8")


def parse_srt(srt_path: str | Path) -> list[dict]:
    """SRT → [{idx, t0_raw, t1_raw, text}]（text 为该 cue 全部文本行合并，保留原始时间戳串）。"""
    blocks = Path(srt_path).read_text(encoding="utf-8").strip().split("\n\n")
    out: list[dict] = []
    for b in blocks:
        lines = [x for x in b.split("\n") if x.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        t0, t1 = (x.strip() for x in lines[1].split("-->"))
        text = " ".join(lines[2:]).strip()
        out.append({"t0": t0, "t1": t1, "text": text})
    return out


def _call_llm(texts: list[str], hint: str | None, providers, profile: str) -> list[str]:
    """单次 LLM 调用，返回归一化后的 cue 文本数组（可能与输入不等长，由上层判定）。"""
    payload = {"hint": hint or "",
               "cues": [{"i": i, "text": t} for i, t in enumerate(texts)]}
    client = OpenAICompatibleClient(providers=list(providers))
    data = client.chat_json(
        [{"role": "system", "content": _load_system_prompt(profile)},
         {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        temperature=0.0,
    )
    norm = []
    for x in data.get("cues") or []:  # 兼容 ["..."] 或 [{"i":..,"text":..}]
        if isinstance(x, str):
            norm.append(x)
        elif isinstance(x, dict):
            norm.append(str(x.get("text", "")))
    return norm


def correct_cues(texts: list[str], hint: str | None = None,
                 providers=("kimi", "minimax"), profile: str = "zh_main") -> list[str]:
    """逐条订正 cue，严格等长返回。等长时单条返空仅用原文补该条（不整条回退）；
    条数不符则重试一次；仍不符或全程异常才整条回退（绝不丢字幕）。"""
    if not texts:
        return texts
    load_env_file(_discover_env_file())
    for attempt in (1, 2):
        try:
            norm = _call_llm(texts, hint, providers, profile)
        except Exception as ex:  # noqa: BLE001
            print(f"  [srt_fix] LLM 失败(第{attempt}次)：{str(ex)[:140]}", file=sys.stderr)
            continue
        if len(norm) == len(texts):
            out, empties = [], 0
            for orig, nw in zip(texts, norm):
                nw = re.sub(r"\s{2,}", " ", nw).strip()
                if nw:
                    out.append(nw)
                else:
                    out.append(orig); empties += 1   # 单条返空→用原文补位
            if empties:
                print(f"  [srt_fix] {empties} 条返空，已用原文补位", file=sys.stderr)
            return out
        print(f"  [srt_fix] 条数不符(in={len(texts)} out={len(norm)})，第{attempt}次", file=sys.stderr)
    print("  [srt_fix] 重试后仍不符，回退原文", file=sys.stderr)
    return texts


def correct_srt(in_srt: str | Path, out_srt: str | Path,
                hint: str | None = None, providers=("kimi", "minimax"),
                profile: str = "zh_main") -> int:
    """读 in_srt → LLM 纠错 → 写 out_srt（时间戳原样）。返回 cue 条数。"""
    cues = parse_srt(in_srt)
    fixed = correct_cues([c["text"] for c in cues], hint=hint, providers=providers, profile=profile)
    lines: list[str] = []
    for i, (c, t) in enumerate(zip(cues, fixed), start=1):
        lines.append(str(i))
        lines.append(f"{c['t0']} --> {c['t1']}")
        lines.append(t)
        lines.append("")
    Path(out_srt).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(cues)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--hint", default=None)
    ap.add_argument("--profile", default="zh_main")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.out:
        n = correct_srt(a.srt, a.out, a.hint, profile=a.profile)
        print(f"订正 {n} 条 → {a.out}")
    else:
        cues = parse_srt(a.srt)
        fixed = correct_cues([c["text"] for c in cues], hint=a.hint, profile=a.profile)
        for i, (c, t) in enumerate(zip(cues, fixed), start=1):
            print(f"{i}\n{c['t0']} --> {c['t1']}\n{t}\n")


if __name__ == "__main__":
    main()
