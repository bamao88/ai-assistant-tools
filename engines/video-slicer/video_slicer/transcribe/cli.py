"""字级转写 CLI：音频/视频 → words.json（字级词表）。

    python -m video_slicer.transcribe --audio /path/clip.mp4 --out-dir var/zh_main/asr
    python -m video_slicer.transcribe --audio-url https://host/a.mp3 --backend aliyun
    python -m video_slicer.transcribe --audio a.mp4 --uploader oss   # 切阿里 OSS 上传通道

默认：火山主、阿里兜底、公网上传。产出 words.json 可直接喂 twostage/resolve.load_paraformer_words。
"""
from __future__ import annotations

import argparse
import sys

from . import DEFAULT_ENV, transcribe_audio


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="字级转写：音频/视频 → 字级词表 JSON（火山主·阿里兜底）")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--audio", help="本地音频/视频（视频会自动抽 mono16k mp3 再上传）")
    src.add_argument("--audio-url", dest="audio_url", help="已有公网音频直链（跳过抽音频+上传）")
    ap.add_argument("--backend", default="volc", choices=["volc", "aliyun"], help="主后端（默认火山）")
    ap.add_argument("--fallback", default="aliyun", choices=["aliyun", "volc", "none"], help="兜底后端（默认阿里；none 关闭）")
    ap.add_argument("--uploader", default="public", choices=["public", "oss"], help="上传通道（默认公网；oss=阿里存储，备选）")
    ap.add_argument("--out-dir", dest="out_dir", help="落 words.json 的目录")
    ap.add_argument("--env-file", dest="env_file", default=str(DEFAULT_ENV), help="KEY=VALUE 凭证文件")
    a = ap.parse_args(argv)

    try:
        result = transcribe_audio(
            audio=a.audio,
            audio_url=a.audio_url,
            backend=a.backend,
            fallback=a.fallback,
            uploader=a.uploader,
            env_file=a.env_file,
            out_dir=a.out_dir,
        )
    except Exception as e:  # noqa: BLE001
        print(f"✗ 转写失败：{e}", file=sys.stderr)
        return 2

    print(f"✓ {result['model']}：{len(result['words'])} 字，"
          f"跨度 {result['words'][0]['begin_time']/1000:.1f}–{result['words'][-1]['end_time']/1000:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
