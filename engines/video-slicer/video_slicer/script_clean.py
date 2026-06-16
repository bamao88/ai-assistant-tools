"""字级去口水执行器：原始口语逐字稿 → 干净脚本。

执行 `references/字级去口水与承接句保护.md` 的规则：删机械口水（语气词/卡顿/重复/残句）、
🚨保护承接句、纠错术语；产出"像本人正常顺畅讲话"的脚本。供字级线（cut_word）做脚本清洗。

与 srt_fix 的分工：srt_fix 是 1:1 不删条的字幕校对（保时间轴）；本模块**会删词删句**，
产出的是清洗后的脚本文本（脚本层去口水），用于评估脚本质量 / 后续字级精剪定位。
"""
from __future__ import annotations

from pathlib import Path

from .cli import _discover_env_file, load_env_file
from .llm import OpenAICompatibleClient

_ENGINE = Path(__file__).resolve().parent.parent
_RULES = _ENGINE / "references" / "字级去口水与承接句保护.md"


def _load_rules() -> str:
    return _RULES.read_text(encoding="utf-8") if _RULES.exists() else ""


CLEAN_TASK = """\
【你的任务 · 字级去口水】
下面是【主讲人张和】一条切片的**原始口语逐字稿**（ASR 产出，含语气词/卡顿/重复/残句/识别错字）。
按上面的规则产出一版**干净脚本**：

1. **删机械口水**：多余语气词（嗯/啊/呃…，保留适量"嗯"过渡）、连续语气词全删、卡顿词（那个那个/真的真的真的）删到留一个、句间/句内重复删前留后、残句整句删。
2. **🚨保护承接句**：四类高危承接句（段间设问引子 / 对比转折 / 解释上文概念 / 数据结论前的主语铺垫）**必须留**，最多只去其中语气词。
3. **纠错术语**：把 ASR 听错的专名改对（如 低发→低代码、爱马仕→Anthropic、cloudagentsdk→Claude Agent SDK、科室→Codex、阿金→Agent），规范英文术语大小写。
4. **删前保后**：重复/残句一律删前面那次、保后面更完整的。
5. **不过碎、不剪秃**：以语义完整短句为最小单位，宁可多留一点；读起来要像本人正常顺畅讲话。

【输出严格 JSON，无 markdown】
{
  "script": "<去口水+纠错后的完整脚本，按自然句换行>",
  "removed": ["<被删的简述，如 '卡顿:真的真的真的→真的'>", "..."],
  "protected": ["<识别为承接句、特意保留的句子，如 '除了极少数的场景比如外呼'>", "..."]
}
只输出这个 JSON 对象。"""


def clean_script(
    raw_text: str,
    hint: str | None = None,
    profile: str = "zh_main",
    providers: list[str] | None = None,
    temperature: float = 0.2,
) -> dict:
    """原始口语脚本 → {script, removed, protected}。profile 预留（规则当前账号无关）。"""
    load_env_file(_discover_env_file())   # 复用引擎共享 .env（LLM provider 密钥）
    rules = _load_rules()
    system = (rules + "\n\n" + CLEAN_TASK) if rules else CLEAN_TASK
    brief = (f"切片主旨（hint）：{hint}\n\n" if hint else "") + f"【原始逐字稿】\n{raw_text}"
    client = OpenAICompatibleClient(providers=providers)
    data = client.chat_json(
        [{"role": "system", "content": system}, {"role": "user", "content": brief}],
        temperature=temperature,
    )
    data.setdefault("script", "")
    data.setdefault("removed", [])
    data.setdefault("protected", [])
    return data


# ====== 字级去口水（返回删词区间 → keep 时间区间，给切片用）======

import re as _re

CLEAN_KEEP_TASK = """\
【你的任务 · 字级去口水（返回要删的字编号区间）】
下面是【主讲人张和】一小段逐字稿，每个字带编号：`#编号 字`。
标出要删的【机械口水】字：多余语气词（嗯/啊/呃，保留适量"嗯"过渡）、连续语气词、卡顿重复词（那个那个/真的真的真的→只留一个）、句间/句内重复（删前留后）、残句。
🚨**承接句保护**：表转折/设问引子/铺垫主语/解释概念的句子**不许删**，最多删其中语气词。**拿不准就不删**（宁可多留，不要剪秃）。

【输出严格 JSON，无 markdown】
{"delete": [[起编号, 止编号], ...]}
每个闭区间=要删掉的一段连续口水字（含两端）；单字口水写 [n,n]；没有要删的就给 {"delete": []}。
只删口水、不删正常内容。只输出这个 JSON 对象。"""


def _bare(s: str) -> str:
    return _re.sub(r"[\s，。！？、；：…—·“”‘’（）()\"']", "", (s or "")).lower()


def _merge_keep(kept: list[dict], pad_s: float, pad_e: float, gap_max: float) -> list[list[float]]:
    """保留字（按时间序）→ 合并成 keep 时间区间（字间停顿>gap_max 断开，两端加 PAD）。搬 cut_build ivs。"""
    ivs: list[list[float]] = []
    for w in kept:
        if ivs and w["start"] - ivs[-1][1] <= gap_max:
            ivs[-1][1] = w["end"]
        else:
            ivs.append([w["start"], w["end"]])
    return [[round(a - pad_s, 3), round(b + pad_e, 3)] for a, b in ivs]


def _chunk_words(seg_words: list[dict], max_chars: int) -> list[tuple[int, list[dict]]]:
    """把选段切成 ~max_chars 字的小块（优先在字间停顿处断），返回 [(全局起始idx, 块词表)]。"""
    chunks: list[tuple[int, list[dict]]] = []
    start = 0
    cur = 0
    for i in range(1, len(seg_words) + 1):
        cur += len(seg_words[i - 1]["text"])
        at_pause = i < len(seg_words) and seg_words[i]["start"] - seg_words[i - 1]["end"] >= 0.3
        if i == len(seg_words) or (cur >= max_chars and at_pause) or cur >= max_chars * 1.6:
            chunks.append((start, seg_words[start:i]))
            start = i
            cur = 0
    return chunks


def _dehesitate_chunk(chunk_words: list[dict], hint: str | None, client, temperature: float) -> set[int]:
    """一小块 → LLM 返回删词区间 → 块内要删的字索引集合（校验越界/非法）。"""
    numbered = "".join(f"#{i} {w['text']}" for i, w in enumerate(chunk_words))
    rules = _load_rules()
    system = (rules + "\n\n" + CLEAN_KEEP_TASK) if rules else CLEAN_KEEP_TASK
    brief = (f"主旨：{hint}\n\n" if hint else "") + f"【逐字稿】\n{numbered}"
    try:
        data = client.chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": brief}],
            temperature=temperature,
        )
    except Exception:  # noqa: BLE001  本块解析失败 → 该块不删（保底）
        return set()
    n = len(chunk_words)
    drop: set[int] = set()
    for rng in data.get("delete", []):
        if not isinstance(rng, list) or len(rng) < 1:
            continue
        a = int(rng[0]); b = int(rng[-1])
        if a > b:
            a, b = b, a
        a, b = max(a, 0), min(b, n - 1)
        if a <= b and (b - a) < n:          # 不允许一次删光整块（防误删）
            drop.update(range(a, b + 1))
    return drop


def clean_to_keep(
    seg_words: list[dict],
    hint: str | None = None,
    profile: str = "zh_main",
    providers: list[str] | None = None,
    pad_s: float = 0.06,
    pad_e: float = 0.12,
    gap_max: float = 0.6,
    max_chars: int = 90,
    temperature: float = 0.2,
) -> dict:
    """选段字级词表 → 去口水后的 keep 时间区间。

    分块（~max_chars 字）逐块走索引法去口水（小块 → JSON 短、删得准），聚合删词索引 →
    保留字 → 合并成 keep 时间区间（直接喂 ffmpeg 切片）。
    返回 {keep_spans, kept_words, kept_text, removed, deleted_idx}。
    """
    from concurrent.futures import ThreadPoolExecutor

    load_env_file(_discover_env_file())
    client = OpenAICompatibleClient(providers=providers)
    chunks = _chunk_words(seg_words, max_chars)
    with ThreadPoolExecutor(max_workers=min(6, len(chunks)) or 1) as ex:   # 分块并行：N块≈1次延迟
        locals_ = list(ex.map(lambda c: _dehesitate_chunk(c[1], hint, client, temperature), chunks))
    drop: set[int] = set()
    removed: list[str] = []
    for (offset, chunk), local in zip(chunks, locals_):
        for i in sorted(local):
            removed.append(chunk[i]["text"])
        drop.update(offset + i for i in local)

    kept = [w for i, w in enumerate(seg_words) if i not in drop]
    if not kept:                                        # 异常全删 → 回退不删
        kept = list(seg_words)
        drop = set()

    return {
        "keep_spans": _merge_keep(kept, pad_s, pad_e, gap_max),
        "kept_words": kept,
        "kept_text": "".join(w["text"] for w in kept),
        "removed": removed,
        "deleted_idx": sorted(drop),
    }


def main() -> int:
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(description="字级去口水：原始口语脚本 → 干净脚本")
    ap.add_argument("input", help="原始逐字稿 txt（每行一句或整段）")
    ap.add_argument("--hint", default=None, help="切片主旨，帮助判断承接句")
    ap.add_argument("--profile", default="zh_main")
    ap.add_argument("--out", default=None, help="输出 JSON 路径（不给则打印）")
    a = ap.parse_args()
    raw = Path(a.input).read_text(encoding="utf-8")
    result = clean_script(raw, hint=a.hint, profile=a.profile)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        print(f"✓ 去口水完成 → {a.out}（删 {len(result['removed'])} 处，护 {len(result['protected'])} 句）", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
