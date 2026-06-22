---
name: simulation-model-conversion
description: >
  Convert simulation cases, model descriptions, AnyLogic/Mesa/SimPy structures,
  or visual prototype requirements into runnable simulation artifacts. Use when
  Codex needs to migrate, reproduce, or translate a simulation model across
  runtimes such as Mesa ABM, SimPy DES, system dynamics, static HTML/legacy JS,
  or scenario-pack JSON while preserving assumptions, mechanisms, metrics,
  visualization requirements, and validation evidence.
---

# Simulation Model Conversion

## Purpose

Convert a simulation source into a runnable target without pretending runtime
equivalence. Preserve mechanism truth, state assumptions, and produce artifacts
that can be tested, inspected, and rerun.

## Workflow

1. **Identify the source boundary.** Name the source type: prose case card,
   `.alp` import, existing Python model, spreadsheet, JSON spec, browser
   prototype, or mixed artifacts. Inspect real local files before making claims.
2. **Extract the mechanism contract.** Record entities, states, events,
   resources, queues, spatial movement, stochastic rules, parameters, costs,
   metrics, and visualization needs.
3. **Choose the target runtime.** Use the smallest target that preserves the
   mechanism:
   - Mesa for heterogeneous agents, spatial/network behavior, local rules.
   - SimPy for queues, service resources, arrivals, repairs, inventory, and DES.
   - System dynamics for aggregate stocks, flows, feedback, and policy levers.
   - Legacy JS/HTML for browser-visible demonstrations and lightweight teaching
     tools when no server runtime should be required.
   - JSON/IR when the output is an interchange contract rather than executable
     code.
4. **Map source to target explicitly.** Create a small mapping table from source
   component/state/transition/variable to target class/function/state/metric.
   Mark approximations as approximations.
5. **Implement the thinnest runnable slice first.** Start with deterministic
   smoke behavior before adding stochastic sweeps, controls, or visuals.
6. **Add evidence artifacts.** Include focused tests, raw CSV/JSON summaries,
   replay frames, screenshots, or browser smoke checks as appropriate.
7. **Write the claim boundary.** Say what the converted model supports and what
   it does not prove about the original runtime or real system.

## Target Deliverables

For executable conversions, prefer this bundle:

- `model.py` or equivalent core model with seeded randomness.
- `run_experiment.py` or a documented run command for sweeps.
- `experiment.json` for defaults and varied parameters.
- A visual surface when requested: Solara, static replay HTML, or legacy JS.
- Tests covering defaults, priority rules, state transitions, outputs, and UI
  markers.
- README commands that reproduce outputs from a clean checkout.

For browser-only conversions:

- Produce one self-contained `index.html` unless the user asks for a framework.
- Avoid CDN and build steps when the request says legacy JS, plain JS, static
  page, classroom demo, or offline.
- Keep simulation state in explicit objects, not hidden DOM state.
- Provide Start/Stop, Step, Reset, parameter controls, metrics, and logs when
  the model has dynamic behavior.

## Evidence Boundaries

Use this wording pattern:

```text
This is a behavioral reproduction, not a runtime import. Source artifacts were
used as structural evidence for entities, parameters, states, and transitions.
Results describe behavior under these assumptions and do not prove equivalence
with the original engine.
```

When an importer is used, treat its output as structural evidence only. Read
the import report before claiming counts, state names, transitions, or default
parameters.

## Reference

Read `references/conversion-checklist.md` when the task includes unclear model
boundaries, multiple possible runtimes, or a required visual/UI conversion.
