---
name: abm-modeling
description: Use when the user needs to design, write, run, visualize, or explain Mesa agent-based models, including Mesa 3 models, SolaraViz inspection apps, parameter sweeps, stochastic experiments, CSV/JSON outputs, scenario packs, and evidence-bounded result interpretation.
---

# ABM Modeling

## Overview

Build a runnable Mesa ABM first, then run a small experiment and explain only what the outputs support. Treat Mesa 3, scripted sweeps, CSV/JSON evidence, and optional SolaraViz inspection as the Mesa-only workflow for this stage.

## Startup Update

At skill activation, make a best-effort update attempt before doing modeling work:

```bash
python3 "$HOME/.codex/skills/abm-modeling/scripts/auto_update_from_github.py"
```

The helper pulls from the configured GitHub source and reinstalls the suite when
safe. It skips dirty checkouts, missing GitHub configuration, network failures,
and recent successful checks without blocking the user task. Set
`SIMULATION_SKILLS_AUTO_UPDATE=0` to disable it.

## Runtime Initialization

Before running Mesa commands in a new workspace, confirm a Python 3.10+
interpreter and a workspace-local dependency cache. Use
`skill-runtime.env.example` (next to this `SKILL.md`) as the committed template
and keep any copied `skill-runtime.env` file untracked. Source it in any agent
before running Mesa scripts.

Default runtime values:

```bash
ABM_MESA_PYTHON=python3.12
ABM_MESA_INSTALL_DIR=.abm-mesa-env
ABM_MESA_OUTPUT_ROOT=outputs
```

Prefer a project environment that already provides `mesa[rec]>=3,<4`. Otherwise
reuse `ABM_MESA_INSTALL_DIR` instead of installing Mesa into `/tmp` for normal
work.

## Workflow

Use the role-based workflow when a task spans model design, implementation,
simulation, verification, and interpretation. It is optionally
subagent-dispatchable when the current agent environment supports subagents, but
it also works as a single-agent checklist.

1. Clarify the phenomenon, agent types, environment, state variables, rules, parameters, metrics, and experiment question.
2. Design the Mesa workflow: Python model, repo integration, scripted sweeps, tests, CSV/JSON outputs, and optional SolaraViz inspection.
3. Create a minimal runnable model before adding sophistication.
4. Run at least one deterministic smoke experiment and one small stochastic sweep when randomness matters.
5. Save raw run data plus a summary; interpret trends, uncertainty, and limits without overclaiming causality.
6. Optional: generate a Mesa Visualization app only after the batch experiment runs; use it for inspection/debugging, not as the sole evidence.
7. Save a local private experience card in `.mesa-abm-experience/` after completing a new model, unless the user opts out.

## Quick Start

Use the bundled Mesa example as the known-good execution path:

```bash
python3.10 abm-modeling/scripts/run_mesa_experiment.py \
  --model abm-modeling/assets/mesa_forest_fire/model.py \
  --config abm-modeling/assets/mesa_forest_fire/experiment.json \
  --output-dir outputs/mesa-forest-fire \
  --install-dir .abm-mesa-env
```

Launch a local configuration page when the user wants to fill parameters in a
browser before running the model:

```bash
python3.10 abm-modeling/scripts/serve_mesa_configurator.py \
  --model abm-modeling/assets/mesa_forest_fire/model.py \
  --config abm-modeling/assets/mesa_forest_fire/experiment.json \
  --output-root outputs/mesa-configurator \
  --install-dir .abm-mesa-env
```

Open the printed localhost URL in a browser — use the agent's built-in browser
if it has one, otherwise ask before opening the system GUI browser. Treat the
configuration page as a browser frontend to `run_mesa_experiment.py`; the
CSV/JSON files written by the runner remain the evidence source.

Generate a Mesa SolaraViz page after the Mesa experiment succeeds:

```bash
python3.10 abm-modeling/scripts/generate_mesa_visualization.py \
  --model abm-modeling/assets/mesa_forest_fire/model.py \
  --config abm-modeling/assets/mesa_forest_fire/experiment.json \
  --output-app /tmp/abm-mesa-viz/app.py

solara run /tmp/abm-mesa-viz/app.py --host 127.0.0.1 --port 8765
```

Then open `http://127.0.0.1:8765` in a browser — use the agent's built-in browser if it has one, otherwise ask before running a GUI browser command such as `open`.

## Resource Routing

Read only the reference needed for the current task:

- `references/roles.md`: Governor, Model Designer, Simulator, Verifier, and Result Analyst responsibilities plus optional subagent dispatch boundaries.
- `references/mesa.md`: Mesa model structure, runner contract, parameter sweeps, outputs.
- `references/model-catalog.md`: Mesa catalog fields and source/license boundary.
- `references/scenario-pack.md`: Scenario-pack layout, runtime adapter, and evidence contract.
- `references/result-interpretation.md`: How to summarize ABM experiment evidence.
- `references/experience-store.md`: Private local experience-store layout and save rules for completed models.

Use scripts instead of retyping runners:

- `scripts/run_mesa_experiment.py`: Installs Mesa into a venv when requested, runs a JSON-configured sweep, writes CSV files and `summary.json`.
- `scripts/serve_mesa_configurator.py`: Serves a local configuration page, writes a submitted experiment config, and calls `run_mesa_experiment.py`.
- `scripts/generate_mesa_visualization.py`: Writes a Mesa SolaraViz `app.py` from a model and experiment config for browser inspection.
- `scripts/save_model_experience.py`: Writes a private local experience card, Markdown summary, and JSONL index from a completed Mesa model run.

Use assets as copyable starting points:

- `assets/mesa_forest_fire/`: Runnable Mesa model and experiment config.
- `assets/mesa_traffic_jam/`: Runnable Mesa signalized-intersection model, sweep configs, and standalone visualization.

## Mesa Requirements

When writing a Mesa model for this skill, expose a `mesa.Model` subclass named in the experiment config. The model must accept keyword parameters plus `seed`, implement `step()`, and provide `snapshot() -> dict` with numeric metrics. Keep seeded randomness explicit so repeated runs are reproducible.

## Mesa Visualization Requirements

Mesa 3 and SolaraViz require Python 3.10+. Visualization is optional and follows evidence generation. Use `scripts/generate_mesa_visualization.py` to create a SolaraViz `app.py`, run it with `solara run`, and inspect the local page in a browser when the user wants to see the simulation — use the agent's built-in browser if it has one, otherwise ask before running GUI browser commands. Do not treat a browser view or screenshot as a substitute for CSV/JSON experiment outputs.

The generator is a default grid/condition-style template that works for the bundled forest-fire model; adapt `agent_portrayal()` and Solara controls for other Mesa model types instead of assuming universal visualization coverage.

## Result Explanation

Every ABM result explanation must state:

- Experiment question and varied parameters.
- Number of runs, seeds, and steps.
- Primary metric trend with raw summary values.
- Stochastic uncertainty or run-to-run variation.
- Model assumptions and what the results do not prove.

## Validation

Before claiming the skill is ready, run:

```bash
python3 -m unittest -v tests/test_skill_contract.py
```

Optionally validate skill packaging with a skill-creator `quick_validate.py` if
one is installed locally:

```bash
QUICK_VALIDATE_PY=/path/to/quick_validate.py
python3 "$QUICK_VALIDATE_PY" abm-modeling
```

`quick_validate.py` imports PyYAML; if the system Python lacks `yaml`, run the same command with a Python environment that has PyYAML installed. Do not hard-code a user-local path into repository docs or CI.
