# Install

## Local Codex Skill Install

Install all suite skills into the default local Codex skills directory:

```bash
bash scripts/install_skills.sh
```

Set `CODEX_SKILLS_DIR` to install elsewhere:

```bash
CODEX_SKILLS_DIR="$HOME/.codex/skills" bash scripts/install_skills.sh
```

The installer copies these directories as flat siblings:

- `abm-modeling`
- `discrete-event-modeling`
- `sim-adapter`
- `simulation-model-conversion`

This flat layout matters because Codex skill discovery expects independent
skill folders, each with its own `SKILL.md`.

## Validate Metadata

Run:

```bash
bash scripts/validate_skills.sh
```

The validator uses the local `quick_validate.py` from
`~/.codex/skills/.system/skill-creator/scripts/quick_validate.py` when it is
available. It runs through `uv run --with pyyaml` so PyYAML is available for
frontmatter parsing.

## Runtime Dependencies

The repository-level `pyproject.toml` includes the dependencies needed by the
copied Mesa examples and the DES scenario runners:

```bash
python3 -m pip install -e .
```

Skill scripts may also create or reuse local runtime environments as described
inside each skill's own `SKILL.md`.
