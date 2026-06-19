#!/usr/bin/env python3
"""subtitle_align —— ④ 字幕搬时间：照③剪辑账本重放，把逐字账本里每个选中字搬到成片时间。★承重墙④。

六环阶段化升级 WS-2 §三/§四。字幕的【时间】不是另算的，是③那把剪刀剪出来的结果：
读 cut manifest(剪辑账本) 的有序 ops，把每个源字时间依次套用 rough_cut→trim_silence→speed →成片时间。
本原子只搬【时间】+ 分句成行；【文字】订正(LLM subtitle_ai_fix / 术语表 / 别动清单)是 WS-4 的事。

剪刀(③)管对齐、AI(④)只换字——所以字幕同步从根上不会被搞乱。

依赖单向：本引擎不 import video-clip，账本是引擎间唯一接口(纯 JSON)，remap_time 在此独立实现(schema 同源)。

用法:
  subtitle_align.py --manifest m.json --words words.json --out clip.srt [--fixes fixes.json] [--cy 1725]
输出：成片时间轴 SRT（⑤ subtitles 渲药丸 + subtitle_burn 烧）。
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

PUNCT = "，。？！、；："
FILLERS = ["你知道吧", "是不是", "对不对", "我跟你说", "你放心", "那么", "就是说",
           "他妈的", "妈的", "卧槽", "啊", "嗯", "呃", "唉", "哈", "呀", "哦", "嘛", "呢", "吧", "哎"]
KEEP_OPS = ("rough_cut", "trim_silence", "script_clean")


# ── 剪辑账本重放（与 video-clip/atoms/_manifest.py 同算法·schema 是接口） ──
def _through_keeps(t, keeps):
    off = 0.0
    for s, e in keeps:
        if s <= t < e:
            return off + (t - s)
        off += (e - s)
    return None


def remap_time(ops, t, is_end=False):
    for op in ops:
        if op["op"] in KEEP_OPS or "keeps" in op:
            nt = _through_keeps(t, op["keeps"])
            if nt is None and is_end:
                nt = _through_keeps(t - 0.03, op["keeps"])
            if nt is None:
                return None
            t = nt
        elif op["op"] == "speed":
            t = t / op["factor"]
    return t


def rough_cut_keeps(ops):
    """源时间轴上的选段(给 derive_sent_indices 用)。"""
    for op in ops:
        if op["op"] == "rough_cut":
            return op["keeps"]
    # 无显式 rough_cut：用第一个 keep op
    for op in ops:
        if "keeps" in op:
            return op["keeps"]
    return []


# ── 分句·字级定位（沉淀自 0618test/build_subs.py，证明可用） ──
def degas(text):
    for f in FILLERS:
        text = text.replace(f, "")
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    text = re.sub(r"(.{2,3}?)\1{1,}", r"\1", text)
    return text.strip("，。？！、；： ")


def derive_sent_indices(sents, keeps):
    """源句与任一选段有重叠即纳入(开篇句内裁切也能纳入；越界分句再由 remap 返回 None 丢弃)。"""
    idxs = []
    for (s, e) in keeps:
        for i, sent in enumerate(sents):
            b = sent["begin_time"] / 1000.0
            en = sent["end_time"] / 1000.0
            if b < e and en > s and i not in idxs:
                idxs.append(i)
    return idxs


def sent_phrases(sent, words):
    """把一句按标点切成短语，每短语取字级 begin/end 真值(源秒)。"""
    b, e = sent["begin_time"], sent["end_time"]
    ws = [w for w in words if b <= w["begin_time"] < e]
    chars = []
    for w in ws:
        t = w["text"]; wb, we = w["begin_time"] / 1000.0, w["end_time"] / 1000.0
        for j, ch in enumerate(t):
            chars.append((ch, wb + (we - wb) * j / len(t), wb + (we - wb) * (j + 1) / len(t)))
    out, cur, p = [], [], 0
    for ch in sent["text"]:
        if ch in PUNCT:
            if cur:
                out.append((cur[0][1], cur[-1][2], "".join(c[0] for c in cur))); cur = []
        elif ch.isspace():
            continue
        else:
            if p < len(chars):
                cur.append((chars[p][0], chars[p][1], chars[p][2])); p += 1
    if cur:
        out.append((cur[0][1], cur[-1][2], "".join(c[0] for c in cur)))
    return out


def cleanup(cues):
    """删单字残渣 / 被邻条包含的口水重复 / <0.8s 碎片并下一条；绝不跨句合并。"""
    cues = [c for c in cues if len(c[2]) >= 2]
    res = []
    for i, c in enumerate(cues):
        nxt = cues[i + 1] if i + 1 < len(cues) else None
        prv = res[-1] if res else None
        if prv and prv[3] == c[3] and c[2] in prv[2]:
            prv[1] = c[1]; continue
        if nxt and nxt[3] == c[3] and c[2] in nxt[2]:
            nxt[0] = min(nxt[0], c[0]); continue
        res.append(c)
    merged, i = [], 0
    while i < len(res):
        c = res[i]
        if (c[1] - c[0]) < 0.8 and i + 1 < len(res) and res[i + 1][3] == c[3]:
            res[i + 1] = [c[0], res[i + 1][1], c[2] + res[i + 1][2], c[3]]; i += 1; continue
        merged.append(c); i += 1
    return merged


def _srt_t(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def build(manifest, words_data, fixes=None):
    ops = manifest["ops"]
    sents, words = words_data["sentences"], words_data["words"]
    keeps = rough_cut_keeps(ops)
    fixes = fixes or {}

    cues = []
    for idx in derive_sent_indices(sents, keeps):
        for (pb, pe, ptext) in sent_phrases(sents[idx], words):
            txt = degas(ptext)
            for k in sorted(fixes, key=len, reverse=True):
                txt = txt.replace(k, fixes[k])
            if not txt:
                continue
            bb = remap_time(ops, pb)
            be = remap_time(ops, pe, is_end=True)
            if bb is None:
                continue
            if be is None or be <= bb:
                be = bb + 0.4
            cues.append([bb, be, txt, idx])
    cues.sort(key=lambda x: x[0])
    cues = cleanup(cues)
    # 无缝：每条结尾延到下一条开头（不留空档；修「句末=切点」被判 None 提前消失）
    for i in range(len(cues) - 1):
        cues[i][1] = cues[i + 1][0]
    if cues:
        cues[-1][1] = cues[-1][1] + 0.5
    return cues


def write_srt(cues, out):
    lines = []
    for i, (b, e, text, _) in enumerate(cues, 1):
        lines.append(str(i)); lines.append(f"{_srt_t(b)} --> {_srt_t(e)}"); lines.append(text); lines.append("")
    Path(out).write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--words", required=True, help="火山字级 words.json（sentences+words，ms）")
    ap.add_argument("--out", required=True, help="成片时间轴 SRT")
    ap.add_argument("--fixes", default=None, help="术语表 fixes.json（可选·WS-4 接 LLM 前的静态打底）")
    a = ap.parse_args()

    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    words_data = json.loads(Path(a.words).read_text(encoding="utf-8"))
    fixes = json.loads(Path(a.fixes).read_text(encoding="utf-8")) if a.fixes and Path(a.fixes).exists() else {}
    cues = build(manifest, words_data, fixes)
    write_srt(cues, a.out)
    final_dur = manifest.get("durations", {}).get("final")
    print(f"DONE subtitle_align  {a.out}  {len(cues)}条分句  成片时长~{final_dur}s")
    for b, e, text, _ in cues:
        print(f"  {b:6.2f}-{e:6.2f} ({e - b:4.1f}s)  {text}")


if __name__ == "__main__":
    main()
