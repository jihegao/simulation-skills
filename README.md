# Simulation Skills

Simulation Skills is a suite of Codex skills and runnable examples for
simulation-backed reasoning, model conversion, agent-based modeling, and
discrete-event simulation.

The repository is organized as a publishable source tree. Installed Codex
skills remain flat siblings under `~/.codex/skills`; the `skills/` directory is
only a GitHub-friendly way to keep the suite together.

## Contents

- `skills/sim-adapter`: routing layer for complex-system reasoning questions.
- `skills/abm-modeling`: Mesa/ABM modeling workflow, scripts, and references.
- `skills/discrete-event-modeling`: SimPy/DES workflow, scripts, and scenario
  assets.
- `skills/simulation-model-conversion`: workflow for converting simulation
  descriptions or models into runnable artifacts.
- `examples/air_defense_mesa`, `examples/field_service_mesa`, and
  `examples/hospital_material_mesa`: Mesa reproductions of local AnyLogic PLE
  example mechanisms.
- `examples/discrete-event`: SimPy scenario examples copied from the local DES
  workspace.
- `examples/global_shipping_mesa`: Mesa/SimPy global shipping dispatch example
  with embedded port GIS points and a CesiumJS 3D globe viewer.
- `examples/global_warming_system_dynamics`: a self-contained stock-flow page
  for short- and medium-term global warming scenario checks.

See `examples/README.md` for the runnable simulation case library.

## Install Skills Locally

```bash
bash scripts/install_skills.sh
```

By default this copies every directory under `skills/` into
`~/.codex/skills/<skill-name>`. Override the destination with:

```bash
CODEX_SKILLS_DIR=/path/to/skills bash scripts/install_skills.sh
```

## Validate

Validate skill metadata:

```bash
bash scripts/validate_skills.sh
```

Run the copied AnyLogic reproduction tests:

```bash
python3 -m unittest discover -s tests -v
```

The Mesa reproduction tests require Mesa, NetworkX, and Solara assets. A local
Python 3.12 environment was used when these examples were copied from the
source workspace.

## Repository Boundary

`sim-adapter` is intentionally a router and evidence-boundary skill. It should
delegate method-specific work to sibling skills such as `abm-modeling` and
`discrete-event-modeling`, not embed those full skills as nested subskills.

See `docs/skill-boundaries.md` for the ownership model and
`docs/install.md` for installation details.
