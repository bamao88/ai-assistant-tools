#!/usr/bin/env python3
"""主观维度 LLM 评委通用封装 —— 给「无唯一答案」的阶段打 rubric 分。

契约：eval/contracts/{1_topic_select,4_hook,3_refine_deduct}.md 的「主观/覆盖率」层。
精确匹配类阶段（②③⑤）不用它；只有选题覆盖率、钩子打分卡、去口水承接句误删用得上。

设计：薄封装。复用引擎现成的 LLM 客户端（与 generate.py 同源），把一段 rubric 提示词 +
结构化 payload 丢给模型，要它返回 JSON 评分。**纯接口**：默认不在自动回归里跑（要网络、
要按发布出口先 route-bypass，见 memory: transcription-local-egress / publishing-local-egress）。
评委分需配人工抽检兜底（见 plan §6.2）。

用法（库）:
  from judge import judge
  r = judge(rubric="给钩子按 戳点/中受众/露答案 各 0-2 分…", payload={...})
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ENGINE_DIR))


def judge(rubric: str, payload: dict, providers=None, temperature: float = 0.0) -> dict:
    """把 rubric + payload 丢给 LLM 评委，返回它的 JSON 评分。失败抛异常（不静默兜底）。"""
    from video_select import _deps  # noqa: F401  挂 video-slicer
    from video_select.generate import _chat_json_retry
    from video_slicer.llm import OpenAICompatibleClient
    from video_slicer.cli import load_env_file, _discover_env_file

    load_env_file(_discover_env_file())
    client = OpenAICompatibleClient(providers=providers)
    user = json.dumps(payload, ensure_ascii=False)
    return _chat_json_retry(client, [
        {"role": "system", "content": rubric},
        {"role": "user", "content": user}], temperature)


# rubric 模板（评分卡）——具体阶段评分器引用这些常量，保证口径一致 ───────────────
RUBRIC_HOOK = (
    "你是短视频钩子评委。对每个候选钩子按三要素各打 0-2 分（0无/1弱/2强）：\n"
    "  戳点(hooky)：3秒内能不能勾住陌生人；中受众(audience)：是否对准目标受众；"
    "露答案(reveal)：有没有过早把结论说完导致没必要看下去（越不露分越高）。\n"
    "并判断 strategy 优先级是否「整句直用 > 剪头尾 > 拼接」。\n"
    "返回 JSON：{\"scores\":[{\"stitched\":..,\"hooky\":0-2,\"audience\":0-2,\"reveal\":0-2,\"comment\":..}]}")

RUBRIC_TOPIC_COVERAGE = (
    "你是选题覆盖率评委。给定【金标准选题清单】和【候选选题清单】，按语义对齐（标题措辞不同"
    "但同义算命中，不能字面比）：\n"
    "  召回：金标准里该选的观点，候选漏了哪些；精确：候选里有没有跑题/凑数的。\n"
    "返回 JSON：{\"matched\":[[gold_idx,cand_idx]],\"gold_missed\":[gold_idx],"
    "\"cand_extra\":[cand_idx],\"recall\":0-1,\"precision\":0-1}")

RUBRIC_DEDUCT_LINKER = (
    "你是去口水复核评委。给定【原正文逐句】和【删除决策】，只判一件事：有没有把承接句、"
    "逻辑连接词、必要语义当口水误删（最大的坑）。删完通读是否仍像正常人说话。\n"
    "返回 JSON：{\"wrongly_deleted\":[{\"sid\":..,\"text\":..,\"why\":..}],\"readable\":true/false}")


if __name__ == "__main__":
    print("judge.py 是库（评委封装）。被 1_topic_select.py / 4_hook.py 在 --judge 时调用。\n"
          "直接跑无意义；要测评委先配好 LLM 出口（route-bypass）后在评分器里加 --judge。",
          file=sys.stderr)
