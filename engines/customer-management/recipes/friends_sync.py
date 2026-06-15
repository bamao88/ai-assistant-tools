#!/usr/bin/env python3
"""friends_sync.py — 好友刷新建行配方：sync + audit + merge 三步合一（§5）。

死脚本时代这是三个独立脚本，必须人手按顺序跑 sync → audit → merge，**漏跑后两步
就会在飞书留下与空 wxid 老行重复的新行**。本配方把三步绑成一个原子流程，人不再
可能忘记补跑 audit/merge。

三步（resolve「对齐」→ 写回，§5）
--------------------------------
  1. sync   : outputs.sync_friends_to_feishu —— 好友名单 → 飞书（UPDATE 已存在 / CREATE 缺行）
  2. audit  : health_check duplicate_creates 的 scan —— 审计这批 CREATE 是否与空 wxid 老行重复
  3. merge  : health_check duplicate_creates 的 merge —— PATCH 老行 wxid / DELETE 重复新行

默认 dry-run（三步都只出 plan，绝不写飞书）。`--apply` 才依次真写（授权门）：
sync.apply → 重新拉表 → audit → merge.apply。各步走各自模块的幂等写回。

⚠️ audit/merge 必须看到 sync **刚 CREATE 出来的新行**才能判重，所以 --apply 模式下
audit/merge 强制从 **live Feishu** 读（--source live），不是本地镜像（镜像还没刷新）。
dry-run 模式下 audit/merge 读本地镜像即可（只是预演，无新行）。

用法：
  python3 -m recipes.friends_sync --role zh2               # 三步全 dry-run（默认）
  python3 -m recipes.friends_sync --role assistant
  python3 -m recipes.friends_sync --role zh2 --apply       # 授权门：三步依次真写
"""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

# engine 根（recipes/ → up 1）入 sys.path。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from capabilities.resolve import core  # noqa: E402
from recipes import health_check  # noqa: E402


def _run_sync_friends(role: str, apply: bool, limit: int) -> int:
    """步骤 1：调 outputs.sync_friends_to_feishu 的 main()（沿用其 argparse + 写回）。"""
    argv = [sys.argv[0], "--role", role]
    if apply:
        argv.append("--apply")
    if limit:
        argv += ["--limit", str(limit)]
    saved = sys.argv
    sys.argv = argv
    try:
        runpy.run_module("outputs.sync_friends_to_feishu", run_name="__main__", alter_sys=True)
    except SystemExit as e:
        return int(e.code or 0)
    finally:
        sys.argv = saved
    return 0


def _run_dup(role: str, apply: bool, source: str) -> int:
    """步骤 2+3：audit（scan）+ merge（auto），复用 health_check duplicate_creates。"""
    args = SimpleNamespace(defect="duplicate_creates", apply=apply, source=source,
                           role=role, loose=False, list=False)
    return health_check.run_defect("duplicate_creates", args)


def main() -> int:
    p = argparse.ArgumentParser(
        description="friends_sync — 好友同步 sync+audit+merge 三步合一（默认 dry-run）")
    p.add_argument("--role", choices=["assistant", "zh2"], default="assistant")
    p.add_argument("--apply", action="store_true", help="授权门：三步依次真写飞书")
    p.add_argument("--limit", type=int, default=0, help="sync 步只处理前 N 个（测试）")
    args = p.parse_args()

    print(f"\n=== friends_sync [{args.role}] {'APPLY' if args.apply else 'DRY-RUN'} ===", file=sys.stderr)

    print("\n--- 步骤 1/3: sync 好友名单 → 飞书 ---", file=sys.stderr)
    rc = _run_sync_friends(args.role, args.apply, args.limit)
    if rc not in (0, None):
        print(f"[friends_sync] sync 步 rc={rc}，中止后续 audit/merge", file=sys.stderr)
        return rc

    # apply 后 audit/merge 必须看 live（镜像未刷新看不到刚 CREATE 的新行）；dry-run 读镜像即可。
    dup_source = "live" if args.apply else "mirror"
    print(f"\n--- 步骤 2/3: audit 重复（读侧={dup_source}）---", file=sys.stderr)
    print(f"--- 步骤 3/3: merge 自动合并（{'APPLY' if args.apply else 'dry-run'}）---", file=sys.stderr)
    rc2 = _run_dup(args.role, args.apply, dup_source)

    print(f"\n=== friends_sync 完成（三步合一，无需再人手补跑 audit/merge）===", file=sys.stderr)
    return rc2


if __name__ == "__main__":
    sys.exit(main())
