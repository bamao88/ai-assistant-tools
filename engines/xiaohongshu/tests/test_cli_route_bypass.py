"""route-bypass preflight checks."""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import cli


def test_find_nonlocal_route_decisions_rejects_upload_cdn_on_exit_node():
    status = """
service=Wi-Fi gateway=192.168.31.1 interface=en1
route decisions for route target IPv4:
23.59.252.178   destination=23.59.252.178   gateway=192.168.31.1    interface=en1
23.59.252.200   destination=default         gateway=-               interface=utun8
"""

    bad = cli._find_nonlocal_route_decisions(status)

    assert bad == [
        "23.59.252.200   destination=default         gateway=-               interface=utun8"
    ]


def test_find_nonlocal_route_decisions_accepts_local_gateway_routes():
    status = """
service=Wi-Fi gateway=192.168.31.1 interface=en1
route decisions for route target IPv4:
23.59.252.178   destination=23.59.252.178   gateway=192.168.31.1    interface=en1
43.159.95.157   destination=43.159.95.157   gateway=192.168.31.1    interface=en1
"""

    assert cli._find_nonlocal_route_decisions(status) == []


def test_probe_xhs_https_hosts_reports_failed_upload_endpoint(monkeypatch):
    def fake_run(cmd, **kwargs):
        url = cmd[-1]
        if url == "https://ros-upload.xiaohongshu.com/":
            return subprocess.CompletedProcess(cmd, 28, stdout="remote_ip= time_connect=0", stderr="timeout")
        return subprocess.CompletedProcess(cmd, 0, stdout="remote_ip=81.69.116.102 http_code=200", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    bad = cli._probe_xhs_https_hosts()

    assert len(bad) == 1
    assert "ros-upload.xiaohongshu.com" in bad[0]


def test_probe_xhs_https_hosts_accepts_http_error_statuses(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="remote_ip=81.69.167.138 http_code=401 time_connect=0.04",
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert cli._probe_xhs_https_hosts() == []
