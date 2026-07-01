from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import shutil

RESERVED_INFO_KEYS = {"description", "storage_state"}


def tools_root() -> Path:
    return Path(__file__).resolve().parents[4]


STATE_DIR = tools_root() / "var" / "state" / "tencent-video-publish"
ACCOUNTS_FILE = STATE_DIR / "accounts.json"


def _empty_config() -> dict:
    return {"default": "", "accounts": {}}


def load_config() -> dict:
    if not ACCOUNTS_FILE.exists():
        return _empty_config()
    try:
        data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _empty_config()
    if not isinstance(data, dict):
        return _empty_config()
    data.setdefault("default", "")
    data.setdefault("accounts", {})
    return data


def save_config(config: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ACCOUNTS_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def account_state_path(slot: str | None = None) -> Path:
    config = load_config()
    resolved = slot or config.get("default") or "default"
    return STATE_DIR / "accounts" / resolved / "storage_state.json"


def storage_state_backups(storage_state: Path) -> list[Path]:
    return sorted(storage_state.parent.glob(f"{storage_state.name}.bak_*"), key=lambda path: path.name)


def latest_storage_state_backup(storage_state: Path) -> Path | None:
    backups = storage_state_backups(storage_state)
    return backups[-1] if backups else None


def restore_latest_storage_state_backup(storage_state: Path) -> Path | None:
    backup = latest_storage_state_backup(storage_state)
    if not backup:
        return None
    storage_state.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, storage_state)
    return backup


def backup_storage_state(storage_state: Path, keep: int = 5) -> Path | None:
    if not storage_state.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = storage_state.with_name(f"{storage_state.name}.bak_{timestamp}")
    shutil.copy2(storage_state, backup)

    backups = storage_state_backups(storage_state)
    for stale in backups[:-keep]:
        try:
            stale.unlink()
        except OSError:
            pass
    return backup


def storage_state_summary(storage_state: Path) -> dict:
    latest_backup = latest_storage_state_backup(storage_state)
    profile_dir = storage_state.parent / "chrome-profile"
    return {
        "storage_state": str(storage_state),
        "logged_state_file_exists": storage_state.exists(),
        "profile_dir": str(profile_dir),
        "profile_dir_exists": profile_dir.exists(),
        "profile_ignored": False,
        "auth_primary": "chrome_profile",
        "storage_state_role": "backup",
        "latest_backup": str(latest_backup) if latest_backup else "",
    }


def normalize_roles(roles: list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    if not roles:
        return []
    normalized: list[str] = []
    for role in roles:
        role = str(role).strip()
        if role and role not in normalized:
            normalized.append(role)
    return normalized


def _account_payload(slot: str, info: dict, default: str) -> dict:
    state_path = Path(info.get("storage_state") or account_state_path(slot))
    roles = normalize_roles(info.get("roles"))
    metadata = {key: value for key, value in info.items() if key not in RESERVED_INFO_KEYS | {"roles"}}
    return {
        "slot": slot,
        "description": info.get("description", ""),
        "roles": roles,
        "is_default": slot == default,
        "is_test": "test" in roles,
        **metadata,
        **storage_state_summary(state_path),
    }


def add_account(slot: str, description: str = "", roles: list[str] | None = None) -> dict:
    slot = slot.strip()
    if not slot:
        raise ValueError("slot must not be empty")
    config = load_config()
    accounts = config.setdefault("accounts", {})
    if slot in accounts:
        raise ValueError(f"account already exists: {slot}")
    state_path = account_state_path(slot)
    accounts[slot] = {
        "description": description,
        "storage_state": str(state_path),
    }
    normalized_roles = normalize_roles(roles)
    if normalized_roles:
        accounts[slot]["roles"] = normalized_roles
    if not config.get("default"):
        config["default"] = slot
    save_config(config)
    return _account_payload(slot, accounts[slot], config.get("default", ""))


def remove_account(slot: str) -> dict:
    config = load_config()
    accounts = config.get("accounts", {})
    if slot not in accounts:
        raise ValueError(f"account does not exist: {slot}")
    removed = accounts.pop(slot)
    if config.get("default") == slot:
        config["default"] = next(iter(accounts), "")
    save_config(config)
    return {"slot": slot, **removed}


def set_default_account(slot: str) -> dict:
    config = load_config()
    if slot not in config.get("accounts", {}):
        raise ValueError(f"account does not exist: {slot}")
    config["default"] = slot
    save_config(config)
    return {"slot": slot, "is_default": True}


def set_account_roles(slot: str, roles: list[str]) -> dict:
    config = load_config()
    accounts = config.get("accounts", {})
    if slot not in accounts:
        raise ValueError(f"account does not exist: {slot}")
    normalized_roles = normalize_roles(roles)
    if normalized_roles:
        accounts[slot]["roles"] = normalized_roles
    else:
        accounts[slot].pop("roles", None)
    save_config(config)
    return _account_payload(slot, accounts[slot], config.get("default", ""))


def list_accounts() -> list[dict]:
    config = load_config()
    default = config.get("default", "")
    accounts = []
    for slot, info in config.get("accounts", {}).items():
        accounts.append(_account_payload(slot, info, default))
    return accounts
