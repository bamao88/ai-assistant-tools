import pytest

from video_slicer.llm import parse_json_response


def test_parse_json_response_from_fenced_block():
    data = parse_json_response("""```json
{"version": 1, "clips": []}
```""")

    assert data["version"] == 1


def test_parse_json_response_rejects_non_object():
    with pytest.raises(ValueError, match="JSON object"):
        parse_json_response("[1, 2, 3]")

