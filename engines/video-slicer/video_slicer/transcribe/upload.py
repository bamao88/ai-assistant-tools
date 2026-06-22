"""上传通道：把本地音频变成公网可拉取的 URL（火山/阿里都只收 URL）。

两条通道，**单向解耦**于转写后端：
- public：免凭证的公网托管（uguu.se 主，0x0.st 兜底）。**默认通道**。
          上传站域名（uguu.se / 0x0.st）已纳入 route-bypass 的 `transcribe` 平台本地分流，
          所以"上传公域"这一步也走本地出口（复刻手动关代理那条可跑通路径，无需真关 VPN）。
- oss   ：上传到我们自己的阿里 OSS，返回 1h 签名直链。
          ⚠ 2026-06：OSS 凭证已过期，`--uploader oss` 暂不可用（续期前请用 public）。
          续期后把新凭证写回 var/credentials/aliyun.env 即可恢复；代码本身不动。

返回统一 (url, cleanup)：cleanup 可为 None；oss 通道返回删临时对象的回调。
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

UploadResult = tuple[str, Callable[[], None] | None]


def _log(m: str) -> None:
    print(m, file=sys.stderr, flush=True)


# ---------- 默认通道：公网托管（免凭证）----------

def public_upload(audio: Path, *, retries: int = 5) -> UploadResult:
    """uguu.se（主）→ 0x0.st（兜底）。串行上传（并发会限流）。"""
    audio = Path(audio)
    for a in range(retries):
        up = subprocess.run(
            ["curl", "-s", "--max-time", "600", "-F", f"files[]=@{audio}", "https://uguu.se/upload"],
            capture_output=True, text=True,
        )
        try:
            url = json.loads(up.stdout)["files"][0]["url"]
            _log(f"[upload] uguu: {url}")
            return url, None
        except Exception:  # noqa: BLE001
            _log(f"[upload] uguu 重试 {a + 1}/{retries}: {(up.stdout or '')[:120]}")
            time.sleep(8)
    for a in range(3):  # fallback 0x0.st
        r = subprocess.run(
            ["curl", "-s", "-A", "videocut/1.0", "--max-time", "600", "-F", f"file=@{audio}", "https://0x0.st"],
            capture_output=True, text=True,
        )
        url = (r.stdout or "").strip()
        if url.startswith("http"):
            _log(f"[upload] 0x0.st: {url}")
            return url, None
        time.sleep(8)
    raise RuntimeError("公网上传失败（uguu + 0x0 均未成功）")


# ---------- 备选通道：阿里 OSS（⚠ 2026-06 凭证已过期，暂不可用）----------

def oss_upload(audio: Path) -> UploadResult:
    """上传到阿里 OSS，返回 (1h 签名直链, cleanup)。需 oss2 + OSS_* 凭证。

    ⚠ 2026-06：var/credentials/aliyun.env 里的 OSS 凭证已过期，本通道暂不可用——
    续期前请用默认的 public 通道。续期后把新 OSS_* 写回该 env 文件即可恢复，
    并把下面这道过期门去掉（或加凭证有效性检查替代）。代码逻辑本身没问题。
    """
    import os

    # 过期门：早失败、给明确指引，免得后面报成晦涩的签名/鉴权错误。
    if os.environ.get("OSS_CHANNEL_EXPIRED", "1") == "1":
        raise RuntimeError(
            "oss 通道已停用：var/credentials/aliyun.env 的 OSS 凭证 2026-06 已过期。"
            "请用默认 public 通道；OSS 续期后写回新凭证并设 OSS_CHANNEL_EXPIRED=0 即可恢复。"
        )

    try:
        import oss2  # 延迟导入：public 通道无需此依赖
    except ImportError as e:  # noqa: BLE001
        raise RuntimeError("oss 通道需要 `pip install oss2`") from e

    need = ["OSS_ACCESS_KEY_ID", "OSS_ACCESS_KEY_SECRET", "OSS_BUCKET", "OSS_ENDPOINT"]
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"oss 通道缺凭证：{', '.join(missing)}（填 var/credentials/aliyun.env）")

    endpoint = os.environ["OSS_ENDPOINT"]
    if not endpoint.startswith("http"):
        endpoint = "https://" + endpoint
    auth = oss2.Auth(os.environ["OSS_ACCESS_KEY_ID"], os.environ["OSS_ACCESS_KEY_SECRET"])
    bucket = oss2.Bucket(auth, endpoint, os.environ["OSS_BUCKET"])

    key = f"videocut-asr/{int(time.time())}-{Path(audio).name}"
    _log(f"[upload] OSS put oss://{os.environ['OSS_BUCKET']}/{key}")
    bucket.put_object_from_file(key, str(audio))
    url = bucket.sign_url("GET", key, 3600, slash_safe=True)  # 1h 足够拉取

    def cleanup() -> None:
        try:
            bucket.delete_object(key)
            _log(f"[upload] OSS 清理 {key}")
        except Exception as e:  # noqa: BLE001
            _log(f"[upload] OSS 清理失败（可忽略）：{e}")

    return url, cleanup


def resolve_uploader(name: str) -> Callable[[Path], UploadResult]:
    if name == "public":
        return public_upload
    if name == "oss":
        return oss_upload
    raise ValueError(f"未知 uploader：{name}（public | oss）")
