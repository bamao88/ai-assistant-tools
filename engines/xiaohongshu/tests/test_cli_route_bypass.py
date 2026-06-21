"""route-bypass preflight checks."""
from __future__ import annotations

import sys
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
