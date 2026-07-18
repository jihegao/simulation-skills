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
- `simulation_skills_contracts`: the provider-owned Version 0.1 contract
  package, deterministic conformance export, contract-only fake adapter, and
  independently packaged real warehouse queue and Equipment Maintenance SimPy
  adapters.

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

Installed skills include a best-effort startup update helper. When a skill is
activated, the helper can pull the configured GitHub source and reinstall the
suite without blocking the task if the network, remote, or checkout state is not
ready. Set `SIMULATION_SKILLS_GITHUB_REPO` when no `origin` remote is available,
or `SIMULATION_SKILLS_AUTO_UPDATE=0` to disable the check.

## Validate

Validate skill metadata:

```bash
bash scripts/validate_skills.sh
```

Run the copied AnyLogic reproduction tests:

```bash
python3 -m unittest discover -s tests -v
```

Build and validate the Version 0.1 provider export:

```bash
python3 scripts/build_contract_export.py
python3 -m unittest tests.test_v0_1_provider_contracts -v
python3 -m unittest tests.test_v0_1_fake_adapter -v
python3 -m unittest tests.test_v0_1_warehouse_des_adapter -v
python3 -m unittest tests.test_v0_1_equipment_maintenance_adapter -v
python3 -m unittest tests.test_v0_1_clean_install -v
```

The export root is
`simulation_skills_contracts/conformance/v0_1/`. Its manifest locks every
document by byte digest and locks the ordered document catalog by RFC 8785
digest. The installed `simulation-skills-fake-adapter` executable exists only
for cross-repository contract conformance; it is not a real simulation runtime
and cannot promote a claim beyond `draft_unreviewed`.

The formal Workstream 0 provider pin is Git tag `contracts-v0.1.0` together
with joint bundle digest
`sha256:6160830cf1f8dfd1699fd97c66ca437de41beaf3795e53b9d09d2d3fe1b00fb6`.
The pin closes the Version 0.1 contract baseline; it does not prove a production
sandbox or authorize the fake adapter as a real runtime.

## Real Warehouse Queue Adapter

The installed `simulation-skills-warehouse-des-adapter` executable implements
the narrow Workstream 1 warehouse continuity slice with SimPy. Its logical ID
is `simulation-skills.simpy.warehouse-des`, and it supports one
`experiment.run` operation for the `warehouse-queueing` Domain Pack.

The adapter consumes a closed, self-contained execution snapshot, runs an
exponential-arrival FIFO queue with a constrained resource and triangular
service times, and emits one complete `simulation.result_set` Artifact. The
Result Set remains `draft_unreviewed`; the adapter reports its actual Python
and SimPy runtime identity and explicitly does not claim calibration, warehouse
validity, comparison, sensitivity, or causality.

The real adapter manifest is packaged independently at
`simulation_skills_contracts/adapters/warehouse_des/adapter-manifest.json`.
It is deliberately not listed in the frozen Workstream 0 conformance export.
The `contracts-v0.1.0` tag, joint bundle digest, fake adapter manifest, and
contract fixtures therefore remain unchanged.

## Real Equipment Maintenance Adapter

The installed `simulation-skills-equipment-maintenance-adapter` executable is
the narrow Equipment Maintenance Domain Pack runtime. Its logical ID is
`simulation-skills.simpy.equipment-maintenance`, and it supports one
`experiment.run` operation for `equipment-maintenance`.

The adapter accepts only a closed, self-contained snapshot. It runs a seeded
SimPy model in which multiple assets fail according to exponential time to
failure, queue for a constrained maintenance resource, and receive triangular
repair times. It emits `availability` and aggregate `unplanned_downtime` in a
complete `simulation.result_set`; identical snapshots replay to identical
Result Set bytes.

The Result Set optional extension echoes the exact Domain Pack binding; the
closed execution manifest remains limited to protocol/runtime evidence
(input digest, seed, runtime identity, and produced refs). Results remain
`draft_unreviewed`: execution is not behavioral validation, calibration, or
domain certification. The adapter never reads Workbench or Domain Pack storage
and does not implement comparison, Finding, review, or export.

Its independently packaged manifest is
`simulation_skills_contracts/adapters/equipment_maintenance/adapter-manifest.json`.
Like the warehouse manifest, it is outside the frozen Workstream 0 conformance
export.

The Mesa reproduction tests require Mesa, NetworkX, and Solara assets. A local
Python 3.12 environment was used when these examples were copied from the
source workspace.

## Repository Boundary

`sim-adapter` is intentionally a router and evidence-boundary skill. It should
delegate method-specific work to sibling skills such as `abm-modeling` and
`discrete-event-modeling`, not embed those full skills as nested subskills.

See `docs/skill-boundaries.md` for the ownership model and
`docs/install.md` for installation details. See `agent.md` for the lightweight
simulation-dispatcher roadmap and method coverage registry. See
`docs/contracts/v0.1.md` for the provider contract and export boundary.
