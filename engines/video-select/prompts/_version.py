#!/usr/bin/env python3
"""提示词版本管理 —— 账本层(bump) + 快照层(snapshot)。

设计真源：doc/plan/视频剪辑skill-第二环选片-分阶段评测-plan.md
账本：versions/<name>/vN.md（每版原文）+ versions.json（当前指针）+ CHANGELOG.md（人看）。

用法:
  # 升版：把当前 <name>.md 归档成新一版，改指针，往 CHANGELOG 追一行待你补分
  python3 _version.py bump body-edit "总编加去重叠红线"

  # 快照：把当前 5 条提示词 + versions.json 复制进某次 run（评测可复现）
  python3 _version.py snapshot <run_dir>

  # 查当前各版本
  python3 _version.py show
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent
NAMES = ["topic-select", "body-edit", "refine-deduct", "hook", "dedup-merge"]
REGISTRY = PROMPTS / "versions.json"
CHANGELOG = PROMPTS / "CHANGELOG.md"


def _load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _next_ver(cur: str) -> str:
    n = int(cur.lstrip("v")) if cur.startswith("v") and cur[1:].isdigit() else 0
    return f"v{n + 1}"


def bump(name: str, note: str) -> None:
    if name not in NAMES:
        sys.exit(f"未知提示词：{name}（应在 {NAMES}）")
    reg = _load_registry()
    new = _next_ver(reg.get(name, "v0"))
    dst = PROMPTS / "versions" / name / f"{new}.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROMPTS / f"{name}.md", dst)
    reg[name] = new
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # CHANGELOG 追一行（分变化留空待跑评测后补）
    line = f"- **{new}**（日期待填 · {note}）：分变化：**未测**。\n"
    txt = CHANGELOG.read_text(encoding="utf-8")
    anchor = f"## {name}\n"
    if anchor in txt:
        i = txt.index(anchor) + len(anchor)
        txt = txt[:i] + line + txt[i:]
    else:
        txt += f"\n## {name}\n{line}"
    CHANGELOG.write_text(txt, encoding="utf-8")
    print(f"✓ {name} → {new}（归档 {dst.relative_to(PROMPTS)}）；CHANGELOG 已追行，记得跑评测补分。")


def snapshot(run_dir: str) -> dict:
    """把当前 5 条提示词 + versions.json 复制进 run_dir/prompts/，返回版本快照。"""
    dst = Path(run_dir) / "prompts"
    dst.mkdir(parents=True, exist_ok=True)
    for n in NAMES:
        shutil.copy2(PROMPTS / f"{n}.md", dst / f"{n}.md")
    reg = _load_registry()
    (dst / "versions.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    return reg


def show() -> None:
    for n, v in _load_registry().items():
        print(f"  {n}: {v}")


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "bump" and len(sys.argv) >= 3:
        bump(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif cmd == "snapshot" and len(sys.argv) >= 3:
        reg = snapshot(sys.argv[2])
        print(f"✓ 快照 → {sys.argv[2]}/prompts/（{reg}）")
    elif cmd == "show":
        show()
    else:
        sys.exit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
