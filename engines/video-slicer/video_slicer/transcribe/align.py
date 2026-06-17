"""把火山原生句(带标点 + 书面数字 ITN) 对齐回字级词 → 富 token 流(带时间)。

为什么需要：去口水的输入升级成"句级带标点 ITN 文本"后，AI 删口水吐出的也是带标点 ITN
文本；但切视频/字幕要精确到秒，而精确时间只在**字级**词里。本模块把"带标点 ITN 文本"
逐段对回字级词，产出"既带标点 ITN、又带时间"的 token 流。供 script_clean 去口水后定位、
cut_video 出字幕。

难点 = 书面数字(ITN)：文本里的 "30%" 在字级是"百分之三十"(5 字)，字符对不上号。
对齐法（**句内一次性建表**，最可靠的地方解决一次）：
  - 普通字/词：和字级词逐个比对（忽略大小写/标点）。
  - 数字段：当作一个**原子块**，吃掉字级里"到下一个能重新对上的锚字之前"的所有字，
    整块绑定那段字的时间（起=首字.start，止=末字.end）。绝不把 "30%" 拆开。
  - 标点：字级没有，直接并进它**前一个 token** 的文本（前 token 删了它也跟着删）。
对不齐 → 抛 `AlignError`，由调用方整句/整段降级回字级裸拼（不断流）。

去口水之后用 `project_cleaned(cleaned, tokens)`：cleaned 是 AI 删口水后的带标点 ITN 文本，
和 tokens 同属"带标点 ITN"这一套词表，做干净的子序列匹配即可挑出保留的 token。
"""
from __future__ import annotations

import re as _re

# 标点/空白：字级词里没有，靠这套规则在文本里识别并并入相邻 token
_SKIP = set(" \t\n，。！？、；：…—·“”‘’（）()\"'《》【】,.!?;:")
# 书面数字字符：阿拉伯数字 + 百分号 + 小数点（中文数字不算，它们在字级里是普通字）
_ITN = set("0123456789%．.")
# 区间分隔符：夹在两个数字之间时并入数字块（如 "1~5分" "5-10倍"），避免被当锚字
_ITN_SEP = set("~～-－—/／")


class AlignError(Exception):
    """带标点 ITN 文本对不齐字级词；调用方应整句/整段降级回字级裸拼。"""


def _bare(s: str) -> str:
    """抹掉标点/空白 + 转小写：比对只看"是哪个字/数字"，不受标点和大小写干扰。"""
    return _re.sub(r"[\s，。！？、；：…—·“”‘’（）()\"'《》【】,.!?;:]", "", s or "").lower()


def _is_skip(ch: str) -> bool:
    return ch in _SKIP


def _is_itn(ch: str) -> bool:
    return ch in _ITN


def map_sentence(text: str, words: list[dict]) -> list[dict]:
    """一个原生句(带标点 ITN) + 它的字级词 → 富 token 列表。

    words: `[{text,start,end}]`（秒，按时间序，无标点的原始字）。
    返回 `[{text,start,end,kind}]`，kind ∈ {"char","itn"}；标点已并入相邻 token 的 text。
    对不齐抛 AlignError。
    """
    toks: list[dict] = []
    pending = ""          # 暂存标点/空白：并到下一个 token 前面（处理句首标点）
    i, j, n = 0, 0, len(text)

    def glue(s: str) -> None:
        nonlocal pending
        if toks:
            toks[-1]["text"] += s
        else:
            pending += s

    while i < n or j < len(words):
        # 1) 文本里的标点/空白：并到前一个 token
        if i < n and _is_skip(text[i]):
            glue(text[i]); i += 1; continue
        # 2) 文本读完但还有字没对上 → 对不齐
        if i >= n:
            raise AlignError(f"文本读完仍剩 {len(words) - j} 个字未对齐")
        # 3) 数字段(ITN)：原子块，吃到下一个锚字
        if _is_itn(text[i]):
            # 收最大数字段：连续数字字符 + "标点后紧跟另一个数字段"也并入
            # （如 "30%、20%" 两块间只隔顿号、无中文锚字，须合并成一个原子块）
            k = i
            while k < n:
                if _is_itn(text[k]):
                    k += 1
                elif text[k] in _ITN_SEP and k + 1 < n and _is_itn(text[k + 1]):
                    k += 1                          # 区间号(如 1~5)夹在数字间 → 并入数字块
                elif _is_skip(text[k]):
                    p = k
                    while p < n and _is_skip(text[p]):
                        p += 1
                    if p < n and _is_itn(text[p]):
                        k = p                       # 吸收中间标点，继续数字段
                    else:
                        break
                else:
                    break
            itn_text = text[i:k]
            a = k                                   # 数字段后、跳过标点，找下一个普通锚字
            while a < n and _is_skip(text[a]):
                a += 1
            anchor = _bare(text[a]) if a < n else None
            start_j = j
            if anchor is None:                      # 数字在句末 → 吃光剩余字
                j = len(words)
            else:
                while j < len(words) and not _bare(words[j]["text"]).startswith(anchor):
                    j += 1
                if j >= len(words):
                    raise AlignError(f"数字块 {itn_text!r} 后的锚字 {anchor!r} 在字级里找不到")
            if j <= start_j:
                raise AlignError(f"数字块 {itn_text!r} 没绑定到任何字")
            blk = words[start_j:j]
            toks.append({"text": pending + itn_text, "start": blk[0]["start"],
                         "end": blk[-1]["end"], "kind": "itn"})
            pending = ""
            i = k
            continue
        # 4) 普通字/词：和 words[j] 比对（按词长从文本取等长片段）
        if j >= len(words):
            raise AlignError(f"字级词读完但文本还剩 {text[i:]!r}")
        wb = _bare(words[j]["text"])
        if not wb:                                  # 理论上字级无空词；保险跳过
            j += 1; continue
        consumed = text[i:i + len(wb)]
        if _bare(consumed) != wb:
            raise AlignError(f"第 {i} 位文本 {consumed!r} 与字 {words[j]['text']!r} 对不上")
        toks.append({"text": pending + consumed, "start": words[j]["start"],
                     "end": words[j]["end"], "kind": "char"})
        pending = ""
        i += len(wb); j += 1

    if pending and toks:                            # 句末残留标点并到最后一个 token
        toks[-1]["text"] += pending
    return toks


def map_clip(sents: list, words: list[dict]) -> list[dict]:
    """一条切片覆盖的多个原生句 → 拼接的富 token 流。

    sents: Sentence 列表（需有 .text / .wi / .wj），words: 全片归一化字级词。
    任一句对不齐 → AlignError 上抛（调用方整段降级）。
    """
    out: list[dict] = []
    for s in sents:
        if s.wi < 0 or s.wj < 0:
            raise AlignError(f"句 {getattr(s, 'sid', '?')} 没有字级索引(wi/wj=-1)")
        out += map_sentence(s.text, words[s.wi:s.wj + 1])
    return out


def project_cleaned(cleaned: str, tokens: list[dict]) -> list[dict]:
    """去口水后的带标点 ITN 文本 + 原富 token 流 → 保留的 token（贪心子序列匹配）。

    cleaned 是 tokens 文本"只删不改"的子序列（同属带标点 ITN 词表，忽略标点/大小写）。
    """
    cb = _bare(cleaned)
    ci = 0
    kept: list[dict] = []
    for t in tokens:
        tb = _bare(t["text"])
        if not tb:                                  # 纯标点 token：跟随保留
            kept.append(t); continue
        if cb[ci:ci + len(tb)] == tb:               # 与删后文本下一段吻合 → 保留
            kept.append(t); ci += len(tb)
        # 否则该 token 被删，跳过
    return kept


def rich_text(tokens: list[dict]) -> str:
    """富 token 流 → 带标点 ITN 文本（直接拼）。"""
    return "".join(t["text"] for t in tokens)
