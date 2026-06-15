#!/usr/bin/env python3
"""cards.py — 任务卡 schema + 加载器（§3 三要素）。

任务卡是 `cards/<name>.md`，非工程师可直接编辑。一张卡打包三要素：

  ① 怎么读（prompt）   —— 喂给 analyze 机器的提示词（命名 fenced 代码块）
  ② 要什么（result）   —— 期望的结果字段 / 输出契约
  ③ 写回规矩（write-back）—— 落飞书/本地哪个字段、用哪个写策略（write_policy 里的命名策略）
  + 先过滤（gate）     —— 调 LLM 前的确定性门（如就业卡：未发开场白→0-LLM stub）

卡片格式（向后兼容现有 employment.md 的「## 段名 + ``` 代码块」写法）：

  - 顶部可选 YAML front-matter（--- 包裹），声明 card metadata：
      name / 引擎 flow / 先过滤 gate / 写回 write-back 策略名。
    缺省时按 `## 元数据` 段或文件名兜底，保证旧卡无 front-matter 也能加载。
  - 正文用 `## 段名` 划分；提示词在段内的 ``` fenced 块里。

加载产物 = `Card` 对象：`card.blocks` 是「段名 → fenced 文本」的有序 dict，
flow 模块按自己需要取块（employment 取 SYSTEM_PROMPT/USER_PROMPT_TEMPLATE/
PREVIOUS_CONTEXT_BLOCK；profile 取 SYSTEM_PROMPT + 注入 FIELD_SPEC）。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# engine 根（capabilities/analyze/ → up 2）
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

CARDS_DIR = Path(__file__).resolve().parents[2] / "cards"

# 段标题（## 开头）；fenced 块（``` 包裹，可选 json/text 标注）
_HEADING_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_FENCE_BLOCK_RE = re.compile(r"```[a-zA-Z0-9]*\n(.*?)\n```", re.DOTALL)
_FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Card:
    """一张任务卡的结构化表示（三要素 + gate）。"""
    name: str
    path: Path
    meta: dict[str, Any]                 # front-matter / 元数据段
    blocks: dict[str, str]               # 段名 → 该段内第一个 fenced 块（提示词）
    raw: str = ""                        # 原始全文（调试用）

    # --- 三要素便捷访问 ---
    @property
    def flow(self) -> str:
        """这张卡走哪个 analyze flow（employment / profile / ...）。"""
        return str(self.meta.get("flow", self.name))

    @property
    def gate(self) -> str:
        """先过滤门标识（确定性 0-LLM 预过滤），如 follow_up_exact_match / none。"""
        return str(self.meta.get("gate", "none"))

    @property
    def write_back(self) -> dict[str, str]:
        """写回规矩：{字段 → write_policy 命名策略}。空 dict = 由 flow 自带契约。"""
        wb = self.meta.get("write_back") or {}
        return wb if isinstance(wb, dict) else {}

    def block(self, name: str, default: str | None = None) -> str:
        if name in self.blocks:
            return self.blocks[name]
        if default is not None:
            return default
        raise KeyError(f"任务卡 {self.name} 缺少段 [{name}]（现有: {list(self.blocks)}）")


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """极简 YAML front-matter 解析（仅支持 key: value / key: {a: b} 一层嵌套），
    避免引入 PyYAML 依赖。无 front-matter → ({}, 原文)。"""
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    body = text[m.end():]
    meta: dict[str, Any] = {}
    cur_key: str | None = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) and cur_key:  # 嵌套子项 (write_back 映射)
            k, _, v = line.strip().partition(":")
            if _:
                meta.setdefault(cur_key, {})
                if isinstance(meta[cur_key], dict):
                    meta[cur_key][k.strip()] = v.strip()
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if not _:
            continue
        if v == "":
            meta[k] = {}
            cur_key = k
        else:
            meta[k] = v
            cur_key = k
    return meta, body


def _parse_sections(body: str) -> dict[str, str]:
    """按 `## 段名` 切段，取每段内第一个 fenced 块作为该段提示词。"""
    blocks: dict[str, str] = {}
    headings = list(_HEADING_RE.finditer(body))
    for i, h in enumerate(headings):
        name = h.group(1).strip()
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        section = body[start:end]
        fm = _FENCE_BLOCK_RE.search(section)
        if fm:
            blocks[name] = fm.group(1)
    return blocks


def load_card(name: str) -> Card:
    """按名字加载任务卡（cards/<name>.md）。"""
    path = CARDS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"任务卡不存在: {path}")
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_front_matter(raw)
    blocks = _parse_sections(body)
    meta.setdefault("name", name)
    return Card(name=name, path=path, meta=meta, blocks=blocks, raw=raw)


def list_cards() -> list[str]:
    """列出 cards/ 下所有任务卡名（不含 .md）。"""
    return sorted(p.stem for p in CARDS_DIR.glob("*.md"))
