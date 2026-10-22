#!/usr/bin/env python3
"""Fail-closed preflight for the publishing skill's existing-Chrome route.

This hook checks supplied inventory and connection observations. It never launches
a browser, accesses a platform, imports credentials, or submits content. Call it
before connecting and again before upload/submit with the current selection.
It is an entrypoint guard, not a global shell/tool interception mechanism.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


PHASES = ("before_connect", "before_upload", "before_submit")


class SessionGuardError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise SessionGuardError(f"PUBLISH_SESSION_{code}", message)


def daily_chrome_root() -> Path:
    """The current OS user's normal Chrome data root, never a launcher slot."""
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Google/Chrome"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            fail("UNVERIFIED_PROFILE", "无法确定本机日常 Chrome 目录；请核对本机浏览器，不启动替代配置。")
        return Path(base) / "Google/Chrome/User Data"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "google-chrome"


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail("INVALID_METADATA", f"缺少或无效的 {field}；保留当前 Chrome，重新读取实际连接信息。")
    return value


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail("INVALID_METADATA", f"缺少或无效的 {field}；不能用默认值代替实际浏览器信息。")
    return value


def chrome_identity(entry: Any, field: str) -> dict[str, str]:
    browser = require_object(entry, field)
    if browser.get("family") != "chrome" or browser.get("type") != "extension":
        fail("WRONG_BROWSER", "仅允许本机已打开的日常 Chrome 扩展入口；禁止 IAB、CDP 或脚本独立配置。")
    metadata = require_object(browser.get("metadata"), f"{field}.metadata")
    return {
        "browser_id": require_string(browser.get("id"), f"{field}.id"),
        "profile_name": require_string(browser.get("profileName"), f"{field}.profileName"),
        "extension_instance_id": require_string(metadata.get("extensionInstanceId"), f"{field}.metadata.extensionInstanceId"),
    }


def verify_local_profile_name(root: Path, directory: str, inventory_name: str) -> None:
    """Bind the disk profile to the extension using only info_cache names.

    Local State is read without modification. No credential/storage files or
    other Local State values are inspected, returned, or included in errors.
    Duplicate display names cannot establish an unambiguous disk binding.
    """
    try:
        local_state = json.loads((root / "Local State").read_text(encoding="utf-8"))
        info_cache = local_state["profile"]["info_cache"]
        if not isinstance(info_cache, dict):
            raise ValueError("invalid profile cache")
    except (OSError, ValueError, KeyError, TypeError):
        fail("PROFILE_METADATA_UNVERIFIED", "无法读取本机 Chrome 的配置名称映射；停止并核对日常 Chrome，不创建替代配置。")
    profile = info_cache.get(directory)
    if not isinstance(profile, dict) or not isinstance(profile.get("name"), str) or not profile["name"].strip():
        fail("PROFILE_DIRECTORY_UNREGISTERED", "Chrome 配置名称映射中没有契约目录；不能把存在的任意目录当作日常配置。")
    name = profile["name"]
    if name != inventory_name:
        fail("PROFILE_NAME_MISMATCH", "磁盘配置目录名称与所选 Chrome 扩展配置名不同；停止并核对同一个日常 Chrome。")
    matches = [key for key, value in info_cache.items() if isinstance(value, dict) and value.get("name") == name]
    if matches != [directory]:
        fail("PROFILE_AMBIGUOUS", "多个 Chrome 配置使用相同名称，无法唯一绑定扩展与磁盘目录；停止并人工核对，不猜配置。")


def guard_session(contract: Any, observed: Any, phase: str) -> dict[str, Any]:
    """Validate a task-locked inventory entry against the current route.

    contract = {
      "schema_version": 1, "host": "local", "browser": <CUA inventory entry>,
      "profile": {"user_data_dir": ".../Google/Chrome", "profile_directory": "Default"}
    }
    observed = {
      "browser": <the currently selected inventory entry>,
      "connection": {
        "host": "local", "transport": "extension", "provider": "cua",
        "browser_id": "2", "extension_instance_id": "...",
        "existing_session": true, "headless": false,
        "launched_new_browser": false, "created_new_context": false,
        "restored_cookies": false
      }
    }

    user_data_dir/profile_directory are optional in observed.connection because
    CUA inventory does not expose disk paths. If provided, both must match the
    locally verified contract. Local State info_cache must uniquely match that
    directory's display name to the selected extension inventory profileName.
    A pass does not prove platform login, ownership, or successful upload.
    """
    if phase not in PHASES:
        fail("INVALID_PHASE", "未知发布会话检查阶段。")
    contract = require_object(contract, "contract")
    observed = require_object(observed, "observed")
    if type(contract.get("schema_version")) is not int or contract.get("schema_version") != 1:
        fail("INVALID_METADATA", "发布会话契约版本必须为 1。")
    if contract.get("host") != "local":
        fail("REMOTE_HOST", "发布只允许本台电脑；禁止连接其它电脑或发布机。")
    expected = chrome_identity(contract.get("browser"), "contract.browser")
    profile = require_object(contract.get("profile"), "contract.profile")
    root = Path(require_string(profile.get("user_data_dir"), "contract.profile.user_data_dir")).expanduser().resolve()
    if root != daily_chrome_root().resolve():
        fail("SCRIPT_PROFILE", "契约指向脚本或非日常 Chrome 数据目录；禁止启动独立配置，请复用本机已有 Chrome。")
    directory = require_string(profile.get("profile_directory"), "contract.profile.profile_directory")
    if Path(directory).name != directory or directory in (".", ".."):
        fail("INVALID_METADATA", "profile_directory 必须是日常 Chrome 目录内已核对的单个配置目录名。")
    if not (root / directory).is_dir():
        fail("UNVERIFIED_PROFILE", "本机不存在契约中的日常 Chrome 配置目录；停止并核对实际配置，不创建新目录。")
    verify_local_profile_name(root, directory, expected["profile_name"])

    actual = chrome_identity(observed.get("browser"), "observed.browser")
    connection = require_object(observed.get("connection"), "observed.connection")
    if connection.get("host") != "local":
        fail("REMOTE_HOST", "发布只允许本台电脑；禁止连接其它电脑或发布机。")
    if connection.get("transport") != "extension" or connection.get("provider") != "cua":
        fail("WRONG_TRANSPORT", "仅允许 CUA 复用现有 Chrome 扩展会话；禁止 CDP、Playwright/Patchright 独立启动器。")
    if any(connection.get(key) for key in ("cdp_endpoint", "debugging_port", "remote_host", "launch_args", "executable_path")):
        fail("SCRIPT_CONNECTION", "发现脚本启动、远程调试或远端连接参数；停止发布，不切换配置。")
    if connection.get("existing_session") is not True:
        fail("NEW_SESSION", "未确认正在复用已打开的 Chrome；禁止创建替代会话。")
    for key in ("headless", "launched_new_browser", "created_new_context", "restored_cookies"):
        if connection.get(key) is not False:
            fail("FORBIDDEN_RECOVERY", f"{key} 必须明确为 false；禁止无头/独立配置/Cookie 恢复。未登录时请用户在当前 Chrome 登录。")
    for key, expected_value in (("user_data_dir", str(root)), ("profile_directory", directory)):
        if key in connection:
            value = connection[key]
            if key == "user_data_dir" and isinstance(value, str):
                value = str(Path(value).expanduser().resolve())
            if value != expected_value:
                fail("SCRIPT_PROFILE", "实际连接的 Chrome 配置与已核对的日常配置不同；禁止换成脚本配置。")
    if actual != expected:
        fail("BROWSER_CHANGED", "实际 Chrome 扩展实例或配置与本轮锁定对象不同；停止并重新核对日常 Chrome，不自动切换。")
    if connection.get("browser_id") != expected["browser_id"] or connection.get("extension_instance_id") != expected["extension_instance_id"]:
        fail("CONNECTION_MISMATCH", "连接目标与本轮已选 Chrome 不一致；不得用另一浏览器连接替代。")

    binding = {"host": "local", **expected, "user_data_dir": str(root), "profile_directory": directory}
    digest = hashlib.sha256(json.dumps(binding, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {
        "allowed": True,
        "code": "PUBLISH_SESSION_OK",
        "phase": phase,
        "binding": binding,
        "binding_sha256": digest,
        "verification": "local-profile-name-and-supplied-extension-connection-contract",
        "platform_login": "check-in-current-browser-page",
    }


def read_json(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Do not echo input: unexpected files could contain credentials.
        fail("INVALID_INPUT", "无法读取会话契约或观察 JSON；未执行任何浏览器操作。")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, help="本轮已核对日常 Chrome 的 JSON 契约")
    parser.add_argument("--observed", required=True, help="当前实际 inventory entry 与 connection metadata 的 JSON")
    parser.add_argument("--phase", required=True, choices=PHASES)
    args = parser.parse_args(argv)
    try:
        result = guard_session(read_json(args.contract), read_json(args.observed), args.phase)
    except SessionGuardError as exc:
        print(json.dumps({"allowed": False, "code": exc.code, "phase": args.phase, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
