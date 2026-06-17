#!/usr/bin/env python3
"""全局取证 · 金标准切片脚本生成器（评测基准这条线 · 不进生产管线）。

问题：现有两阶段里 stage2 只在选题落点 ±6 句的小窗口里挑句（stage2_script.py:WINDOW_PAD=6），
看不到张和在全场别处对同一观点更有力的复述/举例。本脚本反过来：

  对每条**已选定选题**，把张和**整场 3 小时逐字稿**喂给一个 AI，让它在全局范围取证，
  按【论证结构】(钩子→核心论点→全场最有力的论据/举例→收尾)精选组装成一条高质量脚本。

口径：论证结构化精选（不是穷尽堆料）。跨选题之间允许内容重复，但单条内部不堆砌、控时长。
铁律：AI 只能引用真实句号、不得编造/改写——产出是一串句号区间，可校验、可经 resolve 换算成秒剪片。
定稿：本脚本只产**候选**(human_status=pending)；人工筛选拍定后才成金标准 golden.json。

句号索引复用生产线同一个 segment.sentences_from_wordfile，sid↔时间 与 _selection.json 完全一致。

用法:
  python global_evidence.py \\
      --words   var/zh_main/asr/agent_eval_0613/words.json \\
      --selection var/zh_main/cuts/agent全量-volc-native/_selection.json \\
      --out     var/zh_main/eval/agent_eval_0613 \\
      [--persona zh_main] [--providers kimi,minimax] [--limit N] [--host 张和]

产出（落 --out）:
  golden_candidate.json          全部候选（人工定稿前；human_status=pending）
  candidates/clip_NN_<slug>.md   每条一份人工评审稿（方便逐条留/删/改）
  _run.log                       本次运行摘要
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

# baselines/ 上溯到引擎根（含 video_slicer 包），与 select_clips.py 同款无硬编码路径。
_ENGINE = str(Path(__file__).resolve().parent.parent)
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402
from video_slicer.transcribe import segment  # noqa: E402
from video_slicer.twostage.stage1_topics import load_persona  # noqa: E402

_ROLES = {"hook", "argument", "evidence", "closing"}

# ───────────────────────── 提示词（质量核心杠杆 · prompt 迭代主战场）─────────────────────────
GLOBAL_EVIDENCE_TASK = """\
【你的任务 · 全局取证定金标准脚本】
下面给你一条【已选定的选题】+ 张和这场直播的【全场编号句】（每行 `#句号 文本`，按时间顺序；句号是稳定锚点）。
这条选题"选什么"已经定了，**你不要质疑或更换选题**。你的唯一任务：在【全场】范围内，为这条选题挑出能把它讲到最好的张和原话，组装成一条高质量短视频脚本。

【与旧做法的根本区别——这是关键】
不要只盯选题落点附近那一段。张和经常在全场不同位置**反复讲同一个观点、给更好的例子、说更狠的金句**——你要把全场都扫一遍，跨位置取证，把散落各处最有力的原话聚到一条里。

【论证结构（按结构精选，不是堆料）】
一条好切片 = 钩子(hook) + 核心论点(argument) + 全场最有力的 1-2 个论据/举例(evidence) + 收尾(closing，可省)：
- hook：0-3 秒抓人的那句张和原话（反认知 / 戳痛 / 疑问）。
- argument：把这条选题的唯一观点一句话立住。
- evidence：从**全场任意位置**调取最有说服力的论据、案例、数据、金句（允许跨越很远的句号——这就是全局取证的价值）。
- closing：一句收口或升华（没有合适的就不要）。

【钩子纪律（最关键·常犯错）】
- 钩子**第一句就要是反认知 / 戳痛 / 疑问的爆点**。**砍掉开头一切软铺垫和承接语**——如"还有一个最近的认知分享就是""我要给大家讲一下""然后就是刚才我说的""其实""我跟大家讲""那个/这个"这类填充词，绝不能留在钩子开头。
- 若爆点句本身前面挂了一截铺垫（同一句里），就把该句选进来、但在 reason 里注明"钩子从'……'这几个字起念"，让定稿的人知道砍到哪。被砍掉的铺垫可以移作 argument 的第一句。
- 钩子若太弱，**多给 1-2 个备选**：在 segments 里把次选钩子标 role=hook 多放一个，或在 reason 写"备选钩子：句号X"。
- **禁止串味**：钩子必须是张和**就这条选题本身**说的话，绝不能因为某句够炸就从别的话题搬过来（如别条切片的招牌金句）。钩子要能自然引出本条的核心论点。

【反串味（每段都要守）】
- 每一段都必须服务**这一条选题的论点**。张和全场讲很多话题，你只能取真正在论证/支撑本选题的原话；够炸但属于别的话题的句子，不要拿。

【结尾纪律】
- 收尾必须落在一句**完整、有力**的话上。**绝不能停在半截或拖尾**——结尾段尾部若是"包括这个""然后……"、孤立的"嗯/啊"、没说完的从句，要把这些尾巴砍掉，收在前一句完整有力处。

【通用纪律】
- 只能引用给你的真实句号，**绝对不要编造句号、不要改写文字**。挑不出合适内容就少挑、宁缺毋滥。
- 每段是一个连续句号闭区间 [起句号, 止句号]；多段 = 跳接，砍掉中间废话，但每段内部要语义完整。
- 控制总时长约 60–120 秒（宁精勿长）；跨选题之间内容可重复，但**单条内部不许注水堆砌**。
- segments **按论证逻辑顺序排**（hook 在前，哪怕它在全场时间上靠后），不必按时间先后。

【输出严格 JSON，无 markdown】
{"segments":[
  {"role":"hook|argument|evidence|closing", "sids":[起句号, 止句号], "reason":"为什么选这段（一句话）"}
], "title_suggestion":"（可选）若你发现比原标题更好的钩子式标题，否则留空"}
只输出这个 JSON 对象。"""


def load_topics(selection_path: str | Path) -> list[dict]:
    """从 _selection.json 读已选定的选题（选什么已定，本脚本只重做"选哪些原话"）。"""
    data = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    return data.get("clips", [])


def render_full(sents) -> str:
    """全场编号句（喂给 AI 的取证语料）。单说话人口播，只列句号+文本，省 token。"""
    return "\n".join(f"#{s.sid} {s.text}" for s in sents)


def _clean_segments(raw_segments, sents) -> list[dict]:
    """校验 AI 回的 segments：丢非法/编造句号，钳进合法范围，回填文本+时间。"""
    max_sid = sents[-1].sid if sents else -1
    out: list[dict] = []
    for seg in raw_segments or []:
        if not isinstance(seg, dict):
            continue
        sids = seg.get("sids")
        if not isinstance(sids, list) or len(sids) < 2:
            continue
        try:
            a, b = int(sids[0]), int(sids[-1])
        except (TypeError, ValueError):
            continue
        if a > b:
            a, b = b, a
        a, b = max(0, a), min(max_sid, b)          # 钳进合法范围（防越界/编造）
        if a > b:
            continue
        role = seg.get("role", "evidence")
        if role not in _ROLES:
            role = "evidence"
        text = "".join(sents[sid].text for sid in range(a, b + 1))
        out.append({
            "role": role,
            "sids": [a, b],
            "span": [round(sents[a].start, 2), round(sents[b].end, 2)],  # 秒
            "text": text,
            "reason": str(seg.get("reason", ""))[:200],
        })
    return out


def select_evidence(topic: dict, sents, persona_text: str, full_view: str,
                    providers=None, temperature: float = 0.3) -> dict:
    """单条选题 → 全局取证 → 论证结构化 segments（校验+回填时间后的结构化结果）。"""
    brief = (
        f"【已选定选题】\n"
        f"标题：{topic.get('title','')}\n"
        f"核心论点(one_argument)：{topic.get('one_argument','')}\n"
        f"钩子原话(hook_line)：{topic.get('hook_line','')}\n"
        f"受众：{topic.get('audience','')} ｜ 流量潜力：{topic.get('mainstream','')}\n\n"
        f"【全场编号句】\n{full_view}"
    )
    client = OpenAICompatibleClient(providers=providers)
    data = client.chat_json(
        [
            {"role": "system", "content": persona_text + "\n\n" + GLOBAL_EVIDENCE_TASK},
            {"role": "user", "content": brief},
        ],
        temperature=temperature,
    )
    segments = _clean_segments(data.get("segments", []), sents)
    keep_sids = [seg["sids"] for seg in segments]
    time_spans = [seg["span"] for seg in segments]
    est_dur = round(sum(e - s for s, e in time_spans), 1)
    script = "\n".join(seg["text"] for seg in segments)
    return {
        "title": topic.get("title", ""),
        "one_argument": topic.get("one_argument", ""),
        "hook_line": topic.get("hook_line", ""),
        "audience": topic.get("audience", ""),
        "mainstream": topic.get("mainstream", ""),
        "title_suggestion": str(data.get("title_suggestion", "")).strip(),
        "orig_keep_sids": topic.get("keep_sids", []),   # 旧局部窗口结果，留作对照
        "segments": segments,
        "keep_sids": keep_sids,                          # 扁平区间，喂 cut 管线用
        "time_spans": time_spans,
        "est_dur": est_dur,
        "script": script,
        "human_status": "pending",                       # 人工定稿：pending|keep|cut|edited
    }


def _slug(s: str, n: int = 24) -> str:
    keep = "".join(c for c in (s or "") if c.isalnum() or c in "（）()·-_") [:n]
    return keep or "clip"


def write_review_md(out: Path, idx: int, clip: dict) -> None:
    """每条一份人工评审稿：结构清晰，方便逐条留/删/改。"""
    d = out / "candidates"; d.mkdir(parents=True, exist_ok=True)
    role_cn = {"hook": "钩子", "argument": "核心论点", "evidence": "论据/举例", "closing": "收尾"}
    lines = [
        f"# {idx:02d}. {clip['title']}",
        "",
        f"- **核心论点**：{clip['one_argument']}",
        f"- **原钩子**：{clip['hook_line']}",
        f"- **受众/流量**：{clip['audience']} ｜ {clip['mainstream']}",
        f"- **估时**：{clip['est_dur']}s ｜ 段数：{len(clip['segments'])}",
    ]
    if clip["title_suggestion"]:
        lines.append(f"- **AI 建议新标题**：{clip['title_suggestion']}")
    lines += ["", "## 全局取证 · 论证结构", ""]
    for seg in clip["segments"]:
        s, e = seg["span"]
        lines += [
            f"### [{role_cn.get(seg['role'], seg['role'])}] 句号 {seg['sids'][0]}–{seg['sids'][1]}  "
            f"（{s:.1f}–{e:.1f}s）",
            f"> {seg['text']}",
            f"*取证理由：{seg['reason']}*",
            "",
        ]
    lines += [
        "## 组装后脚本（候选）", "", clip["script"], "",
        "---",
        "## 人工定稿（在此处改）",
        "- 状态（留 keep / 删 cut / 改 edited）：**pending**",
        "- 备注：",
        "",
        f"> 对照·旧局部窗口选段句号：{clip['orig_keep_sids']}",
    ]
    (d / f"clip_{idx:02d}_{_slug(clip['title'])}.md").write_text("\n".join(lines), encoding="utf-8")


def run(words_json: str, selection_json: str, out_dir: str, persona: str = "zh_main",
        host: str = "张和", providers=None, limit=None) -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    _, sents = segment.sentences_from_wordfile(words_json, host=host)
    persona_text = load_persona(persona)
    topics = load_topics(selection_json)
    if limit:
        topics = topics[:limit]
    full_view = render_full(sents)
    print(f"[全局取证] {len(sents)} 句 / {len(topics)} 选题 / 语料 {len(full_view)} 字", file=sys.stderr)

    clips, log = [], []
    for i, topic in enumerate(topics, 1):
        title = topic.get("title", f"clip{i}")
        print(f"  ({i}/{len(topics)}) {title[:28]}…", file=sys.stderr)
        try:
            clip = select_evidence(topic, sents, persona_text, full_view, providers=providers)
        except Exception as ex:  # noqa: BLE001  每条独立容错：一条失败不拖累整批
            print(f"      ✗ 失败跳过：{str(ex)[:160]}", file=sys.stderr)
            log.append(f"{i:02d} ✗ {title} :: {str(ex)[:160]}")
            continue
        clips.append(clip)
        write_review_md(out, i, clip)
        log.append(f"{i:02d} ✓ {title} :: {len(clip['segments'])}段 {clip['est_dur']}s")

    golden = {
        "source_words": str(words_json),
        "selection": str(selection_json),
        "persona": persona, "host": host,
        "method": "global_evidence/论证结构化精选",
        "human_status": "pending",       # 整体定稿状态
        "clips": clips,
    }
    (out / "golden_candidate.json").write_text(
        json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "_run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"[done] 候选 {len(clips)} 条 → {out}/golden_candidate.json", file=sys.stderr)
    return golden


def main() -> int:
    ap = argparse.ArgumentParser(prog="global_evidence",
                                 description="全局取证·金标准切片脚本生成器（评测基准，不进生产）")
    ap.add_argument("--words", required=True, help="火山字级词表 words.json（含原生 sentences）")
    ap.add_argument("--selection", required=True, help="已选定选题 _selection.json")
    ap.add_argument("--out", required=True, help="产物目录（建议 var/<account>/eval/<run>）")
    ap.add_argument("--persona", default="zh_main")
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    ap.add_argument("--limit", type=int, default=None, help="只跑前 N 条选题（先小跑省钱）")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    run(a.words, a.selection, a.out, persona=a.persona, host=a.host,
        providers=providers, limit=a.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
