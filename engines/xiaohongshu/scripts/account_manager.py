"""多账号管理，对应独立的账号配置管理。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# 账号配置文件路径
_CONFIG_DIR = Path.home() / ".xhs"
_ACCOUNTS_FILE = _CONFIG_DIR / "accounts.json"

# 命名账号端口起始值（默认账号使用 9222）
_NAMED_PORT_START = 9223


def _load_config() -> dict:
    """加载账号配置。"""
    if not _ACCOUNTS_FILE.exists():
        return {"default": "", "accounts": {}}
    with open(_ACCOUNTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_config(config: dict) -> None:
    """保存账号配置。"""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def list_accounts() -> list[dict]:
    """列出所有账号。"""
    config = _load_config()
    default = config.get("default", "")
    accounts = config.get("accounts", {})
    result = []
    for slot, info in accounts.items():
        result.append(
            {
                "slot": slot,
                "description": info.get("description", ""),
                "is_default": slot == default,
                "profile_dir": get_profile_dir(slot),
                "port": info.get("port", _NAMED_PORT_START),
            }
        )
    return result


def add_account(slot: str, description: str = "") -> None:
    """添加账号，自动分配独立端口（从 _NAMED_PORT_START 递增）。"""
    config = _load_config()
    accounts = config.setdefault("accounts", {})
    if slot in accounts:
        raise ValueError(f"账号 '{slot}' 已存在")

    # 自动分配端口：取已有端口的最大值（至少 _NAMED_PORT_START - 1）加 1
    existing_ports = {info.get("port", _NAMED_PORT_START) for info in accounts.values()}
    port = max(existing_ports | {_NAMED_PORT_START - 1}) + 1

    accounts[slot] = {"description": description, "port": port}

    # 如果是第一个账号，设为默认
    if not config.get("default"):
        config["default"] = slot

    _save_config(config)

    # 创建 Profile 目录
    profile_dir = get_profile_dir(slot)
    os.makedirs(profile_dir, exist_ok=True)

    logger.info("添加账号: %s (port=%d)", slot, port)


def remove_account(slot: str) -> None:
    """删除账号。"""
    config = _load_config()
    accounts = config.get("accounts", {})
    if slot not in accounts:
        raise ValueError(f"账号 '{slot}' 不存在")

    del accounts[slot]

    # 如果删除的是默认账号，清除默认
    if config.get("default") == slot:
        config["default"] = next(iter(accounts), "")

    _save_config(config)
    logger.info("删除账号: %s", slot)


def set_default_account(slot: str) -> None:
    """设置默认账号。"""
    config = _load_config()
    accounts = config.get("accounts", {})
    if slot not in accounts:
        raise ValueError(f"账号 '{slot}' 不存在")

    config["default"] = slot
    _save_config(config)
    logger.info("默认账号设置为: %s", slot)


def update_account_description(slot: str, description: str) -> None:
    """更新账号描述（存储小红书账号名称）。"""
    config = _load_config()
    accounts = config.get("accounts", {})
    if slot not in accounts:
        raise ValueError(f"账号 '{slot}' 不存在")
    accounts[slot]["description"] = description
    _save_config(config)
    logger.info("账号 %s 描述已更新: %s", slot, description)


def get_default_account() -> str:
    """获取默认账号 slot。"""
    config = _load_config()
    return config.get("default", "")


def get_profile_dir(slot: str) -> str:
    """获取账号的 Chrome Profile 目录。"""
    return str(_CONFIG_DIR / "accounts" / slot / "chrome-profile")


def _get_profile_dir(slot: str) -> str:
    """获取账号的 Chrome Profile 目录（别名，向后兼容）。"""
    return get_profile_dir(slot)


def get_account_port(slot: str) -> int:
    """获取指定账号的 Chrome 调试端口。"""
    config = _load_config()
    accounts = config.get("accounts", {})
    if slot not in accounts:
        raise ValueError(f"账号 '{slot}' 不存在")
    return accounts[slot].get("port", _NAMED_PORT_START)
