#!/usr/bin/env python3
"""config.py — publish-prep engine 的唯一路径解析器（跨仓单点，仿 customer-management）。

engine 代码住 tools/engines/publish-prep；skill 资产（规则/池/模板/prompt）住
tools/skills/publish-prep/assets；业务依赖（core.py LLM 客户端 / .env / content items /
dbs-xhs-title skill）住 assistant_zh 或 ~/.claude。所有绝对路径收口到这里。

* import-time 廉价：只算路径，不读写文件。
* 可被环境变量覆盖：PUBLISH_PREP_DATA_ROOT 指向 assistant_zh 仓根（多机/搬家改一处）。
"""
from __future__ import annotations

import os
from pathlib import Path

# tools/engines/publish-prep/config.py → parents: [0]=publish-prep [1]=engines [2]=tools [3]=AI_Assistant
_HERE = Path(__file__).resolve()
TOOLS_ROOT = _HERE.parents[2]
AI_ROOT = _HERE.parents[3]

# --- assistant_zh 仓根（业务依赖所在）---
DATA_ROOT = Path(os.environ.get("PUBLISH_PREP_DATA_ROOT", str(AI_ROOT / "assistant_zh"))).resolve()

# --- skill 资产（本 engine 的规则/池/模板/prompt 真源）---
SKILL_ASSETS = TOOLS_ROOT / "skills" / "publish-prep" / "assets"
PLATFORM_RULES = SKILL_ASSETS / "platform_rules.yaml"
KEYWORD_POOL = SKILL_ASSETS / "keyword_pool.yaml"
TEMPLATES_DIR = SKILL_ASSETS / "templates"
PROMPTS_DIR = SKILL_ASSETS / "prompts"
BODY_VIDEO_PROMPT = PROMPTS_DIR / "body_video.md"

# --- assistant_zh 业务依赖 ---
KNOWLEDGE_INGEST = DATA_ROOT / "workflow" / "knowledge_ingest"   # core.py（OpenAI 兼容 LLM 客户端）
ENV_FILE = DATA_ROOT / "knowledge_base" / ".env"                 # Kimi/MiniMax key
TMP_DIR = DATA_ROOT / "tmp" / "slice_copy_test"                  # 试跑产物

# --- 外部 skill ---
DBS_TITLE_SKILL = Path(os.path.expanduser("~/.claude/skills/dbs-xhs-title/SKILL.md"))
