"""quick-research：一键跑 info + transcript + keyframes + 写 RESEARCH.md。"""

from __future__ import annotations

import logging
from pathlib import Path

from .info import fetch_info
from .keyframes import extract_keyframes
from .storage import video_dir_from_url
from .transcript import fetch_transcript

logger = logging.getLogger(__name__)


def quick_research(
    url: str,
    langs: list[str],
    keyframes_mode: str = "interval:60",
    whisper_model: str = "base",
    allow_whisper: bool = True,
) -> dict:
    """一键研究一个视频。

    Args:
        langs: 字幕语言优先级，如 ["zh", "en"]
        keyframes_mode: "interval:<秒数>" | "scene-change" | "none"
        allow_whisper: 字幕抓不到时是否回退 Whisper
    """
    # 1. info + 封面
    info = fetch_info(url, download_thumbnail=True)
    video_id = info["video_id"]
    d = video_dir_from_url(url, video_id)

    # 2. transcript
    try:
        transcript = fetch_transcript(
            url,
            langs=langs,
            force_whisper=False,
            whisper_model=whisper_model,
        )
    except Exception as e:
        logger.warning("transcript 失败: %s", e)
        transcript = {"success": False, "error": str(e), "source": "none"}

    # 如果字幕抓不到且允许 Whisper，已经在 fetch_transcript 里尝试过了
    # （force_whisper=False 时它会自动降级）。所以这里不用再跑一次。

    # 3. keyframes
    kf_result: dict | None = None
    if keyframes_mode != "none":
        try:
            if keyframes_mode.startswith("interval:"):
                interval = float(keyframes_mode.split(":", 1)[1])
                kf_result = extract_keyframes(url, mode="interval", interval=interval)
            elif keyframes_mode == "scene-change":
                kf_result = extract_keyframes(url, mode="scene-change")
            else:
                logger.warning("未知 keyframes_mode=%s，跳过抽帧", keyframes_mode)
        except Exception as e:
            logger.warning("keyframes 失败: %s", e)
            kf_result = {"success": False, "error": str(e)}

    # 4. 写 RESEARCH.md
    research_md = _render_research_md(info, transcript, kf_result, keyframes_mode)
    research_path = d / "RESEARCH.md"
    research_path.write_text(research_md, encoding="utf-8")

    return {
        "success": True,
        "video_id": video_id,
        "platform": info["platform"],
        "video_dir": str(d),
        "research_md": str(research_path),
        "info": {
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "webpage_url": info.get("webpage_url"),
            "thumbnail_path": info.get("thumbnail_path"),
        },
        "transcript": {
            "source": transcript.get("source"),
            "srt_path": transcript.get("srt_path"),
            "txt_path": transcript.get("txt_path"),
            "error": transcript.get("error"),
        },
        "keyframes": kf_result,
    }


def _render_research_md(
    info: dict,
    transcript: dict,
    keyframes: dict | None,
    keyframes_mode: str,
) -> str:
    """组装 RESEARCH.md 内容。"""
    lines: list[str] = []
    lines.append(f"# 视频研究：{info.get('title', '(无标题)')}")
    lines.append("")
    lines.append("## 基础信息")
    lines.append(f"- **标题**：{info.get('title')}")
    lines.append(f"- **作者/频道**：{info.get('uploader')}")
    duration = info.get("duration")
    if duration:
        mins, secs = divmod(int(duration), 60)
        lines.append(f"- **时长**：{mins}:{secs:02d}")
    if info.get("upload_date"):
        d = info["upload_date"]
        lines.append(f"- **发布日期**：{d[:4]}-{d[4:6]}-{d[6:]}")
    lines.append(f"- **URL**：{info.get('webpage_url')}")
    lines.append(f"- **平台**：{info.get('platform')}")
    if info.get("view_count") is not None:
        lines.append(f"- **播放量**：{info['view_count']:,}")
    lines.append("")

    if info.get("description"):
        desc = info["description"].strip()
        if len(desc) > 800:
            desc = desc[:800] + "…"
        lines.append("## 作者简介/视频描述")
        lines.append("")
        lines.append(desc)
        lines.append("")

    # 转写
    lines.append("## 字幕/转写")
    if transcript.get("success"):
        source_label = {
            "manual": "✅ 人工字幕",
            "auto": "🔸 自动生成字幕",
            "whisper": "🤖 Whisper 本地转写",
        }.get(transcript.get("source"), transcript.get("source"))
        lines.append(f"- **来源**：{source_label}")
        lines.append(f"- **纯文本**：`{transcript.get('txt_path')}`")
        lines.append(f"- **带时间戳**：`{transcript.get('srt_path')}`")
    else:
        lines.append(f"- ⚠️ 未获取到转写：{transcript.get('error', '未知原因')}")
    lines.append("")

    # 关键帧
    lines.append("## 关键帧截图")
    if keyframes and keyframes.get("success"):
        lines.append(f"- **模式**：{keyframes_mode}")
        lines.append(f"- **目录**：`{keyframes.get('keyframes_dir')}`")
        lines.append(f"- **帧数**：{keyframes.get('frame_count')}")
        lines.append("")
        lines.append("| 时间戳 | 文件 |")
        lines.append("|--------|------|")
        for f in keyframes.get("frames", [])[:30]:
            name = Path(f["path"]).name
            lines.append(f"| {f['timestamp']} | `{name}` |")
        if keyframes.get("frame_count", 0) > 30:
            lines.append(f"| … | （共 {keyframes['frame_count']} 帧，详见目录） |")
    elif keyframes is None:
        lines.append("- 已跳过（keyframes_mode=none）")
    else:
        lines.append(f"- ⚠️ 抽帧失败：{keyframes.get('error', '未知')}")
    lines.append("")

    lines.append("## 使用提示")
    lines.append("")
    lines.append("- 引用视频时：标题 + 作者 + URL（见上）")
    lines.append("- 配图：直接从 `keyframes/` 里选时间戳对应的 PNG")
    lines.append("- 找具体段落：`search --video-id ... --keyword ...` 回溯时间戳")
    lines.append("")

    return "\n".join(lines)
