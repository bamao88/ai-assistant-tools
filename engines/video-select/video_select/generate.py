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
BODY_WINDOW_PAD = 6
BODY_CONTEXT_ONLY_PAD = 8
BODY_MIN_DURATION_SEC = 45.0
BODY_DROP_SENTENCE_PATTERNS = (
    "simple test",
    "豆包手机",
    "合资公司",
    "sde",
    "s d e",
    "前向部署",
    "待会",
    "截图",
    "ppt",
    "评论区",
    "扣个一",
    "教程",
    "演示",
    "然后我来",
    "下一页",
    "打开看一下",
    "怎么打不开",
    "另外一个消息",
    "配这个团队",
    "逆向",
    "代码泄露",
    "review",
    "追平",
)
BODY_INCOMPLETE_ENDINGS = (
    "这个。",
    "这个",
    "的这个。",
    "的这个",
    "相关的。",
    "相关的",
    "包括",
    "比如",
    "超过了。",
    "超过了",
)
BODY_KEEP_SHORT_PATTERNS = (
    "认知太重要",
    "已经过时",
    "面试成功",
    "应聘成功",
    "很多案例",
    "非常多",
    "提效",
    "自动化",
    "搞定",
    "岗位",
)
BODY_BAD_OPENING_PATTERNS = (
    "完全以",
    "啊，像",
    "更大的信息量",
    "清晰地呈现",
    "就什么意思",
    "对啊",
    "行，反正",
    "行,反正",
    "在那个时候",
    "那相当于",
    "发的认知",
)


def load_topics(selection_path: str | Path) -> list[dict]:
    data = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    return data.get("clips", [])


def render_full(sents) -> str:
    return "\n".join(f"#{s.sid} {s.text}" for s in sents)


def _window_sids(sents, spans, pad: int = BODY_WINDOW_PAD) -> list[int]:
    """粗区间 → 放宽后的正文候选句号（去重、按时间顺序）。"""
    if not sents:
        return []
    max_sid = sents[-1].sid
    keep: set[int] = set()
    for span in spans or []:
        if not isinstance(span, (list, tuple)) or len(span) < 2:
            continue
        try:
            lo = max(0, int(span[0]) - pad)
            hi = min(max_sid, int(span[-1]) + pad)
        except (TypeError, ValueError):
            continue
        if lo <= hi:
            keep.update(range(lo, hi + 1))
    return sorted(s.sid for s in sents if s.sid in keep)


def _allowed_ranges(ids: list[int]) -> list[list[int]]:
    if not ids:
        return []
    out = []
    start = prev = ids[0]
    for sid in ids[1:]:
        if sid == prev + 1:
            prev = sid
            continue
        out.append([start, prev])
        start = prev = sid
    out.append([start, prev])
    return out


def _render_sids(sents, ids: list[int]) -> str:
    return "\n".join(
        f"#{sid} [{sents[sid].start:.1f}-{sents[sid].end:.1f}s] {sents[sid].text}"
        for sid in ids
    )


def _context_only_sids(sents, selectable: list[int], pad: int = BODY_CONTEXT_ONLY_PAD) -> list[int]:
    """给 LLM 读前后边界用的上下文句。不可被选入正文。"""
    if not sents or not selectable:
        return []
    max_sid = sents[-1].sid
    selectable_set = set(selectable)
    keep: set[int] = set()
    for lo, hi in _allowed_ranges(selectable):
        keep.update(range(max(0, lo - pad), lo))
        keep.update(range(hi + 1, min(max_sid, hi + pad) + 1))
    return sorted(s.sid for s in sents if s.sid in keep and s.sid not in selectable_set)


def _span_in_allowed(sids, ranges: list[list[int]]) -> bool:
    if not isinstance(sids, list) or not sids:
        return False
    try:
        a, b = int(sids[0]), int(sids[-1])
    except (TypeError, ValueError):
        return False
    return a <= b and any(a >= lo and b <= hi for lo, hi in ranges)


def _filter_segments_to_allowed(raw: list[dict], allowed: list[list[int]]) -> list[dict]:
    """LLM 偶尔会引用候选池外句号；这里做确定性丢弃，避免全场串味进入正文。"""
    return [s for s in raw if _span_in_allowed(s.get("sids"), allowed)]


def _has_drop_pattern(text: str) -> bool:
    low = text.lower()
    return any(p.lower() in low for p in BODY_DROP_SENTENCE_PATTERNS)


def _has_keep_short_pattern(text: str) -> bool:
    low = text.lower()
    return any(p.lower() in low for p in BODY_KEEP_SHORT_PATTERNS)


def _has_bad_opening(text: str) -> bool:
    stripped = text.strip()
    return any(stripped.startswith(p) for p in BODY_BAD_OPENING_PATTERNS)


def _enforce_min_body_duration(body: list[dict]) -> list[dict]:
    duration = sum(seg["span"][1] - seg["span"][0] for seg in body)
    if 0 < duration < BODY_MIN_DURATION_SEC:
        text = "".join(seg["text"] for seg in body)
        if not _has_keep_short_pattern(text):
            return []
    return body


def _make_body_segment(role: str, lo: int, hi: int, sents, reason: str) -> dict:
    return {
        "role": role if role in BODY_ROLES else "evidence",
        "sids": [lo, hi],
        "span": [round(sents[lo].start, 2), round(sents[hi].end, 2)],
        "text": "".join(sents[i].text for i in range(lo, hi + 1)),
        "reason": reason,
    }


def _sanitize_body(body: list[dict], sents) -> list[dict]:
    """确定性清理正文：硬停止句不进成片；太短的正文直接判空。"""
    cleaned: list[dict] = []
    for seg in body:
        lo, hi = seg["sids"]
        role = seg.get("role", "evidence")
        reason = seg.get("reason", "")
        run_start: int | None = None
        for sid in range(lo, hi + 1):
            if _has_drop_pattern(sents[sid].text):
                if run_start is not None and run_start <= sid - 1:
                    cleaned.append(_make_body_segment(role, run_start, sid - 1, sents, reason))
                run_start = None
                continue
            if run_start is None:
                run_start = sid
        if run_start is not None:
            cleaned.append(_make_body_segment(role, run_start, hi, sents, reason))

    cleaned = [
        seg for seg in cleaned
        if (seg["span"][1] - seg["span"][0]) >= 10.0 or _has_keep_short_pattern(seg["text"])
    ]
    return _enforce_min_body_duration(cleaned)


def _trim_initial_bad_opening(body: list[dict], sents) -> list[dict]:
    """首句若明显是上文尾巴，向后裁到第一句能独立开的句子。"""
    out = list(body)
    while out:
        first = out[0]
        lo, hi = first["sids"]
        while lo <= hi and _has_bad_opening(sents[lo].text):
            lo += 1
        if lo <= hi:
            out[0] = _make_body_segment(first.get("role", "argument"), lo, hi, sents, first.get("reason", ""))
            return _enforce_min_body_duration(out)
        out.pop(0)
    return []


def _ensure_formula_opening(topic: dict, body: list[dict], sents, allowed: list[list[int]]) -> list[dict]:
    """公式类标题若模型从解释句开始，补回紧邻的公式句。"""
    if not body:
        return body
    title = topic.get("title", "")
    if not any(mark in title for mark in ("+", "=", "公式")):
        return body
    first_lo, first_hi = body[0]["sids"]
    for span in topic.get("rough_sid_spans") or []:
        if not isinstance(span, (list, tuple)) or not span:
            continue
        try:
            sid = int(span[0])
        except (TypeError, ValueError):
            continue
        if not (0 <= sid < first_lo <= sid + 3):
            continue
        text = sents[sid].text
        if ("等于" not in text) and ("叫" not in text):
            continue
        if not _span_in_allowed([sid, first_hi], allowed):
            continue
        body = list(body)
        body[0] = _make_body_segment(body[0].get("role", "argument"), sid, first_hi, sents, body[0].get("reason", ""))
        return _sanitize_body(body, sents)
    return body


def _ensure_opportunity_opening(topic: dict, body: list[dict], sents, allowed: list[list[int]]) -> list[dict]:
    """机会/岗位类如果从行业例子半截开头，补回粗区间内的机会来源句。"""
    if not body:
        return body
    title = topic.get("title", "")
    one_argument = topic.get("one_argument", "")
    if not any(mark in title + one_argument for mark in ("机会", "岗位", "布道师", "非互联网")):
        return body
    first_lo, first_hi = body[0]["sids"]
    for span in topic.get("rough_sid_spans") or []:
        if not isinstance(span, (list, tuple)) or not span:
            continue
        try:
            rough_start = int(span[0])
        except (TypeError, ValueError):
            continue
        if not (rough_start < first_lo <= rough_start + 24):
            continue
        start = rough_start
        for sid in range(rough_start, first_lo):
            if any(mark in sents[sid].text for mark in ("机会", "企业 AI 落地", "转型的红利")):
                start = sid
                break
        if not _span_in_allowed([start, first_hi], allowed):
            continue
        body = list(body)
        body[0] = _make_body_segment(body[0].get("role", "argument"), start, first_hi, sents, body[0].get("reason", ""))
        return _sanitize_body(body, sents)
    return body


def _looks_incomplete(text: str) -> bool:
    stripped = text.strip()
    return any(stripped.endswith(p) for p in BODY_INCOMPLETE_ENDINGS)


def _extend_incomplete_out(body: list[dict], sents, allowed: list[list[int]]) -> list[dict]:
    """最后一句明显半截时，在同一允许窗口内向后补到完整句，最多 3 句。"""
    if not body:
        return body
    out = list(body)
    last = out[-1]
    lo, hi = last["sids"]
    added = 0
    while _looks_incomplete(sents[hi].text) and added < 3:
        nxt = hi + 1
        if not _span_in_allowed([lo, nxt], allowed):
            break
        if _has_drop_pattern(sents[nxt].text):
            break
        hi = nxt
        added += 1
    if hi != last["sids"][1]:
        out[-1] = _make_body_segment(last.get("role", "evidence"), lo, hi, sents, last.get("reason", ""))
    return out


def _chat_json_retry(client, msgs, temperature):
    """长稿偶发 JSON 截断/超时/返回非对象(null/列表)，重试一次；仍失败则抛清晰错误
    （上层按 clip try/except 跳过这条，而不是后面 .get 崩在 'NoneType'）。"""
    last: Exception = RuntimeError("chat_json 未返回结果")
    for _ in (1, 2):
        try:
            r = client.chat_json(msgs, temperature=temperature)
            if isinstance(r, dict):
                return r
            last = TypeError(f"LLM 返回非 JSON 对象：{type(r).__name__}")
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


# ───────────────────────── ① 总编 ─────────────────────────
def select_body(topic: dict, sents, full_view: str,
                providers=None, temperature: float = 0.0) -> tuple[list[dict], dict]:
    """局部候选取材 + 逻辑编排 → 正文 segments，出口过精选合并门禁。"""
    rough = topic.get("rough_sid_spans") or topic.get("keep_sids") or []
    cand_sids = _window_sids(sents, rough, BODY_WINDOW_PAD)
    context_sids = _context_only_sids(sents, cand_sids)
    allowed = _allowed_ranges(cand_sids)
    if not cand_sids:
        return [], {"title_suggestion": ""}
    brief = (f"【已选定选题】\n标题：{topic.get('title','')}\n"
             f"核心论点(one_argument)：{topic.get('one_argument','')}\n"
             f"钩子原话参考(hook_line)：{topic.get('hook_line','')}\n"
             f"受众：{topic.get('audience','')} ｜ 流量潜力：{topic.get('mainstream','')}\n"
             f"原始粗区间 rough_sid_spans：{json.dumps(rough, ensure_ascii=False)}\n"
             f"允许正文句号范围（rough_sid_spans ±{BODY_WINDOW_PAD}）："
             f"{json.dumps(allowed, ensure_ascii=False)}\n\n"
             f"【候选句（可选，选题粗区间 ±{BODY_WINDOW_PAD}，按时间顺序）】\n"
             f"{_render_sids(sents, cand_sids)}\n\n"
             f"【前后文（候选窗前后各 {BODY_CONTEXT_ONLY_PAD} 句，context-only，不可选，只供判断话题边界）】\n"
             f"{_render_sids(sents, context_sids) if context_sids else '（无）'}")
    client = OpenAICompatibleClient(providers=providers)
    data = _chat_json_retry(client, [
        {"role": "system", "content": load_prompt("body-edit")},
        {"role": "user", "content": brief}], temperature)
    raw = [{"role": s.get("role", "evidence"), "sids": s.get("sids", []),
            "reason": s.get("reason", "")}
           for s in data.get("segments", []) if isinstance(s, dict) and s.get("sids")]
    raw = _filter_segments_to_allowed(raw, allowed)
    body = gates.merge_segments(raw, sents)   # 精选合并：去重叠 + 合并相邻碎段
    body = _sanitize_body(body, sents)
    body = _ensure_formula_opening(topic, body, sents, allowed)
    body = _ensure_opportunity_opening(topic, body, sents, allowed)
    body = _trim_initial_bad_opening(body, sents)
    body = _extend_incomplete_out(body, sents, allowed)
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
         f"- **命中富集维度**：{'、'.join(clip.get('hit_dims', [])) or '—'}",
         f"- **正文估时**：{clip['est_dur']}s ｜ 正文段数：{len(clip['segments'])}"]
    if clip.get("dedup_merged_from"):
        L.append(f"- **去重合并自**：clip {clip['dedup_merged_from']}")
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
    prompt_versions = _deps.snapshot_prompts(out)   # 快照层：提示词原文+版本入 run，分数可复现
    golden = {"source_words": str(words_json), "selection": str(selection_json),
              "host": host, "method": "video-select/generate", "human_status": "pending",
              "prompt_versions": prompt_versions, "clips": clips}
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
                    "mainstream": topic.get("mainstream", ""), "hit_dims": topic.get("hit_dims", []),
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
