#!/usr/bin/env bash
# Idempotent re-runnable installer for the assistant_zh_video-cover skill's dual-host
# project-local symlinks (NOT global ~/.claude/skills — this skill is scope: assistant_zh).
#
#   bash install-symlinks.sh
#
# Re-run after moving the tools dir, or whenever a link is lost. Deletes old links
# and recreates them pointing at the single tools source.
set -euo pipefail

SRC="/Volumes/ExtSSD2601/AI_Assistant/tools/skills/assistant_zh_video-cover"
PROJECT="/Volumes/ExtSSD2601/AI_Assistant/assistant_zh"

if [ ! -f "$SRC/SKILL.md" ]; then
  echo "ERROR: source missing or no SKILL.md at $SRC" >&2
  exit 1
fi

for HOST in .claude .agents; do
  DIR="$PROJECT/$HOST/skills"
  mkdir -p "$DIR"
  ln -sfn "$SRC" "$DIR/assistant_zh_video-cover"
  echo "linked $DIR/assistant_zh_video-cover -> $(readlink "$DIR/assistant_zh_video-cover")"
done

echo "OK (idempotent)"
