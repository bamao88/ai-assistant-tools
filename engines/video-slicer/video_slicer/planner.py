from __future__ import annotations

import json
import re

from .llm import OpenAICompatibleClient, parse_json_response
from .models import ClipPlan, Segment, clip_plan_from_dict
from .transcript import Cue, cues_to_prompt_lines, detect_language


# Only drop degenerate sub-clips/segments; length is judged by argument
# completeness, not a budget. The operator reviews/edits the plan before render.
MIN_CLIP_SECONDS = 2


SYSTEM_PROMPT = """你是视频切片助手。输入是一份带时间戳、带说话人标注的会议/直播/答疑逐字稿。你的任务不是按时间顺序把讲得好的段落一段段切出来，而是【先定主题，再缝合】：从整场里挑出极少数最值得独立成片的【主题】，每个主题把分散在各处、只属于主讲人(host)的发言缝合成一条视频。只输出严格 JSON，不要 markdown。

【第一原则：宁缺毋滥，按主题成片】
一场内容通常只产出 2-3 条视频（最多 max_clips 条），绝不是有多少教学点就切多少条。
正确做法：通读全场 → 归纳出 2-3 个最强主题 → 每个主题作为一条视频。不要把整场顺序切成十几段。
如果整场连一个够格的主题都没有，clips 为空数组、note 写「不建议切」，不要硬凑。

【缝合：一条视频 = 一个主题下多段 host 发言的拼接】
同一主题的内容常分散在逐字稿不同时间点（例如开头讲一半、过很久又补一段）。把这些【只属于 host】的片段按播放顺序收进同一条视频的 segments 里，中间穿插的学员提问、闲聊、跑题一律不收。
- 每条视频的 segments 是有序列表，每段是一对真实出现的 HH:MM:SS.mmm；可以是 1 段，也可以是多段缝合。
- 段与段之间允许跳剪（这正是缝合的意义）；但每一段【内部】必须连续、且只有 host 在说话。
- 答疑/对话型：host 常自己复述题面再答，优先收这种自洽的回答段；纯学员发言的段不要。
- 讲座/独白型同样按主题缝合，不必拘泥于「整段从头到尾连续」。

【选片标准：什么样的主题才配成片（同时满足）】
1. 自洽独立：脱离上下文也能听懂，不依赖别人的提问、不依赖「看我屏幕 / 这个文档」这类现场指代。
2. 代表定位：最能体现主讲人核心定位的「判断性观点」——账号定位是「懂 AI 产品、懂技术落地、懂一线产品判断」。要判断、洞察、反常识结论，不要泛泛的操作步骤、工具用法、事务安排。
3. 有钩子有金句：开头抓人，含可被单独截出来引用、甚至有点反常识的结论。
4. 彼此差异化：最终的 2-3 条主题必须互不重复，各占一个角度。同一个点只保留最强的一条，绝不让同一主题出现两次。
5. 成片成本低：优先成段独白，或主讲人自己复述了题面的答疑。

【果断排除】
纯工具操作流程、必须配屏幕演示才看得懂的、过渡句与事务性内容（试音、问候、时间/报名/物料/作业安排）、和核心定位关系不大的。

【隐私硬约束：只剪主讲人(host)】
所有 segment 区间内只能有 host 的发言；其他人（学员/嘉宾/提问者）的话一律不能被收进任何 segment。
- 若某条主题必须让观众知道「在答什么」，只能在 reason 里用一行【中性背景】交代，不写任何人的姓名/公司/身份，能少则少。
- 凡涉及某个具体学员的公司内情（裁员、具体业务等），直接不切。

【边界】
- 每段 segment 开头从一句完整、不依赖上文的话起（不要从「所以 / 那么 / 对吧 / 啊 / 然后」这类承接词起）。
- 整条视频结尾落在结论或金句上，收得住，不停在半句话。
- 边界尽量贴时间戳段落。

【输出 JSON】
严格 JSON 对象：{"version":1,"clips":[{"id","title","segments":[{"start","end"}],"reason","tags"}],"note":""}
- clips：精选后的 2-3 条（最多 max_clips），每条是一个主题。
- segments：该主题下按播放顺序排列的 host-only 片段；单段或多段缝合都行。
- title：一句话主题，最好本身就是个判断性观点。
- reason：依次写「缝合说明（这条把哪几处讲同一主题的话拼在一起）｜满足了哪条选片标准 ｜（答疑需要时）一行中性背景」。
- note：一两句说明你为什么没选其它候选（让我知道你筛过了，不是漏了）；整片没有够格主题时 clips 为空数组、note 写「不建议切」。
start/end 用逐字稿里真实出现的 HH:MM:SS.mmm，不要编造内容。"""


def generate_ai_clip_plan(
    video: str,
    transcript: str,
    cues: list[Cue],
    mode: str,
    query: str | None = None,
    max_clips: int = 3,
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
    note = str(result.get("note") or "")
    if not (result.get("clips") or []):
        # The prompt is allowed to refuse — nothing in this video clears the bar.
        raise ValueError(f"模型判定：不建议切片。{note}".strip())
    result.setdefault("version", 1)
    result.setdefault("source", {"video": video, "transcript": transcript, "language": language})
    plan = clip_plan_from_dict(result)
    plan.clips = _enforce_clip_lengths(plan.clips)
    # Privacy is a hard rule the prompt can't guarantee: deterministically trim
    # each clip to its longest host-only sub-span (drop it if none qualifies).
    plan.clips = _enforce_host_only(plan.clips, cues, resolved_host)
    if not plan.clips:
        raise ValueError(f"精选后没有满足 host-only 的片段。{note}".strip())
    plan.selection_note = note  # why other candidates were dropped; surfaced by the CLI
    # Rendering settings are operator choices, not the model's — override whatever
    # the model may have emitted with the values passed on the CLI.
    if layout is not None:
        plan.defaults.layout = layout
    if subtitle is not None:
        plan.defaults.subtitle = subtitle
    if join is not None:
        plan.defaults.join = join
    return plan


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


def _enforce_host_only(clips: list, cues: list[Cue], host: str | None) -> list:
    """Guarantee each clip's [start,end] contains only the host. Trim every clip
    to the longest contiguous window free of non-host speech; drop clips with no
    host-only window long enough. This is the deterministic backstop behind the
    prompt's privacy rule."""
    if not host:
        return clips
    intruders = [(c.start, c.end) for c in cues if c.speaker and c.speaker != host]
    kept = []
    for clip in clips:
        window = _largest_host_window(clip.start, clip.end, intruders)
        if window and (window[1] - window[0]) >= MIN_CLIP_SECONDS:
            if (window[0], window[1]) != (clip.start, clip.end):
                clip.reason = (clip.reason + " ｜ [自动校正] 已剔除区间内非主讲人发言").strip(" ｜")
            clip.start, clip.end = window
            kept.append(clip)
    return kept


def _largest_host_window(start: float, end: float, intruders: list) -> tuple[float, float] | None:
    """Within [start,end], return the longest sub-interval not covered by any
    intruder span. Returns (start,end) unchanged when there are no intruders."""
    blocks = sorted((max(start, a), min(end, b)) for a, b in intruders if b > start and a < end)
    best: tuple[float, float] | None = None
    cursor = start
    for a, b in blocks:
        if a > cursor and (best is None or (a - cursor) > best[1] - best[0]):
            best = (cursor, a)
        cursor = max(cursor, b)
    if end > cursor and (best is None or (end - cursor) > best[1] - best[0]):
        best = (cursor, end)
    return best

