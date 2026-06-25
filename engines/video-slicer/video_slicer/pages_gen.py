#!/usr/bin/env python3
"""pages_gen —— 一条 clip 的逐字稿 → 框架页 pages JSON（slicer.py 的 pages 字段）。

这是 video_framework_slicer 的「唯一缺口」补全：原本 pages 手写，现在一次 LLM
调用读 clip 逐字稿自动产出同 schema 的 pages 数组，渲染层(slicer.py)一行不动。

复用 video-slicer 引擎的 LLM 客户端（Kimi/MiniMax provider 链、temp=0、json_mode、
think 块剥离、重试），套路同 planner.py。

【迁移说明（video-tools-migration 阶段2）】
  原住 assistant_zh/workflow/video_framework_slicer/，靠 sys.path 反向依赖本引擎。
  现迁入 video_slicer 包，改正常包内相对导入（D1：内容决策归 slicer 家族）。
  张和分页 prompt 抽到定制层 profiles/<profile>/pages_system_prompt.txt（默认 zh_main），
  引擎代码不再内嵌账号 prompt（多租户，见迁移计划 §3.2）。

用法：
  python -m video_slicer.pages_gen <clip.srt> [--duration SEC] [--hint "核心"] [--profile zh_main] [--out pages.json]
  # 不带 --out 时把 pages JSON 打到 stdout
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

from .llm import OpenAICompatibleClient
from .cli import load_env_file, _discover_env_file

VALID_BLOCKS = {"hero", "arrow", "mid", "key", "sub", "gap"}

# 翻页硬地板：每页原速最小停留秒数。成片后 compose 还会按语速整体最高 2x 加速，
# 14s 原速 ≈ 7-8s 最终停留——对应「大幅放慢·页少content厚」档（见 pages_system_prompt.txt
# 核心原则：内容块驱动翻页）。两页 start 间隔不够，就把后页内容并进前页，而不是硬翻。
MIN_DWELL_SEC = 14

_ENGINE_ROOT = Path(__file__).resolve().parent.parent  # engines/video-slicer


def _load_system_prompt(profile: str = "zh_main") -> str:
    """从定制层读分页 system prompt（账号特定，迁移计划 §3.2 定制层①）。"""
    p = _ENGINE_ROOT / "profiles" / profile / "pages_system_prompt.txt"
    if not p.exists():
        raise FileNotFoundError(f"pages_gen: 缺定制层 prompt {p}（profile={profile}）")
    return p.read_text(encoding="utf-8")


def cues_from_srt(srt_path: str | Path) -> tuple[list[tuple[float, str]], float]:
    """从 SRT 取中文 cue（clip 相对秒 + 文本）。双语 SRT 只取含中文的行。返回 (cues, 末尾秒)。"""
    def secs(ts: str) -> float:
        ts = ts.strip().replace(".", ",")
        h, m, rest = ts.split(":")
        s, ms = (rest.split(",") + ["0"])[:2]
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    cues: list[tuple[float, str]] = []
    last = 0.0
    blocks = Path(srt_path).read_text(encoding="utf-8").strip().split("\n\n")
    for b in blocks:
        lines = [x for x in b.split("\n") if x.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        t0, t1 = (secs(x) for x in lines[1].split("-->"))
        last = max(last, t1)
        zh = [x for x in lines[2:] if re.search(r"[一-鿿]", x)]
        text = (zh[0] if zh else lines[2]).strip()
        if text:
            cues.append((t0, text))
    return cues, last


def _mmss(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"


def _merge_pages(prev: dict, cur: dict) -> None:
    """把 cur 页内容并进 prev 页（论点驱动翻页的兜底：停留不够久就不另开页）。
    次论点的 hero 降级为 key（每页只留 1 个 hero）、丢掉重复的向下箭头，前面垫个大间距。"""
    prev["blocks"].append({"type": "gap", "size": "l"})
    for b in cur["blocks"]:
        if b["type"] == "arrow":
            continue
        if b["type"] == "hero":
            prev["blocks"].append({"type": "key", "text": b.get("text", "")})
        else:
            prev["blocks"].append(b)


def _sanitize(pages: list, duration: float, min_dwell: float = MIN_DWELL_SEC) -> list:
    """收口 LLM 输出：丢非法 block、保证 start 单调且落区间内、首页归零，
    并按 min_dwell 合并停留过短的页（翻页太快的硬地板，见 MIN_DWELL_SEC）。"""
    out = []
    for p in pages:
        if not isinstance(p, dict):
            continue
        blocks = []
        for b in p.get("blocks", []):
            if not isinstance(b, dict) or b.get("type") not in VALID_BLOCKS:
                continue
            t = b["type"]
            if t == "hero":
                blocks.append({"type": "hero", "text": str(b.get("text", "")).strip(),
                               "uw": int(b.get("uw", 330))})
            elif t == "arrow":
                blocks.append({"type": "arrow"})
            elif t in ("mid", "key", "sub"):
                blocks.append({"type": t, "text": str(b.get("text", "")).strip()})
            elif t == "gap":
                blocks.append({"type": "gap", "size": b.get("size", "l") if b.get("size") in ("l", "m") else "l"})
        blocks = [b for b in blocks if b["type"] in ("arrow", "gap") or b.get("text")]
        if not blocks:
            continue
        try:
            start = max(0, int(p.get("start", 0)))
        except (TypeError, ValueError):
            start = 0
        out.append({"start": min(start, max(0, int(duration) - 1)),
                    "title": str(p.get("title", "")).strip() or "要点", "blocks": blocks})
    if not out:
        raise ValueError("pages_gen: 模型没产出可用的 pages。")
    out.sort(key=lambda p: p["start"])
    out[0]["start"] = 0
    # 论点驱动翻页：相邻两页 start 间隔 < min_dwell 就把后页并进前页（不硬翻）。
    merged: list = [out[0]]
    for p in out[1:]:
        if p["start"] - merged[-1]["start"] < min_dwell:
            _merge_pages(merged[-1], p)
        else:
            merged.append(p)
    # 末页停留（到片尾）也得够久，否则并回上一页。
    while len(merged) > 1 and float(duration) - merged[-1]["start"] < min_dwell:
        _merge_pages(merged[-2], merged.pop())
    return merged


def generate_pages(srt_path: str | Path, duration: float | None = None,
                   hint: str | None = None, providers=("kimi", "minimax"),
                   profile: str = "zh_main", min_dwell: float = MIN_DWELL_SEC) -> list:
    load_env_file(_discover_env_file())  # 复用引擎的 .env 加载（同一份共享 .env）
    cues, last = cues_from_srt(srt_path)
    dur = duration or last
    transcript = "\n".join(f"[{_mmss(t)}] {txt}" for t, txt in cues)
    payload = {"duration_sec": round(dur), "hint": hint or "", "transcript": transcript}
    client = OpenAICompatibleClient(providers=list(providers))
    data = client.chat_json(
        [{"role": "system", "content": _load_system_prompt(profile)},
         {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        temperature=0.0,
    )
    return _sanitize(data.get("pages") or [], dur, min_dwell)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--hint", default=None)
    ap.add_argument("--profile", default="zh_main")
    ap.add_argument("--min-dwell", type=float, default=MIN_DWELL_SEC,
                    help=f"每页原速最小停留秒数（默认 {MIN_DWELL_SEC}，越大翻页越慢/页越少）")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    pages = generate_pages(a.srt, a.duration, a.hint, profile=a.profile, min_dwell=a.min_dwell)
    blob = json.dumps({"pages": pages}, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(blob + "\n", encoding="utf-8")
        print(f"写出 {len(pages)} 页 → {a.out}")
    else:
        print(blob)


if __name__ == "__main__":
    main()
