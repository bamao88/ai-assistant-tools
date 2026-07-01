from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from video_slicer import pages_gen


def _page(start: int, title: str | None = None) -> dict:
    return {
        "start": start,
        "title": title or f"p{start}",
        "blocks": [
            {"type": "hero", "text": f"论点 {start}", "uw": 330},
            {"type": "key", "text": f"1. 要点 {start}"},
        ],
    }


def test_sanitize_caps_pages_to_default_max_pages():
    raw = [_page(0), _page(30), _page(60), _page(90), _page(120)]

    pages = pages_gen._sanitize(raw, duration=180, min_dwell=14)

    assert len(pages) == pages_gen.MAX_PAGES
    assert pages[0]["start"] == 0
    assert any(len(p["blocks"]) > 2 for p in pages)


def test_sanitize_still_merges_short_dwell_and_short_final_page():
    raw = [_page(0), _page(5), _page(30), _page(44)]

    pages = pages_gen._sanitize(raw, duration=50, min_dwell=14, max_pages=10)

    assert [p["start"] for p in pages] == [0, 30]
    assert len(pages[0]["blocks"]) > 2
    assert len(pages[1]["blocks"]) > 2


def test_generate_pages_max_pages_override_can_loosen_cap(monkeypatch, tmp_path):
    srt = tmp_path / "clip.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:10,000\n第一句。\n\n"
        "2\n00:00:10,000 --> 00:00:20,000\n第二句。\n",
        encoding="utf-8",
    )

    class StubClient:
        def __init__(self, *args, **kwargs):
            pass

        def chat_json(self, *args, **kwargs):
            return {"pages": [_page(0), _page(30), _page(60), _page(90), _page(120)]}

    monkeypatch.setattr(pages_gen, "OpenAICompatibleClient", StubClient)
    monkeypatch.setattr(pages_gen, "load_env_file", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pages_gen, "_discover_env_file", lambda: tmp_path / ".env")
    monkeypatch.setattr(pages_gen, "_load_system_prompt", lambda _profile: "prompt")

    default_pages = pages_gen.generate_pages(srt, duration=180, providers=("stub",))
    loose_pages = pages_gen.generate_pages(srt, duration=180, providers=("stub",), max_pages=5)

    assert len(default_pages) == 3
    assert len(loose_pages) == 5


def test_cli_help_exposes_max_pages_option():
    result = subprocess.run(
        [sys.executable, "-m", "video_slicer.pages_gen", "--help"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--max-pages" in result.stdout


def test_pages_prompt_keeps_strict_two_to_three_page_policy():
    prompt = (
        Path(__file__).parents[1]
        / "profiles"
        / "zh_main"
        / "pages_system_prompt.txt"
    ).read_text(encoding="utf-8")

    assert "2-3 页" in prompt
    assert "宁少勿多" in prompt
    assert "同一论点不因时长拆页" in prompt
    assert "4-5 页" not in prompt
    assert "越长越多" not in prompt
