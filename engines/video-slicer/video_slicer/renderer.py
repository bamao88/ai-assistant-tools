from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from .ffmpeg import concat_segments, render_segment
from .llm import LLMConfigError, OpenAICompatibleClient
from .models import Clip, ClipPlan
from .subtitles import (
    SubtitleTempFile,
    align_translation_cues,
    extract_cues,
    load_optional_zh_cues,
    make_bilingual_cues,
    offset_cues,
    split_long_cues,
    write_srt,
)
from .transcript import Cue


def render_plan(
    video: str,
    plan: ClipPlan,
    cues: list[Cue],
    out_dir: str = "outputs",
    out_file: str | None = None,
    join: bool | None = None,
    layout: str | None = None,
    subtitle_mode: str | None = None,
    source_language: str | None = None,
    zh_transcript: str | None = None,
    crf: int = 18,
    preset: str = "medium",
    max_sub_chars: int = 16,
) -> list[str]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    should_join = plan.defaults.join if join is None else join
    selected_layout = layout or plan.defaults.layout
    selected_subtitle = subtitle_mode or plan.defaults.subtitle
    language = source_language or plan.source_language or "unknown"
    zh_cues = load_optional_zh_cues(zh_transcript)

    if should_join:
        output_path = out_file or str(output_dir / "joined.mp4")
        render_joined(
            video, plan, cues, output_path, selected_layout, selected_subtitle,
            language, zh_cues, crf, preset, max_sub_chars,
        )
        return [output_path]

    outputs = []
    for clip in plan.clips:
        output_path = str(output_dir / f"{clip.id}.mp4")
        clip_start, clip_end = padded_range(clip, plan)
        clip_cues = extract_cues(cues, clip_start, clip_end)
        subtitle_cues = resolve_subtitle_cues(clip_cues, selected_subtitle, language, zh_cues, clip_start, clip_end)
        write_sidecar_subtitles(output_dir, clip.id, selected_subtitle, subtitle_cues)
        if should_burn(selected_subtitle):
            with SubtitleTempFile(split_long_cues(subtitle_cues, max_sub_chars)) as subtitle_path:
                render_segment(video, output_path, clip_start, clip_end, selected_layout, subtitle_path, crf, preset)
        else:
            render_segment(video, output_path, clip_start, clip_end, selected_layout, crf=crf, preset=preset)
        outputs.append(output_path)
    return outputs


def render_joined(
    video: str,
    plan: ClipPlan,
    cues: list[Cue],
    output_path: str,
    layout: str,
    subtitle_mode: str,
    language: str,
    zh_cues: list[Cue] | None,
    crf: int = 18,
    preset: str = "medium",
    max_sub_chars: int = 16,
) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    joined_subtitle_cues: list[Cue] = []
    running_offset = 0.0
    with TemporaryDirectory() as temp_dir:
        segment_paths = []
        for index, clip in enumerate(plan.clips, start=1):
            clip_start, clip_end = padded_range(clip, plan)
            clip_cues = extract_cues(cues, clip_start, clip_end)
            subtitle_cues = resolve_subtitle_cues(clip_cues, subtitle_mode, language, zh_cues, clip_start, clip_end)
            joined_subtitle_cues.extend(offset_cues(subtitle_cues, running_offset))
            segment_path = str(Path(temp_dir) / f"segment-{index:03d}.mp4")
            if should_burn(subtitle_mode):
                with SubtitleTempFile(split_long_cues(subtitle_cues, max_sub_chars)) as subtitle_path:
                    render_segment(video, segment_path, clip_start, clip_end, layout, subtitle_path, crf, preset)
            else:
                render_segment(video, segment_path, clip_start, clip_end, layout, crf=crf, preset=preset)
            segment_paths.append(segment_path)
            running_offset += clip_end - clip_start
        concat_segments(segment_paths, output_path)
    if subtitle_mode in {"soft", "auto", "bilingual"}:
        write_srt(joined_subtitle_cues, Path(output_path).with_suffix(".srt"))


def padded_range(clip: Clip, plan: ClipPlan) -> tuple[float, float]:
    return (
        max(0, clip.start - plan.defaults.padding_start_seconds),
        clip.end + plan.defaults.padding_end_seconds,
    )


def resolve_subtitle_cues(
    clip_cues: list[Cue],
    subtitle_mode: str,
    language: str,
    zh_cues: list[Cue] | None,
    clip_start: float,
    clip_end: float,
) -> list[Cue]:
    if subtitle_mode == "none":
        return []
    if subtitle_mode == "soft":
        return clip_cues
    wants_bilingual = subtitle_mode == "bilingual" or (
        language == "en" and subtitle_mode in {"auto", "burned"}
    )
    if not wants_bilingual:
        return clip_cues
    if zh_cues is not None:
        translated_cues = extract_cues(zh_cues, clip_start, clip_end)
        if translated_cues:
            return align_translation_cues(clip_cues, translated_cues)
    if not OpenAICompatibleClient.available():
        raise LLMConfigError(
            "Bilingual subtitles require OPENAI_API_KEY and VIDEO_SLICER_MODEL, "
            "or pass --zh-transcript, or use --subtitle soft/none."
        )
    client = OpenAICompatibleClient()
    translated = client.translate_texts([cue.text for cue in clip_cues], target_language="zh")
    return make_bilingual_cues(clip_cues, translated)


def write_sidecar_subtitles(output_dir: Path, clip_id: str, subtitle_mode: str, cues: list[Cue]) -> None:
    if subtitle_mode in {"soft", "auto", "bilingual"} and cues:
        suffix = "bilingual" if subtitle_mode in {"auto", "bilingual"} else "source"
        write_srt(cues, output_dir / f"{clip_id}.{suffix}.srt")


def should_burn(subtitle_mode: str) -> bool:
    return subtitle_mode in {"auto", "burned"}
