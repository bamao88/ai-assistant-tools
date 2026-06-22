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


def snapshot_prompts(out_dir: str | Path) -> dict:
    """快照层：把当前 prompts/*.md + versions.json 复制进 out_dir/prompts/，
    让每次 run 的分数永远查得到「是哪段提示词文本、哪个版本」跑出来的（可复现）。
    返回当前版本注册表（写进 golden 便于溯源）。设计见 prompts/_version.py。"""
    dst = Path(out_dir) / "prompts"
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(PROMPTS_DIR.glob("*.md")):
        shutil.copy2(p, dst / p.name)
    reg_path = PROMPTS_DIR / "versions.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else {}
    (dst / "versions.json").write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return reg
