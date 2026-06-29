---
name: discrete-event-modeling
description: Use when Codex needs to design, write, run, experiment with, or explain discrete-event simulations in SimPy, including queues, resources, arrivals, service processes, reneging, repair systems, inventory flows, parameter sweeps, stochastic experiments, CSV/JSON outputs, ModelingIR or SimAgent-compatible export planning, and evidence-bounded interpretation.
---

# Discrete-Event Modeling

## Overview

Build a runnable DES model first, then run a small experiment and explain only what the outputs support. Prefer SimPy for Python-native workflows, explicit event processes, resource contention, queues, repair systems, inventory replenishment, and automated validation.

## Startup Update

At skill activation, make a best-effort update attempt before doing modeling work:

```bash
python3 "$HOME/.codex/skills/discrete-event-modeling/scripts/auto_update_from_github.py"
```

The helper pulls from the configured GitHub source and reinstalls the suite when
safe. It skips dirty checkouts, missing GitHub configuration, network failures,
and recent successful checks without blocking the user task. Set
`SIMULATION_SKILLS_AUTO_UPDATE=0` to disable it.

## Workflow

1. Clarify the entities, arrivals, resources, queues, service processes, event rules, parameters, metrics, and experiment question.
2. Create a minimal runnable SimPy model before adding sophistication.
3. Run at least one deterministic smoke experiment and one small stochastic sweep when randomness matters.
4. Save raw run data plus a summary; interpret trends, uncertainty, bottlenecks, and limits without overclaiming causality.
5. When asked for integration, export or describe a `modeling-ir/v0` or SimAgent-compatible spec as an artifact boundary, not by importing simulator internals.

## Quick Start

For the DES agent-swarm MVP, use `des_mvp.py` as the shared CLI/backend path
for Codex, Claude Code, OpenCode, or direct terminal use:

```bash
python3 discrete-event-modeling/scripts/des_mvp.py \
  "repair jobs arrive every 16 minutes, compare one and two repairers over 24 hours" \
  --output-root outputs/des_mvp \
  --session-file outputs/des_mvp/session.json \
  --install-dir /tmp/des-simpy-env
```

The MVP currently uses deterministic local parsing for supported repair-queue
and spare-parts inventory requests, then writes `request.json`, generated
model/config files, runner CSVs, `summary.json`, `answer.md`,
`ascii_topology.txt`, `metrics_chart.txt`, and `chart.csv`.

For continuous conversations, keep passing the same `--session-file`. Agent
frontends can use this file to let follow-up turns modify the previous request,
such as `change repairers to 3` or `set reorder point to 10 and 30`.

For direct terminal use, `chat` mode reads one turn per line until `exit` or
`quit`:

```bash
python3 discrete-event-modeling/scripts/des_mvp.py chat \
  --output-root outputs/des_mvp \
  --session-file outputs/des_mvp/session.json
```

Use the bundled repair-queue example as the known-good execution path:

```bash
python3 discrete-event-modeling/scripts/run_simpy_experiment.py \
  --model discrete-event-modeling/assets/simpy_repair_queue/model.py \
  --config discrete-event-modeling/assets/simpy_repair_queue/experiment.json \
  --output-dir /tmp/des-simpy-results \
  --install-dir /tmp/des-simpy-env
```

## Resource Routing

Use scripts instead of retyping runners:

- `scripts/des_mvp.py`: Shared agent-swarm MVP entrypoint. Converts supported
  user language into a structured modeling request, generates a SimPy model,
  runs the experiment, and writes evidence-bounded result artifacts. Use
  `--session-file` for continuing dialogue and `chat` for stdin-driven
  conversation loops. Successful runs include `ascii_topology.txt`,
  `metrics_chart.txt`, and `chart.csv`.
- `scripts/run_simpy_experiment.py`: Installs SimPy into a venv when requested, runs a JSON-configured sweep, writes per-run CSV files and `summary.json`.

Use assets as copyable starting points:

- `assets/simpy_repair_queue/`: Repair arrivals, limited repair crews, queue waits, utilization, and throughput.
- `assets/simpy_spare_parts_inventory/`: Stochastic part demand, replenishment lead time, stockouts, and service level.

## SimPy Model Requirements

When writing a SimPy model for this skill, expose a Python class named in the experiment config. The class must accept keyword parameters plus `seed`, create its own `simpy.Environment`, and implement `run(until: float) -> list[dict]`. Return rows with a numeric `time` field and numeric metrics. Keep seeded randomness explicit so repeated runs are reproducible.

Use Python 3.10+ for SimPy 4 workflows; prefer Python 3.12 when available. If a local install configured `.codex/skill-runtime.env`, source it before running tests or examples so `DES_SIMPY_TEST_PYTHON` selects the intended interpreter.

Use SimPy concepts directly:

- `simpy.Environment` for simulated time.
- `simpy.Resource` or `simpy.PriorityResource` for constrained servers, crews, machines, beds, docks, or inspectors.
- `simpy.Container` or `simpy.Store` for fluids, inventory, buffers, and spare parts.
- Process functions with `yield env.timeout(...)`, `yield request`, and combined events such as `request | env.timeout(patience)` when modeling reneging.

## Result Explanation

Every DES result explanation must state:

- Experiment question and varied parameters.
- Number of runs, seeds, and simulated time horizon.
- Primary metric trend with raw summary values.
- Queueing, utilization, stockout, or delay mechanism that explains the trend.
- Stochastic uncertainty or run-to-run variation.
- Model assumptions and what the results do not prove.

## Integration Boundary

Keep this skill as a modeling expertise pack. Scenario packs may include export notes or generated specs, but do not import SGR, simulator, or SimAgent internals. Cross-repo integration should happen through explicit files such as `modeling-ir/v0`, SimAgent-compatible specs, CSV outputs, and `summary.json`.

## Validation

Before claiming the skill is ready, run:

```bash
python3 -m unittest -v tests/test_skill_contract.py
python3 /path/to/quick_validate.py discrete-event-modeling
```

`quick_validate.py` imports PyYAML; if the system Python lacks `yaml`, run it with a Python environment that has PyYAML installed.
