from __future__ import annotations

from pathlib import Path
import json
import subprocess


def ffprobe_duration(video_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def render_segment(
    video_path: str,
    output_path: str,
    start: float,
    end: float,
    layout: str = "original",
    burned_subtitle_path: str | None = None,
    crf: int = 18,
    preset: str = "medium",
) -> None:
    duration = end - start
    if duration <= 0:
        raise ValueError("Segment duration must be positive.")

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        video_path,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
    ]
    video_filter = build_video_filter(layout, burned_subtitle_path)
    if video_filter:
        command.extend(["-vf", video_filter])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str(crf),
            # Screen-share footage is near-static, so x264 would otherwise spend
            # very few bits and the clip degrades hard after the platform
            # re-encodes it. yuv420p keeps it playable on every mobile target.
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            output_path,
        ]
    )
    subprocess.run(command, check=True)


def concat_segments(segment_paths: list[str], output_path: str) -> None:
    if not segment_paths:
        raise ValueError("No segments to concatenate.")
    list_path = Path(output_path).with_suffix(".concat.txt")
    list_path.write_text(
        "".join(f"file '{_escape_concat_path(path)}'\n" for path in segment_paths),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                output_path,
            ],
            check=True,
        )
    finally:
        list_path.unlink(missing_ok=True)


def build_video_filter(layout: str, subtitle_path: str | None = None) -> str | None:
    base = _layout_graph(layout)
    if not subtitle_path:
        return base or None
    subtitle = f"subtitles='{_escape_filter_path(subtitle_path)}'"
    # _blur_pad ends on a linear filter (setsar=1), so the burned captions
    # attach to the final overlaid frame and sit over the blurred bars.
    return f"{base},{subtitle}" if base else subtitle


def _layout_graph(layout: str) -> str:
    if layout == "original":
        return ""
    if layout == "vertical":
        return _blur_pad(1080, 1920)
    if layout == "square":
        return _blur_pad(1080, 1080)
    raise ValueError(f"Unsupported layout: {layout}")


def _blur_pad(width: int, height: int) -> str:
    """Fit the whole frame onto a blurred, cover-scaled copy of itself.

    A center crop of a 2160x1080 dual-pane screen-share keeps only the dead gap
    between the PPT and the speaker. Instead we scale the source to *fit* the
    target (so both panes stay visible), and fill the letterbox margins with a
    blurred, zoomed copy of the same frame.
    """
    return (
        "split=2[bg0][fg0];"
        f"[bg0]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},boxblur=20:2[bgb];"
        f"[fg0]scale={width}:{height}:force_original_aspect_ratio=decrease[fgb];"
        "[bgb][fgb]overlay=(W-w)/2:(H-h)/2,setsar=1"
    )


def _escape_filter_path(path: str) -> str:
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _escape_concat_path(path: str) -> str:
    return path.replace("'", "'\\''")

