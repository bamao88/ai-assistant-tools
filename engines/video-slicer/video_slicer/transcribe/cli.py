"""字级转写 CLI：音频/视频 → words.json（字级词表）。

    python -m video_slicer.transcribe --audio /path/clip.mp4 --out-dir var/zh_main/asr
    python -m video_slicer.transcribe --audio-url https://host/a.mp3 --backend aliyun
    python -m video_slicer.transcribe --audio a.mp4 --uploader oss   # 切阿里 OSS 上传通道

默认：火山主、阿里兜底、公网上传。产出 words.json 可直接喂 twostage/resolve.load_paraformer_words。

转录前自动跑 route-bypass，把**整条转录链路**钉到本地网关出口（与发布同一套机制）：
国内 ASR API（火山/阿里）+ public 上传站（uguu.se/0x0.st）。这等价于"手动关代理"那条
能跑通的路径——上传公域音频 + 调 API 全程走本地，但 VPN 照开、不影响 LLM 翻墙。
`--skip-route-bypass` 可关。路由是优化项不是硬前置：钉不上只告警、不挡转录。

注：`--uploader oss`（阿里 OSS）凭证 2026-06 已过期，暂不可用；请用默认 public。
"""
from __future__ import annotations

import argparse
import json
import os
import platform as _platform
import shlex
import subprocess
import sys
import tempfile

from . import DEFAULT_ENV, REPO_ROOT, transcribe_audio

# 复用发布那套 route-bypass：平台包装器 + transcribe 平台域名组。
_PREFLIGHT_SCRIPT = REPO_ROOT / "engines" / "route-bypass" / "scripts" / "publish-network-preflight.zsh"
_PREFLIGHT_PLATFORM = "transcribe"


def _log(m: str) -> None:
    print(m, file=sys.stderr, flush=True)


def _route_bypass_preflight() -> None:
    """把国内 ASR API 域名钉到本地出口。需要 sudo 改路由表；非 TTY 直跑失败时退到
    osascript 管理员授权。任何失败只告警、不抛错（转录失败只是慢，不该挡住出字幕）。"""
    script = _PREFLIGHT_SCRIPT
    if not script.exists():
        _log(f"[transcribe] ⚠ route-bypass 前置脚本不存在，跳过本地分流：{script}")
        return

    try:
        r = subprocess.run(
            [str(script), _PREFLIGHT_PLATFORM, "apply"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180, check=False,
        )
    except Exception as e:  # noqa: BLE001
        _log(f"[transcribe] ⚠ route-bypass 前置异常（继续转录）：{e}")
        return

    if r.returncode == 0:
        _log("[transcribe] 本地网络分流已应用：国内 ASR 走本地出口")
        return

    # 直跑要 sudo，非 TTY 拿不到密码 → macOS 退到管理员授权弹框（与发布 reference 同一段）。
    needs_admin = "sudo:" in r.stderr or "password is required" in r.stderr
    if _platform.system() == "Darwin" and needs_admin:
        log_path = os.path.join(tempfile.gettempdir(), "transcribe-route-bypass-apply.log")
        command = (
            f"{shlex.quote(str(script))} {shlex.quote(_PREFLIGHT_PLATFORM)} apply "
            f"> {shlex.quote(log_path)} 2>&1; status=$?; "
            f"tail -200 {shlex.quote(log_path)}; exit $status"
        )
        try:
            ar = subprocess.run(
                ["osascript", "-e",
                 f"do shell script {json.dumps(command)} with administrator privileges"],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=240, check=False,
            )
        except Exception as e:  # noqa: BLE001
            _log(f"[transcribe] ⚠ route-bypass 管理员授权异常（继续转录）：{e}")
            return
        if ar.returncode == 0:
            _log("[transcribe] 本地网络分流已应用（管理员授权）：国内 ASR 走本地出口")
            return
        r = ar

    tail = (r.stderr or r.stdout or "").strip()[-300:]
    _log(f"[transcribe] ⚠ route-bypass 前置未生效（继续转录，可能走海外较慢）：{tail}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="字级转写：音频/视频 → 字级词表 JSON（火山主·阿里兜底）")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--audio", help="本地音频/视频（视频会自动抽 mono16k mp3 再上传）")
    src.add_argument("--audio-url", dest="audio_url", help="已有公网音频直链（跳过抽音频+上传）")
    ap.add_argument("--backend", default="volc", choices=["volc", "aliyun"], help="主后端（默认火山）")
    ap.add_argument("--fallback", default="aliyun", choices=["aliyun", "volc", "none"], help="兜底后端（默认阿里；none 关闭）")
    ap.add_argument("--uploader", default="public", choices=["public", "oss"], help="上传通道（默认公网 uguu/0x0，已走本地分流；oss=阿里存储，⚠ 2026-06 凭证过期暂不可用）")
    ap.add_argument("--out-dir", dest="out_dir", help="落 words.json 的目录")
    ap.add_argument("--env-file", dest="env_file", default=str(DEFAULT_ENV), help="KEY=VALUE 凭证文件")
    ap.add_argument("--skip-route-bypass", dest="skip_route_bypass", action="store_true",
                    help="跳过转录前本地网络分流（route-bypass）。路由已钉过或不在意国内出口时用")
    a = ap.parse_args(argv)

    if not a.skip_route_bypass:
        _route_bypass_preflight()

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
