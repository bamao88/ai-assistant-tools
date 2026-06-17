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
from ..transcribe import align, segment
from . import cut_video, pipeline, resolve


def _slug(s: str, n: int = 20) -> str:
    keep = "".join(c for c in (s or "") if c.isalnum() or c in "（）()·-_ ")[:n].strip()
    return keep.replace(" ", "_") or "clip"


def dump_process_files(out: Path, words_json, words, sents, result) -> None:
    """把各阶段中间产物落成直观文件，便于人工逐阶段查看。"""
    d = out / "_过程文件"; d.mkdir(exist_ok=True)
    (d / "0_字级词表_说明.txt").write_text(
        f"阶段0 转写产物（本流程的输入）\n字级词表文件：{words_json}\n共 {len(words)} 个字（带毫秒级时间戳）\n", encoding="utf-8")
    # 1 分句
    (d / "1_分句.txt").write_text(
        "\n".join(f"{s.sid}|{s.start:.2f}-{s.end:.2f}|{s.text}" for s in sents) + "\n", encoding="utf-8")
    # 2 选题（可读）
    md = ["# 阶段2 选题（stage1 选出的所有选题）", ""]
    for i, c in enumerate(result["clips"], 1):
        md += [f"## {i:02d}. {c.get('title','')}",
               f"- 钩子原话：{c.get('hook_line','')}",
               f"- 论点：{c.get('one_argument','')}",
               f"- 受众：{c.get('audience','')} ｜ 流量潜力：{c.get('mainstream','')}",
               f"- 句号区间（在 1_分句.txt 里的句号）：{c.get('keep_sids','')}",
               f"- 句级时间段（秒）：{c.get('sentence_time_spans','')}", ""]
    (d / "2_选题.md").write_text("\n".join(md), encoding="utf-8")
    # 3 文字片段（去口水前）
    sd = d / "3_文字片段_去口水前"; sd.mkdir(exist_ok=True)
    for i, c in enumerate(result["clips"], 1):
        (sd / f"clip_{i:02d}_{_slug(c.get('title',''))}.txt").write_text(
            f"# {c.get('title','')}\n（阶段3 文字片段·去口水前·原始拼接）\n\n{c.get('script','')}\n", encoding="utf-8")


def run_cut(video, words_json, out_dir, persona="zh_main", host="张和",
            providers=None, limit=None, crop=None, snap=False, no_video=False) -> dict:
    """no_video=True：纯文字模式——只出文案/字幕(.txt/.srt)，跳过 ffmpeg 切视频（验证/无视频时用）。"""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    words, sents = segment.sentences_from_wordfile(words_json, host=host)
    print(f"[adapt] 转录 → {len(words)} 字 / {len(sents)} 句", file=sys.stderr)
    align_total = align_ok = 0                          # 原生句↔字级 对齐统计（P1 指标）
    align_fails: list[dict] = []

    sel_path = out / "_selection.json"                  # 选题缓存：复用则可断点续切（避免重跑 stage1/2、避免选题漂移）
    if sel_path.exists():
        result = json.loads(sel_path.read_text(encoding="utf-8"))
        print(f"[resume] 复用已存选题 {len(result['clips'])} 条", file=sys.stderr)
    else:
        result = pipeline.run_from_sentences(sents, persona=persona, host=host,
                                             providers=providers, limit=limit, source=str(words_json))
        sel_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    dump_process_files(out, words_json, words, sents, result)   # 各阶段中间产物落盘
    clips_out = []
    for i, clip in enumerate(result["clips"], 1):
        title = clip.get("title", f"clip{i}")
        base = out / f"clip_{i:02d}_{_slug(title)}"
        print(f"[切片] ({i}/{len(result['clips'])}) {title[:24]}…", file=sys.stderr)
        done_marker = base.with_suffix(".txt") if no_video else base.with_suffix(".mp4")
        if done_marker.exists():                       # 断点续跑：已产出的跳过
            print("        ↳ 已存在，跳过", file=sys.stderr)
            clips_out.append({"title": title, "mp4": str(base.with_suffix(".mp4")), "dur": None, "removed": None})
            continue
        try:                                            # 每条独立容错：一条失败(网络/去口水/切片)不拖累整批
            # 1) 选段的字 + 句（按 keep_sids 收集 host 句的字，并记下覆盖的句供建富 token）
            seg_words = []
            seg_sents = []
            for a, b in clip.get("keep_sids", []):
                for sid in range(a, b + 1):
                    if 0 <= sid < len(sents) and sents[sid].wi >= 0:
                        seg_words += words[sents[sid].wi: sents[sid].wj + 1]
                        seg_sents.append(sents[sid])
            if not seg_words:
                continue
            # 富 token（句级带标点 ITN + 时间）：任一句对不齐则降级回字级裸拼（不断流）
            rich = None
            if seg_sents:
                align_total += 1
                try:
                    rich = align.map_clip(seg_sents, words)
                    align_ok += 1
                except align.AlignError as ae:
                    msg = str(ae)[:120]
                    print(f"        ↳ 原生句对齐失败，降级字级裸拼：{msg}", file=sys.stderr)
                    align_fails.append({"clip": i, "title": title, "reason": msg})
            # 2) 去口水 → keep 区间（富 token 在则字幕/文案带标点 ITN）
            ck = script_clean.clean_to_keep(seg_words, hint=f"{title}｜{clip.get('one_argument','')}",
                                            providers=providers, rich_tokens=rich)
            spans = ck["keep_spans"]
            # 3) 边界吸字间静音（可选·轻微，默认关；去口水已是字精度）
            if snap and spans:
                spans = [s["snapped"] for s in resolve.snap_segments(spans, words, mode="silence_mid", gap_search=0.25)]
            # 4) 切视频(纯文字模式跳过) + 相对字幕 + 文案
            if not no_video:
                cut_video.cut_clip(video, spans, base.with_suffix(".mp4"), crop=crop)
            cut_video.relative_srt(ck["kept_words"], spans, base.with_suffix(".srt"))
            dur = sum(e - s for s, e in spans)
            base.with_suffix(".txt").write_text(
                f"# {title}\n钩子：{clip.get('hook_line','')}\n时长：{dur:.1f}s ｜ 删 {len(ck['removed'])} 处口水\n\n{ck['kept_text']}\n",
                encoding="utf-8")
            clips_out.append({"title": title, "mp4": str(base.with_suffix(".mp4")),
                              "dur": round(dur, 1), "removed": len(ck["removed"]), "keep_spans": spans})
        except Exception as ex:  # noqa: BLE001
            print(f"        ✗ 失败跳过：{str(ex)[:150]}", file=sys.stderr)
            continue
    # 索引
    idx = [f"# 字级线切片索引（{len(clips_out)} 条）", ""]
    for c in clips_out:
        idx.append(f"- **{c['title']}**（{c['dur']}s, 删{c['removed']}处）  `{c['mp4']}`")
    (out / "index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print("\n".join(idx), file=sys.stderr)
    return {"clips": clips_out}


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
    ap.add_argument("--snap", action="store_true", help="边界轻微吸字间静音（默认关；去口水已字精度）")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    run_cut(a.video, a.words, a.out, persona=a.persona, host=a.host, providers=providers,
            limit=a.limit, crop=a.crop, snap=a.snap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
