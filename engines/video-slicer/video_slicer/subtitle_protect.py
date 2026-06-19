#!/usr/bin/env python3
"""subtitle_protect —— ④ 别动清单钉回 + 结构自检。subtitle_ai_fix(LLM) 之后的最后一道。

LLM 再聪明也会把自造叫法改"对"（如把口播里故意说的「爱马仕」当口误改成别的）。本原子拿
LLM 前(pre=subtitle_align 输出)和 LLM 后(post=subtitle_ai_fix 输出)逐条比对，按【别动清单】把被
改掉的受保护词强制钉回；同时做结构自检：1:1 条数核对、无空格吞字(post 不该把字吞没)。

依赖单向：本引擎自给自足，不 import 别的引擎。
用法:
  subtitle_protect.py --pre 对齐.srt --post AI订正.srt --keeplist keeplist.json --out 定稿.srt
  keeplist.json = ["爱马仕", "某自造词", ...]
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path


def parse_srt(p):
    out = []
    for b in Path(p).read_text(encoding="utf-8").strip().split("\n\n"):
        L = [x for x in b.split("\n") if x.strip()]
        if len(L) < 3 or "-->" not in L[1]:
            continue
        t0, t1 = (x.strip() for x in L[1].split("-->"))
        out.append({"t0": t0, "t1": t1, "text": " ".join(L[2:]).strip()})
    return out


def _nonspace(s):
    return re.sub(r"\s", "", s)


def protect(pre, post, keeplist, swallow_ratio=0.6):
    """返回 (final_texts, report)。逐条钉回受保护词 + 结构自检。"""
    n = len(pre)
    report = {"count_pre": n, "count_post": len(post), "count_match": n == len(post),
              "restored": [], "swallow_warn": []}
    if n != len(post):
        return None, report                          # 1:1 破了，拒绝出稿
    final = []
    for i in range(n):
        pt, qt = pre[i]["text"], post[i]["text"]
        use = qt
        for term in keeplist:
            if term in pt and term not in qt:        # 受保护词被 LLM 改没了 → 整条钉回
                use = pt
                report["restored"].append({"i": i, "term": term, "llm": qt, "restored": pt})
                break
        # 无空格吞字：post 非空格字数比 pre 掉太多(超过 swallow_ratio)→ 疑似吞字，警告(不自动改)
        np_, nq = len(_nonspace(pt)), len(_nonspace(use))
        if np_ >= 4 and nq < np_ * swallow_ratio:
            report["swallow_warn"].append({"i": i, "pre": pt, "post": use, "pre_chars": np_, "post_chars": nq})
        final.append({"t0": post[i]["t0"], "t1": post[i]["t1"], "text": use})
    return final, report


def write_srt(cues, out):
    lines = []
    for i, c in enumerate(cues, 1):
        lines += [str(i), f"{c['t0']} --> {c['t1']}", c["text"], ""]
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pre", required=True, help="LLM 前(subtitle_align 输出)")
    ap.add_argument("--post", required=True, help="LLM 后(subtitle_ai_fix 输出)")
    ap.add_argument("--keeplist", default=None, help='别动清单 JSON 数组["爱马仕",...]')
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    pre = parse_srt(a.pre); post = parse_srt(a.post)
    keeplist = json.loads(Path(a.keeplist).read_text(encoding="utf-8")) if a.keeplist and Path(a.keeplist).exists() else []
    final, rep = protect(pre, post, keeplist)

    print(f"== ④ 别动清单钉回 + 结构自检 ==")
    print(f"  1:1 条数 pre={rep['count_pre']} post={rep['count_post']} → {'PASS' if rep['count_match'] else 'FAIL'}")
    if final is None:
        raise SystemExit("1:1 条数不符，拒绝出稿（subtitle_ai_fix 应保证等长）")
    print(f"  别动清单钉回 {len(rep['restored'])} 条" + (f"：{[r['term'] for r in rep['restored']]}" if rep['restored'] else ""))
    for r in rep["restored"]:
        print(f"    #{r['i']} 「{r['llm']}」→ 钉回「{r['restored']}」(保护词 {r['term']})")
    print(f"  无空格吞字 → {'PASS' if not rep['swallow_warn'] else f'{len(rep[chr(39)+chr(115)+chr(119)])} 条疑似吞字'}" if False else
          f"  无空格吞字 → {'PASS' if not rep['swallow_warn'] else str(len(rep['swallow_warn']))+' 条疑似吞字(警告)'}")
    for w in rep["swallow_warn"]:
        print(f"    #{w['i']} {w['pre_chars']}字→{w['post_chars']}字  「{w['pre']}」→「{w['post']}」")
    write_srt(final, a.out)
    print(f"DONE subtitle_protect  {a.out}  {len(final)}条")


if __name__ == "__main__":
    main()
