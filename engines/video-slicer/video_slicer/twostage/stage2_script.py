"""阶段二 · 定脚本边界（外科手术）。

对阶段一的每条选题，只盯它粗区间附近的【张和句子】，按 in/out 纪律精选要哪几句。
AI 只回句号区间（keep_sids），代码据此拼脚本、回查时间。
"""
from __future__ import annotations

from ..llm import OpenAICompatibleClient
from .index import Sentence, render_window

WINDOW_PAD = 6  # 粗区间两侧各放宽几句，给阶段二修 in/out 的余量


STAGE2_TASK = """\
【你的任务 · 阶段二定脚本】
下面是一条已选定选题的资料 + 它附近的【张和候选句】（每行 `#句号 文本`，已按时间顺序）。
按上面的「in/out 点纪律」，挑出真正要进这条切片的句子：

- in 点：从 hook 那句（或能直接立住论点的句子）起，砍掉前面的软铺垫/承接语。
- out 点：论点说完即收，不拖到他转下个话题。
- 允许跳接：可挑不连续的句子段，砍掉中间废话，但保持时间先后、拼接后逻辑顺。
- 只能选给你的候选句号；不要编造句号。挑不出合适内容就给空。

【输出严格 JSON，无 markdown】
{"keep_sids": [[起句号, 止句号], ...]}   // 每个 [a,b] 是一段连续保留的闭区间；多段=跳接
只输出这个 JSON 对象。"""


def _window_sids(sentences: list[Sentence], spans: list[list[int]]) -> list[int]:
    """粗区间 → 放宽后的 host 候选句号（去重、按序）。"""
    keep: set[int] = set()
    max_sid = sentences[-1].sid if sentences else 0
    for span in spans:
        if not span:
            continue
        lo = max(0, int(span[0]) - WINDOW_PAD)
        hi = min(max_sid, int(span[-1]) + WINDOW_PAD)
        keep.update(range(lo, hi + 1))
    host_sids = [s.sid for s in sentences if s.is_host and s.sid in keep]
    return sorted(host_sids)


def select_script(
    clip: dict,
    sentences: list[Sentence],
    persona_text: str,
    providers: list[str] | None = None,
    temperature: float = 0.2,
) -> list[list[int]]:
    cand_sids = _window_sids(sentences, clip.get("rough_sid_spans", []))
    if not cand_sids:
        return []
    window = render_window(sentences, cand_sids)
    brief = (
        f"标题：{clip.get('title','')}\n"
        f"论点(one_argument)：{clip.get('one_argument','')}\n"
        f"钩子原话(hook_line)：{clip.get('hook_line','')}\n\n"
        f"【候选句】\n{window}"
    )
    client = OpenAICompatibleClient(providers=providers)
    data = client.chat_json(
        [
            {"role": "system", "content": persona_text + "\n\n" + STAGE2_TASK},
            {"role": "user", "content": brief},
        ],
        temperature=temperature,
    )
    spans = data.get("keep_sids", [])
    # 规整：丢非法/空段，确保 a<=b
    out: list[list[int]] = []
    cand_set = set(cand_sids)
    for sp in spans:
        if not sp or len(sp) < 2:
            continue
        a, b = int(sp[0]), int(sp[-1])
        if a > b:
            a, b = b, a
        # 落在候选窗口内的部分才保留
        if a in cand_set or b in cand_set:
            out.append([a, b])
    return out
