"""video-research 统一 CLI 入口。

子命令：info / transcript / transcribe-local / keyframes / search / quick-research
输出：JSON（ensure_ascii=False）
Exit code：0=成功 / 1=前置失败（如 ffmpeg 未装）/ 2=运行错误
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

# 让脚本能直接 `python scripts/cli.py ...` 运行
sys.path.insert(0, str(Path(__file__).parent))

from video_research.info import fetch_info  # noqa: E402
from video_research.keyframes import extract_keyframes, extract_keyframes_from_local  # noqa: E402
from video_research.local_transcribe import transcribe_local_media  # noqa: E402
from video_research.quick_research import quick_research  # noqa: E402
from video_research.transcript import fetch_transcript, search_transcript  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("video-research")


def _output(data: dict, exit_code: int = 0) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def _check_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        _output(
            {
                "success": False,
                "error": "未检测到 ffmpeg。请先安装：macOS `brew install ffmpeg`",
            },
            exit_code=1,
        )


# ---------- 子命令 ----------


def cmd_info(args: argparse.Namespace) -> None:
    data = fetch_info(args.url, download_thumbnail=not args.no_thumbnail)
    _output(data)


def cmd_transcript(args: argparse.Namespace) -> None:
    _check_ffmpeg()
    langs = [s.strip() for s in args.lang.split(",") if s.strip()]
    data = fetch_transcript(
        args.url,
        langs=langs,
        force_whisper=args.force_whisper,
        whisper_model=args.whisper_model,
    )
    _output(data, exit_code=0 if data.get("success") else 2)


def cmd_transcribe_local(args: argparse.Namespace) -> None:
    _check_ffmpeg()
    glossary = _split_csv_args(args.glossary)
    replacements = _parse_replacements(args.replace)
    language = None if args.lang.lower() in {"auto", "none"} else args.lang
    data = transcribe_local_media(
        inputs=args.input,
        output_dir=args.out_dir,
        language=language,
        whisper_model=args.whisper_model,
        device=args.device,
        compute_type=args.compute_type,
        cpu_threads=args.cpu_threads,
        vad_filter=not args.no_vad,
        initial_prompt=args.initial_prompt,
        glossary=glossary,
        replacements=replacements,
    )
    _output(data, exit_code=0 if data.get("success") else 2)


def cmd_keyframes(args: argparse.Namespace) -> None:
    _check_ffmpeg()
    if args.video_id:
        if not args.at:
            _output(
                {"success": False, "error": "--video-id 模式必须配合 --at 使用"},
                exit_code=2,
            )
        at_list = [s.strip() for s in args.at.split(",") if s.strip()]
        data = extract_keyframes_from_local(args.video_id, at_list)
        _output(data)

    if not args.url:
        _output({"success": False, "error": "缺少 --url 或 --video-id"}, exit_code=2)

    mode_count = sum([bool(args.at), bool(args.interval), bool(args.scene_change)])
    if mode_count != 1:
        _output(
            {
                "success": False,
                "error": "三选一：--at / --interval / --scene-change",
            },
            exit_code=2,
        )

    if args.at:
        at_list = [s.strip() for s in args.at.split(",") if s.strip()]
        data = extract_keyframes(args.url, mode="at", at_list=at_list)
    elif args.interval:
        data = extract_keyframes(
            args.url, mode="interval", interval=args.interval, max_frames=args.max_frames
        )
    else:
        data = extract_keyframes(
            args.url,
            mode="scene-change",
            scene_threshold=args.scene_threshold,
            max_frames=args.max_frames,
        )
    _output(data)


def cmd_search(args: argparse.Namespace) -> None:
    data = search_transcript(args.video_id, args.keyword, context_chars=args.context)
    _output(data, exit_code=0 if data.get("success") else 2)


def cmd_quick_research(args: argparse.Namespace) -> None:
    _check_ffmpeg()
    langs = [s.strip() for s in args.lang.split(",") if s.strip()]
    data = quick_research(
        args.url,
        langs=langs,
        keyframes_mode=args.keyframes,
        whisper_model=args.whisper_model,
    )
    _output(data)


def _split_csv_args(values: list[str] | None) -> list[str]:
    items: list[str] = []
    for value in values or []:
        items.extend(part.strip() for part in value.split(",") if part.strip())
    return items


def _parse_replacements(values: list[str] | None) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"--replace 格式应为 FROM=TO，收到: {value}")
        old, new = value.split("=", 1)
        old, new = old.strip(), new.strip()
        if not old:
            raise ValueError(f"--replace 左侧不能为空，收到: {value}")
        replacements[old] = new
    return replacements


# ---------- parser ----------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-research",
        description="视频素材研究：字幕/转写 + 关键帧 + 元数据",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # info
    sub = subparsers.add_parser("info", help="抓取视频元数据 + 下载封面")
    sub.add_argument("--url", required=True, help="视频 URL")
    sub.add_argument("--no-thumbnail", action="store_true", help="不下载封面图")
    sub.set_defaults(func=cmd_info)

    # transcript
    sub = subparsers.add_parser(
        "transcript", help="抓字幕或 Whisper 转写"
    )
    sub.add_argument("--url", required=True, help="视频 URL")
    sub.add_argument(
        "--lang", default="zh,en", help="语言优先级（逗号分隔），默认 zh,en"
    )
    sub.add_argument(
        "--force-whisper",
        action="store_true",
        help="跳过字幕抓取，强制 Whisper 转写",
    )
    sub.add_argument(
        "--whisper-model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper 模型（默认 base，~150MB）",
    )
    sub.set_defaults(func=cmd_transcript)

    # transcribe-local
    sub = subparsers.add_parser(
        "transcribe-local", help="本地音视频文件转逐字稿"
    )
    sub.add_argument(
        "--input",
        action="append",
        required=True,
        help="本地视频/音频文件路径；多个文件重复传 --input",
    )
    sub.add_argument(
        "--out-dir",
        help="输出目录；默认写入 data/local_transcripts/<时间戳>",
    )
    sub.add_argument(
        "--lang",
        default="zh",
        help="转写语言代码，默认 zh；传 auto 自动识别",
    )
    sub.add_argument(
        "--whisper-model",
        default="base",
        help="faster-whisper 模型名或 HuggingFace repo（默认 base）",
    )
    sub.add_argument("--device", default="cpu", help="Whisper device，默认 cpu")
    sub.add_argument(
        "--compute-type",
        default="int8",
        help="faster-whisper compute_type，默认 int8",
    )
    sub.add_argument(
        "--cpu-threads",
        type=int,
        default=0,
        help="CPU 线程数；0 使用 faster-whisper 默认值",
    )
    sub.add_argument("--no-vad", action="store_true", help="关闭静音过滤")
    sub.add_argument(
        "--initial-prompt",
        help="传给 Whisper 的初始提示词，用于改善领域术语识别",
    )
    sub.add_argument(
        "--glossary",
        action="append",
        help="领域术语，逗号分隔；可重复传入",
    )
    sub.add_argument(
        "--replace",
        action="append",
        help="转写后做确定性术语替换，格式 FROM=TO；可重复传入",
    )
    sub.set_defaults(func=cmd_transcribe_local)

    # keyframes
    sub = subparsers.add_parser(
        "keyframes", help="抽关键帧（三种模式三选一）"
    )
    sub.add_argument("--url", help="视频 URL（与 --video-id 二选一）")
    sub.add_argument(
        "--video-id",
        help="已下载过的视频 key（如 youtube_xxx），配合 --at 使用",
    )
    sub.add_argument(
        "--at",
        help='指定时间戳列表，逗号分隔。格式 SS / MM:SS / HH:MM:SS。例："00:30,01:45"',
    )
    sub.add_argument(
        "--interval", type=float, help="每 N 秒抽一帧（浮点秒）"
    )
    sub.add_argument(
        "--scene-change", action="store_true", help="场景切换检测抽帧"
    )
    sub.add_argument(
        "--scene-threshold",
        type=float,
        default=0.3,
        help="场景切换阈值 0-1（默认 0.3）",
    )
    sub.add_argument(
        "--max-frames", type=int, default=60, help="总帧数上限（默认 60）"
    )
    sub.set_defaults(func=cmd_keyframes)

    # search
    sub = subparsers.add_parser(
        "search", help="在已下载的 transcript 里搜关键词"
    )
    sub.add_argument(
        "--video-id",
        required=True,
        help="视频 key（如 youtube_xxx，对应 data/ 目录名）",
    )
    sub.add_argument("--keyword", required=True, help="搜索关键词")
    sub.add_argument(
        "--context", type=int, default=60, help="命中上下文字符数（默认 60）"
    )
    sub.set_defaults(func=cmd_search)

    # quick-research
    sub = subparsers.add_parser(
        "quick-research", help="一键研究：info + transcript + keyframes + RESEARCH.md"
    )
    sub.add_argument("--url", required=True, help="视频 URL")
    sub.add_argument("--lang", default="zh,en", help="字幕语言优先级")
    sub.add_argument(
        "--keyframes",
        default="interval:60",
        help="关键帧策略：interval:<秒数> | scene-change | none（默认 interval:60）",
    )
    sub.add_argument(
        "--whisper-model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
    )
    sub.set_defaults(func=cmd_quick_research)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        logger.exception("执行失败")
        _output({"success": False, "error": str(e)}, exit_code=2)


if __name__ == "__main__":
    main()
