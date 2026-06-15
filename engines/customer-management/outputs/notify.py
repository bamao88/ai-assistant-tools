#!/usr/bin/env python3
"""
notify.py — 学员表更新摘要 / 失败告警 → lark-cli im +send

用法:
    python3 -m student_manage.notify             # 成功摘要(从 last_update_summary.json 读)
    python3 -m student_manage.notify --error "xxx失败原因"  # 失败告警 @吴湘萍
    python3 -m student_manage.notify --dry-run   # 打印不发
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/Volumes/ExtSSD2601/AI_Assistant/assistant_zh/student_manage")
CONFIG_FILE  = BASE_DIR / "feishu_config.json"
SUMMARY_FILE = BASE_DIR / "last_update_summary.json"
DIFF_FILE    = BASE_DIR / "incremental_changes.json"
LOG_DIR      = BASE_DIR / "logs"


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def send_text(chat_id: str, text: str, dry_run: bool = False) -> None:
    """text 包含 <at user_id="..."></at> 时走 --content (JSON);否则用 --text。"""
    has_at = "<at" in text
    if has_at:
        payload = json.dumps({"text": text}, ensure_ascii=False)
        cmd = [
            "lark-cli", "im", "+messages-send",
            "--profile", "zh",
            "--chat-id", chat_id,
            "--msg-type", "text",
            "--content", payload,
        ]
    else:
        cmd = [
            "lark-cli", "im", "+messages-send",
            "--profile", "zh",
            "--chat-id", chat_id,
            "--text", text,
        ]
    if dry_run:
        print("DRY RUN — 不发送:")
        print(text)
        return
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"[notify] lark-cli 发送失败: {result.stderr[:500]}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(result.stdout)
        if not data.get("ok"):
            print(f"[notify] 发送响应非 ok: {data}", file=sys.stderr)
            sys.exit(1)
    except json.JSONDecodeError:
        # 容忍空响应
        pass


def _summarize_from_feishu_sync(fs: dict) -> list[str]:
    """从 summary.feishu_sync 的 snapshot 里生成详细 diff 描述。"""
    lines = []
    created = fs.get("created", 0)
    updated = fs.get("updated", 0)
    if created == 0 and updated == 0:
        lines.append("\n(本次无飞书表改动 — 数据已同步)")
        return lines

    create_samples = fs.get("create_samples") or []
    if create_samples:
        lines.append(f"\n新增 {created} 名学员:")
        for c in create_samples[:10]:
            lines.append(f"  • {c.get('微信昵称','?')} ({c.get('wxid','')})")
        if len(create_samples) > 10:
            lines.append(f"  ...还有 {len(create_samples) - 10} 人")

    fc = fs.get("field_change_counts") or {}
    if fc:
        lines.append(f"\n更新 {updated} 条记录, 字段变化:")
        for f, c in sorted(fc.items(), key=lambda x: -x[1]):
            lines.append(f"  • {f}: {c} 条")

    enrich_samples = fs.get("enrich_samples") or []
    if enrich_samples:
        lines.append("\n富化样本 (自我介绍 / 加入的目的 / offer情况):")
        for s in enrich_samples[:5]:
            lines.append(f"  • {s.get('wxid','')} {s.get('field','')}: {s.get('value','')[:80]}")

    unm = fs.get("unmatched_remote_count", 0)
    if unm:
        lines.append(f"\n飞书有但本地无 (已离群,未删除): {unm} 人")

    return lines


def build_success_summary(summary: dict, include_diff: bool = True) -> str:
    lines = []
    lines.append("✅ 学员表周更新完成")
    lines.append(f"时间: {summary.get('updateTime','')}")

    total = summary.get("totalStudents", 0)
    lines.append(f"\n总人数: {total}")

    sd = summary.get("semesterDist", {})
    if sd:
        order = ["1期", "2期", "3期", "4期", "4.5期", "5期", "AI产品训练营", "(未知)"]
        sd_lines = [f"  {k}: {sd[k]}" for k in order if k in sd]
        lines.append("\n各期分布:")
        lines.extend(sd_lines)

    fs = summary.get("feishu_sync") or {}
    if fs:
        lines.append("\n飞书同步:")
        lines.append(f"  新增 {fs.get('created',0)} / 更新 {fs.get('updated',0)}")
        if fs.get("skipped_locked_fields"):
            lines.append(f"  锁定字段: {','.join(fs['skipped_locked_fields'])}")
        if fs.get("errors"):
            lines.append(f"  ⚠️ 错误: {len(fs['errors'])} (见日志)")

    pc = summary.get("privateChats") or {}
    if pc and pc.get("withMessages"):
        lines.append(f"\n本周新私聊: {pc.get('withMessages',0)} 人 / {pc.get('totalNewMessages',0)} 条")

    if include_diff and fs:
        lines.extend(_summarize_from_feishu_sync(fs))

    log_path = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    lines.append(f"\n日志: {log_path}")
    return "\n".join(lines)


def build_error_alert(error_msg: str, user_open_id: str) -> str:
    """带 @ 的失败告警(text 类型支持 <at user_id=\"xxx\"></at> 标记)"""
    return (
        f'<at user_id="{user_open_id}">吴湘萍</at> 学员表周更新失败\n'
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"原因:\n{error_msg[:1000]}\n\n"
        f"日志: {LOG_DIR}/{datetime.now().strftime('%Y-%m-%d')}.log"
    )


def main():
    p = argparse.ArgumentParser(description="学员表更新通知")
    p.add_argument("--error", type=str, default="", help="失败告警内容(触发 @吴湘萍)")
    p.add_argument("--dry-run", action="store_true", help="打印不发")
    args = p.parse_args()

    config = load_config()
    chat_id = config.get("chat_id")
    user_open_id = config.get("user_open_id")
    if not chat_id:
        print("[ERROR] feishu_config.json 缺 chat_id", file=sys.stderr)
        sys.exit(1)

    if args.error:
        if not user_open_id:
            print("[ERROR] feishu_config.json 缺 user_open_id(@用户需要)", file=sys.stderr)
            sys.exit(1)
        text = build_error_alert(args.error, user_open_id)
    else:
        if not SUMMARY_FILE.exists():
            print(f"[ERROR] {SUMMARY_FILE} 不存在,无法生成摘要", file=sys.stderr)
            sys.exit(1)
        summary = json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))
        text = build_success_summary(summary)

    send_text(chat_id, text, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
