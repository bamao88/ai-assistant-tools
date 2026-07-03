#!/usr/bin/env python3
"""批量给 12 条切片生成正文（Kimi + MiniMax 各一版），全部写 tmp/ 测试目录。

复用 gen_copy.py 的 SYSTEM / USER_TMPL / srt_to_text / core。
⚠️ 只写 tmp/slice_copy_test/，绝不碰 out_v1/**/publish_copy.md。
"""
import sys
import os
import json
import glob
from pathlib import Path

ROOT = Path("/Volumes/ExtSSD2601/AI_Assistant/assistant_zh")
SLICER = ROOT / "workflow" / "video_framework_slicer"
sys.path.insert(0, str(SLICER))
import gen_copy  # noqa: E402  复用 SYSTEM/USER_TMPL/srt_to_text/core
core = gen_copy.core

OUT = ROOT / "tmp" / "slice_copy_test"
OUT.mkdir(parents=True, exist_ok=True)

# 发布序里 c07 之后的 12 条；标题取自 publish_queue.md
CLIPS = {
    "c18": "把项目当求职项目：理解不同代际架构、放弃 workflow 上 Agent SDK",
    "c02": "已经不需要看代码了：再大的代码库 AI 都能读懂",
    "c22": "求职包装别纠结：分清公司的问题和你的问题",
    "c08": "进步靠多上麦接受批评",
    "c05": "新同学开课前看什么：黑客级调研 + 从 0 到 1 做产品",
    "c04": "设计师转型靠的是趋势和气质",
    "c19": "做一句话生成 App 别急着做完：先假设已完美，倒推谁来用",
    "c03": "售前、项目经理都得会现场做 demo：别给自己设限",
    "c12": "AI 老忘事，就把规则写进 CLAUDE.md 最显要位置",
    "c14": "维护上下文：苗头不对别一直追问，直接改 prompt 或 rewind",
    "c10": "让 AI 操控浏览器做闭环自动验证",
    "c20": "研发早期给 agent 更大 token 预算、更长时间去 push to limit",
}
PROVIDERS = ["kimi", "minimax"]


def clip_dir(c: str) -> Path:
    hits = glob.glob(str(SLICER / "out_v1" / f"v1_{c}_*"))
    if not hits:
        raise FileNotFoundError(f"no dir for {c}")
    return Path(hits[0])


def main():
    total = len(CLIPS) * len(PROVIDERS)
    n = 0
    for c, title in CLIPS.items():
        d = clip_dir(c)
        srt = d / "clip.fixed.srt"
        if not srt.exists():
            srt = d / "clip.srt"
        transcript = gen_copy.srt_to_text(srt)
        user = gen_copy.USER_TMPL.format(transcript=transcript, title=title)
        for prov in PROVIDERS:
            n += 1
            os.environ["LLM_PROVIDER"] = prov
            outfile = OUT / f"{c}_{prov}.json"
            print(f"[{n}/{total}] {c} via {prov} ...", flush=True)
            try:
                raw = core.call_llm(gen_copy.SYSTEM, user, temperature=0.7, json_mode=True)
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"_raw": raw}
            except Exception as e:
                data = {"_error": str(e)[:300]}
            data["_clip"] = c
            data["_title"] = title
            data["_provider"] = prov
            data["_model"] = os.environ.get(f"{prov.upper()}_MODEL", "")
            outfile.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"    -> {outfile.name}  {'OK' if '正文' in data else data.get('_error', 'PARSE_FAIL')}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
