"""共享接线：把 video-slicer 的轻量句/时间核心挂上 sys.path，并集中读 prompts/。

依赖方向是单向的：video-select → video-slicer（只读用它的逐字稿→句/时间核心，
不重复造）。所有提示词一律从 `prompts/` 读，代码里不再内嵌 prompt 字符串常量。
"""
from __future__ import annotations

import json
import shutil
import sys
from functools import lru_cache
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]          # engines/video-select/
PROMPTS_DIR = ENGINE_ROOT / "prompts"
_SLICER = ENGINE_ROOT.parent / "video-slicer"              # engines/video-slicer/

if _SLICER.exists() and str(_SLICER) not in sys.path:
    sys.path.insert(0, str(_SLICER))


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """读 prompts/<name>.md 整篇当 system prompt。name 不含扩展名。"""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"提示词不存在：{path}")
    return path.read_text(encoding="utf-8")
