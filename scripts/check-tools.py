#!/usr/bin/env python3
"""Validate the tools registry (schema v2) against the filesystem and
Claude/Codex install state (Codex uses ~/.agents/skills).

  python3 scripts/check-tools.py [--verbose] [--strict] [--host claude|codex|all]

Checks:
  - every skill source exists and (for dir kind) has SKILL.md
  - every engine / vendor path exists
  - every skill uses_engines / uses_vendor reference exists in the registry
  - every skills/*/SKILL.md is either registered or explicitly deprecated
  - engines/*/SKILL.md files are clearly non-trigger engine runbooks
  - every first-party frontmatter name exactly matches its registry name
  - every skill is installed for its declared hosts (missing hosts = [claude])
  - no deprecated trigger is still present in selected host/legacy directories
Exit non-zero on any error; --strict also fails on warnings.
"""
from __future__ import annotations
import argparse, os, sys
from collections import Counter
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry.yaml"
CLAUDE_SKILLS = Path.home() / ".claude" / "skills"
CODEX_SKILLS = Path.home() / ".agents" / "skills"
LEGACY_CODEX_SKILLS = Path.home() / ".codex" / "skills"
HOSTS = ("claude", "codex")


def skill_hosts(skill: dict) -> list[str]:
    hosts = skill.get("hosts", ["claude"])
    if not isinstance(hosts, list) or not hosts or any(h not in HOSTS for h in hosts):
        raise ValueError("hosts must be a nonempty list containing claude and/or codex")
    if len(hosts) != len(set(hosts)):
        raise ValueError("hosts must not contain duplicates")
    return hosts


def host_dirs(host: str = "all") -> dict[str, Path]:
    return {h: p for h, p in (("claude", CLAUDE_SKILLS), ("codex", CODEX_SKILLS))
            if host == "all" or h == host}


def stale_dirs(host: str = "all") -> dict[str, Path]:
    dirs = host_dirs(host)
    if host in ("all", "codex"):
        dirs["codex legacy"] = LEGACY_CODEX_SKILLS
    return dirs


def valid_name(name: object) -> bool:
    # Preserve exact project prefixes, including uppercase and underscores.
    return (isinstance(name, str) and bool(name) and name not in (".", "..")
            and "/" not in name and "\\" not in name and "\x00" not in name)


def link_destination(link: Path) -> Path:
    return (link.parent / os.readlink(link)).resolve()


def check_frontmatter(skill_md: Path, expected_name: str, errors: list) -> None:
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"skill {expected_name}: missing YAML frontmatter in {skill_md}")
        return
    try:
        end = lines.index("---", 1)
        frontmatter = yaml.safe_load("\n".join(lines[1:end]))
    except (ValueError, yaml.YAMLError) as exc:
        errors.append(f"skill {expected_name}: invalid YAML frontmatter ({exc})")
        return
    actual = frontmatter.get("name") if isinstance(frontmatter, dict) else None
    if actual != expected_name:
        errors.append(f"skill {expected_name}: frontmatter name {actual!r} does not match registry")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--strict", action="store_true", help="fail on warnings as well as errors")
    ap.add_argument("--host", choices=(*HOSTS, "all"), default="all")
    args = ap.parse_args(argv)
    reg = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))

    errors, warns, oks = [], [], []

    skill_names = [s["name"] for s in reg.get("skills", [])]
    engine_ids = {e["id"] for e in reg.get("engines", [])}
    vendor_ids = {v["id"] for v in reg.get("vendor", [])}
    deprecated_ids = {d["id"] for d in reg.get("deprecated", [])}
    registered_skill_dirs: set[str] = set()
    selected = host_dirs(args.host)

    for name, count in Counter(skill_names).items():
        if count > 1:
            errors.append(f"skill {name}: duplicate registry entry")

    # skills
    for s in reg.get("skills", []):
        name, kind = s["name"], s.get("install_kind", "dir")
        if not valid_name(name):
            errors.append(f"skill {name!r}: name must be a single path component")
            continue
        try:
            hosts = skill_hosts(s)
        except ValueError as exc:
            errors.append(f"skill {name}: {exc}")
            hosts = []
        if kind not in ("dir", "file"):
            errors.append(f"skill {name}: unknown install_kind {kind}")
            continue
        src = ROOT / s["source"]
        source_parts = Path(s["source"]).parts
        if source_parts[:1] == ("skills",) and len(source_parts) >= 2:
            registered_skill_dirs.add(source_parts[1])
        if not src.exists():
            errors.append(f"skill {name}: source missing {src}"); continue
        if kind == "dir" and not (src / "SKILL.md").exists():
            errors.append(f"skill {name}: no SKILL.md in {src}"); continue
        if (kind == "dir" and not src.is_dir()) or (kind == "file" and not src.is_file()):
            errors.append(f"skill {name}: source is not a {kind}"); continue
        if not s.get("external", False):
            check_frontmatter(src / "SKILL.md" if kind == "dir" else src, name, errors)
        for engine_id in s.get("uses_engines", []) or []:
            if engine_id not in engine_ids:
                errors.append(f"skill {name}: unknown uses_engines id {engine_id}")
        for vendor_id in s.get("uses_vendor", []) or []:
            if vendor_id not in vendor_ids:
                errors.append(f"skill {name}: unknown uses_vendor id {vendor_id}")
        # Project-local entries retain source/reference/frontmatter validation,
        # but are never required in either host's shared global directory.
        scope = s.get("scope")
        if scope and scope != "global":
            oks.append(f"skill {name} (scope={scope}, project-local)"); continue
        for host in hosts:
            if host not in selected:
                continue
            base = selected[host]
            if kind == "dir":
                inst, want = base / name, src.resolve()
            else:
                inst, want = base / name / "SKILL.md", src.resolve()
            if not inst.is_symlink():
                warns.append(f"skill {name} [{host}]: not installed (run sync-skills.py)")
            else:
                try:
                    correct = link_destination(inst) == want
                except (OSError, RuntimeError):
                    correct = False
                if not correct:
                    warns.append(f"skill {name} [{host}]: install points elsewhere -> {os.readlink(inst)}")
                else:
                    oks.append(f"skill {name} [{host}]")

    # Every first-party SKILL.md under skills/ should be accounted for.
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        dirname = skill_md.parent.name
        if dirname in registered_skill_dirs:
            continue
        if dirname in deprecated_ids:
            marker = skill_md.read_text(encoding="utf-8", errors="replace")[:1200]
            if "DEPRECATED" in marker or "已废弃" in marker:
                oks.append(f"deprecated source {dirname} (retained, not installed)")
            else:
                errors.append(
                    f"deprecated source {dirname}: SKILL.md must clearly say DEPRECATED/已废弃"
                )
            continue
        errors.append(
            f"unregistered skill dir {dirname}: add it to registry.yaml or move it out of skills/"
        )

    # Engines can keep SKILL.md only as compatibility/runbook docs. They must not
    # present themselves as triggerable skills.
    for engine_skill in sorted((ROOT / "engines").glob("*/SKILL.md")):
        text = engine_skill.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        has_no_trigger = (
            "do not trigger" in lower
            or "not trigger" in lower
            or "not a trigger" in lower
            or "不要作为可触发" in text
            or "不是当前 tools 目录的可触发" in text
            or "不作为可触发" in text
        )
        has_trigger_language = "时触发" in text or "when user says" in lower or "when the user says" in lower
        rel = engine_skill.relative_to(ROOT)
        if not has_no_trigger:
            errors.append(f"{rel}: engine SKILL.md must clearly state it is not triggerable")
        elif has_trigger_language:
            errors.append(f"{rel}: remove trigger language from engine runbook")
        else:
            oks.append(f"engine runbook {rel}")

    # engines & vendor
    for e in reg.get("engines", []):
        if not (ROOT / e["path"]).exists():
            errors.append(f"engine {e['id']}: path missing {e['path']}")
        else:
            oks.append(f"engine {e['id']}")
    for v in reg.get("vendor", []):
        if not (ROOT / v["path"]).exists():
            errors.append(f"vendor {v['id']}: path missing {v['path']}")
        else:
            oks.append(f"vendor {v['id']}")

    # Check both current hosts and Codex's former discovery directory. Leave
    # cleanup ownership decisions to sync-skills.py; this command is read-only.
    for dep in reg.get("deprecated", []):
        if not valid_name(dep["id"]):
            errors.append(f"deprecated {dep['id']!r}: id must be a single path component")
            continue
        for host, directory in stale_dirs(args.host).items():
            p = directory / dep["id"]
            if p.exists() or p.is_symlink():
                warns.append(f"deprecated {dep['id']} [{host}]: still present at {p}")

    if args.verbose:
        for o in oks:
            print(f"  ok   {o}")
    for w in warns:
        print(f"  WARN {w}")
    for e in errors:
        print(f"  ERR  {e}")
    print(f"\n{len(oks)} ok, {len(warns)} warnings, {len(errors)} errors")
    return 1 if errors or (args.strict and warns) else 0


if __name__ == "__main__":
    sys.exit(main())
