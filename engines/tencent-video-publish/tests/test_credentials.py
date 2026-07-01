from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tvp import accounts
from tvp.core import credential_metadata, parse_cookie_string, promote_storage_state_candidate


def write_state(path: Path, cookie_name: str) -> None:
    path.write_text(
        json.dumps(
            {
                "cookies": [{"name": cookie_name, "value": "value"}],
                "origins": [],
            }
        ),
        encoding="utf-8",
    )


def read_cookie_names(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [cookie["name"] for cookie in data["cookies"]]


def test_parse_cookie_string_ignores_cookie_attributes() -> None:
    cookies = parse_cookie_string(
        "sessionid=abc; wxuin=123; Path=/; Secure; HttpOnly; SameSite=Lax"
    )

    names = [cookie["name"] for cookie in cookies]
    assert names == ["sessionid", "wxuin"]
    assert cookies[0]["httpOnly"] is True
    assert all(cookie["url"] == "https://channels.weixin.qq.com" for cookie in cookies)


def test_promote_storage_state_candidate_backs_up_and_replaces(tmp_path: Path) -> None:
    official = tmp_path / "storage_state.json"
    candidate = tmp_path / "storage_state.json.candidate_20260622_120000_000000"
    write_state(official, "old")
    write_state(candidate, "new")

    result = promote_storage_state_candidate(candidate, official)

    assert result["promoted"] is True
    assert not candidate.exists()
    assert read_cookie_names(official) == ["new"]
    backups = sorted(tmp_path.glob("storage_state.json.bak_*"))
    assert len(backups) == 1
    assert read_cookie_names(backups[0]) == ["old"]


def test_invalid_candidate_does_not_replace_official(tmp_path: Path) -> None:
    official = tmp_path / "storage_state.json"
    candidate = tmp_path / "storage_state.json.candidate_20260622_120000_000000"
    write_state(official, "old")
    candidate.write_text("{not json", encoding="utf-8")

    with pytest.raises(RuntimeError):
        promote_storage_state_candidate(candidate, official)

    assert candidate.exists()
    assert read_cookie_names(official) == ["old"]
    assert not list(tmp_path.glob("storage_state.json.bak_*"))


def test_auth_metadata_marks_chrome_profile_as_primary(tmp_path: Path) -> None:
    storage_state = tmp_path / "storage_state.json"

    metadata = credential_metadata(storage_state, "chrome_profile")
    summary = accounts.storage_state_summary(storage_state)

    assert metadata["profile_ignored"] is False
    assert metadata["auth_primary"] == "chrome_profile"
    assert metadata["storage_state_role"] == "backup"
    assert metadata["credential_source"] == "chrome_profile"
    assert summary["profile_ignored"] is False
    assert summary["auth_primary"] == "chrome_profile"
    assert summary["storage_state_role"] == "backup"


def test_latest_storage_state_backup_uses_mtime_not_name(tmp_path: Path) -> None:
    official = tmp_path / "storage_state.json"
    old_manual = tmp_path / "storage_state.json.bak_before_restore_20260622_154003"
    newer_timestamped = tmp_path / "storage_state.json.bak_20260701_121014_119410"
    write_state(official, "official")
    write_state(old_manual, "old")
    write_state(newer_timestamped, "new")
    os.utime(old_manual, (100, 100))
    os.utime(newer_timestamped, (200, 200))

    assert accounts.storage_state_backups(official) == [old_manual, newer_timestamped]
    assert accounts.latest_storage_state_backup(official) == newer_timestamped


def test_backup_storage_state_uses_private_permissions(tmp_path: Path) -> None:
    official = tmp_path / "storage_state.json"
    write_state(official, "official")
    official.chmod(0o644)

    backup = accounts.backup_storage_state(official)

    assert backup is not None
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
