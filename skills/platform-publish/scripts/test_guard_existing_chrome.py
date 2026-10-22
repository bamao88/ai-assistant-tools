"""Meaningful offline contract checks; no browser or platform interaction."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from guard_existing_chrome import PHASES, SessionGuardError, guard_session


class SessionGuardTests(unittest.TestCase):
    def setUp(self):
        # Disk metadata is an offline fixture, not the user's Chrome session.
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.chrome_root = Path(self.temporary_directory.name) / "Chrome"
        (self.chrome_root / "Default").mkdir(parents=True)
        (self.chrome_root / "Profile 1").mkdir()
        self.local_state = self.chrome_root / "Local State"
        self.info_cache = {"Default": {"name": "用户1"}, "Profile 1": {"name": "MiaoDX"}}
        self.write_info_cache()
        root_patch = patch("guard_existing_chrome.daily_chrome_root", return_value=self.chrome_root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        # Representative CUA extension inventory shape; IDs are per-task fixtures.
        browser = {
            "family": "chrome", "id": "2", "name": "Chrome", "type": "extension",
            "profileName": "用户1", "metadata": {"extensionInstanceId": "daily-extension-fixture"},
        }
        self.contract = {
            "schema_version": 1, "host": "local", "browser": browser,
            "profile": {"user_data_dir": str(self.chrome_root), "profile_directory": "Default"},
        }
        self.observed = {
            "browser": deepcopy(browser),
            "connection": {
                "host": "local", "transport": "extension", "provider": "cua",
                "browser_id": "2", "extension_instance_id": "daily-extension-fixture",
                "existing_session": True, "headless": False,
                "launched_new_browser": False, "created_new_context": False, "restored_cookies": False,
            },
        }

    def write_info_cache(self):
        self.local_state.write_text(json.dumps({"profile": {"info_cache": self.info_cache}}), encoding="utf-8")

    def reject(self, code, *, contract=None, observed=None):
        with self.assertRaises(SessionGuardError) as raised:
            guard_session(contract or self.contract, observed or self.observed, "before_upload")
        self.assertEqual(raised.exception.code, "PUBLISH_SESSION_" + code)

    def test_approved_existing_extension_all_phases(self):
        digests = []
        for phase in PHASES:
            result = guard_session(self.contract, self.observed, phase)
            self.assertTrue(result["allowed"])
            digests.append(result["binding_sha256"])
        self.assertEqual(len(set(digests)), 1)

    def test_historical_cdp_route_rejected_even_when_visible(self):
        self.observed["connection"].update(transport="cdp", cdp_endpoint="http://127.0.0.1:9230", headless=False)
        self.reject("WRONG_TRANSPORT")

    def test_script_profile_rejected_even_if_extension_label_claimed(self):
        self.observed["connection"]["user_data_dir"] = str(Path.home() / ".xhs/accounts/猫猫电视机/chrome-profile")
        self.reject("SCRIPT_PROFILE")

    def test_contract_cannot_authorize_script_directory(self):
        self.contract["profile"]["user_data_dir"] = str(Path.home() / ".xhs/chrome-profile")
        self.reject("SCRIPT_PROFILE")

    def test_nonexistent_profile_is_not_created(self):
        self.contract["profile"]["profile_directory"] = "nonexistent-publish-guard-test-profile"
        self.reject("UNVERIFIED_PROFILE")
        self.assertFalse((self.chrome_root / self.contract["profile"]["profile_directory"]).exists())

    def test_default_directory_cannot_bind_another_extension_profile_name(self):
        # Matching browser/connection IDs alone cannot authorize a wrong disk profile.
        self.contract["browser"]["profileName"] = "MiaoDX"
        self.observed["browser"]["profileName"] = "MiaoDX"
        self.reject("PROFILE_NAME_MISMATCH")

    def test_matching_nondefault_profile_directory_is_supported(self):
        self.contract["profile"]["profile_directory"] = "Profile 1"
        self.contract["browser"]["profileName"] = "MiaoDX"
        self.observed["browser"]["profileName"] = "MiaoDX"
        self.assertTrue(guard_session(self.contract, self.observed, "before_connect")["allowed"])

    def test_duplicate_profile_names_cannot_bind_a_disk_directory(self):
        self.info_cache["Profile 1"]["name"] = "用户1"
        self.write_info_cache()
        self.reject("PROFILE_AMBIGUOUS")

    def test_missing_local_state_fails_closed(self):
        self.local_state.unlink()
        self.reject("PROFILE_METADATA_UNVERIFIED")

    def test_unregistered_existing_directory_fails_closed(self):
        del self.info_cache["Default"]
        self.write_info_cache()
        self.reject("PROFILE_DIRECTORY_UNREGISTERED")

    def test_remote_host_rejected(self):
        self.observed["connection"]["host"] = "MiDX02"
        self.reject("REMOTE_HOST")

    def test_iab_rejected(self):
        self.observed["browser"].update(type="iab", family="chromium")
        self.reject("WRONG_BROWSER")

    def test_other_chrome_profile_or_extension_rejected(self):
        for field, value in (("id", "4"), ("profileName", "MiaoDX"), ("metadata", {"extensionInstanceId": "another-instance"})):
            observed = deepcopy(self.observed)
            observed["browser"][field] = value
            self.reject("BROWSER_CHANGED", observed=observed)

    def test_new_session_and_recovery_rejected(self):
        for field in ("headless", "launched_new_browser", "created_new_context", "restored_cookies"):
            observed = deepcopy(self.observed)
            observed["connection"][field] = True
            self.reject("FORBIDDEN_RECOVERY", observed=observed)

    def test_unknown_recovery_metadata_fails_closed(self):
        del self.observed["connection"]["launched_new_browser"]
        self.reject("FORBIDDEN_RECOVERY")

    def test_cdp_parameter_cannot_hide_under_extension_transport(self):
        self.observed["connection"]["debugging_port"] = 9230
        self.reject("SCRIPT_CONNECTION")

    def test_connection_must_match_selected_inventory(self):
        self.observed["connection"]["browser_id"] = "4"
        self.reject("CONNECTION_MISMATCH")

    def test_profile_path_if_observed_must_match(self):
        self.observed["connection"].update(user_data_dir=str(self.chrome_root), profile_directory="Default")
        self.assertTrue(guard_session(self.contract, self.observed, "before_upload")["allowed"])
        self.observed["connection"]["profile_directory"] = "Profile 1"
        self.reject("SCRIPT_PROFILE")

    def test_new_inventory_ids_can_be_locked_for_a_new_task(self):
        for value in (self.contract["browser"], self.observed["browser"]):
            value["id"] = "17"
            value["metadata"]["extensionInstanceId"] = "fresh-per-task-instance"
        self.observed["connection"].update(browser_id="17", extension_instance_id="fresh-per-task-instance")
        self.assertTrue(guard_session(self.contract, self.observed, "before_connect")["allowed"])

    def test_cli_failure_is_nonzero_and_does_not_echo_bad_json(self):
        script = Path(__file__).with_name("guard_existing_chrome.py")
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / "contract.json"
            observed = Path(directory) / "observed.json"
            contract.write_text(json.dumps(self.contract), encoding="utf-8")
            observed.write_text("not-json confidential-example-value", encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), "--contract", str(contract), "--observed", str(observed), "--phase", "before_connect"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["code"], "PUBLISH_SESSION_INVALID_INPUT")
        self.assertNotIn("confidential-example-value", result.stderr)


if __name__ == "__main__":
    unittest.main()
