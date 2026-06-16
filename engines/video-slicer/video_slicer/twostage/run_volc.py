"""字级剪辑线 · 端到端（火山转录文件 → 自动选片 → 逐条去口水 → 切片文案）。止于文案，不渲染。

链路：火山字级词表 + 句级分句 --(adapt_volc)--> Sentence 表
     --(twostage stage1 选题 + stage2 定脚本)--> 每条切片(选题+keep_sids+原始脚本)
     --(script_clean 去口水)--> 每条切片的干净文案。

用法：
  python -m video_slicer.twostage.run_volc \\
      --words   剪口播/1_转录/subtitles_words.json \\
      --sentences 剪口播/2_分析/sentences.txt \\
      --persona zh_main --md cand.md --out cand.json \\
      [--limit N] [--providers kimi,minimax] [--host 张和]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..cli import _discover_env_file, load_env_file
from .. import script_clean
from . import adapt_volc, pipeline


def _clean_clips(result: dict, providers: list[str] | None) -> dict:
    """对每条切片的原始脚本跑去口水，挂上 script_clean / removed / protected。"""
    for i, c in enumerate(result["clips"], 1):
        title = c.get("title", "")
        print(f"[去口水] ({i}/{len(result['clips'])}) {title[:24]}…", file=sys.stderr)
        hint = f"{title}｜{c.get('one_argument', '')}"
        try:
            cleaned = script_clean.clean_script(c.get("script", ""), hint=hint, providers=providers)
        except Exception as ex:  # noqa: BLE001  一条失败不拖累整批
            print(f"         ↳ 去口水失败：{str(ex)[:120]}", file=sys.stderr)
            cleaned = {"script": c.get("script", ""), "removed": [], "protected": []}
        c["script_clean"] = cleaned.get("script", "")
        c["removed"] = cleaned.get("removed", [])
        c["protected"] = cleaned.get("protected", [])
    return result


def to_markdown(result: dict) -> str:
    out = [f"# 字级线选片+去口水文案（{len(result['clips'])} 条）· persona={result['persona']}", ""]
    for i, c in enumerate(result["clips"], 1):
        out.append(f"## {i}. {c.get('title','')}")
        out.append(f"- 论点：{c.get('one_argument','')}")
        out.append(f"- 钩子原话：{c.get('hook_line','')}")
        out.append(f"- 受众：{c.get('audience','')} ｜ 流量：{c.get('mainstream','')} ｜ 估时：{c.get('est_duration','')}s")
        out.append(f"- 句号：{c.get('keep_sids','')} ｜ 时间段：{c.get('sentence_time_spans','')}")
        out.append(f"- 去口水：删 {len(c.get('removed',[]))} 处 ｜ 护承接句 {len(c.get('protected',[]))} 句")
        out.append("- **切片文案（去口水后）**：")
        for line in (c.get("script_clean") or "").split("\n"):
            if line.strip():
                out.append(f"  > {line}")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(prog="run_volc", description="字级线端到端：火山转录 → 选片 → 去口水文案")
    ap.add_argument("--words", required=True, help="火山字级词表 subtitles_words.json")
    ap.add_argument("--sentences", required=True, help="句级分句 sentences.txt")
    ap.add_argument("--persona", default="zh_main")
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 条选题（省钱调试）")
    ap.add_argument("--out", default=None, help="输出 JSON")
    ap.add_argument("--md", default=None, help="可读 markdown")
    a = ap.parse_args()

    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    sentences = adapt_volc.load_volc_sentences(a.words, a.sentences, host=a.host)
    print(f"[adapt] 火山转录 → {len(sentences)} 句（单说话人={a.host}）", file=sys.stderr)

    result = pipeline.run_from_sentences(sentences, persona=a.persona, host=a.host,
                                         providers=providers, limit=a.limit, source=str(a.words))
    result = _clean_clips(result, providers)

    blob = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(blob + "\n", encoding="utf-8")
        print(f"写出 {len(result['clips'])} 条 → {a.out}", file=sys.stderr)
    if a.md:
        Path(a.md).write_text(to_markdown(result) + "\n", encoding="utf-8")
        print(f"可读文案 → {a.md}", file=sys.stderr)
    if not a.out and not a.md:
        print(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
