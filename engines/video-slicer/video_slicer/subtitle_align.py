#!/usr/bin/env python3
"""subtitle_align —— ④ 字幕搬时间：把逐字账本里每个选中字搬到「拼好身子(assembled)」时间。★承重墙④。

六环阶段化升级 + WS-6 伴随轨重构。字幕从此走「伴随轨(.srt 便签)」：本原子只做 **源 → assembled
一次简单换算**（只套③粗剪 rough_cut 的选段映射），不再事后多级回算到成片时间。
往后的「动时间轴」操作（③c 去长静音、③d 变速、⑥拼钩子）由各自原子用**同一把刀**把这张字幕便签
一起裁/缩/偏移（trim_silence/speed_adapt/prepend_hook 的 --srt-in/--srt-out），像素只在最后一步烧一次。

这样字幕时间永远 == 画音被同一把剪刀剪过后的时间，从不另算 → bug① 字幕显示已删内容/卡屏 从根上消失。
本原子只搬【时间】+ 分句成行；【文字】订正(LLM subtitle_ai_fix / 术语表 / 别动清单)是 WS-4 的事。

依赖单向：本引擎不 import video-clip，账本是引擎间唯一接口(纯 JSON)。

用法:
  subtitle_align.py --manifest m.json --words words.json --out clip.srt [--fixes fixes.json]
输出：assembled(拼好身子) 时间轴 SRT（随后由 ③c/③d/⑥ 各原子按同一把刀同步裁缩，末步烧字）。
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

PUNCT = "，。？！、；："
FILLERS = ["你知道吧", "是不是", "对不对", "我跟你说", "你放心", "那么", "就是说",
           "他妈的", "妈的", "卧槽", "啊", "嗯", "呃", "唉", "哈", "呀", "哦", "嘛", "呢", "吧", "哎"]
MAX_FILL = 1.0   # 衔接补洞封顶：只补「小空档」，长停顿留给 ③c 去静音连字幕一起裁，绝不硬撑卡屏
GAP_SPLIT = 1.0  # 短语内字与字时间间隔超此值即断句：避免一条字幕横跨长停顿/未转写区（旧版卡屏 + 字幕字音脱节的根因）


# ── 源 → assembled 的单次换算（与 video-clip/atoms/_manifest.py 同算法·schema 是接口） ──
def _through_keeps(t, keeps):
    """分段线性映射：t 落在某保留区间[s,e)→偏移到累计保留时长；落在被删处→None。"""
    off = 0.0
    for s, e in keeps:
        if s <= t < e:
            return off + (t - s)
        off += (e - s)
    return None


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
    """源逐字账本 → assembled(拼好身子) 时间轴的分句 SRT cue。只套③粗剪 rough_cut 一次映射。"""
    ops = manifest["ops"]
    sents, words = words_data["sentences"], words_data["words"]
    keeps = rough_cut_keeps(ops)          # 源时间轴上的选段（assembled 由它们顺序拼成）
    fixes = fixes or {}

    cues = []
    for idx in derive_sent_indices(sents, keeps):
        for (pb, pe, ptext) in sent_phrases(sents[idx], words):
            txt = degas(ptext)
            for k in sorted(fixes, key=len, reverse=True):
                txt = txt.replace(k, fixes[k])
            if not txt:
                continue
            bb = _through_keeps(pb, keeps)             # 源 → assembled，一次换算
            be = _through_keeps(pe, keeps)
            if be is None:                             # 句末正好落选段右边界(切点)：回退微小量夹回段内
                be = _through_keeps(pe - 0.03, keeps)
            if bb is None:                             # 该短语整体落在③未选区 → 本就不该出现，丢
                continue
            if be is None or be <= bb:
                be = bb + 0.4
            cues.append([bb, be, txt, idx])
    cues.sort(key=lambda x: x[0])
    cues = cleanup(cues)
    # 衔接补洞：只把「小空档(≤MAX_FILL)」补到下一条开头，避免相邻条之间闪烁；
    # 长停顿不在这里硬撑（那正是旧版卡屏14s的根因）——留给 ③c 去静音按同一把刀把字幕一起裁掉。
    for i in range(len(cues) - 1):
        gap = cues[i + 1][0] - cues[i][1]
        if 0 < gap <= MAX_FILL:
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
    asm_dur = manifest.get("durations", {}).get("assembled")
    print(f"DONE subtitle_align  {a.out}  {len(cues)}条分句  assembled时长~{asm_dur}s（随后随③c/③d/⑥同刀裁缩）")
    for b, e, text, _ in cues:
        print(f"  {b:6.2f}-{e:6.2f} ({e - b:4.1f}s)  {text}")


if __name__ == "__main__":
    main()
