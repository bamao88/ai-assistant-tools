#!/usr/bin/env python3
"""Check the media Skill source collection; optionally its links and Git snapshot.

python3 scripts/check-media-skills.py [--installed] [--git-ref <ref>]
This is source/registration validation, not a content-production replay.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOMAINS = {"strategy", "research", "topics", "materials", "production",
           "distribution", "community", "review"}
SKIP = {"__pycache__", ".pytest_cache", ".DS_Store"}
DOMAIN_LABELS = {"strategy": "定位与运营底座", "research": "调研与洞察",
                 "topics": "选题与内容规划", "materials": "素材与知识准备",
                 "production": "内容制作", "distribution": "平台适配与发布",
                 "community": "互动与用户关系", "review": "数据、复盘与改进"}
CATALOG = ROOT / "doc/media-operations-catalog.md"


def catalog_text(skills: list[dict]) -> str:
    lines = ["# 新媒体运营 Skill 导航", "",
             "由 `registry.yaml` 生成。更新命令：`python3 scripts/check-media-skills.py --write-catalog`。",
             "项目归属决定适用范围；全局可选不表示可套用于其他账号。名称可以用 `$名称` 调用。", ""]
    for domain, label in DOMAIN_LABELS.items():
        lines += [f"## {label}", "", "| 调用名 | 适用范围 | 用途 |", "|---|---|---|"]
        for skill in skills:
            if skill["media_domain"] != domain:
                continue
            purpose = skill.get("purpose", "").replace("|", " / ").replace("\n", " ")
            if skill.get("compatibility_for"):
                purpose += f"；兼容入口，实际职责见 `{skill['compatibility_for']}`"
            lines.append(f"| [{skill['name']}](../{skill['source']}/SKILL.md) | "
                         f"{skill.get('project', '通用')} | {purpose} |")
        lines.append("")
    return "\n".join(lines)


def source_files(source: Path):
    candidates = []
    for path in sorted(source.rglob("*")):
        if any(part in SKIP or part.endswith((".pyc", ".pyo"))
               for part in path.relative_to(source).parts):
            continue
        if path.is_file() or path.is_symlink():
            candidates.append(path)
    # Skill-local ignore rules also identify live rotation cursors and usage
    # ledgers. Preserve them locally without treating them as source assets.
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "-z", "--stdin"], cwd=ROOT,
        input=b"\0".join(os.fsencode(p.relative_to(ROOT)) for p in candidates) + b"\0",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ignored.returncode not in (0, 1):
        raise RuntimeError(ignored.stderr.decode(errors="replace"))
    exclusions = {os.fsdecode(p) for p in ignored.stdout.split(b"\0") if p}
    for path in candidates:
        if str(path.relative_to(ROOT)) not in exclusions:
            yield path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--installed", action="store_true")
    ap.add_argument("--git-ref")
    ap.add_argument("--write-catalog", action="store_true")
    args = ap.parse_args()
    registry = yaml.safe_load((ROOT / "registry.yaml").read_text())
    skills = [s for s in registry["skills"] if s.get("media_domain")]
    errors, count, total_bytes = [], 0, 0
    expected_catalog = catalog_text(skills)
    if args.write_catalog:
        CATALOG.write_text(expected_catalog)
    if not CATALOG.exists() or CATALOG.read_text() != expected_catalog:
        errors.append("media catalog is stale; run with --write-catalog")
    tree = {}
    if args.git_ref:
        raw = subprocess.check_output(
            ["git", "ls-tree", "-rz", "--full-tree", args.git_ref], cwd=ROOT)
        for entry in raw.split(b"\0"):
            if entry:
                metadata, name = entry.split(b"\t", 1)
                mode, kind, oid = metadata.decode().split()
                tree[os.fsdecode(name)] = (mode, oid)

    for skill in skills:
        name = skill["name"]
        source = ROOT / skill["source"]
        if (skill["media_domain"] not in DOMAINS
                or Path(skill["source"]).is_absolute()
                or not source.is_dir() or source.is_symlink()
                or not source.resolve().is_relative_to(ROOT / "skills")):
            errors.append(f"{name}: invalid domain or canonical source")
            continue
        entry = source / "SKILL.md"
        try:
            parts = entry.read_text().split("---", 2)
            frontmatter = yaml.safe_load(parts[1]) if len(parts) == 3 else {}
            if frontmatter.get("name") != name or not frontmatter.get("description"):
                errors.append(f"{name}: invalid name/description")
        except (OSError, yaml.YAMLError, AttributeError) as exc:
            errors.append(f"{name}: invalid SKILL.md ({exc})")
        project = skill.get("project")
        # Existing customer-management keeps its call stable until the next
        # coordinated project rename. Every newly centralized name is prefixed.
        if project and not name.startswith(project + "_") and name != "customer-management":
            errors.append(f"{name}: project prefix missing")
        if (source / ".git").exists():
            errors.append(f"{name}: nested repository must not be exported")
        for path in source_files(source):
            rel = path.relative_to(ROOT).as_posix()
            if path.is_symlink():
                target = path.resolve()
                if not target.exists() or not target.is_relative_to(ROOT):
                    errors.append(f"{rel}: broken or external source symlink")
                data = os.fsencode(os.readlink(path))
                mode = "120000"
            else:
                data = path.read_bytes()
                mode = "100755" if path.stat().st_mode & 0o111 else "100644"
            if len(data) >= 100 * 1024 * 1024:
                errors.append(f"{rel}: exceeds GitHub regular file limit")
            if path.name == ".env" or path.suffix in {".pem", ".key"}:
                errors.append(f"{rel}: credential file in source collection")
            count += 1
            total_bytes += len(data)
            if args.git_ref:
                oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                if tree.get(rel) != (mode, oid):
                    errors.append(f"{rel}: Git snapshot missing or differs from canonical file")
        if args.installed:
            links = []
            if (skill.get("scope", "global") == "global"
                    and "codex" in skill.get("hosts", [])):
                links.append(Path.home() / ".agents/skills" / name)
            if skill.get("project_entry"):
                links.append(ROOT / skill["project_entry"])
            for link in links:
                if not link.is_symlink() or link.resolve() != source.resolve():
                    errors.append(f"{name}: missing or incorrect entry {link}")

    print(f"{len(skills)} media entries; {count} source files; {total_bytes:,} bytes")
    print("Validation: logic/contract (source, metadata" +
          (", installed links" if args.installed else "") +
          (", Git snapshot" if args.git_ref else "") + ")")
    for error in errors:
        print("ERROR:", error)
    print(f"{len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
