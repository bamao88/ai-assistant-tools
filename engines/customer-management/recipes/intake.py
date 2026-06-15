#!/usr/bin/env python3
"""intake.py — 新学员入表配方：gather → 判断 → 写回（§5/§6）。

把「把这个新学员整理进表」落成一条命令：
  1. gather  : 对 worksheet 里每个 wxid 拉读取侧 bundle（本地+飞书镜像+微信+付款+diff），
               让 agent/人看清「这人飞书有没有行、缺什么」再决定怎么写（判断环节）。
  2. 写回    : 把 worksheet 交给 outputs.intake_writer，按 wxid 写客户管理表 + all_student.json
               （只填空 + 多选 append + 付款凭证上传；幂等）。

worksheet schema 见 outputs/intake_writer.py（wxid -> {name,ziwo,qudao,mark5,phone,pay,...}）。
人读 runbook：`new_student_intake_runbook.md`（P5 合并进 skill references）。

默认 dry-run（gather 只读 + intake_writer 不加 --apply）。`--apply` 才真写（授权门）。

用法：
  python3 -m recipes.intake <worksheet.json>            # gather 上下文 + intake dry-run
  python3 -m recipes.intake <worksheet.json> --apply    # 授权门：真写飞书+本地
  python3 -m recipes.intake <worksheet.json> --no-gather # 跳过 gather 上下文（只写回）
"""

from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

# engine 根（recipes/ → up 1）入 sys.path。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from recipes import gather as gather_mod  # noqa: E402


def _gather_context(wxids: list[str]) -> None:
    """步骤 1：对 worksheet 的 wxid 拉 gather bundle（只读）并人读打印（判断输入）。"""
    if not wxids:
        return
    args = SimpleNamespace(wxid=wxids, new=False, group=None, analyze=False,
                           pretty=True, limit=0)
    bundle = gather_mod.gather(args)
    print(gather_mod.render_pretty(bundle), file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description="intake — 新学员入表（gather → 判断 → 写回）")
    p.add_argument("worksheet", help="worksheet JSON 路径（schema 见 outputs/intake_writer）")
    p.add_argument("--apply", action="store_true", help="授权门：真写飞书+本地")
    p.add_argument("--no-gather", action="store_true", help="跳过 gather 上下文打印")
    args = p.parse_args()

    ws_path = Path(args.worksheet)
    if not ws_path.exists():
        print(f"[ERROR] worksheet 不存在: {ws_path}", file=sys.stderr)
        return 1

    if not args.no_gather:
        try:
            ws = json.loads(ws_path.read_text(encoding="utf-8"))
            wxids = list(ws.keys()) if isinstance(ws, dict) else []
            print("=== 步骤 1/2: gather 上下文（判断输入，只读）===", file=sys.stderr)
            _gather_context(wxids)
        except Exception as e:
            print(f"[WARN] gather 上下文失败（继续写回）: {e}", file=sys.stderr)

    print(f"\n=== 步骤 2/2: intake_writer 写回（{'APPLY' if args.apply else 'dry-run'}）===", file=sys.stderr)
    forwarded = [str(ws_path)]
    if args.apply:
        forwarded.append("--apply")
    sys.argv = ["outputs.intake_writer"] + forwarded
    try:
        runpy.run_module("outputs.intake_writer", run_name="__main__", alter_sys=True)
    except SystemExit as e:
        return int(e.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
