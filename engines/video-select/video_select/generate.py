#!/usr/bin/env python3
"""流程二 · 生成候选（Runner 第 2 段）—— 产出「成片脚本」。

对每条选题循环一次，内部 4 步（3 步各读 1 条 prompts/ 提示词，组装是纯代码）：
  ① 总编   body-edit.md   → 选段 segments（句级区间 + 逻辑顺序）  → 出口过 gates.merge_segments（精选合并）
  ② 组装   纯代码          → script_raw（各段原话按序粘成草稿）
  ③ 去口水决策 refine-deduct.md → deletions（删哪些字、带位置·可执行）
  ④ 钩子   hook.md         → hook_options（整句优先·拼接兜底）
  → 汇总落盘：golden_candidate.json（机读真源）+ candidates/clip_NN.md（人读评审稿）

提示词全在 prompts/，代码里无内嵌 prompt 字符串。逐字稿→句/时间核心 import 自 video-slicer。
设计真源：doc/plan/视频剪辑skill-第二环选片-plan.md §4。

用法:
  python -m video_select.generate --words words.json --selection _selection.json --out <dir> \\
      [--providers kimi,minimax] [--limit N] [--only 6-22]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import _deps  # noqa: F401  挂 video-slicer 到 sys.path
from ._deps import load_prompt
from . import gates

from video_slicer.transcribe import segment  # noqa: E402
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402

BODY_ROLES = {"argument", "evidence", "closing"}


def load_topics(selection_path: str | Path) -> list[dict]:
    data = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    return data.get("clips", [])


def render_full(sents) -> str:
    return "\n".join(f"#{s.sid} {s.text}" for s in sents)


def _chat_json_retry(client, msgs, temperature):
    try:
        return client.chat_json(msgs, temperature=temperature)
    except Exception:  # noqa: BLE001  长稿偶发 JSON 截断/超时，重试一次
        return client.chat_json(msgs, temperature=temperature)


# ───────────────────────── ① 总编 ─────────────────────────
def select_body(topic: dict, sents, full_view: str,
                providers=None, temperature: float = 0.3) -> tuple[list[dict], dict]:
    """全局取证 + 逻辑编排 → 正文 segments，出口过精选合并门禁。"""
    brief = (f"【已选定选题】\n标题：{topic.get('title','')}\n"
             f"核心论点(one_argument)：{topic.get('one_argument','')}\n"
             f"钩子原话参考(hook_line)：{topic.get('hook_line','')}\n"
             f"受众：{topic.get('audience','')} ｜ 流量潜力：{topic.get('mainstream','')}\n\n"
             f"【全场编号句】\n{full_view}")
    client = OpenAICompatibleClient(providers=providers)
    data = _chat_json_retry(client, [
        {"role": "system", "content": load_prompt("body-edit")},
        {"role": "user", "content": brief}], temperature)
    raw = [{"role": s.get("role", "evidence"), "sids": s.get("sids", []),
            "reason": s.get("reason", "")}
           for s in data.get("segments", []) if isinstance(s, dict) and s.get("sids")]
    body = gates.merge_segments(raw, sents)   # 精选合并：去重叠 + 合并相邻碎段
    return body, {"title_suggestion": str(data.get("title_suggestion", "")).strip()}


# ───────────────────────── ③ 去口水决策 ─────────────────────────
def deduct_disfluency(body: list[dict], sents, providers=None) -> tuple[list[dict], str]:
    """字级去口水决策：删哪些字（带位置·可执行）。返回 (deletions, preview)。"""
    if not body:
        return [], ""
    lines = []
    for s in body:
        for sid in range(s["sids"][0], s["sids"][1] + 1):
            lines.append(f"#{sid} {sents[sid].text}")
    user = "【正文逐句】\n" + "\n".join(lines)
    client = OpenAICompatibleClient(providers=providers)
    data = _chat_json_retry(client, [
        {"role": "system", "content": load_prompt("refine-deduct")},
        {"role": "user", "content": user}], 0.3)
    out = []
    max_sid = sents[-1].sid if sents else -1
    for d in data.get("deletions", []) or []:
        sid = d.get("sid")
        text = (d.get("text") or "").strip()
        if not isinstance(sid, int) or not (0 <= sid <= max_sid) or not text:
            continue
        src = sents[sid].text
        verbatim = text in src or text.replace(" ", "") in src.replace(" ", "")
        out.append({"sid": sid, "text": text, "kind": str(d.get("kind", ""))[:20],
                    "verbatim": verbatim})
    return out, str(data.get("preview", "")).strip()


# ───────────────────────── ④ 钩子 ─────────────────────────
def _parse_sid_range(sid) -> tuple[int, int] | None:
    if isinstance(sid, int):
        return sid, sid
    if isinstance(sid, str) and sid.strip():
        s = sid.strip()
        try:
            if "-" in s:
                a, b = s.split("-", 1)
                a, b = int(a), int(b)
                return (a, b) if a <= b else (b, a)
            return int(s), int(s)
        except ValueError:
            return None
    return None


def _hook_view(sents, body, extra_spans=None) -> str:
    """钩子候选池：正文覆盖句(±3) ∪ 选题原始选段区(±2)。"""
    n = len(sents)
    ids: set[int] = set()
    for s in body:
        a, b = s["sids"]
        ids.update(range(max(0, a - 3), min(n - 1, b + 3) + 1))
    for span in extra_spans or []:
        if isinstance(span, (list, tuple)) and len(span) >= 2:
            a, b = int(span[0]), int(span[-1])
            ids.update(range(max(0, a - 2), min(n - 1, b + 2) + 1))
    return "\n".join(f"#{i} {sents[i].text}" for i in sorted(ids))


def gen_hook_options(core: dict, body, sents, providers=None) -> list[dict]:
    """钩子候选：整句优先、拼接兜底。"""
    if not body:
        return []
    view = _hook_view(sents, body, extra_spans=core.get("orig_keep_sids"))
    user = (f"标题：{core['title']}\n论点：{core['one_argument']}\n"
            f"目标受众：{core.get('audience','')}\n\n【候选原话句】\n{view}")
    client = OpenAICompatibleClient(providers=providers)
    data = _chat_json_retry(client, [
        {"role": "system", "content": load_prompt("hook")},
        {"role": "user", "content": user}], 0.4)
    out = []
    for h in data.get("hooks", []) or []:
        frags = []
        for fr in h.get("fragments", []) or []:
            txt = (fr.get("text") or "").strip()
            rng = _parse_sid_range(fr.get("sid"))
            if not txt or rng is None:
                continue
            a, b = rng
            if not (0 <= a <= b < len(sents)):
                continue
            src = "".join(sents[i].text for i in range(a, b + 1))
            sid_disp = a if a == b else f"{a}-{b}"
            verbatim = txt in src or re.sub(r"\s", "", txt) in re.sub(r"\s", "", src)
            frags.append({"sid": sid_disp, "text": txt, "verbatim": verbatim})
        if not frags:
            continue
        stitched = (h.get("stitched") or "".join(f["text"] for f in frags)).strip()
        out.append({"stitched": stitched, "fragments": frags,
                    "strategy": str(h.get("strategy", ""))[:20], "why": str(h.get("why", ""))[:200]})
    return out


# ───────────────────────── 汇总 ─────────────────────────
def finalize_clip(core: dict, body: list[dict], sents, providers=None) -> dict:
    """正文 segments → 完整 clip：补 ④钩子 + ②组装 + ③去口水决策。"""
    keep_sids = [s["sids"] for s in body]
    time_spans = [s["span"] for s in body]
    est_dur = round(sum(e - s for s, e in time_spans), 1)
    script_raw = "\n".join(s["text"] for s in body)
    hook_options = gen_hook_options(core, body, sents, providers=providers)
    deletions, preview = deduct_disfluency(body, sents, providers=providers)
    clip = dict(core)
    clip.update({"hook_options": hook_options, "segments": body, "keep_sids": keep_sids,
                 "time_spans": time_spans, "est_dur": est_dur, "script_raw": script_raw,
                 "deletions": deletions, "script_preview": preview,
                 "human_status": core.get("human_status", "pending")})
    return clip


def _slug(s: str, n: int = 24) -> str:
    keep = "".join(c for c in (s or "") if c.isalnum() or c in "（）()·-_")[:n]
    return keep or "clip"


HUMAN_HEADER = "## 人工评审环（在此处改 · 留 keep / 删 cut / 改 edited）"


def write_review_md(out: Path, idx: int, clip: dict) -> None:
    d = out / "candidates"
    d.mkdir(parents=True, exist_ok=True)
    role_cn = {"argument": "核心论点", "evidence": "论据/举例", "closing": "收尾"}
    L = [f"# {idx:02d}. {clip['title']}", "",
         f"- **核心论点**：{clip['one_argument']}",
         f"- **受众/流量**：{clip.get('audience','')} ｜ {clip.get('mainstream','')}",
         f"- **正文估时**：{clip['est_dur']}s ｜ 正文段数：{len(clip['segments'])}"]
    if clip.get("title_suggestion"):
        L.append(f"- **AI 建议新标题**：{clip['title_suggestion']}")
    L.append(f"- **原钩子(参考)**：{clip.get('hook_line','')}")

    L += ["", "## ① 开场钩子（整句优先·拼接兜底·挑一个）", ""]
    if clip.get("hook_options"):
        for h in clip["hook_options"]:
            srcs = " + ".join(f"#{f['sid']}「{f['text']}」" + ("" if f["verbatim"] else "⚠")
                              for f in h["fragments"])
            L.append(f"- 拟稿：**{h['stitched']}**（{h.get('strategy','')}）")
            L.append(f"  - 片段：{srcs}")
            if h["why"]:
                L.append(f"  - 理由：{h['why']}")
    else:
        L.append("-（未生成）")

    L += ["", "## ② 正文 · 论证结构（句号可回查时间·不含钩子）", ""]
    for s in clip["segments"]:
        a, b = s["span"]
        L += [f"### [{role_cn.get(s['role'], s['role'])}] 句号 {s['sids'][0]}–{s['sids'][1]}（{a:.1f}–{b:.1f}s）",
              f"> {s['text']}", f"*取证理由：{s.get('reason','')}*", ""]

    L += ["## ③ 组装脚本（原始拼接·带口水·未删）", "", clip["script_raw"], ""]
    L += ["## ④ 字级去口水决策（删哪些字·带位置·可执行）", ""]
    if clip.get("deletions"):
        for dd in clip["deletions"]:
            flag = "" if dd.get("verbatim", True) else " ⚠非原话子串"
            L.append(f"- #{dd['sid']} 删「{dd['text']}」（{dd.get('kind','')}）{flag}")
        L += ["", "**删后预览（仅供核对，真源是上面的删除项）：**", clip.get("script_preview") or "（无）", ""]
    else:
        L += ["-（未生成）", ""]

    L += ["---", HUMAN_HEADER, "- 选定钩子：", "- 状态：**pending**", "- 备注："]
    (d / f"clip_{idx:02d}_{_slug(clip['title'])}.md").write_text("\n".join(L), encoding="utf-8")


def _parse_only(only: str | None) -> set[int] | None:
    if not only:
        return None
    only = only.strip()
    if "-" in only:
        a, b = only.split("-", 1)
        return set(range(int(a), int(b) + 1))
    return {int(only)}


def _write_golden(out: Path, by_idx: dict, words_json, selection_json, host, log):
    clips = [by_idx[i] for i in sorted(by_idx)]
    golden = {"source_words": str(words_json), "selection": str(selection_json),
              "host": host, "method": "video-select/generate", "human_status": "pending",
              "clips": clips}
    (out / "golden_candidate.json").write_text(
        json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "_run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    return golden


def run(words_json, selection_json, out_dir, host="张和", providers=None,
        limit=None, only=None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _, sents = segment.sentences_from_wordfile(words_json, host=host)
    topics = load_topics(selection_json)
    if limit:
        topics = topics[:limit]
    want = _parse_only(only)
    full_view = render_full(sents)
    todo = [i for i in range(1, len(topics) + 1) if want is None or i in want]
    print(f"[generate] {len(sents)}句 / 处理{len(todo)}条(共{len(topics)}) / 语料{len(full_view)}字",
          file=sys.stderr)

    gpath = out / "golden_candidate.json"
    by_idx: dict[int, dict] = {}
    if want is not None and gpath.exists():
        for pos, c in enumerate(json.loads(gpath.read_text(encoding="utf-8")).get("clips", []), 1):
            c["idx"] = c.get("idx") or pos
            by_idx[c["idx"]] = c
    log = []
    for i in todo:
        topic = topics[i - 1]
        title = topic.get("title", f"clip{i}")
        print(f"  ({i}/{len(topics)}) {title[:26]}…", file=sys.stderr)
        try:
            body, extra = select_body(topic, sents, full_view, providers=providers)
            core = {"title": topic.get("title", ""), "one_argument": topic.get("one_argument", ""),
                    "hook_line": topic.get("hook_line", ""), "audience": topic.get("audience", ""),
                    "mainstream": topic.get("mainstream", ""),
                    "orig_keep_sids": topic.get("keep_sids", []), "human_status": "pending"}
            core.update(extra)
            clip = finalize_clip(core, body, sents, providers=providers)
        except Exception as ex:  # noqa: BLE001
            print(f"      ✗ {str(ex)[:150]}", file=sys.stderr)
            log.append(f"{i:02d} ✗ {title}")
            continue
        clip["idx"] = i
        by_idx[i] = clip
        write_review_md(out, i, clip)
        log.append(f"{i:02d} ✓ {title} :: 正文{len(body)}段/{clip['est_dur']}s "
                   f"钩子{len(clip['hook_options'])}个 删词{len(clip['deletions'])}处")
    golden = _write_golden(out, by_idx, words_json, selection_json, host, log)
    print(f"[done] 共{len(golden['clips'])}条（重跑{len(todo)}）→ {gpath}", file=sys.stderr)
    return golden


def main() -> int:
    ap = argparse.ArgumentParser(prog="generate", description="流程二·生成候选 Runner（成片脚本）")
    ap.add_argument("--words", required=True)
    ap.add_argument("--selection", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", default=None, help="只处理这些选题序号（如 6-22 或 8）")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    run(a.words, a.selection, a.out, host=a.host, providers=providers, limit=a.limit, only=a.only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
