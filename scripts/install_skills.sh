#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
UPDATE_HELPER="$ROOT_DIR/scripts/auto_update_skills.py"
SOURCE_REMOTE="$(git -C "$ROOT_DIR" remote get-url origin 2>/dev/null || true)"

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
  if [ -f "$UPDATE_HELPER" ]; then
    mkdir -p "$DEST_DIR/$skill_name/scripts"
    cp "$UPDATE_HELPER" "$DEST_DIR/$skill_name/scripts/auto_update_from_github.py"
    chmod +x "$DEST_DIR/$skill_name/scripts/auto_update_from_github.py"
    {
      printf 'SIMULATION_SKILLS_SOURCE_ROOT=%s\n' "$ROOT_DIR"
      printf 'SIMULATION_SKILLS_GITHUB_REPO=%s\n' "$SOURCE_REMOTE"
    } > "$DEST_DIR/$skill_name/.simulation-skills-update.env"
  fi
  echo "installed $skill_name -> $DEST_DIR/$skill_name"
done
