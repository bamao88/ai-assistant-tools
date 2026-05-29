#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TRANSCRIPT_SCRIPT = SCRIPT_DIR / "fetch_tencent_meeting_transcripts_stable.py"
VIDEO_SCRIPT = SCRIPT_DIR / "download_tencent_meeting_videos_stable.py"


def add_sources_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "sources",
        nargs="*",
        help="Tencent Meeting share URLs, or local files that contain those URLs.",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Additional URL or file path. Can be repeated.",
    )
    parser.add_argument(
        "--codes",
        nargs="*",
        help="Optional subset of short codes to process.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified Tencent Meeting downloader for transcripts and recording videos."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    transcripts = subparsers.add_parser(
        "transcripts",
        help="Download transcripts with API-first strategy and Chrome fallback.",
    )
    add_sources_arguments(transcripts)
    transcripts.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "tencent_meeting_transcripts",
        help="Directory for transcripts, manifests, and diagnostics.",
    )
    transcripts.add_argument(
        "--strategy",
        choices=("auto", "api", "chrome"),
        default="auto",
        help="auto=API first then Chrome fallback, api=API only, chrome=Chrome only.",
    )
    transcripts.add_argument(
        "--initial-limit",
        type=int,
        default=120,
        help="Paragraph count requested on the first public transcript API page.",
    )
    transcripts.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds for Tencent API calls.",
    )
    transcripts.add_argument(
        "--settle-seconds",
        type=float,
        default=3.0,
        help="Seconds to wait after opening each page in Chrome.",
    )

    videos = subparsers.add_parser(
        "videos",
        help="Download recording videos from the public sharing download endpoint.",
    )
    add_sources_arguments(videos)
    videos.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "tencent_meeting_videos",
        help="Directory for videos, manifests, and diagnostics.",
    )
    videos.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    videos.add_argument(
        "--metadata-only",
        action="store_true",
        help="Resolve download URLs and write manifests without downloading media files.",
    )
    videos.add_argument(
        "--include-audio",
        action="store_true",
        help="Download audio files when the endpoint returns them.",
    )
    videos.add_argument(
        "--video-type",
        "--video-types",
        action="append",
        dest="video_types",
        choices=("video_main", "video_stream_1", "video_stream_2", "all"),
        default=None,
        help="Video variants to download. Default: video_main.",
    )

    both = subparsers.add_parser(
        "both",
        help="Run transcript export and video download sequentially for the same inputs.",
    )
    add_sources_arguments(both)
    both.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "tencent_meeting_bundle",
        help="Root directory. Transcripts go to transcripts/, videos go to videos/.",
    )
    both.add_argument(
        "--strategy",
        choices=("auto", "api", "chrome"),
        default="auto",
        help="Transcript strategy.",
    )
    both.add_argument(
        "--initial-limit",
        type=int,
        default=120,
        help="Transcript API initial paragraph limit.",
    )
    both.add_argument(
        "--transcript-timeout",
        type=int,
        default=30,
        help="Transcript API timeout in seconds.",
    )
    both.add_argument(
        "--video-timeout",
        type=int,
        default=60,
        help="Video HTTP timeout in seconds.",
    )
    both.add_argument(
        "--settle-seconds",
        type=float,
        default=3.0,
        help="Seconds to wait after opening each page in Chrome for transcript fallback.",
    )
    both.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only resolve video metadata, do not download media bytes.",
    )
    both.add_argument(
        "--include-audio",
        action="store_true",
        help="Download audio files alongside videos when available.",
    )
    both.add_argument(
        "--video-type",
        "--video-types",
        action="append",
        dest="video_types",
        choices=("video_main", "video_stream_1", "video_stream_2", "all"),
        default=None,
        help="Video variants to download. Default: video_main.",
    )

    return parser


def append_common_inputs(command: list[str], args: argparse.Namespace) -> None:
    for item in args.sources:
        command.append(item)
    for item in args.input:
        command.extend(["--input", item])
    if args.codes:
        command.extend(["--codes", *args.codes])


def run_command(command: list[str]) -> int:
    print(shlex.join(command), flush=True)
    return subprocess.run(command, check=False).returncode


def run_transcripts(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(TRANSCRIPT_SCRIPT),
        "--output-dir",
        str(args.output_dir),
        "--strategy",
        args.strategy,
        "--initial-limit",
        str(args.initial_limit),
        "--timeout",
        str(args.timeout),
        "--settle-seconds",
        str(args.settle_seconds),
    ]
    append_common_inputs(command, args)
    return run_command(command)


def run_videos(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(VIDEO_SCRIPT),
        "--output-dir",
        str(args.output_dir),
        "--timeout",
        str(args.timeout),
    ]
    if args.metadata_only:
        command.append("--metadata-only")
    if args.include_audio:
        command.append("--include-audio")
    for video_type in args.video_types or ["video_main"]:
        command.extend(["--video-type", video_type])
    append_common_inputs(command, args)
    return run_command(command)


def run_both(args: argparse.Namespace) -> int:
    transcript_args = argparse.Namespace(
        sources=args.sources,
        input=args.input,
        codes=args.codes,
        output_dir=args.output_dir / "transcripts",
        strategy=args.strategy,
        initial_limit=args.initial_limit,
        timeout=args.transcript_timeout,
        settle_seconds=args.settle_seconds,
    )
    video_args = argparse.Namespace(
        sources=args.sources,
        input=args.input,
        codes=args.codes,
        output_dir=args.output_dir / "videos",
        timeout=args.video_timeout,
        metadata_only=args.metadata_only,
        include_audio=args.include_audio,
        video_types=args.video_types or ["video_main"],
    )

    transcript_code = run_transcripts(transcript_args)
    video_code = run_videos(video_args)
    return transcript_code or video_code


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "transcripts":
        return run_transcripts(args)
    if args.command == "videos":
        return run_videos(args)
    if args.command == "both":
        return run_both(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
