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


def test_upload_video_parser_accepts_skip_route_bypass() -> None:
    args = cli.build_parser().parse_args(
        [
            "upload-video",
            "--file",
            "/tmp/video.mp4",
            "--title",
            "title",
            "--skip-route-bypass",
        ]
    )

    assert args.skip_route_bypass is True


def test_publish_item_parser_accepts_skip_route_bypass() -> None:
    args = cli.build_parser().parse_args(
        [
            "publish-item",
            "--item-dir",
            "/tmp/item",
            "--skip-route-bypass",
        ]
    )

    assert args.skip_route_bypass is True
