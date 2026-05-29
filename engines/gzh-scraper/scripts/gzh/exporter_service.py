#!/usr/bin/env python3
"""Start and health-check the local wechat-article-exporter service."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXPORTER_DIR = os.path.join(ROOT_DIR, "wechat-article-exporter")
RUNTIME_DIR = os.path.join(ROOT_DIR, ".runtime")
PID_FILE = os.path.join(RUNTIME_DIR, "exporter.pid")
LOG_FILE = os.path.join(RUNTIME_DIR, "exporter.log")


def ensure_exporter_running(
    base_url: str = "http://localhost:3000",
    wait_seconds: int = 45,
) -> dict[str, Any]:
    """Ensure exporter is reachable, starting it in the background if needed."""
    base_url = (base_url or "http://localhost:3000").rstrip("/")

    if is_exporter_reachable(base_url):
        return {"success": True, "started": False, "url": base_url}

    if not os.path.isdir(EXPORTER_DIR):
        return {
            "success": False,
            "error": f"未找到 wechat-article-exporter 目录: {EXPORTER_DIR}",
            "url": base_url,
        }

    os.makedirs(RUNTIME_DIR, exist_ok=True)

    try:
        _ensure_node_deps()
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "error": f"安装 exporter 依赖失败: {exc}",
            "log": LOG_FILE,
            "url": base_url,
        }

    existing_pid = _read_pid()
    if existing_pid and _pid_running(existing_pid):
        started = False
        proc: subprocess.Popen[bytes] | None = None
    else:
        try:
            proc = _start_exporter_process()
            started = True
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"启动 exporter 失败: {exc}",
                "log": LOG_FILE,
                "url": base_url,
            }

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_exporter_reachable(base_url):
            return {
                "success": True,
                "started": started,
                "url": base_url,
                "pid": _read_pid(),
                "log": LOG_FILE,
            }
        if proc is not None and proc.poll() is not None:
            return {
                "success": False,
                "error": f"exporter 进程提前退出，退出码 {proc.returncode}",
                "log": LOG_FILE,
                "url": base_url,
            }
        time.sleep(1)

    return {
        "success": False,
        "error": f"等待 exporter 启动超时（{wait_seconds}s）",
        "log": LOG_FILE,
        "url": base_url,
        "pid": _read_pid(),
    }


def is_exporter_reachable(base_url: str, timeout: int = 2) -> bool:
    """Return True if the exporter HTTP service accepts requests."""
    try:
        req = Request(base_url.rstrip("/") + "/")
        req.add_header("User-Agent", "gzh-scraper-healthcheck")
        with urlopen(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 500
    except HTTPError as exc:
        return exc.code < 500
    except (URLError, TimeoutError, OSError):
        return False


def _ensure_node_deps() -> None:
    node_modules = os.path.join(EXPORTER_DIR, "node_modules")
    if os.path.isdir(node_modules):
        return

    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n[{time.ctime()}] Installing exporter dependencies\n")
        subprocess.run(
            ["corepack", "enable"],
            cwd=EXPORTER_DIR,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
        subprocess.run(
            ["yarn", "install"],
            cwd=EXPORTER_DIR,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )


def _start_exporter_process() -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env.setdefault("BROWSER", "none")
    env.setdefault("HOST", "127.0.0.1")

    with open(LOG_FILE, "ab", buffering=0) as log:
        log.write(f"\n[{time.ctime()}] Starting exporter\n".encode("utf-8"))
        proc = subprocess.Popen(
            ["yarn", "dev"],
            cwd=EXPORTER_DIR,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(proc.pid))
    return proc


def _read_pid() -> int | None:
    try:
        with open(PID_FILE, encoding="utf-8") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure wechat-article-exporter is running")
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--wait", type=int, default=45)
    args = parser.parse_args()

    result = ensure_exporter_running(args.base_url, args.wait)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
