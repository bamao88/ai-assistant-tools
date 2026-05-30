from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .ffmpeg import ffprobe_duration
from .models import build_manual_plan, load_clip_plan, write_clip_plan
from .planner import generate_ai_clip_plan
from .renderer import render_plan
from .timecode import parse_clip_range
from .transcript import detect_language, parse_transcript
from .validation import validate_clip_plan, validate_input_file


def load_env_file(env_file: Path) -> None:
    """Populate os.environ from a .env file (only keys not already set).

    Mirrors the knowledge_ingest pipeline's loader so the same shared .env —
    typically reached via the .env symlink in this tool's directory — provides
    MINIMAX_*/KIMI_* credentials to both tools from one source of truth.
    """
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _discover_env_file() -> Path:
    override = os.environ.get("VIDEO_SLICER_ENV_FILE")
    if override:
        return Path(override)
    # Package layout: video_slicer/cli.py -> tool root holds the .env (symlink).
    return Path(__file__).resolve().parent.parent / ".env"


def main(argv: list[str] | None = None) -> int:
    load_env_file(_discover_env_file())
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            command_validate(args)
        elif args.command == "plan":
            command_plan(args)
        elif args.command == "render":
            command_render(args)
        else:
            parser.print_help()
            return 2
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-slicer")
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate", help="Validate local video and transcript inputs.")
    validate.add_argument("--video", required=True)
    validate.add_argument("--transcript", required=True)

    plan = subparsers.add_parser("plan", help="Create a clip_plan.json.")
    plan.add_argument("--video", required=True)
    plan.add_argument("--transcript", required=True)
    plan.add_argument("--mode", choices=["manual", "query", "auto"], required=True)
    plan.add_argument("--query")
    plan.add_argument("--clip", action="append", default=[])
    plan.add_argument("--out", default="clip_plan.json")
    plan.add_argument("--layout", choices=["original", "vertical", "square"], default="original")
    plan.add_argument("--subtitle", choices=["auto", "none", "soft", "burned", "bilingual"], default="auto")
    plan.add_argument("--join", action="store_true")
    plan.add_argument("--max-clips", type=int, default=3, help="精选上限，通常 1-3 条。")
    plan.add_argument("--host", help="主讲人姓名；只切此人说话的内容（留空则取出现最多的说话人）。")

    render = subparsers.add_parser("render", help="Render clips from a plan or --clip ranges.")
    render.add_argument("--video", required=True)
    render.add_argument("--transcript", required=True)
    render.add_argument("--clip-plan")
    render.add_argument("--clip", action="append", default=[])
    render.add_argument("--out-dir", default="outputs")
    render.add_argument("--out")
    render.add_argument("--join", action="store_true")
    render.add_argument("--layout", choices=["original", "vertical", "square"])
    render.add_argument("--subtitle", choices=["auto", "none", "soft", "burned", "bilingual"])
    render.add_argument("--source-language", choices=["auto", "en", "zh", "unknown"], default="auto")
    render.add_argument("--zh-transcript")
    render.add_argument("--crf", type=int, default=18, help="x264 quality (lower = higher quality/bitrate).")
    render.add_argument("--preset", default="medium", help="x264 speed/efficiency preset.")
    render.add_argument(
        "--max-sub-chars",
        type=int,
        default=16,
        help="Split burned-in caption cues longer than this many characters.",
    )

    return parser


def command_validate(args: argparse.Namespace) -> None:
    validate_input_file(args.video, "Video")
    validate_input_file(args.transcript, "Transcript")
    cues = parse_transcript(args.transcript)
    duration = ffprobe_duration(args.video)
    print(f"video_duration={duration:.3f}s")
    print(f"transcript_cues={len(cues)}")
    print(f"transcript_language={detect_language(cues, args.transcript)}")


def command_plan(args: argparse.Namespace) -> None:
    validate_input_file(args.video, "Video")
    validate_input_file(args.transcript, "Transcript")
    cues = parse_transcript(args.transcript)
    language = detect_language(cues, args.transcript)
    if args.mode == "manual":
        if not args.clip:
            raise ValueError("manual mode requires at least one --clip START-END.")
        ranges = [parse_clip_range(value) for value in args.clip]
        plan = build_manual_plan(
            video=args.video,
            transcript=args.transcript,
            language=language,
            ranges=ranges,
            layout=args.layout,
            subtitle=args.subtitle,
            join=args.join,
        )
    else:
        plan = generate_ai_clip_plan(
            video=args.video,
            transcript=args.transcript,
            cues=cues,
            mode=args.mode,
            query=args.query,
            max_clips=args.max_clips,
            layout=args.layout,
            subtitle=args.subtitle,
            join=args.join,
            host=args.host,
        )
    duration = ffprobe_duration(args.video)
    validate_clip_plan(plan, video_duration=duration, cues=cues)
    write_clip_plan(plan, args.out)
    print(f"wrote {args.out} ({len(plan.clips)} clips)")
    note = getattr(plan, "selection_note", "")
    if note:
        print(f"筛选说明: {note}")


def command_render(args: argparse.Namespace) -> None:
    validate_input_file(args.video, "Video")
    validate_input_file(args.transcript, "Transcript")
    cues = parse_transcript(args.transcript)
    language = detect_language(cues, args.transcript) if args.source_language == "auto" else args.source_language
    if args.clip_plan:
        plan = load_clip_plan(args.clip_plan)
        if not plan.source_language:
            plan.source_language = language
    else:
        if not args.clip:
            raise ValueError("render requires --clip-plan or at least one --clip START-END.")
        ranges = [parse_clip_range(value) for value in args.clip]
        plan = build_manual_plan(
            video=args.video,
            transcript=args.transcript,
            language=language,
            ranges=ranges,
            layout=args.layout or "original",
            subtitle=args.subtitle or "auto",
            join=args.join,
        )
    duration = ffprobe_duration(args.video)
    validate_clip_plan(plan, video_duration=duration, cues=cues)
    outputs = render_plan(
        video=args.video,
        plan=plan,
        cues=cues,
        out_dir=args.out_dir,
        out_file=args.out,
        join=args.join or None,
        layout=args.layout,
        subtitle_mode=args.subtitle,
        source_language=language,
        zh_transcript=args.zh_transcript,
        crf=args.crf,
        preset=args.preset,
        max_sub_chars=args.max_sub_chars,
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    raise SystemExit(main())

