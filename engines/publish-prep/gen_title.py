#!/usr/bin/env python3
"""标题生成器（调外部模型按 dbs-xhs-title 75 公式库起标题）。

把 dbs-xhs-title skill 整篇当知识喂给模型（skill = 单一真源），模型读「已定稿正文」，
选公式、生成标题、标编号。口径按 2026-06-29 战略转向＝企业 AI 落地（去训练营/招生）。

用法:
    python3 gen_title.py --body-file <正文.txt> [--spine ...] [--title 主题] [--provider kimi|minimax]
    或 import：from gen_title import gen_title
"""
import sys
import os
import json
import argparse
from pathlib import Path

import config

sys.path.insert(0, str(config.KNOWLEDGE_INGEST))
import core  # noqa: E402
core.load_env(config.ENV_FILE)

SKILL_MD = config.DBS_TITLE_SKILL.read_text(encoding="utf-8")

SYSTEM = f"""你是小红书标题公式匹配器。你的任务：读一条讲 AI 的口播视频正文，从下面的 75 个验证过的爆款公式库里，选最合适的公式，为它生成标题。

【这个账号】张和本人，前小米 AI 实验室早期员工、AI 出海公司 CEO，长期在一线给企业做 AI 落地。内容主线＝企业 AI 落地（落地真相 / 踩坑 / 一线判断）。受众=关注 AI 落地 / AI 工程 / 想转型的人。标题要能让目标人群停下来，不写招生/训练营口径。

【硬铁律】
1. 每个标题必须能追溯到一个公式编号（输出里写 #N）。
2. ≤20 字（含标点）。
3. 留悬念，不把答案说完——看完标题观众还想点进来。
4. 话题往大众词扩，别缩窄成行业黑话；但强名词（Claude Code / Anthropic 等自带流量）顶到最前，别翻译掉。
5. 张力检查：对比/数字/悬念/冲突/时间承诺/结果承诺，至少命中 2 项。
6. 禁用破折号「——」。
7. 流量锚必须真实，禁夸大身份/职位/数字（张和是"早期员工"非"负责人"）。

【公式库与完整规则（dbs-xhs-title）】
{SKILL_MD}

【输出】严格 JSON，不要任何额外文字：
{{"采用":{{"标题":"","公式号":"#N","公式名":"","理由":"一句话"}},"备选":[{{"标题":"","公式号":"#N"}},{{"标题":"","公式号":"#N"}}]}}"""

USER_TMPL = """这条视频的正文：

「{body}」

核心论点(spine)：{spine}
内容主题：{title}

按公式库给这条视频起标题（采用 1 个 + 备选 2 个）。只输出 JSON。"""


def gen_title(body: str, spine: str = "", title: str = "", provider: str = "kimi") -> dict:
    os.environ["LLM_PROVIDER"] = provider
    user = USER_TMPL.format(body=body, spine=spine or "（见正文）", title=title or "（见正文）")
    raw = core.call_llm(SYSTEM, user, temperature=0.6, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--spine", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--provider", choices=["kimi", "minimax"], default="kimi")
    args = ap.parse_args()
    body = Path(args.body_file).read_text(encoding="utf-8")
    out = gen_title(body, args.spine, args.title, args.provider)
    out["_provider"] = args.provider
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
