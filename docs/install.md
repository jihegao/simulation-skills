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

## Startup Auto-Update

`scripts/install_skills.sh` copies `scripts/auto_update_skills.py` into every
installed skill as `scripts/auto_update_from_github.py`. Each skill's
`SKILL.md` asks Codex to run that helper at activation.

The helper is best-effort:

- It uses `SIMULATION_SKILLS_GITHUB_REPO` first, then the source checkout's
  `origin` remote.
- It only treats GitHub remotes as update sources.
- It skips dirty source or cache checkouts instead of overwriting local work.
- It reinstalls the suite into `CODEX_SKILLS_DIR` or the current local Codex
  skills directory after a successful update.
- It records a short cooldown under `~/.cache/simulation-skills` to avoid
  repeated network checks in the same working session.

Disable it with:

```bash
SIMULATION_SKILLS_AUTO_UPDATE=0
```

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
