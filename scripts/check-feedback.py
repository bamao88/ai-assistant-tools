#!/usr/bin/env python3
"""Summarize feedback status files.

Default mode reports missing/unknown statuses without failing. Use --strict when
cleaning the feedback backlog and you want missing status metadata to fail.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK = ROOT / "feedback"
VALID_STATUSES = {"open", "fixed", "obsolete", "cannot-reproduce"}


def status_from_text(text: str) -> str | None:
    # Prefer YAML frontmatter, but accept legacy top-of-file status lines.
    frontmatter = re.match(r"\A---\n(.*?)\n---", text, re.S)
    candidates = [frontmatter.group(1)] if frontmatter else []
    candidates.append("\n".join(text.splitlines()[:30]))
    for block in candidates:
        match = re.search(r"(?im)^\s*(?:\*\*)?status(?:\*\*)?\s*:\s*([a-z-]+)", block)
        if match:
            return match.group(1).strip().lower()
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    counts: Counter[str] = Counter()
    missing: list[Path] = []
    invalid: list[tuple[Path, str]] = []

    for path in sorted(FEEDBACK.glob("*.md")):
        if path.name == "README.md":
            continue
        status = status_from_text(path.read_text(encoding="utf-8"))
        if status is None:
            counts["missing"] += 1
            missing.append(path)
        elif status not in VALID_STATUSES:
            counts["invalid"] += 1
            invalid.append((path, status))
        else:
            counts[status] += 1

    total = sum(counts.values())
    print(f"{total} feedback files")
    for key in sorted(VALID_STATUSES | {"missing", "invalid"}):
        if counts[key]:
            print(f"  {key}: {counts[key]}")

    if missing:
        print("\nMissing status:")
        for path in missing:
            print(f"  {path.relative_to(ROOT)}")

    if invalid:
        print("\nInvalid status:")
        for path, status in invalid:
            print(f"  {path.relative_to(ROOT)}: {status}")

    if args.strict and (missing or invalid):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
