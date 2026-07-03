#!/usr/bin/env bash
# Idempotent installer for publish-prep skill's dual-host project-local symlinks
# (NOT global ~/.claude/skills — scope: assistant_zh).
#   bash install-symlinks.sh
# Re-run after moving the tools dir or if a link is lost.
set -euo pipefail

SRC="/Volumes/ExtSSD2601/AI_Assistant/tools/skills/publish-prep"
PROJECT="/Volumes/ExtSSD2601/AI_Assistant/assistant_zh"

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "ERROR: source missing or no SKILL.md at $SRC" >&2
  exit 1
fi

for HOST in .claude .agents; do
  DIR="$PROJECT/$HOST/skills"
  mkdir -p "$DIR"
  ln -sfn "$SRC" "$DIR/publish-prep"
  echo "linked $DIR/publish-prep -> $(readlink "$DIR/publish-prep")"
done

echo "OK (idempotent)"
