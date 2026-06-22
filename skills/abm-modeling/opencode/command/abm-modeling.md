---
description: Build, run, visualize, and interpret Mesa agent-based models
---

# ABM Modeling (OpenCode entry point)

OpenCode has no native "skill" concept — it loads commands from
`.opencode/command/*.md` — so this command is a thin entry point that defers to
the shared `SKILL.md` (the same agentskills.io package Claude Code and Codex load
directly). It intentionally does **not** duplicate skill instructions.

## Run a Mesa ABM task

1. Locate the `abm-modeling` package directory. By default it is
   `abm-modeling/` relative to the workspace root and contains `SKILL.md`,
   `references/`, `scripts/`, and `assets/`.
2. Read and follow `abm-modeling/SKILL.md`; use its `Resource Routing` for
   references, scripts, and assets.
3. Source the runtime template before running anything:
   `source abm-modeling/skill-runtime.env.example`.
4. Run experiments with `abm-modeling/scripts/run_mesa_experiment.py` and treat
   its CSV/JSON outputs as the evidence source.

`SKILL.md` is the single source of truth. If anything here disagrees with it,
follow `SKILL.md`.

## Install for OpenCode

Keep the `abm-modeling/` package present in the workspace, then register the
command in OpenCode's command directory (project `.opencode/command/` or
`~/.opencode/command/`):

```bash
cp abm-modeling/opencode/command/abm-modeling.md .opencode/command/abm-modeling.md
```

Then invoke `/abm-modeling` in OpenCode. The command references the package by its
workspace path (`abm-modeling/SKILL.md`), so it resolves correctly both in-tree
and after being copied into `.opencode/command/`.
