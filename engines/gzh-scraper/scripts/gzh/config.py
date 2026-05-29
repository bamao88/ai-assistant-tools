"""配置管理 — ~/.gzh-scraper/config.json"""

from __future__ import annotations

import json
import os
from typing import Any

CONFIG_DIR = os.path.expanduser("~/.gzh-scraper")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

_DEFAULT_CONFIG: dict[str, Any] = {
    "exporter_url": "http://localhost:3000",
    "auth_key": "",
    "watchlist": [],
}


def _ensure_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> dict[str, Any]:
    """加载配置，不存在则返回默认值。"""
    if not os.path.exists(CONFIG_FILE):
        return dict(_DEFAULT_CONFIG)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        data = json.load(f)
    # 合并默认值
    for k, v in _DEFAULT_CONFIG.items():
        data.setdefault(k, v)
    return data


def save_config(config: dict[str, Any]) -> None:
    """保存配置到文件。"""
    _ensure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_exporter_url(config: dict[str, Any] | None = None) -> str:
    cfg = config or load_config()
    return cfg.get("exporter_url", _DEFAULT_CONFIG["exporter_url"])


def get_auth_key(config: dict[str, Any] | None = None) -> str:
    cfg = config or load_config()
    return cfg.get("auth_key", "")


def set_auth_key(key: str) -> None:
    cfg = load_config()
    cfg["auth_key"] = key
    save_config(cfg)
