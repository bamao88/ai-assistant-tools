#!/usr/bin/env python3
"""Install/repair ~/.claude/skills symlinks from registry.yaml, and remove stale
triggers (deprecated skills folded into the L1 routers).

Idempotent. Default = apply. Use --dry-run to preview.

  python3 scripts/sync-skills.py [--dry-run]

Install kinds (per skill in registry.yaml):
  dir  -> ~/.claude/skills/<name>          symlink to <root>/<source dir>
  file -> ~/.claude/skills/<name>/SKILL.md symlink to <root>/<source SKILL.md>
          (used for external vendor clones that expose only a SKILL.md)
"""
from __future__ import annotations
import argparse, os, sys, shutil
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry.yaml"
CLAUDE_SKILLS = Path.home() / ".claude" / "skills"


def load_registry() -> dict:
    with open(REGISTRY, encoding="utf-8") as f:
        return yaml.safe_load(f)


def points_into_root(link: Path) -> bool:
    try:
        return str(ROOT) in os.readlink(link)
    except OSError:
        return False


def install_skill(skill: dict, dry: bool, log: list):
    name = skill["name"]
    source = (ROOT / skill["source"]).resolve()
    kind = skill.get("install_kind", "dir")
    if not source.exists():
        log.append(f"  ✗ {name}: source missing {source}")
        return False

    if kind == "dir":
        target = CLAUDE_SKILLS / name
        want = source
    elif kind == "file":
        target = CLAUDE_SKILLS / name / "SKILL.md"
        want = source
    else:
        log.append(f"  ✗ {name}: unknown install_kind {kind}")
        return False

    # already correct?
    if target.is_symlink() and Path(os.readlink(target)) == want:
        log.append(f"  = {name} ({kind}) ok")
        return True

    if dry:
        log.append(f"  + {name} ({kind}) -> would link {target} -> {want}")
        return True

    if target.is_symlink() or target.exists():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(want)
    log.append(f"  + {name} ({kind}) linked -> {want}")
    return True


def remove_stale(dep_id: str, dry: bool, log: list):
    """Remove a deprecated trigger from ~/.claude/skills if (and only if) it is one
    of ours: a symlink, or a dir whose SKILL.md is a symlink into the tools root."""
    p = CLAUDE_SKILLS / dep_id
    if not (p.exists() or p.is_symlink()):
        return
    is_ours = p.is_symlink() and points_into_root(p)
    if not is_ours and p.is_dir():
        sk = p / "SKILL.md"
        is_ours = sk.is_symlink() and points_into_root(sk)
    if not is_ours:
        log.append(f"  ! {dep_id}: present but not ours — leaving alone")
        return
    if dry:
        log.append(f"  - {dep_id}: would remove stale trigger")
        return
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    else:
        p.unlink()
    log.append(f"  - {dep_id}: removed stale trigger")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    reg = load_registry()
    CLAUDE_SKILLS.mkdir(parents=True, exist_ok=True)

    log: list = []
    log.append("== install skills ==")
    ok = all(install_skill(s, args.dry_run, log) for s in reg.get("skills", []))

    log.append("== remove stale triggers ==")
    for dep in reg.get("deprecated", []):
        remove_stale(dep["id"], args.dry_run, log)

    print("\n".join(log))
    print("\nDONE" + (" (dry-run)" if args.dry_run else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
