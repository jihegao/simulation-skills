#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="${SKILL_VALIDATOR:-$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py}"

if [ ! -f "$VALIDATOR" ]; then
  echo "missing validator: $VALIDATOR" >&2
  exit 1
fi

for skill_dir in "$ROOT_DIR"/skills/*; do
  [ -d "$skill_dir" ] || continue
  [ -f "$skill_dir/SKILL.md" ] || continue
  echo "validating $(basename "$skill_dir")"
  uv run --with pyyaml python "$VALIDATOR" "$skill_dir"
done
