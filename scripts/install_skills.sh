#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"

mkdir -p "$DEST_DIR"

for skill_dir in "$ROOT_DIR"/skills/*; do
  [ -d "$skill_dir" ] || continue
  [ -f "$skill_dir/SKILL.md" ] || continue
  skill_name="$(basename "$skill_dir")"
  rsync -a \
    --delete \
    --exclude '.DS_Store' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    "$skill_dir/" "$DEST_DIR/$skill_name/"
  echo "installed $skill_name -> $DEST_DIR/$skill_name"
done
