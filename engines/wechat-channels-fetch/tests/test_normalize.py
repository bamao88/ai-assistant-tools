from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from wcf.core import extract_feed_objects, extract_next_marker, normalize_contact, normalize_feed_object


def test_extract_feed_objects_accepts_object_field() -> None:
    response = {"data": {"object": [{"id": "1"}, {"id": "2"}], "lastBuffer": "next"}}
    assert [item["id"] for item in extract_feed_objects(response)] == ["1", "2"]
    assert extract_next_marker(response) == "next"


def test_extract_feed_objects_accepts_object_list_field() -> None:
    response = {"data": {"objectList": [{"id": "1"}]}}
    assert extract_feed_objects(response) == [{"id": "1"}]


def test_normalize_feed_object_keeps_ids_and_counts() -> None:
    normalized = normalize_feed_object(
        {
            "id": "123_456",
            "objectNonceId": "nonce",
            "nickname": "作者",
            "likeCount": "7",
            "objectDesc": {
                "description": "标题正文",
                "mediaType": 4,
                "media": [{"url": "https://example.com/video.mp4", "coverUrl": "https://example.com/c.jpg"}],
            },
        }
    )
    assert normalized["object_id"] == "123_456"
    assert normalized["nonce_id"] == "nonce"
    assert normalized["description"] == "标题正文"
    assert normalized["like_count"] == 7
    assert normalized["cover_url"] == "https://example.com/c.jpg"


def test_normalize_contact_handles_nested_contact() -> None:
    normalized = normalize_contact(
        {
            "contact": {
                "username": "finder_user",
                "nickname": "账号",
                "headUrl": "https://example.com/a.jpg",
            }
        }
    )
    assert normalized["username"] == "finder_user"
    assert normalized["nickname"] == "账号"
