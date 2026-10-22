#!/usr/bin/env python3
"""Generate a periodic skill governance audit report.

This is a reporting tool. It does not modify skills or registry state.
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry.yaml"
REPORT_DIR = ROOT / "var" / "review" / "skill-audits"

ARCH_DOC_BY_SKILL = {
    "platform-fetch": "doc/platform-fetch-architecture.md",
    "Agent-Publish": "doc/publish-architecture.md",
    "content-creator-research": "doc/content-creator-research-architecture.md",
    "content-production-prep": "doc/publish-architecture.md",
    "video-clip": "doc/video-skill-architecture.md",
    "customer-management": "doc/customer-management-architecture.md",
    "content-topic-planning": "doc/content-topic-planning-architecture.md",
    "assistant_zh_video-cover": "doc/video-cover-architecture.md",
}


def run_cmd(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def git_dirty_paths() -> set[str]:
    code, output = run_cmd(["git", "status", "--porcelain"])
    if code != 0:
        return set()
    paths: set[str] = set()
    for line in output.splitlines():
        if not line.strip():
            continue
        raw = line[3:].strip()
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.add(raw.strip('"'))
    return paths


def git_commit_touch_counts(days: int) -> Counter[str]:
    code, output = run_cmd(
        ["git", "log", f"--since={days}.days", "--name-only", "--pretty=format:--COMMIT--"]
    )
    counts: Counter[str] = Counter()
    if code != 0:
        return counts
    current: set[str] = set()
    for line in output.splitlines() + ["--COMMIT--"]:
        line = line.strip()
        if not line:
            continue
        if line == "--COMMIT--":
            for path in current:
                counts[path] += 1
            current = set()
        else:
            current.add(line)
    return counts


def path_touched(path: str, prefixes: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)


def skill_prefixes(skill: dict, engine_paths: dict[str, str]) -> list[str]:
    prefixes = [skill["source"]]
    for engine_id in skill.get("uses_engines", []) or []:
        engine_path = engine_paths.get(engine_id)
        if engine_path:
            prefixes.append(engine_path)
    return prefixes


def feedback_status_counts() -> tuple[Counter[str], list[str]]:
    code, output = run_cmd([sys.executable, "scripts/check-feedback.py"])
    counts: Counter[str] = Counter()
    missing: list[str] = []
    in_missing = False
    for line in output.splitlines():
        if line.startswith("  ") and ":" in line and not in_missing:
            key, value = line.strip().split(":", 1)
            if value.strip().isdigit():
                counts[key] = int(value.strip())
        elif line == "Missing status:":
            in_missing = True
        elif in_missing and line.startswith("  "):
            missing.append(line.strip())
    return counts, missing


def official_docs_links_present() -> bool:
    doc = ROOT / "doc" / "skill-governance-architecture.md"
    if not doc.exists():
        return False
    text = doc.read_text(encoding="utf-8", errors="replace")
    required = [
        "https://developers.openai.com/codex/build-skills",
        "https://developers.openai.com/codex/skills-and-plugins",
        "https://developers.openai.com/codex/agent-configuration/agents-md",
        "https://docs.anthropic.com/en/docs/claude-code/skills",
    ]
    return all(url in text for url in required)


def join_names(names: list[str]) -> str:
    return "、".join(f"`{name}`" for name in names)


def build_recommendations(
    *,
    check_tools_code: int,
    rows: list[dict],
    by_score: list[tuple[int, str, list[str], list[str]]],
    feedback_missing: list[str],
    retained_deprecated: list[str],
    official_docs_ok: bool,
) -> list[str]:
    recommendations: list[str] = []

    if check_tools_code != 0:
        recommendations.append("先处理 `check-tools.py` 的 error/warning；这是结构硬门。")

    row_by_name = {row["name"]: row for row in rows}
    missing_arch_by_priority = [
        name
        for _score, name, _reasons, _long_refs in by_score
        if row_by_name.get(name, {}).get("layer") in {"L1", "L2"}
        and not row_by_name.get(name, {}).get("arch_doc")
    ]
    if missing_arch_by_priority:
        names = missing_arch_by_priority[:3]
        recommendations.append(
            f"优先给 {join_names(names)} 补架构 runbook；这些 L1/L2 工作流仍缺少维护说明书。"
        )

    high_dirty = [
        row["name"]
        for row in sorted(rows, key=lambda r: (-r["dirty"], r["name"]))
        if row["dirty"] >= 10
    ]
    if high_dirty:
        names = high_dirty[:3]
        recommendations.append(
            f"收口 {join_names(names)} 的未提交相关改动；先分清哪些是正常进行中，哪些已经需要整理或提交。"
        )

    long_ref_names = [
        name
        for _score, name, _reasons, long_refs in by_score
        if long_refs
    ]
    if long_ref_names:
        names = long_ref_names[:3]
        recommendations.append(
            f"复核 {join_names(names)} 的长 reference；如要拆分或合并，先按官方 Skill 文档重新确认最佳实践。"
        )

    if feedback_missing:
        recommendations.append(
            f"分批给 {len(feedback_missing)} 个 feedback 文件补 `status` frontmatter，先分类，不顺手展开修复。"
        )

    if retained_deprecated:
        recommendations.append(
            f"确认 {len(retained_deprecated)} 个保留的废弃 source 是否仍有说明价值；没有价值时再做小范围清理计划。"
        )

    if not official_docs_ok:
        recommendations.append(
            "恢复 `doc/skill-governance-architecture.md` 中的官方 Skill 最佳实践链接。"
        )

    if not recommendations:
        recommendations.append("本轮没有必须立刻处理的治理动作；保持定期巡检即可。")

    return recommendations[:3]


def audit(days: int) -> tuple[str, int]:
    reg = load_registry()
    skills = reg.get("skills", [])
    engines = {e["id"]: e["path"] for e in reg.get("engines", [])}
    dirty = git_dirty_paths()
    touch_counts = git_commit_touch_counts(days)
    feedback_counts, feedback_missing = feedback_status_counts()
    check_tools_code, check_tools_output = run_cmd([sys.executable, "scripts/check-tools.py"])

    deprecated_ids = {d["id"] for d in reg.get("deprecated", [])}
    retained_deprecated = []
    for dep_id in sorted(deprecated_ids):
        skill_md = ROOT / "skills" / dep_id / "SKILL.md"
        if skill_md.exists():
            retained_deprecated.append(f"skills/{dep_id}/SKILL.md")

    rows = []
    attention = []
    layer_counts = Counter(s.get("layer", "unknown") for s in skills)

    for skill in skills:
        name = skill["name"]
        source = skill["source"]
        source_path = ROOT / source
        prefixes = skill_prefixes(skill, engines)
        commits = sum(count for path, count in touch_counts.items() if path_touched(path, prefixes))
        dirty_count = sum(1 for path in dirty if path_touched(path, prefixes))
        skill_md = source_path / "SKILL.md" if source_path.is_dir() else source_path
        skill_lines = line_count(skill_md)

        long_refs = []
        ref_dir = source_path / "references" if source_path.is_dir() else None
        if ref_dir and ref_dir.exists():
            for ref_file in sorted(ref_dir.glob("*.md")):
                lines = line_count(ref_file)
                if lines > 300:
                    long_refs.append(f"{rel(ref_file)} ({lines} lines)")

        layer = skill.get("layer", "unknown")
        arch_doc = ARCH_DOC_BY_SKILL.get(name)
        missing_arch = layer in {"L1", "L2"} and not arch_doc
        arch_exists = bool(arch_doc and (ROOT / arch_doc).exists())

        reasons = []
        score = 0
        if commits >= 20:
            score += 3
            reasons.append(f"{days} 天内相关提交 {commits} 次")
        elif commits >= 8:
            score += 2
            reasons.append(f"{days} 天内相关提交 {commits} 次")
        if dirty_count:
            score += 2
            reasons.append(f"当前有 {dirty_count} 个未提交相关改动")
        if skill_lines > 500:
            score += 2
            reasons.append(f"SKILL.md {skill_lines} 行，超过 500 行建议拆 reference")
        if long_refs:
            score += 1
            reasons.append(f"{len(long_refs)} 个 reference 超过 300 行")
        if missing_arch:
            score += 1
            reasons.append("L1/L2 工作流暂无架构文档映射")
        elif arch_doc and not arch_exists:
            score += 2
            reasons.append(f"登记的架构文档不存在：{arch_doc}")

        if score:
            attention.append((score, name, reasons, long_refs))

        rows.append(
            {
                "name": name,
                "layer": layer,
                "source": source,
                "commits": commits,
                "dirty": dirty_count,
                "skill_lines": skill_lines,
                "arch_doc": arch_doc or "",
                "score": score,
            }
        )

    by_score = sorted(attention, key=lambda item: (-item[0], item[1]))
    official_docs_ok = official_docs_links_present()
    recommendations = build_recommendations(
        check_tools_code=check_tools_code,
        rows=rows,
        by_score=by_score,
        feedback_missing=feedback_missing,
        retained_deprecated=retained_deprecated,
        official_docs_ok=official_docs_ok,
    )
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    report_path = REPORT_DIR / f"{stamp}_skill-audit.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Skill 定期巡检报告 - {now}",
        "",
        "## 结论",
        "",
        f"- 正式 skill 数：{len(skills)}；分层："
        + ", ".join(f"{k}={v}" for k, v in sorted(layer_counts.items())),
        f"- `check-tools.py`：{'通过' if check_tools_code == 0 else '有问题'}。",
        f"- feedback 状态："
        + ", ".join(f"{k}={v}" for k, v in sorted(feedback_counts.items()) if v),
        f"- 保留的废弃 source：{len(retained_deprecated)} 个。",
        f"- 需要关注的 skill 候选：{len(by_score)} 个。",
        f"- 官方 Skill 最佳实践链接：{'已配置' if official_docs_ok else '缺失'}。",
        "",
        "## 硬性检查",
        "",
        "```text",
        check_tools_output,
        "```",
        "",
        "## 优先关注候选",
        "",
    ]

    if by_score:
        lines += ["| Skill | 分数 | 原因 |", "|---|---:|---|"]
        for score, name, reasons, _long_refs in by_score[:12]:
            lines.append(f"| `{name}` | {score} | {'；'.join(reasons)} |")
    else:
        lines.append("本轮没有发现需要优先关注的 skill。")

    lines += ["", "## 废弃入口与幽灵入口", ""]
    if retained_deprecated:
        lines.append("以下废弃 source 仍保留在 `skills/`，应定期确认是否还需要保留说明文件：")
        lines.extend(f"- `{path}`" for path in retained_deprecated)
    else:
        lines.append("未发现保留在 `skills/` 下的废弃 source。")

    lines += ["", "## Feedback 状态", ""]
    if feedback_missing:
        lines.append(f"仍有 {len(feedback_missing)} 个反馈缺少状态，建议分批补 `status` frontmatter：")
        lines.extend(f"- `{path}`" for path in feedback_missing[:20])
        if len(feedback_missing) > 20:
            lines.append(f"- ... 另有 {len(feedback_missing) - 20} 个")
    else:
        lines.append("所有 feedback 文件都有机器可读状态。")

    lines += [
        "",
        "## 全量 Skill 指标",
        "",
        "| Skill | 层级 | 近期开动 | 未提交相关改动 | SKILL.md 行数 | 架构文档 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in sorted(rows, key=lambda r: (r["layer"], r["name"])):
        arch = row["arch_doc"] or ""
        lines.append(
            f"| `{row['name']}` | {row['layer']} | {row['commits']} | {row['dirty']} | "
            f"{row['skill_lines']} | {arch} |"
        )

    lines += ["", "## 建议动作", ""]
    lines.extend(f"{index}. {item}" for index, item in enumerate(recommendations, start=1))

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(report_path), check_tools_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90, help="git history window")
    parser.add_argument("--strict", action="store_true", help="fail if check-tools fails")
    args = parser.parse_args()

    report_path, check_tools_code = audit(args.days)
    print(report_path)
    if args.strict and check_tools_code != 0:
        return check_tools_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
