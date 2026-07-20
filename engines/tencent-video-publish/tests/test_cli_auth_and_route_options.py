from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import cli
from tvp import core


def test_ensure_shipinhao_route_bypass_can_be_skipped(monkeypatch) -> None:
    def fail_if_called() -> dict:
        raise AssertionError("route-bypass verification should not run when skipped")

    monkeypatch.setattr(core, "verify_shipinhao_route_bypass", fail_if_called)

    assert core.ensure_shipinhao_route_bypass(skip_route_bypass=True) == {
        "skipped": True,
        "mode": "current-egress",
        "reason": "cli --skip-route-bypass",
    }


def test_ensure_shipinhao_route_bypass_can_be_skipped_by_env(monkeypatch) -> None:
    def fail_if_called() -> dict:
        raise AssertionError("route-bypass verification should not run when skipped")

    monkeypatch.setenv("PLATFORM_PUBLISH_NETWORK_MODE", "current-egress")
    monkeypatch.setattr(core, "verify_shipinhao_route_bypass", fail_if_called)

    assert core.ensure_shipinhao_route_bypass() == {
        "skipped": True,
        "mode": "current-egress",
        "reason": "env PLATFORM_PUBLISH_NETWORK_MODE=current-egress",
    }


def test_upload_video_parser_accepts_auth_and_route_options() -> None:
    args = cli.build_parser().parse_args(
        [
            "upload-video",
            "--file",
            "/tmp/video.mp4",
            "--title",
            "title",
            "--skip-route-bypass",
            "--login-if-needed",
            "--login-timeout",
            "240",
        ]
    )

    assert args.skip_route_bypass is True
    assert args.login_if_needed is True
    assert args.login_timeout == 240


def test_publish_item_parser_accepts_auth_and_route_options() -> None:
    args = cli.build_parser().parse_args(
        [
            "publish-item",
            "--item-dir",
            "/tmp/item",
            "--skip-route-bypass",
            "--login-if-needed",
            "--login-timeout",
            "240",
        ]
    )

    assert args.skip_route_bypass is True
    assert args.login_if_needed is True
    assert args.login_timeout == 240


def test_check_login_parser_storage_fallback_is_opt_in() -> None:
    default_args = cli.build_parser().parse_args(["check-login"])
    fallback_args = cli.build_parser().parse_args(["check-login", "--storage-fallback"])

    assert default_args.storage_fallback is False
    assert fallback_args.storage_fallback is True
