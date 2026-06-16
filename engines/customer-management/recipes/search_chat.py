#!/usr/bin/env python3
"""search_chat.py — `search-chat` 命令入口（薄壳,逻辑在 read_chat.cmd_search）。

单独成模块是因为 __main__ 用 runpy(alter_sys=True) 跑目标,会覆盖 argv[0],
无法靠 argv[0] 在同一模块里区分 read-chat / search-chat;故两个 dispatch key 各指一个模块。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recipes.read_chat import cmd_search  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(cmd_search(sys.argv[1:]))
