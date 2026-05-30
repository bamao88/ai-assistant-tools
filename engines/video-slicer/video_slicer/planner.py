from __future__ import annotations

import json
import re

from .llm import OpenAICompatibleClient, parse_json_response
from .models import ClipPlan, clip_plan_from_dict
from .transcript import Cue, cues_to_prompt_lines, detect_language


# Only drop degenerate sub-clips; length is judged by argument completeness, not
# by a budget. The operator reviews/edits the resulting plan before rendering.
MIN_CLIP_SECONDS = 2


SYSTEM_PROMPT = """你是视频切片助手。输入是一份带时间戳、带说话人标注的会议/直播逐字稿。你的任务不是把所有讲得好的内容都切出来，而是【高度精选】出极少数最值得独立成片的片段。只输出严格 JSON，不要 markdown。

【第一原则：宁缺毋滥】
一个视频通常只产出 1-3 个切片，绝不是有多少教学点就切多少条。先在心里把所有候选列出来，再用下面的标准狠狠筛到最强的 1-3 个（最多 max_clips 条）。把整段视频切成十几条是错误的。如果整片连一个够格的点都没有，就让 clips 为空数组、在 note 写「不建议切」，不要硬凑。

【选片标准：什么样的点才配成片（要同时满足）】
1. 自洽独立：脱离上下文也能听懂，不依赖别人的提问、不依赖「看我屏幕 / 这个文档」这类现场指代。
2. 代表定位：最能体现主讲人核心定位的「判断性观点」——账号定位是「懂 AI 产品、懂技术落地、懂一线产品判断」。要判断、洞察、反常识结论，不要泛泛的操作步骤、工具用法、事务安排。
3. 有钩子有金句：开头抓人，含可被单独截出来引用、甚至有点反常识的结论。
4. 彼此差异化：最终留下的几条主题不重复，各占一个角度。
5. 成片成本低：优先成段独白，或主讲人自己复述了题面的答疑；若一个点高度依赖一来一回的对话、必须大量剔除别人的话才能勉强凑成一条，直接放弃。

【果断排除】
纯工具操作流程、必须配屏幕演示才看得懂的、涉及具体个人/公司内情的、过渡句与事务性内容（试音、问候、时间/报名/物料/作业安排）、和核心定位关系不大的。

【隐私硬约束：只剪主讲人(host)】
切片 [start,end] 区间内只能有 host 的发言；其他人（学员/嘉宾/提问者）的话一律不能被包含进区间。
- 答疑类之所以能剪，是因为 host 常自己复述题面再答；优先选这种自洽回答。
- 若某条必须让观众知道「在答什么」，只能在 reason 里用一行【中性背景】交代，不写任何人的姓名/公司/身份，能少则少。
- 凡涉及某个具体学员的公司内情（裁员、具体业务等），直接不切。

【边界】
- 开头从一句完整、不依赖上文的话起（不要从「所以 / 那么 / 对吧 / 啊 / 然后」这类承接词起）。
- 结尾落在结论或金句上，收得住，不停在半句话。
- 边界尽量贴时间戳段落。纯讲座/独白型素材：切片内部连续、不做内部跳剪。
- 若真实切点落在同一段内部，在 reason 里写「段内切：实际切点在 HH:MM:SS」，整段先保留交后续精剪。

【输出 JSON】
严格 JSON 对象：{"version":1,"clips":[{"id","title","start","end","reason","tags"}],"note":""}
- clips：精选后的 1-3 条（最多 max_clips）。reason 依次写：对应满足了哪条选片标准 ｜ 开头首句原文 ｜ 结尾末句原文 ｜（答疑需要时）一行中性背景 ｜（段内切时）切点说明。
- note：一两句说明你为什么没选其它候选（让我知道你筛过了，不是漏了）；若整片没有够格的点，clips 为空数组、note 写「不建议切」。
start/end 用逐字稿里真实出现的 HH:MM:SS.mmm，不要编造内容。"""


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
    note = str(result.get("note") or "")
    if not (result.get("clips") or []):
        # The prompt is allowed to refuse — nothing in this video clears the bar.
        raise ValueError(f"模型判定：不建议切片。{note}".strip())
    result.setdefault("version", 1)
    result.setdefault("source", {"video": video, "transcript": transcript, "language": language})
    plan = clip_plan_from_dict(result)
    plan.clips = _enforce_clip_lengths(plan.clips)
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

