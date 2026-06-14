"""阶段一 · 选题（编辑判断）。

输入：整场编号逐字稿（带说话人）。输出：少而精的选题候选，每条带「粗句号区间」。
AI 只做编辑判断 + 指出大概在哪几句，**不吐时间戳**；精修边界交给阶段二。
"""
from __future__ import annotations

from pathlib import Path

from ..llm import OpenAICompatibleClient
from .index import Sentence, render_numbered

PERSONA_DIR = Path(__file__).resolve().parents[2] / "personas"


def load_persona(name: str) -> str:
    path = PERSONA_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"persona 不存在：{path}")
    return path.read_text(encoding="utf-8")


STAGE1_TASK = """\
【你的任务 · 阶段一选题】
读下面这场【编号逐字稿】（每行 `#句号 [说话人] 文本`）。按上面的「选题闸 5 关 + 标题硬要求 + 数量纪律」，从张和(host)的发言里挑出少而精的短视频切片选题。学员的话只作背景，不能作为选题主体。

【关键：你只负责"选什么"，不负责"切在哪一毫秒"】
- 不要输出任何时间戳。
- 每条选题只需指出它大概落在哪些【句号区间】（rough_sid_spans）——给出承载这个观点的张和句子的大致起止句号即可，可以略宽，精确 in/out 交给下一步。
- 若一个观点由不连续的几段拼成，就给多个区间。

【输出严格 JSON，无 markdown】
{"clips":[{
  "title": "钩子式标题（挂流量锚、疑问/反认知句式）",
  "one_argument": "一句话——这条唯一要观众记住的观点",
  "hook_line": "能当 0-3 秒钩子的张和原话（逐字稿里真有的）",
  "audience": "破圈大众/AI从业者/创业者老板/转型求职 之一或组合",
  "mainstream": "高/中/低",
  "why": "为什么会被传播 / 记忆点",
  "rough_sid_spans": [[起句号, 止句号]]
}]}
按 mainstream 高→低排序。**覆盖优先、宁多勿漏，目标 18-25 条**：过得了选题闸的都收（含细分操作技巧/insider 干货，低流量的标 mainstream=低也要收），只排除寒暄/跑题/重复/立不住观点的段落。只输出这个 JSON 对象。"""


def select_topics(
    sentences: list[Sentence],
    persona: str,
    providers: list[str] | None = None,
    temperature: float = 0.2,
) -> list[dict]:
    persona_text = load_persona(persona)
    transcript = render_numbered(sentences)
    client = OpenAICompatibleClient(providers=providers)
    data = client.chat_json(
        [
            {"role": "system", "content": persona_text + "\n\n" + STAGE1_TASK},
            {"role": "user", "content": transcript},
        ],
        temperature=temperature,
    )
    clips = data.get("clips", [])
    return [c for c in clips if c.get("rough_sid_spans")]
