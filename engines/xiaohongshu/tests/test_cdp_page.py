"""CDP Page behavior tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from xhs.cdp import Page
from xhs.errors import CDPError


def test_navigate_tolerates_session_response_timeout():
    page = object.__new__(Page)

    def send_session(method, params):
        assert method == "Page.navigate"
        assert params == {"url": "https://www.xiaohongshu.com/explore"}
        raise CDPError("等待 session 响应超时 (id=1008)")

    page._send_session = send_session

    page.navigate("https://www.xiaohongshu.com/explore")


def test_navigate_reraises_other_cdp_errors():
    page = object.__new__(Page)

    def send_session(method, params):
        raise CDPError("CDP 错误: target closed")

    page._send_session = send_session

    with pytest.raises(CDPError, match="target closed"):
        page.navigate("https://www.xiaohongshu.com/explore")
