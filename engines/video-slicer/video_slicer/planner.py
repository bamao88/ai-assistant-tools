from __future__ import annotations

import json
import re

from .llm import OpenAICompatibleClient, parse_json_response
from .models import ClipPlan, clip_plan_from_dict
from .transcript import Cue, cues_to_prompt_lines, detect_language


# Only drop degenerate sub-clips; length is judged by argument completeness, not
# by a budget. The operator reviews/edits the resulting plan before rendering.
MIN_CLIP_SECONDS = 2


SYSTEM_PROMPT = """你是专业视频切片助手。输入是一份带时间戳、带说话人标注的会议/直播逐字稿。请把它切成若干「可独立成片」的片段，只输出严格 JSON，不要任何解释或 markdown。

【合格切片的定义】
一个切片 = 一个脱离上下文、单独发布也成立的完整论点，必须同时具备：
- 干净的开头钩子：从一句完整、不依赖上文的话起；禁止以「所以 / 那么 / 对吧 / 啊 / 就是说 / 然后 / 等等」这类承接或语气词开头。
- 自洽的主体：把这一个观点讲透。
- 收得住的结尾：落在结论或金句上，绝不停在半句话。
判断单位是「观点」，不是时长。长度由论点完整性决定：宁可长也要完整独立，不要为凑时长而切、也不要因为太长而硬截。没有最短/最长限制。

【说话人硬约束（最重要）】
只能切 host（主讲人）说的内容。逐字稿每行都标了说话人。任何其他人（学员 / 观众 / 提问者）开口的区间，绝不能纳入切片。
答疑场景：只有当 host 自己复述了问题再作答时，「读题 + 讲透的回答」才算合格的一条；如果问题是别人口述的，就只能从 host 自洽的独白部分起，或直接放弃该条。
绝对禁止：即使为了覆盖全程或凑够条数，也不能把「中间夹了其他人说话」的对话区间整段切成一条。这种区间只能取其中 host 连续独白的子段，取不出自洽子段就放弃，宁缺毋滥。每条 clip 的 [start,end] 区间内不能出现任何非 host 的说话。

【边界规则】
1. 切片内部连续，不做内部跳剪。
2. 切片之间允许留空档——中间的废话不必纳入任何切片。
3. start/end 必须用逐字稿中真实出现的时间戳，格式 HH:MM:SS.mmm，对齐到句子/段落边界。
4. 若真实切点落在同一句/同一段内部（前半属上一条、后半属下一条），不要硬拆：边界先取整句/整段，并在 reason 里写明「段内切：实际切点在 HH:MM:SS，前/后半归属」，交后续精剪。

【必须跳过，绝不切】
试音 /「能听到吗」、问候寒暄、时间安排 / 报名 / 物料 / 作业等事务性内容、纯过渡句、没说完的半截话。

【颗粒度】
默认中等：一个完整论点一条。若某条信息量过大、含两个以上可独立的子主张，仍先按一条给出，但在 reason 末尾用「可拆分：……」列出子点及大致起止。

【覆盖（最重要的硬指标）】
从逐字稿开头到结尾，严格按时间顺序通览一遍，确保 host 讲的每一个完整论点都被切出一条，一个都不要漏。
- 不要因为某个论点「比较短」「和前面话题相关」「不如别处精彩」就跳过它，或把它并进相邻的一条。判断只看它本身是否是一个完整独立论点。
- 后半段、收尾段那些较短的论点/答疑最容易被漏，请特别留意，逐个切出来。
- 答疑部分：host 每复述并讲透一个问题，就单独成一条，哪怕只有几十秒；相邻的不同问题分别成条，不要合并。
- 宁可多切几条完整论点，也不要漏掉中间的论点。

【数量】
覆盖优先：在不重复、每条都成立的前提下，尽量把所有完整论点都切出来，最多 max_clips 条。不要为了压数量而漏掉论点；也不要把不成立的过场凑成一条。

【输出 JSON】
严格 JSON 对象：{"version":1,"clips":[{"id","title","start","end","reason","tags"}]}
- id：短横线安全的字符串，如 "clip-01"。
- title：这一条的核心主张，一句话。
- reason：依次包含——为什么成立 ｜ 开头首句原文 ｜ 结尾末句原文 ｜（如有）段内切说明 ｜（如有）可拆分点。
- tags：3-5 个主题词。
只用逐字稿里出现的时间戳，不要编造任何内容。"""


def generate_ai_clip_plan(
    video: str,
    transcript: str,
    cues: list[Cue],
    mode: str,
    query: str | None = None,
    max_clips: int = 6,
    client: OpenAICompatibleClient | None = None,
    layout: str | None = None,
    subtitle: str | None = None,
    join: bool | None = None,
    host: str | None = None,
) -> ClipPlan:
    if mode not in {"query", "auto"}:
        raise ValueError("AI planning mode must be query or auto.")
    if mode == "query" and not query:
        raise ValueError("--query is required for query mode.")
    client = client or OpenAICompatibleClient()
    language = detect_language(cues, transcript)
    transcript_lines = cues_to_prompt_lines(cues, limit=1200)
    resolved_host = host or _dominant_speaker(cues)
    user_goal = query or "挑出信息密度高、能独立成片的完整论点。"
    payload = {
        "host": resolved_host or "（未标注，请把出现最多的说话人视为 host）",
        "language": language,
        "mode": mode,
        "max_clips": max_clips,
        "goal": user_goal,
        "transcript_cues": transcript_lines,
    }
    # Low temperature: clip selection should be consistent, not creative — this
    # is the main lever against run-to-run recall variance.
    raw = client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.0,
        json_mode=True,
    )
    result = _coerce_plan_json(raw)
    result.setdefault("version", 1)
    result.setdefault("source", {"video": video, "transcript": transcript, "language": language})
    plan = clip_plan_from_dict(result)
    # Coverage-audit second pass: the first pass drops short / mid-stream
    # arguments inconsistently, so we ask the model to find what it missed and
    # merge those in. This is what makes recall reliably clear the bar.
    plan.clips = _merge_clips(plan.clips, _coverage_audit(client, payload, plan.clips, max_clips))
    plan.clips = _enforce_clip_lengths(plan.clips)
    # Rendering settings are operator choices, not the model's — override whatever
    # the model may have emitted with the values passed on the CLI.
    if layout is not None:
        plan.defaults.layout = layout
    if subtitle is not None:
        plan.defaults.subtitle = subtitle
    if join is not None:
        plan.defaults.join = join
    return plan


def _coverage_audit(client, payload: dict, existing, max_clips: int):
    """Second pass: list the clips found so far and ask the model to walk the
    transcript again and return only the complete host arguments that were
    missed (especially short Q&A). Returns a list[Clip] (possibly empty)."""
    found = "\n".join(f"- [{_fmt(c.start)}–{_fmt(c.end)}] {c.title}" for c in existing)
    audit_payload = {
        "host": payload["host"],
        "max_clips": max_clips,
        "已切出的片段": found,
        "transcript_cues": payload["transcript_cues"],
    }
    system = (
        SYSTEM_PROMPT
        + "\n\n【本次任务：查漏】下面给出「已切出的片段」列表。请你从头到尾按时间顺序重新通览逐字稿，"
        "只找出其中被遗漏的、host 讲的完整论点（重点是较短的答疑、收尾论点），"
        "按相同 JSON schema 只输出这些遗漏项；如果确实没有遗漏，返回 {\"clips\":[]}。不要重复已切出的片段。"
    )
    try:
        raw = client.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(audit_payload, ensure_ascii=False)},
            ],
            temperature=0.0,
            json_mode=True,
        )
        data = _coerce_plan_json(raw)
        data.setdefault("version", 1)
        return clip_plan_from_dict(data).clips
    except (ValueError, RuntimeError):
        return []  # audit is best-effort; never fail the whole plan on it


def _fmt(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def _merge_clips(base: list, extra: list) -> list:
    """Add audited clips that don't substantially overlap an existing one, then
    sort chronologically and reassign clean sequential ids."""
    merged = list(base)
    for clip in extra:
        if not any(_overlaps(clip, kept) for kept in merged):
            merged.append(clip)
    merged.sort(key=lambda c: c.start)
    for index, clip in enumerate(merged, start=1):
        clip.id = f"clip-{index:02d}"
    return merged


def _overlaps(a, b, ratio: float = 0.5) -> bool:
    overlap = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    shorter = min(a.duration, b.duration) or 1
    return overlap / shorter >= ratio


def _coerce_plan_json(content: str) -> dict:
    """Accept either {"clips": [...]} or a bare top-level [...] array — models
    drift between the two, especially as max_clips grows."""
    try:
        return parse_json_response(content)
    except ValueError:
        pass
    match = re.search(r"\[.*\]", content, flags=re.DOTALL)
    if match:
        array = json.loads(match.group(0))
        if isinstance(array, list):
            return {"clips": array}
    raise ValueError("Could not parse a clip plan from the model response.")


def _dominant_speaker(cues: list[Cue]) -> str | None:
    """The speaker who talks across the most cues — used as the default host
    when the caller doesn't name one explicitly."""
    counts: dict[str, int] = {}
    for cue in cues:
        if cue.speaker:
            counts[cue.speaker] = counts.get(cue.speaker, 0) + 1
    return max(counts, key=lambda name: counts[name]) if counts else None


def _enforce_clip_lengths(clips: list) -> list:
    """Only drop degenerate sub-clips; length is the model's call, not ours."""
    kept = [clip for clip in clips if clip.duration >= MIN_CLIP_SECONDS]
    if not kept:
        raise ValueError("Model returned no usable clips.")
    return kept

