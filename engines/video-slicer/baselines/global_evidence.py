#!/usr/bin/env python3
"""全局取证 · 金标准切片脚本生成器（评测基准这条线 · 不进生产管线）。

问题：现有两阶段里 stage2 只在选题落点 ±6 句的小窗口里挑句（stage2_script.py:WINDOW_PAD=6），
看不到张和在全场别处对同一观点更有力的复述/举例。本脚本反过来：对每条**已选定选题**，把张和
**整场逐字稿**喂给 AI 在全局取证，按论证结构精选组装。

一条 clip 的四级流水线（钩子单独拎出来，只有一个出处）：
  ① 开场钩子   短·炸·可跨句抠片段拼接（gen_hook_options）——钩子唯一来源
  ② 正文·论证结构  论点/论据/收尾（select_body·全局取证）——句号可回查时间
  ③ 组装脚本   ②各段原话原始拼接（带口水）
  ④ 精修脚本   去口水/去重复/开篇独立/结尾干脆（refine_script，只删理顺不改写实质）
  → 人工定稿   挑一个钩子 + 核对精修忠实度 + 拍板

口径：论证结构化精选（不堆料）。铁律：②只引真实句号、可经 resolve 换算成秒；①每片段标 sid 可校验；
④允许调语序/合并但只用原话出现过的字词、不新增观点（③原始版并排留着供核对）。
句号索引复用生产线同一个 segment.sentences_from_wordfile，sid↔时间 与 _selection.json 完全一致。

用法:
  python global_evidence.py --words words.json --selection _selection.json --out <dir> \\
      [--persona zh_main] [--providers kimi,minimax] [--limit N] [--only 6-22] [--migrate]
  --migrate：不重跑正文，对已存 golden_candidate.json 的每条补①钩子+④精修+换新版式（保留人工定稿区）。

产出（落 --out）：golden_candidate.json + candidates/clip_NN_<slug>.md + _run.log
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

_ENGINE = str(Path(__file__).resolve().parent.parent)
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)
from video_slicer.llm import OpenAICompatibleClient  # noqa: E402
from video_slicer.cli import load_env_file, _discover_env_file  # noqa: E402
from video_slicer.transcribe import segment  # noqa: E402
from video_slicer.twostage.stage1_topics import load_persona  # noqa: E402

BODY_ROLES = {"argument", "evidence", "closing"}   # 正文角色；钩子不在正文里，单独生成

# ═══════════════════════ ② 正文·全局取证（提示词=质量核心杠杆）═══════════════════════
BODY_TASK = """\
【你的任务 · 全局取证定正文】
下面给你一条【已选定的选题】+ 张和这场直播的【全场编号句】（每行 `#句号 文本`；句号是稳定锚点）。
选题"选什么"已定，**不要质疑或更换**。你只产**正文**（论点→论据→收尾），**不要产钩子**（钩子另有专门步骤生成）。

【与旧做法的根本区别】
不要只盯选题落点附近。张和常在全场不同位置反复讲同一观点、给更好的例子——你要扫全场，跨位置取证，把散落各处最有力的原话聚到一条里。

【正文结构】
- argument：把这条选题的唯一观点一句话立住（这是正文第一句，不必是钩子）。
- evidence：从**全场任意位置**调取最有说服力的论据/案例/数据/金句（允许跨很远句号——这就是全局取证的价值）。
- closing：一句收口或升华（没有合适的就不要）。

【反串味】每一段都必须服务**这一条选题的论点**；够炸但属于别话题的句子不要拿。
【结尾纪律】closing 落在完整有力的话上，不要停在半截或拖尾（后续精修还会再收一遍）。
【通用纪律】
- 只能引用真实句号，**不要编造句号、不要改写文字**。挑不出就少挑。
- 每段是连续句号闭区间 [起,止]；多段=跳接。
- **每段短而准**：尽量 ~6 句以内，只取最锋利几句，**禁止一段圈几十句照搬**。
- 总时长约 60–120 秒；单条内部不堆砌。按论证逻辑顺序排。

【输出严格 JSON，无 markdown】
{"segments":[{"role":"argument|evidence|closing","sids":[起,止],"reason":"为什么选这段（一句话）"}],
 "title_suggestion":"（可选）更好的钩子式标题，否则留空"}
只输出这个 JSON 对象。"""

# ═══════════════════════ ① 开场钩子（几个短句拼成一个顺口句子·戳点·中受众·露答案）═══════════════════════
HOOK_TASK = """\
给你一条切片的【论点 + 目标受众】+ 候选原话句（每行 `#句号 文本`）。设计 2-3 个开场钩子候选，按吸引力从高到低排。

【钩子三要素（缺一不可）】
1. **戳中痛点**：直接戳目标受众最痛/最焦虑的那个点。
2. **中目标用户**：让"目标受众"一听就觉得"说的就是我"。
3. **让人看到答案**：钩子里要露出反转/答案/能得到什么——不是只抛个悬念吊着。

【形态·关键（别拆太碎）】
- 一个钩子 = **一个完整、顺口的句子**，由**几个短句**自然拼成、连起来读是流畅的一整句话——**不是蹦字、不是碎片硬拼**。
- 从原话里挑**几个短句**（每个短句是一个有意义的短语/小句，不是单个词）拼成这一句；砍掉"啊/然后/就是/这个"等口水和承接词。
- 反着说：不要把好几整句硬塞压成一个碎片，也不要把碎片再硬拼；目标是"**几个短句 → 一个句子**"。
- 允许直接用张和这条选题的招牌原话当钩子（如果候选句里有那种一句就立住的金句，优先用它）。

【铁律】每个片段 text 必须是给你的某句号原话里**一字不差**的连续子串；stitched 是这些短句拼成的顺口句子（可加极少量衔接字，但原话以片段为准），不得编造、不得跨到没给你的句子。
【输出严格 JSON】{"hooks":[{"fragments":[{"sid":句号,"text":"原话短句"}],"stitched":"几个短句拼成的顺口钩子句","why":"怎么同时做到戳点/中受众/露答案"}]}
只输出这个 JSON 对象。"""

# ═══════════════════════ ④ 精修（去口水/去重复/开篇独立/结尾干脆）═══════════════════════
REFINE_TASK = """\
对下面这段张和原话做【精修】，产出能直接当短视频成片用的正文脚本。这段是从一场长直播里切出来的，按短视频标准收拾干净：
【必须做】
1. 去口水：删"啊/嗯/这个/那个/然后/就是/对吧/你知道吧"等口头禅与口吃；同一句重说的只留一遍最顺的。
2. 去重复+顺语序：把反复绕回、表达同一意思的几句合并成一句最利落的，语序可调整让它通顺。
3. 开篇独立：第一句**不能承接上文**。原素材开头常有"就是他…""然后…""还有一个…"这类接上面内容的承接/转折词——剪掉，让第一句自己立得住。
4. 结尾干脆：结尾**不要像没讲完、还在引导往下听**（如"那接下来…""这个我们后面再说…""听懂了吗我们继续…"），收在一句完整有力的话上。
【铁律】只能用原话里**出现过的字词**，**不得新增观点、不得改写措辞的实质含义、不得编造**——你是在"删和理顺"，不是重写。保留张和口吻和关键金句。
【输出严格 JSON】{"refined":"精修后的脚本纯文本"}
只输出这个 JSON 对象。"""


def load_topics(selection_path: str | Path) -> list[dict]:
    data = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    return data.get("clips", [])


def render_full(sents) -> str:
    return "\n".join(f"#{s.sid} {s.text}" for s in sents)


def _chat_json_retry(client, msgs, temperature):
    try:
        return client.chat_json(msgs, temperature=temperature)
    except Exception:  # noqa: BLE001  长稿偶发 JSON 截断/超时，重试一次
        return client.chat_json(msgs, temperature=temperature)


def _clean_segments(raw_segments, sents) -> list[dict]:
    """校验 AI 回的正文 segments：丢非法/编造句号，钳进合法范围，回填文本+时间。"""
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
        a, b = max(0, a), min(max_sid, b)
        if a > b:
            continue
        role = seg.get("role", "evidence")
        if role not in BODY_ROLES:
            role = "evidence"
        text = "".join(sents[sid].text for sid in range(a, b + 1))
        out.append({"role": role, "sids": [a, b],
                    "span": [round(sents[a].start, 2), round(sents[b].end, 2)],
                    "text": text, "reason": str(seg.get("reason", ""))[:200]})
    return out


def select_body(topic: dict, sents, persona_text: str, full_view: str,
                providers=None, temperature: float = 0.3) -> tuple[list[dict], dict]:
    """② 全局取证 → 正文 segments（论点/论据/收尾，无钩子）。"""
    brief = (f"【已选定选题】\n标题：{topic.get('title','')}\n"
             f"核心论点(one_argument)：{topic.get('one_argument','')}\n"
             f"钩子原话参考(hook_line)：{topic.get('hook_line','')}\n"
             f"受众：{topic.get('audience','')} ｜ 流量潜力：{topic.get('mainstream','')}\n\n"
             f"【全场编号句】\n{full_view}")
    client = OpenAICompatibleClient(providers=providers)
    data = _chat_json_retry(client, [
        {"role": "system", "content": persona_text + "\n\n" + BODY_TASK},
        {"role": "user", "content": brief}], temperature)
    body = _clean_segments(data.get("segments", []), sents)
    return body, {"title_suggestion": str(data.get("title_suggestion", "")).strip()}


def _sentence_view(sents, body, extra_spans=None) -> str:
    """钩子候选池：正文覆盖句(±3) ∪ 选题原始选段区(orig_keep_sids, ±2)，逐句列出。
    纳入 orig 区是因为很多选题的招牌钩子句在正文取证段之外（如"传统脚本已死"在全场很早处），
    但 orig 区仍是这条选题自己的地盘，不会串到别的话题。"""
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


def gen_hook_options(core: dict, body, sents, persona_text: str, providers=None) -> list[dict]:
    """① 钩子候选（几个短句拼成一个顺口句子；候选池含正文区+选题原始选段区）。"""
    if not body:
        return []
    view = _sentence_view(sents, body, extra_spans=core.get("orig_keep_sids"))
    user = (f"标题：{core['title']}\n论点：{core['one_argument']}\n"
            f"目标受众：{core.get('audience','')}\n\n【候选原话句】\n{view}")
    client = OpenAICompatibleClient(providers=providers)
    data = _chat_json_retry(client, [
        {"role": "system", "content": persona_text + "\n\n" + HOOK_TASK},
        {"role": "user", "content": user}], 0.4)
    out = []
    for h in data.get("hooks", []) or []:
        frags = []
        for fr in h.get("fragments", []) or []:
            txt = (fr.get("text") or "").strip()
            rng = _parse_sid_range(fr.get("sid"))     # 容错：AI 可能把 sid 给成区间"761-763"
            if not txt or rng is None:
                continue
            a, b = rng
            if not (0 <= a <= b < len(sents)):
                continue
            src = "".join(sents[i].text for i in range(a, b + 1))   # 区间原文（跨句短句也能校验）
            sid_disp = a if a == b else f"{a}-{b}"
            frags.append({"sid": sid_disp, "text": txt, "verbatim": txt in src})
        if not frags:
            continue
        stitched = (h.get("stitched") or "".join(f["text"] for f in frags)).strip()
        out.append({"stitched": stitched, "fragments": frags, "why": str(h.get("why", ""))[:200]})
    return out


def refine_script(raw_script: str, core: dict, providers=None) -> str:
    """④ 精修：去口水/去重复/开篇独立/结尾干脆（只删理顺，不改写实质）。"""
    if not raw_script.strip():
        return ""
    user = f"选题：{core['title']}\n论点：{core['one_argument']}\n\n【待精修正文（原始拼接）】\n{raw_script}"
    client = OpenAICompatibleClient(providers=providers)
    data = _chat_json_retry(client, [
        {"role": "system", "content": REFINE_TASK},
        {"role": "user", "content": user}], 0.3)
    return str(data.get("refined", "")).strip()


def finalize_clip(core: dict, body: list[dict], sents, persona_text: str, providers=None,
                  steps=("hooks", "refine"), prev: dict | None = None) -> dict:
    """正文 segments → 完整 clip：补①钩子候选 + ③组装 + ④精修。
    steps 控制重算哪些 LLM 步骤（其余沿用 prev）：如 --hooks-only 只重钩子、保留已有精修。"""
    prev = prev or {}
    keep_sids = [s["sids"] for s in body]
    time_spans = [s["span"] for s in body]
    est_dur = round(sum(e - s for s, e in time_spans), 1)
    script_raw = "\n".join(s["text"] for s in body)
    hook_options = (gen_hook_options(core, body, sents, persona_text, providers=providers)
                    if "hooks" in steps else prev.get("hook_options", []))
    script_refined = (refine_script(script_raw, core, providers=providers)
                      if "refine" in steps else prev.get("script_refined", ""))
    clip = dict(core)
    clip.update({"hook_options": hook_options, "segments": body, "keep_sids": keep_sids,
                 "time_spans": time_spans, "est_dur": est_dur,
                 "script_raw": script_raw, "script_refined": script_refined,
                 "human_status": core.get("human_status", "pending")})
    return clip


def _slug(s: str, n: int = 24) -> str:
    keep = "".join(c for c in (s or "") if c.isalnum() or c in "（）()·-_")[:n]
    return keep or "clip"


HUMAN_HEADER = "## 人工定稿（在此处改）"


def write_review_md(out: Path, idx: int, clip: dict, human_block: str | None = None) -> None:
    """四级流水线版式：①开场钩子 ②正文论证结构 ③组装脚本 ④精修脚本 → 人工定稿。"""
    d = out / "candidates"; d.mkdir(parents=True, exist_ok=True)
    role_cn = {"argument": "核心论点", "evidence": "论据/举例", "closing": "收尾"}
    L = [f"# {idx:02d}. {clip['title']}", "",
         f"- **核心论点**：{clip['one_argument']}",
         f"- **受众/流量**：{clip.get('audience','')} ｜ {clip.get('mainstream','')}",
         f"- **正文估时(精修前)**：{clip['est_dur']}s ｜ 正文段数：{len(clip['segments'])}"]
    if clip.get("title_suggestion"):
        L.append(f"- **AI 建议新标题**：{clip['title_suggestion']}")
    L.append(f"- **原钩子(参考)**：{clip.get('hook_line','')}")

    L += ["", "## ① 开场钩子（短·炸·挑一个；钩子唯一出处）",
          "（**拟稿**=可能重排/加衔接，**原话以片段为准**；⚠=该片段非逐字子串需人工核对）", ""]
    if clip.get("hook_options"):
        for h in clip["hook_options"]:
            srcs = " + ".join(f"#{f['sid']}「{f['text']}」" + ("" if f["verbatim"] else "⚠")
                              for f in h["fragments"])
            verbatim_join = "".join(f["text"] for f in h["fragments"])
            L.append(f"- 拟稿：**{h['stitched']}**")
            L.append(f"  - 原话拼接：{verbatim_join}")
            L.append(f"  - 片段：{srcs}")
            if h["why"]:
                L.append(f"  - 理由：{h['why']}")
    else:
        L.append("-（未生成，待补）")

    L += ["", "## ② 正文 · 论证结构（取证依据·句号可回查时间·不含钩子）", ""]
    for s in clip["segments"]:
        a, b = s["span"]
        L += [f"### [{role_cn.get(s['role'], s['role'])}] 句号 {s['sids'][0]}–{s['sids'][1]}（{a:.1f}–{b:.1f}s）",
              f"> {s['text']}", f"*取证理由：{s.get('reason','')}*", ""]

    L += ["## ③ 组装脚本（原始拼接·带口水·未删）", "", "〔开场：从 ① 挑一个钩子〕", clip["script_raw"], ""]
    L += ["## ④ 精修脚本（去口水/去重复/开篇独立/结尾干脆·待人工核对忠实度）", "",
          "〔开场：从 ① 挑一个钩子〕", clip.get("script_refined") or "（未生成）", "", "---"]

    if human_block:
        L.append(human_block.rstrip())
    else:
        L += [HUMAN_HEADER, "- 选定钩子：", "- 状态（留 keep / 删 cut / 改 edited）：**pending**",
              "- 备注：", "", f"> 对照·旧局部窗口选段句号：{clip.get('orig_keep_sids','')}"]
    (d / f"clip_{idx:02d}_{_slug(clip['title'])}.md").write_text("\n".join(L), encoding="utf-8")


def _core_from_topic(topic: dict) -> dict:
    return {"title": topic.get("title", ""), "one_argument": topic.get("one_argument", ""),
            "hook_line": topic.get("hook_line", ""), "audience": topic.get("audience", ""),
            "mainstream": topic.get("mainstream", ""), "orig_keep_sids": topic.get("keep_sids", []),
            "human_status": "pending"}


def _parse_only(only: str | None) -> set[int] | None:
    if not only:
        return None
    only = only.strip()
    if "-" in only:
        a, b = only.split("-", 1)
        return set(range(int(a), int(b) + 1))
    return {int(only)}


def _existing_human_block(out: Path, idx: int) -> str | None:
    """迁移时保留人工定稿区（尤其用户已写的反馈）。"""
    for p in (out / "candidates").glob(f"clip_{idx:02d}_*.md"):
        m = re.search(re.escape(HUMAN_HEADER) + r".*", p.read_text(encoding="utf-8"), re.DOTALL)
        if m:
            return m.group(0)
    return None


def _write_golden(out: Path, by_idx: dict, words_json, selection_json, persona, host, log):
    clips = [by_idx[i] for i in sorted(by_idx)]
    golden = {"source_words": str(words_json), "selection": str(selection_json),
              "persona": persona, "host": host, "method": "global_evidence/四级流水线",
              "human_status": "pending", "clips": clips}
    (out / "golden_candidate.json").write_text(json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "_run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    return golden


def run(words_json, selection_json, out_dir, persona="zh_main", host="张和",
        providers=None, limit=None, only=None) -> dict:
    """全新生成：每条做 ②正文 + ①钩子 + ④精修。--only 合并进已存 golden。"""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    _, sents = segment.sentences_from_wordfile(words_json, host=host)
    persona_text = load_persona(persona)
    topics = load_topics(selection_json)
    if limit:
        topics = topics[:limit]
    want = _parse_only(only)
    full_view = render_full(sents)
    todo = [i for i in range(1, len(topics) + 1) if want is None or i in want]
    print(f"[全局取证] {len(sents)}句 / 处理{len(todo)}条(共{len(topics)}) / 语料{len(full_view)}字", file=sys.stderr)

    gpath = out / "golden_candidate.json"
    by_idx: dict[int, dict] = {}
    if want is not None and gpath.exists():
        for pos, c in enumerate(json.loads(gpath.read_text(encoding="utf-8")).get("clips", []), 1):
            c["idx"] = c.get("idx") or pos
            by_idx[c["idx"]] = c
    log = []
    for i in todo:
        topic = topics[i - 1]; title = topic.get("title", f"clip{i}")
        print(f"  ({i}/{len(topics)}) {title[:26]}…", file=sys.stderr)
        try:
            body, extra = select_body(topic, sents, persona_text, full_view, providers=providers)
            core = _core_from_topic(topic); core.update(extra)
            clip = finalize_clip(core, body, sents, persona_text, providers=providers)
        except Exception as ex:  # noqa: BLE001
            print(f"      ✗ {str(ex)[:150]}", file=sys.stderr); log.append(f"{i:02d} ✗ {title}"); continue
        clip["idx"] = i; by_idx[i] = clip
        write_review_md(out, i, clip)
        log.append(f"{i:02d} ✓ {title} :: 正文{len(body)}段/{clip['est_dur']}s 钩子{len(clip['hook_options'])}个")
    golden = _write_golden(out, by_idx, words_json, selection_json, persona, host, log)
    print(f"[done] 共{len(golden['clips'])}条（重跑{len(todo)}）→ {gpath}", file=sys.stderr)
    return golden


def migrate(words_json, out_dir, persona="zh_main", host="张和", providers=None, only=None,
            steps=("hooks", "refine")) -> dict:
    """不重跑正文：对已存 golden 每条，拆掉旧钩子段→正文，重算 steps 指定的步骤（其余沿用旧值），
    换新版式，保留人工定稿区。steps=('hooks',) 即只重钩子。"""
    out = Path(out_dir)
    gpath = out / "golden_candidate.json"
    if not gpath.exists():
        raise FileNotFoundError(f"没有可迁移的 {gpath}")
    _, sents = segment.sentences_from_wordfile(words_json, host=host)
    persona_text = load_persona(persona)
    want = _parse_only(only)
    src = json.loads(gpath.read_text(encoding="utf-8"))
    by_idx: dict[int, dict] = {}
    log = []
    for pos, c in enumerate(src.get("clips", []), 1):
        idx = c.get("idx") or pos
        if want is not None and idx not in want:
            by_idx[idx] = c; continue            # 不在范围：原样保留
        # 拆钩子：旧 segments 里 role!=hook 的即正文；时间从 sents 回填（旧 span 已带）
        body = [s for s in c.get("segments", []) if s.get("role") != "hook"]
        for s in body:
            s.setdefault("reason", "")
        core = {"title": c.get("title", ""), "one_argument": c.get("one_argument", ""),
                "hook_line": c.get("hook_line", ""), "audience": c.get("audience", ""),
                "mainstream": c.get("mainstream", ""), "orig_keep_sids": c.get("orig_keep_sids", []),
                "title_suggestion": c.get("title_suggestion", ""), "human_status": c.get("human_status", "pending")}
        print(f"  ({idx}) {core['title'][:26]}… 正文{len(body)}段 [{'+'.join(steps)}]", file=sys.stderr)
        try:
            clip = finalize_clip(core, body, sents, persona_text, providers=providers, steps=steps, prev=c)
        except Exception as ex:  # noqa: BLE001
            print(f"      ✗ {str(ex)[:150]}", file=sys.stderr); by_idx[idx] = c; log.append(f"{idx:02d} ✗"); continue
        clip["idx"] = idx; by_idx[idx] = clip
        write_review_md(out, idx, clip, human_block=_existing_human_block(out, idx))
        log.append(f"{idx:02d} ✓ 正文{len(body)}段 钩子{len(clip['hook_options'])}个 精修{len(clip['script_refined'])}字")
    golden = _write_golden(out, by_idx, src.get("source_words", words_json),
                           src.get("selection", ""), persona, host, log)
    print(f"[migrate done] {len(golden['clips'])}条 → {gpath}", file=sys.stderr)
    return golden


def main() -> int:
    ap = argparse.ArgumentParser(prog="global_evidence", description="全局取证·金标准四级流水线（评测基准，不进生产）")
    ap.add_argument("--words", required=True)
    ap.add_argument("--selection", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--persona", default="zh_main")
    ap.add_argument("--host", default="张和")
    ap.add_argument("--providers", default="kimi,minimax")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", default=None, help="只处理这些选题序号（如 6-22 或 8）")
    ap.add_argument("--migrate", action="store_true",
                    help="不重跑正文：对已存 golden 补①钩子+④精修+换新版式（保留人工定稿区）")
    ap.add_argument("--hooks-only", action="store_true", help="迁移时只重算①钩子（保留已有正文+④精修）")
    a = ap.parse_args()
    load_env_file(_discover_env_file())
    providers = [p.strip() for p in a.providers.split(",") if p.strip()]
    if a.migrate or a.hooks_only:
        steps = ("hooks",) if a.hooks_only else ("hooks", "refine")
        migrate(a.words, a.out, persona=a.persona, host=a.host, providers=providers, only=a.only, steps=steps)
    else:
        if not a.selection:
            ap.error("全新生成需要 --selection（或加 --migrate 走迁移）")
        run(a.words, a.selection, a.out, persona=a.persona, host=a.host,
            providers=providers, limit=a.limit, only=a.only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
