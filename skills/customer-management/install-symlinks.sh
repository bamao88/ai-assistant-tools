#!/usr/bin/env bash
# Idempotent re-runnable installer for the customer-management skill's dual-host
# project-local symlinks (NOT global ~/.claude/skills — this skill is scope: assistant_zh).
#
#   bash install-symlinks.sh
#
# Re-run after moving the tools dir, or whenever a link is lost. Deletes old links
# and recreates them pointing at the single tools source. See references/symlink-rebuild.md.
set -euo pipefail

SRC="/Volumes/ExtSSD2601/AI_Assistant/tools/skills/customer-management"
PROJECT="/Volumes/ExtSSD2601/AI_Assistant/assistant_zh"

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "ERROR: source missing or no SKILL.md at $SRC" >&2
  exit 1
fi

for HOST in .claude .agents; do
  DIR="$PROJECT/$HOST/skills"
  mkdir -p "$DIR"
  ln -sfn "$SRC" "$DIR/customer-management"
  echo "linked $DIR/customer-management -> $(readlink "$DIR/customer-management")"
done

echo "OK (idempotent)"
