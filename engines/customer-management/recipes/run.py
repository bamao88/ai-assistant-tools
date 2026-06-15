#!/usr/bin/env python3
"""
run.py — 学员主数据周更新顶层入口

⚠️ DEPRECATED (2026-05-18)：第 5 步飞书 sync 已停用。
    旧"学员表" tbl2LOMxbMV4ipwe 不再维护。飞书唯一真源 = 客户管理表 tblfCYoeornDw0XF。
    写飞书统一走 `workflow.student_employment_tracking.sync_to_feishu`。
    这个脚本只保留 1/2/3/4 步本地主数据维护；--auto 模式禁用。

执行序列:
    1. extract_students.py    群成员/wxid/手机号(规则)
    2. llm_enrich.py          ★ Kimi per-student 增量富化(只扫上次之后的新消息)
    3. update_csv.py          (复用 update_and_notify.py 的 CSV+summary 逻辑)
    4. ❌ sync_to_feishu.py   DEPRECATED — 不再执行
    5. notify.py              成功摘要发飞书（可选）

    注: 旧 merge_refer (合并 refer/*.xlsx 推广员/消费) 已于 2026-06-15 删除。
        手机号/推广员/消费改飞书侧人工维护;自我介绍/客户画像改走 LLM analyze。

用法:
    python3 -m student_manage.run --dry-run     # 1/2/3-dry/4 本地预览
    python3 -m student_manage.run --skip-llm    # 跳过 LLM 只跑规则 pipeline
    python3 -m student_manage.run --auto        # ⚠️ DEPRECATED：会拒绝执行
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

# engine 根（recipes/ → up 1）：子进程 `-m` 调用以此为 cwd/PYTHONPATH 锚点。
ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_ROOT))
import config

BASE_DIR = config.BASE_DIR
LOG_DIR  = config.LOG_DIR


def log(text: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [run] {text}"
    print(line)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_step(name: str, cmd: list[str]) -> None:
    """跑一步,失败直接 raise。stdout/stderr 实时打印 + 进日志。"""
    log(f"━━━ {name} ━━━")
    log(f"$ {' '.join(cmd)}")
    log_path = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    with log_path.open("a", encoding="utf-8") as logf:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, cwd=str(ENGINE_ROOT))
        for line in proc.stdout:
            sys.stdout.write(line)
            logf.write(line)
        rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"{name} 退出码 {rc}")
    log(f"✓ {name} 完成")


def notify_error(reason: str) -> None:
    """发飞书失败告警 @吴湘萍。本身失败时只打印,不再级联。"""
    try:
        subprocess.run(
            ["python3", "-m", "outputs.notify", "--error", reason],
            timeout=30,
            check=False,
            cwd=str(ENGINE_ROOT),
        )
    except Exception as e:
        log(f"[ALARM_FAILED] notify 调用失败: {e}")


def main():
    p = argparse.ArgumentParser(description="学员表周更新")
    p.add_argument("--auto", action="store_true", help="全自动:真推真发")
    p.add_argument("--dry-run", action="store_true", help="不调 Kimi、不推飞书、不发通知")
    p.add_argument("--bootstrap", action="store_true", help="LLM 全量(忽略 progress)")
    p.add_argument("--skip-llm", action="store_true", help="跳过 LLM 步")
    args = p.parse_args()

    is_apply = args.auto and not args.dry_run

    # —— DEPRECATION GUARD (2026-05-18) ——
    # 旧"学员表" tbl2LOMxbMV4ipwe 不再维护；--auto 模式会推旧表，已禁用。
    if is_apply:
        log("✗ --auto 模式已 DEPRECATED：")
        log("  旧学员表 tbl2LOMxbMV4ipwe 不再维护。")
        log("  写飞书统一走 `python3 -m outputs.sync_to_feishu --apply`")
        log("  （唯一真源 = 客户管理表 tblfCYoeornDw0XF）")
        log("")
        log("  本脚本现在只用于本地主数据维护。建议改用：")
        log("    python3 -m recipes.run --dry-run   # 本地预览")
        log("    python3 -m recipes.run --skip-llm  # 跳过 LLM 只跑规则")
        sys.exit(2)

    log(f"═══════════════════════════════════════")
    log(f"学员主数据更新 开始 | mode: DRY-RUN（本地维护）")
    log(f"═══════════════════════════════════════")

    try:
        # 1. 规则抽取
        run_step("Step 1: extract_students",
                 ["python3", str(BASE_DIR / "extract_students.py")])

        # 2. LLM 富化(可选跳过/dry-run)
        if args.skip_llm:
            log("Step 3: llm_enrich SKIPPED (--skip-llm)")
        else:
            llm_cmd = ["python3", "-m", "student_manage.llm_enrich"]
            if args.bootstrap:
                llm_cmd.append("--bootstrap")
            if args.dry_run:
                llm_cmd.append("--dry-run")
            run_step("Step 3: llm_enrich", llm_cmd)

        # 4. 规则 enrich (xlsx self-intro + semester)
        run_step("Step 4a: enrich_students (rules)",
                 ["python3", str(BASE_DIR / "enrich_students.py")])

        # 4b. CSV 导出 + summary
        run_step("Step 4b: update_and_notify (CSV + summary)",
                 ["python3", str(BASE_DIR / "update_and_notify.py")])

        # 5. ❌ DEPRECATED: 旧学员表 sync 已停用。写飞书走客户管理表 sync。
        log("Step 5: sync_to_feishu SKIPPED (DEPRECATED — 旧学员表不再维护)")
        log("       写飞书改走 `python3 -m workflow.student_employment_tracking.sync_to_feishu --apply`")

        # 6. notify 在 dry-run 模式下也不发
        log("Step 6: notify SKIPPED (only local maintenance, no feishu push)")

    except Exception as e:
        log(f"✗ 失败: {e}")
        log(traceback.format_exc())
        if is_apply:
            notify_error(f"{e}\n\n(完整 traceback 见日志)")
        sys.exit(1)

    log(f"═══════════════════════════════════════")
    log(f"学员表周更新 完成")
    log(f"═══════════════════════════════════════")


if __name__ == "__main__":
    main()
