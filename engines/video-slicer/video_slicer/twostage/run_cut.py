"""字级线 · 端到端切片（源视频 + 火山转录 → 自动选片 → 字级去口水 → 切出干净片段）。

链路：转录字级词表 --(segment 自动分句)--> 句表
     --(twostage stage1 精选 + stage2 定边界)--> 每条切片(keep_sids)
     --(script_clean.clean_to_keep 字级去口水)--> 每条切片的 keep 时间区间(秒)
     --(resolve 边界吸字间静音, 可选)--> --(cut_video 从源视频切)--> clip_N.mp4 + 相对SRT + 文案

用法：
  python -m video_slicer.twostage.run_cut \\
      --video 源视频.mp4 --words subtitles_words.json \\
      --out var/zh_main/cuts/<名> --persona zh_main \\
      [--limit N] [--crop crop=1080:800:0:1120] [--providers kimi,minimax]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..cli import _discover_env_file, load_env_file
from .. import script_clean
from ..transcribe import segment
from . import cut_video, pipeline, resolve


def _slug(s: str, n: int = 20) -> str:
    keep = "".join(c for c in (s or "") if c.isalnum() or c in "（）()·-_ ")[:n].strip()
    return keep.replace(" ", "_") or "clip"


def run_cut(video, words_json, out_dir, persona="zh_main", host="张和",
            providers=None, limit=None, crop=None, snap=True) -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    words, sents = segment.sentences_from_wordfile(words_json, host=host)
    print(f"[adapt] 转录 → {len(words)} 字 / {len(sents)} 句", file=sys.stderr)
    word_list = [{"text": w["text"], "begin_time": int(w["start"] * 1000), "end_time": int(w["end"] * 1000)}
                 for w in words]  # resolve.load 用 ms schema

    result = pipeline.run_from_sentences(sents, persona=persona, host=host,
                                         providers=providers, limit=limit, source=str(words_json))
    clips_out = []
    for i, clip in enumerate(result["clips"], 1):
        title = clip.get("title", f"clip{i}")
        print(f"[切片] ({i}/{len(result['clips'])}) {title[:24]}…", file=sys.stderr)
        # 1) 选段的字（按 keep_sids 收集 host 句的字）
        seg_words = []
        for a, b in clip.get("keep_sids", []):
            for sid in range(a, b + 1):
                if 0 <= sid < len(sents) and sents[sid].wi >= 0:
                    seg_words += words[sents[sid].wi: sents[sid].wj + 1]
        if not seg_words:
            continue
        # 2) 字级去口水 → keep 区间
        ck = script_clean.clean_to_keep(seg_words, hint=f"{title}｜{clip.get('one_argument','')}",
                                        providers=providers)
        spans = ck["keep_spans"]
        # 3) 边界吸字间静音（更自然）
        if snap and spans:
            snapped = resolve.snap_segments(spans, resolve.load_paraformer_words.__wrapped__ if False else word_list_to_words(word_list), mode="silence_mid")
            spans = [s["snapped"] for s in snapped]
        # 4) 切视频 + 相对字幕 + 文案
        base = out / f"clip_{i:02d}_{_slug(title)}"
        try:
            cut_video.cut_clip(video, spans, base.with_suffix(".mp4"), crop=crop)
            cut_video.relative_srt(ck["kept_words"], spans, base.with_suffix(".srt"))
        except Exception as ex:  # noqa: BLE001
            print(f"        ✗ 切片失败：{str(ex)[:150]}", file=sys.stderr)
            continue
        dur = sum(e - s for s, e in spans)
        base.with_suffix(".txt").write_text(
            f"# {title}\n钩子：{clip.get('hook_line','')}\n时长：{dur:.1f}s ｜ 删 {len(ck['removed'])} 处口水\n\n{ck['kept_text']}\n",
            encoding="utf-8")
        clips_out.append({"title": title, "mp4": str(base.with_suffix(".mp4")),
                          "dur": round(dur, 1), "removed": len(ck["removed"]),
                          "keep_spans": spans})
    # 索引
    idx = [f"# 字级线切片索引（{len(clips_out)} 条）", ""]
    for c in clips_out:
        idx.append(f"- **{c['title']}**（{c['dur']}s, 删{c['removed']}处）  `{c['mp4']}`")
    (out / "index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print("\n".join(idx), file=sys.stderr)
    return {"clips": clips_out}


def word_list_to_words(word_list):
    """ms 词表 → resolve 认的秒词表 [{text,start,end}]。"""
    return [{"text": w["text"], "start": w["begin_time"] / 1000, "end": w["end_time"] / 1000} for w in word_list]


def main() -> int:
    ap = argparse.ArgumentParser(prog="run_cut", description="字级线端到端切片：源视频+转录 → 去口水切片")
    ap.add_argument("--video", required=True, help="源视频")
    ap.add_argument("--words", required=True, help="火山字级词表 subtitles_words.json")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--persona", default="zh_main")
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    ap.add_argument("--limit", type=int, default=None, help="只切前 N 条选题（省钱）")
    ap.add_argument("--crop", default=None, help="如 crop=1080:800:0:1120 裁下半摄像头")
    ap.add_argument("--no-snap", action="store_true", help="不做字间静音吸附")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    run_cut(a.video, a.words, a.out, persona=a.persona, host=a.host, providers=providers,
            limit=a.limit, crop=a.crop, snap=not a.no_snap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
