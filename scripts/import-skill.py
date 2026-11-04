#!/usr/bin/env python3
"""Concentrate a manually installed skill in tools, preserving its former entry.

  python3 scripts/import-skill.py /path/to/skill --host codex --dry-run
  python3 scripts/import-skill.py /path/to/skill --host codex

The source is backed up under var/migrations before its entry becomes a symlink.
Existing different sources, external symlinks, and nested repositories require
review instead of overwriting. No Git staging, commits, or network operations.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = {".git", ".venv", ".local-runtime", "node_modules", "__pycache__", ".DS_Store"}


def payload(source: Path) -> dict[str, str]:
    result = {}
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        if path.is_symlink():
            # Relative internal links remain meaningful after the directory moves.
            target = path.resolve(strict=True)
            target.relative_to(source.resolve())
            if path.readlink().is_absolute():
                raise ValueError(f"absolute link requires review: {relative}")
            result[str(relative)] = "link:" + str(path.readlink())
        elif path.is_file():
            result[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def metadata(source: Path) -> dict:
    lines = (source / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md needs YAML frontmatter")
    data = yaml.safe_load("\n".join(lines[1:lines.index("---", 1)]))
    name = data.get("name") if isinstance(data, dict) else None
    if (not isinstance(name, str) or not name or name in {".", ".."}
            or any(c in name for c in ("/", "\\", "\0"))):
        raise ValueError("name must be a single safe path component")
    if not isinstance(data.get("description"), str) or not data["description"].strip():
        raise ValueError("description is required")
    return data


def import_skill(source: Path, host: str, dry: bool = False) -> dict:
    # Keep the lexical installation entry: never move the target of a symlink.
    source = source.expanduser().absolute()
    if source.is_symlink():
        raise ValueError("source is a symlink; review its owning project before importing the target")
    source = source.resolve(strict=True)
    if not source.is_dir() or not (source / "SKILL.md").is_file():
        raise ValueError("source must be a directory containing SKILL.md")
    if any(p.name == ".git" for p in source.rglob(".git")):
        raise ValueError("source contains an owning Git repository; review it before migration")
    data = metadata(source)
    name = data["name"]
    target = ROOT / "skills" / name
    if source == target.resolve():
        raise ValueError("already a canonical source; use sync-skills.py to install")
    if source.is_relative_to(ROOT.resolve()):
        raise ValueError("source is already inside tools; register its current source instead")
    manifest = payload(source)
    registry_path = ROOT / "registry.yaml"
    old_registry = registry_path.read_text(encoding="utf-8")
    registry = yaml.safe_load(old_registry)
    existing = [s for s in registry.get("skills", []) if s["name"] == name]
    if any(d["id"] == name for d in registry.get("deprecated", [])):
        raise ValueError(f"{name} is a retired trigger; use its registered replacement")
    if target.exists() or target.is_symlink():
        raise ValueError(f"canonical source already exists: {target}; compare the versions before merging")
    if existing:
        raise ValueError(f"registry already contains {name}; compare its registered source")
    entry = {"name": name, "source": f"skills/{name}", "install_kind": "dir",
             "hosts": [host], "scope": "global", "purpose": data["description"]}
    # Preserve all existing YAML formatting, comments and unrelated edits.
    document = yaml.compose(old_registry)
    skills_node = next(v for k, v in document.value if k.value == "skills")
    position = skills_node.end_mark.index
    indent = max(0, skills_node.value[0].start_mark.column - 2) if skills_node.value else 2
    block = "\n" + "\n".join(" " * indent + line for line in yaml.safe_dump(
        [entry], allow_unicode=True, sort_keys=False, width=1000).splitlines()) + "\n\n"
    # An explicit empty list (skills: []) must become a block list first.
    start = skills_node.start_mark.index if not skills_node.value else position
    new_registry = old_registry[:start] + block + old_registry[position:]
    parsed = yaml.safe_load(new_registry)
    if parsed["skills"] != registry["skills"] + [entry]:
        raise ValueError("cannot append to registry without changing existing records")
    report = {"name": name, "source": str(source), "target": str(target),
              "files": len(manifest), "host": host, "dry_run": dry}
    if dry:
        return report
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = ROOT / "var" / "migrations" / f"skill-import-{stamp}" / name
    backup.parent.mkdir(parents=True, exist_ok=False)
    created = False
    moved = False
    try:
        target.mkdir(parents=True, exist_ok=False)
        created = True
        shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True,
                        ignore=lambda _p, entries: EXCLUDED.intersection(entries))
        if payload(target) != manifest:
            raise ValueError("copied payload differs; source has been preserved")
        registry_path.write_text(new_registry, encoding="utf-8")
        shutil.move(str(source), str(backup))
        moved = True
        source.symlink_to(target, target_is_directory=True)
    except Exception:
        registry_path.write_text(old_registry, encoding="utf-8")
        if moved:
            if source.is_symlink():
                source.unlink()
            shutil.move(str(backup), str(source))
        if created:
            shutil.rmtree(target)
        raise
    report["backup"] = str(backup)
    (backup.parent / "receipt.json").write_text(json.dumps(
        {**report, "sha256": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--host", choices=("codex", "claude"), default="codex")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(import_skill(args.source, args.host, args.dry_run), ensure_ascii=False, indent=2))
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"Import stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
