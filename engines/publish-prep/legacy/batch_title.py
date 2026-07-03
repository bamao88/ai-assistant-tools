#!/usr/bin/env python3
"""批量给 13 条切片生成标题（step2）+ 关键词（step3），全部写 tmp/。

标题：读 {c}_kimi.json 的已定稿正文 → gen_title（Kimi + MiniMax 对比）。
关键词：build_keywords 确定性构造（不调模型）。
⚠️ 只写 tmp/slice_copy_test/，不碰 publish_copy.md。
"""
import sys
import json
from pathlib import Path

ROOT = Path("/Volumes/ExtSSD2601/AI_Assistant/assistant_zh")
SLICER = ROOT / "workflow" / "video_framework_slicer"
sys.path.insert(0, str(SLICER))
import gen_title as gt  # noqa: E402
from build_keywords import build_keywords  # noqa: E402

TMP = ROOT / "tmp" / "slice_copy_test"
ORDER = ["c07", "c18", "c02", "c22", "c08", "c05", "c04", "c19", "c03", "c12", "c14", "c10", "c20"]
PROVIDERS = ["kimi", "minimax"]


def main():
    total = len(ORDER) * len(PROVIDERS)
    n = 0
    for c in ORDER:
        src = TMP / f"{c}_kimi.json"
        if not src.exists():
            print(f"!! {c}: 缺 {src.name}", flush=True)
            continue
        d = json.loads(src.read_text(encoding="utf-8"))
        body = d.get("正文", "")
        spine = d.get("spine", "")
        title = d.get("_title", "")

        # step3 关键词（确定性，一次即可）
        kws = build_keywords(body + " " + spine + " " + title)
        (TMP / f"{c}_keywords.json").write_text(
            json.dumps({"_clip": c, "keywords": kws}, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # step2 标题（两个 provider 对比）
        for prov in PROVIDERS:
            n += 1
            print(f"[{n}/{total}] title {c} via {prov} ...", flush=True)
            try:
                out = gt.gen_title(body, spine, title, prov)
            except Exception as e:
                out = {"_error": str(e)[:300]}
            out["_clip"] = c
            out["_provider"] = prov
            ok = "采用" in out
            (TMP / f"{c}_title_{prov}.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"    -> {c}_title_{prov}.json  {'OK: ' + out['采用'].get('标题','') if ok else out.get('_error','PARSE_FAIL')}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
