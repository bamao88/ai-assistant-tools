from pathlib import Path

from video_slicer import srt_fix


def test_prompt_requires_clean_filler_and_ai_typo_fix():
    prompt = (
        Path(__file__).resolve().parents[1]
        / "profiles"
        / "zh_main"
        / "srt_fix_system_prompt.txt"
    ).read_text(encoding="utf-8")

    assert "成片字幕级口语清理" in prompt
    assert "纯口水 cue" in prompt
    assert '返回空字符串 ""' in prompt
    assert "AII" in prompt
    assert "AI1" in prompt


def test_correct_cues_allows_empty_only_for_filler_cues(monkeypatch):
    monkeypatch.setattr(srt_fix, "load_env_file", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(srt_fix, "_discover_env_file", lambda: None)
    monkeypatch.setattr(
        srt_fix,
        "_call_llm",
        lambda texts, hint, providers, profile: ["AI 能做事", "", ""],
    )

    out = srt_fix.correct_cues(["AII 能做事", "啊，", "AI 产品能落地"], hint=None)

    assert out == ["AI 能做事", "", "AI 产品能落地"]
