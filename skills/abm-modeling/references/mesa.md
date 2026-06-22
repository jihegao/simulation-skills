# Mesa Reference

Use Mesa when the user wants Python code, repeatable experiments, testable outputs, or integration with an existing Python project.

This skill targets Mesa 3 and SolaraViz, so use Python 3.10+ for Mesa runs and browser visualization.

## Runtime Environment

At workspace initialization, check whether the target project already has a
Python 3.10+ environment with `mesa[rec]>=3,<4`. If it does, run the Mesa
scripts with that interpreter. If it does not, use the committed
`skill-runtime.env.example` template (next to `SKILL.md`) and reuse a
workspace-local `.abm-mesa-env` cache:

```bash
ABM_MESA_PYTHON=python3.12
ABM_MESA_INSTALL_DIR=.abm-mesa-env
ABM_MESA_OUTPUT_ROOT=outputs
```

`ABM_MESA_INSTALL_DIR` is honored by `run_mesa_experiment.py` and
`serve_mesa_configurator.py`; `ABM_MESA_PYTHON` is honored by the configurator
when it invokes the runner. Source the template in any agent and keep a copied
`skill-runtime.env` untracked. Use temporary directories only for disposable
demos or smoke outputs, not for the normal dependency cache.

## Model Contract

For compatibility with `scripts/run_mesa_experiment.py`, write a model module that provides:

- A `mesa.Model` subclass named by `experiment.json` field `model_class`.
- Constructor keyword arguments for every field in `parameters`.
- Optional `seed` keyword argument for reproducibility.
- `step()` method.
- `snapshot() -> dict` returning scalar metrics; numeric values are summarized.

Example config shape:

```json
{
  "experiment_name": "density_sweep",
  "model_class": "ForestFireModel",
  "steps": 25,
  "primary_metric": "burned_fraction",
  "seeds": [11, 12],
  "parameters": {
    "width": 20,
    "height": 20,
    "density": [0.45, 0.65]
  }
}
```

The runner treats list-valued parameters as sweep dimensions and scalar parameters as fixed values.

## Implementation Pattern

Keep the model minimal and explicit:

1. Define agent state and update rules.
2. Define environment structure such as grid, network, or continuous space.
3. Seed randomness explicitly with `random.Random(seed)`.
4. Create agents in `__init__`.
5. Make `step()` update one tick.
6. Make `snapshot()` return metrics used by the experiment question.

Avoid adding visualization until a batch experiment runs. Visualization is useful for debugging but should not be the only evidence.

## Experiment Command

```bash
python3.10 abm-modeling/scripts/run_mesa_experiment.py \
  --model path/to/model.py \
  --config path/to/experiment.json \
  --output-dir path/to/output \
  --install-dir .abm-mesa-env
```

Outputs:

- `run_000.csv`, `run_001.csv`, ...: per-step metrics for each parameter/seed run.
- `summary.json`: aggregate metrics, parameter effects, and interpretation text.

## Configuration Page

When a user wants a configuration page to fill parameters in a browser after
the model is built, use `scripts/serve_mesa_configurator.py`:

```bash
python3.10 abm-modeling/scripts/serve_mesa_configurator.py \
  --model path/to/model.py \
  --config path/to/experiment.json \
  --output-root outputs/mesa-configurator \
  --install-dir .abm-mesa-env
```

Open the printed localhost URL in a browser — use the agent's built-in browser
if it has one, otherwise ask before opening the system GUI browser. The
configuration page renders scalar and comma-separated sweep fields from `experiment.json`,
writes the submitted config to a run directory, and invokes
`run_mesa_experiment.py`. Keep the browser page as the parameter-entry surface;
use the runner's CSV/JSON outputs for evidence and result claims.

## Visualization Command

After the batch experiment succeeds, generate a SolaraViz entrypoint:

```bash
python3.10 abm-modeling/scripts/generate_mesa_visualization.py \
  --model path/to/model.py \
  --config path/to/experiment.json \
  --output-app /tmp/abm-mesa-viz/app.py

solara run /tmp/abm-mesa-viz/app.py --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765` in a browser to inspect the simulation — use the agent's built-in browser if it has one, otherwise use an external GUI browser only when the user asks for it or approves it. Keep screenshots and visual inspection separate from the CSV/JSON evidence used for claims.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Randomness is not seeded | Accept `seed` and use an explicit random generator |
| Only final screenshots are saved | Save per-step CSV plus summary JSON |
| One run is treated as a conclusion | Run multiple seeds and report variation |
| Metrics are hidden in model internals | Return them from `snapshot()` |
| Sweep changes several concepts at once | Start with one primary varied parameter |
| Visualization is treated as proof | Use SolaraViz for inspection; use CSV/JSON outputs for evidence |
