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

CLEAN_KEEP_TASK = """\
【你的任务 · 字级去口水（只输出删后的纯文本）】
下面是【主讲人张和】一条切片的逐字稿。按上面的规则删掉【机械口水】：多余语气词、连续语气词、卡顿重复词（那个那个/真的真的真的）、句间/句内重复、残句。
🚨**承接句保护**：四类高危承接句（段间设问引子 / 对比转折 / 解释上文概念 / 数据结论前的主语铺垫）**不许删**，最多只删其中的语气词。**删前保后**，**拿不准就不删**（宁可多留，不要剪秃）。

⚠️**硬性约束（为了能精确对齐时间轴）**：
- 只**删字**，**不许改字 / 纠错 / 调换顺序 / 补字**——保留下来的字必须和原文**一字不差**（ASR 错字也照原样留着）。

【输出】只输出**删口水后剩下的字**（原样拼接成一段，可加自然标点）。
**不要 JSON、不要解释、不要任何前后缀**，直接给删后的文本。"""

# 对齐用：抹掉标点/空白，只留可比对的字
import re as _re

def _bare(s: str) -> str:
    # 抹掉标点/空白 + 统一小写：对齐只看"是哪个字"，不受 LLM 擅自改大小写/加空格影响
    return _re.sub(r"[\s，。！？、；：…—·“”‘’（）()\"']", "", (s or "")).lower()


def _diff_removed(seg_words: list[dict], kept_words: list[dict]) -> list[str]:
    """从保留集反推被删的字，按连续段汇总成简述。"""
    kept_ids = {id(w) for w in kept_words}
    out: list[str] = []
    run: list[str] = []
    for w in seg_words:
        if id(w) in kept_ids:
            if run:
                out.append("".join(run))
                run = []
        else:
            run.append(w["text"])
    if run:
        out.append("".join(run))
    return [r for r in out if _bare(r)]


def _merge_keep(kept: list[dict], pad_s: float, pad_e: float, gap_max: float) -> list[list[float]]:
    """保留字（按时间序）→ 合并成 keep 时间区间（字间停顿>gap_max 断开，两端加 PAD）。搬 cut_build ivs。"""
    ivs: list[list[float]] = []
    for w in kept:
        if ivs and w["start"] - ivs[-1][1] <= gap_max:
            ivs[-1][1] = w["end"]
        else:
            ivs.append([w["start"], w["end"]])
    return [[round(a - pad_s, 3), round(b + pad_e, 3)] for a, b in ivs]


def _align_kept(seg_words: list[dict], kept_text: str) -> list[dict]:
    """把"删后纯文本"贪心对齐回原字 → 保留的字（含时间）。删后文本应是原字的子序列。"""
    cl = _bare(kept_text)
    ci = 0
    kept: list[dict] = []
    for w in seg_words:
        t = _bare(w["text"])
        if not t:               # 纯标点/空 token：跟随保留
            kept.append(w)
            continue
        if cl[ci:ci + len(t)] == t:   # 与删后文本下一段吻合 → 这个字保留
            kept.append(w)
            ci += len(t)
        # 否则：这个字被删了，跳过（不前移 ci）
    return kept


def clean_to_keep(
    seg_words: list[dict],
    hint: str | None = None,
    profile: str = "zh_main",
    providers: list[str] | None = None,
    pad_s: float = 0.06,
    pad_e: float = 0.12,
    gap_max: float = 0.6,
    temperature: float = 0.2,
) -> dict:
    """选段字级词表 → 去口水后的 keep 时间区间。

    seg_words: [{text,start,end}]（秒，选段逐字）。LLM 输出"只删不改"的纯文本，
    代码对齐回原字 → 保留字 → 合并成 keep 时间区间（直接喂 ffmpeg 切片）。
    返回 {keep_spans, kept_words, kept_text, removed, protected}。
    """
    load_env_file(_discover_env_file())
    rules = _load_rules()
    system = (rules + "\n\n" + CLEAN_KEEP_TASK) if rules else CLEAN_KEEP_TASK
    raw_text = "".join(w["text"] for w in seg_words)
    brief = (f"切片主旨（hint）：{hint}\n\n" if hint else "") + f"【逐字稿】\n{raw_text}"
    client = OpenAICompatibleClient(providers=providers)
    cleaned = client.chat(                              # 纯文本输出，绕开 JSON 脆弱性
        [{"role": "system", "content": system}, {"role": "user", "content": brief}],
        temperature=temperature,
    )
    cleaned = _re.sub(r"^```[a-z]*\s*|\s*```$", "", (cleaned or "").strip())

    kept = _align_kept(seg_words, cleaned)
    # 保底：对齐消费 < 60% 删后文本（说明 LLM 改了字/漂移/没好好删），回退不删整段切
    if not kept or len(_bare("".join(w["text"] for w in kept))) < 0.6 * len(_bare(cleaned)):
        kept = list(seg_words)

    return {
        "keep_spans": _merge_keep(kept, pad_s, pad_e, gap_max),
        "kept_words": kept,
        "kept_text": "".join(w["text"] for w in kept),
        "removed": _diff_removed(seg_words, kept),
        "protected": [],
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
