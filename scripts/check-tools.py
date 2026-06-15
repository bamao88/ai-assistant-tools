#!/usr/bin/env python3
"""Validate the tools registry (schema v2) against the filesystem and
~/.claude/skills install state.

  python3 scripts/check-tools.py [--verbose]

Checks:
  - every skill source exists and (for dir kind) has SKILL.md
  - every engine / vendor path exists
  - every skill is installed as the expected symlink in ~/.claude/skills
  - no deprecated trigger is still present in ~/.claude/skills
Exit non-zero on any error.
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry.yaml"
CLAUDE_SKILLS = Path.home() / ".claude" / "skills"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    reg = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))

    errors, warns, oks = [], [], []

    # skills
    for s in reg.get("skills", []):
        name, kind = s["name"], s.get("install_kind", "dir")
        src = ROOT / s["source"]
        if not src.exists():
            errors.append(f"skill {name}: source missing {src}"); continue
        if kind == "dir" and not (src / "SKILL.md").exists():
            errors.append(f"skill {name}: no SKILL.md in {src}"); continue
        # scope-gated skills (e.g. scope: assistant_zh) are project-local: verify the
        # source exists (above) but do NOT expect them in the global ~/.claude/skills.
        scope = s.get("scope")
        if scope and scope != "global":
            oks.append(f"skill {name} (scope={scope}, project-local)"); continue
        if kind == "dir":
            inst, want = CLAUDE_SKILLS / name, src.resolve()
        else:
            inst, want = CLAUDE_SKILLS / name / "SKILL.md", src.resolve()
        if not inst.is_symlink():
            warns.append(f"skill {name}: not installed (run sync-skills.py)")
        elif Path(os.readlink(inst)).resolve() != want:
            warns.append(f"skill {name}: install points elsewhere -> {os.readlink(inst)}")
        else:
            oks.append(f"skill {name}")

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

    # deprecated triggers must be gone
    for dep in reg.get("deprecated", []):
        p = CLAUDE_SKILLS / dep["id"]
        if p.exists() or p.is_symlink():
            warns.append(f"deprecated {dep['id']}: still present in ~/.claude/skills")

    if args.verbose:
        for o in oks:
            print(f"  ok   {o}")
    for w in warns:
        print(f"  WARN {w}")
    for e in errors:
        print(f"  ERR  {e}")
    print(f"\n{len(oks)} ok, {len(warns)} warnings, {len(errors)} errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
