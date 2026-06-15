#!/usr/bin/env python3
"""选题 prompt 迭代工作台 —— 整场逐字稿 → 切片候选(选题层)。不渲染、不切片，只出候选 JSON 供人审。

现状：选题层无 prompt（人工写候选 md）。这是从 0 起草的选题 prompt，先在 tmp 跑文本验证。
输入：腾讯 minutes JSON（paragraphs[] 带 ms 时间戳）。
输出：clip 候选数组，每条含 title/one_argument/segments/hook_line/mainstream/audience/why。

用法:
  python select_clips.py <minutes.json> [--persona zh_main] [--out cand.json]

【固化说明（video-tools-migration 阶段1）】
  这是「方案A 基准」——单阶段选段（一次 LLM 同时定选题 + 选段），由 tmp 固化进引擎做
  方案A vs 方案B(twostage 词级) vs 金标准 的脚本级对照真源（见迁移计划 §1.4 / §7.2 D6）。
  与线上 planner 区别：本脚本只出「选题层候选」、不渲染不切片。原 tmp 版的张和选题 prompt
  原样保留以作忠实基线；persona 解耦（抽到 profiles/zh_main）属阶段2/5 范围，不在本固化内动。
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

_ENGINE = "/Volumes/ExtSSD2601/AI_Assistant/tools/engines/video-slicer"
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402

SELECT_SYSTEM_PROMPT = """你是张和自媒体主号(招生破圈向)的短视频切片选题官。输入是张和一场口播/答疑的完整逐字稿(带 mm:ss 时间戳)。你的任务：从中挑出**少而精**的、能在社交平台上钩住陌生人的切片候选。宁缺毋滥，挑不出就少挑，不要把每个话题块都切。只输出严格 JSON，不要 markdown。

【根本认知】
切片不是"把逐字稿按话题分块"，而是"用张和的原话当素材，重新立一条短视频选题"。判断标准永远是"陌生人刷到会不会停下来、看完记不记得住、想不想了解训练营"，不是"张和讲到了什么"。

【选题闸：每条候选必须同时过这 5 关，过不了就不出】
1. 独立可懂：抽掉课堂内部语境后，零背景的陌生人能看懂吗？(残留"第二步/咱们人不多/评论区打一下/上一期回放"这类现场语境的，要么换 in 点切掉，要么放弃。)
2. 单一论点：这条只讲一个观点。张和把好几件事连着讲时，拆成多条，或只取最锋利的一段，不要一条塞 3 个点。
3. 值不值得切 = 看「反认知度」，不看「内不内行」。判断标准是这个观点够不够反认知/戳痛/有冲击，而不是名词内不内行。⚠️常见误区：把"专有名词=内行=低流量"——这是错的。Claude Code、Codex、Karpathy、DeepSeek、腾讯、a16z、YC 这类专有名词/权威人物/机构，本身就是**搜索词、话题词、自带流量池**，是资产不是负债。真正该闸掉的只有"既没名词、又不大众、又不反认知"的纯冷门机制(某CLI怎么配、skill内部结构、自研某平台架构)。
4. 价值一句话说清：能用一句话说出"观众看完得到什么"。说不清=选题没立住。
5. 炸点可前置：逐字稿里有没有一句张和原话，反认知或戳痛点，能当 0-3 秒钩子。把 segment 的 in 点切到这句话前面，砍掉它前面的软铺垫。

【标题/钩子硬要求（学竞品爆款，否则白瞎流量）】
- **每条标题必须挂至少一个「流量锚」**：{自带流量的专有名词(Claude Code/Codex/Karpathy/DeepSeek/腾讯/a16z/YC…) | 权威人物或机构 | 具象数字+反差(如"3个月""80%程序员""全扔了") | 身份标签(普通人/转型者/老板)}。题里有强名词就必须顶到标题最前，别翻译掉、别模糊化(反例:讲Claude Code却写"一个载入史册的产品")。
- **句式默认疑问 / 反问 / 反认知断言，禁平陈述**。同赛道高赞几乎全是疑问句。反例(陈述)"AI Native是一把手工程"；正例"为什么AI Native做不起来？十个有九个老板没亲自下场"。
- **能挂张和独家流量锚就挂**：前小米AI实验室早期员工 / AI出海公司CEO / 一线用Claude Code+Codex。这是别人没有的权威背书。
- title 给最终钩子式标题(不是话题陈述)；hook_line 仍是逐字稿里张和真原话。

【in/out 点纪律(关键)】
- 口播是张和原声，改不了内容，但你能选 in/out。
- in 点：切到 hook_line 那句之前，丢掉"他现在就是…可能还没那么完美""对吧那么第二步"这种软开场。
- out 点：论点说完就收，不要拖到他转下个话题。
- 允许跳接：一条候选可由 2-3 个不连续 segment 拼成(中间砍废话)，但拼接后逻辑要顺、按时间顺序。

【每条候选字段】
- title: 钩子式标题，不是陈述。反例(陈述)"Cloud Code是足以载入史册的产品"；正例(钩子)"我把过去三年给客户做的AI方案，全扔了"。
- one_argument: 一句话——这条唯一要观众记住的观点。
- segments: [{"start":"mm:ss","end":"mm:ss"}]，in 点已切到炸点前。
- hook_line: 当 0-3 秒的那句张和原话(逐字稿里真有的)。
- mainstream: "高"/"中"/"低"——大众流量潜力自评。低的要给合并/降级理由。
- audience: 这条主要打谁(破圈大众/AI从业者/创业者老板/转型求职)。
- why: 为什么会被传播 / 记忆点是什么。
- duration_sec: 估算时长(秒)。

【数量】
一场逐字稿挑 6-12 条精的即可，按 mainstream 高→低排序输出。低流量 insider 话题除非特别锋利，否则不出。

【输出 JSON】
{"clips":[{"title":"...","one_argument":"...","segments":[{"start":"09:50","end":"10:44"}],"hook_line":"...","mainstream":"高","audience":"...","why":"...","duration_sec":84}]}
只输出这个 JSON 对象。"""


def transcript_from_minutes(mj_path: str | Path) -> str:
    data = json.loads(Path(mj_path).read_text(encoding="utf-8"))
    paras = data["minutes"]["paragraphs"]
    lines = []
    for p in paras:
        ms = p.get("start_time", 0)
        mm, ss = divmod(int(ms) // 1000, 60)
        txt = "".join(w.get("text", "") for s in p.get("sentences", []) for w in s.get("words", []))
        if txt.strip():
            lines.append(f"[{mm:02d}:{ss:02d}] {txt.strip()}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("minutes")
    ap.add_argument("--out", default=None)
    ap.add_argument("--providers", default="kimi,minimax")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    transcript = transcript_from_minutes(a.minutes)
    client = OpenAICompatibleClient(providers=a.providers.split(","))
    data = client.chat_json(
        [{"role": "system", "content": SELECT_SYSTEM_PROMPT},
         {"role": "user", "content": transcript}],
        temperature=0.2,
    )
    clips = data.get("clips", [])
    blob = json.dumps({"clips": clips}, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(blob + "\n", encoding="utf-8")
        print(f"写出 {len(clips)} 条候选 → {a.out}")
    else:
        print(blob)


if __name__ == "__main__":
    main()
