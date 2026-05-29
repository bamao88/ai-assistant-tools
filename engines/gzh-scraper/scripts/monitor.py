#!/usr/bin/env python3
"""定时监控脚本 — 供 cron 调用。

用法：
    python monitor.py
    # 或在 crontab 中：
    # 0 */4 * * * cd /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-scraper && python scripts/monitor.py >> /tmp/gzh-monitor.log 2>&1
"""

from __future__ import annotations

import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from gzh.api_client import ExporterClient
from gzh.config import get_auth_key, get_exporter_url
from gzh.exporter_service import ensure_exporter_running
from gzh.monitor_runner import run_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("gzh-monitor-cron")


def main() -> None:
    exporter = ensure_exporter_running(get_exporter_url(), wait_seconds=45)
    if not exporter.get("success"):
        logger.error("exporter 启动失败: %s", exporter.get("error", ""))
        print(json.dumps({"success": False, "error": exporter.get("error"), "exporter": exporter}, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 1. 检查 auth 状态
    auth_key = get_auth_key()
    if not auth_key:
        logger.error("未配置 auth-key，请先运行 cli.py login + set-auth-key")
        _notify_expired("未配置 auth-key")
        sys.exit(1)

    client = ExporterClient()
    auth = client.check_auth()
    if not auth.get("authenticated"):
        logger.error("登录已过期: %s", auth.get("error", ""))
        _notify_expired(auth.get("error", "登录已过期"))
        sys.exit(1)

    logger.info("登录状态正常，用户: %s", auth.get("nick_name", ""))

    # 2. 执行监控
    result = run_monitor()
    logger.info(
        "监控完成: checked=%d, downloaded=%d",
        result.get("checked", 0),
        result.get("downloaded", 0),
    )

    # 输出 JSON 结果
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _notify_expired(reason: str) -> None:
    """登录过期通知（终端输出，可扩展为飞书/邮件通知）。"""
    msg = f"⚠️ 公众号采集登录过期: {reason}\n请运行: python cli.py login"
    logger.warning(msg)
    # TODO: 可扩展飞书 webhook 通知
    # _send_feishu_notification(msg)


if __name__ == "__main__":
    main()
