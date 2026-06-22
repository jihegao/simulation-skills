# Scenario Pack Contract

This is the minimal scenario-pack contract for future reusable Mesa ABM work in
`abm-modeling`. A scenario pack is the bridge between a model catalog entry
and evidence-producing runs.

## Purpose

Scenario packs describe how to run, measure, and interpret a bounded ABM case.
They should make experiment protocols portable across agents without depending
on browser visualization or informal notebook state.

## Expected Sections

A mature scenario pack should include:

- `scenario.md`: phenomenon, model assumptions, scope, and claim boundaries.
- Parameter contract: names, defaults, sweep values, and units when known.
- Metric contract: metric names, types, interpretation, and output paths.
- Protocol contract: setup, steps, seeds or repetitions, stop conditions.
- Adapter contract: runner command, local model path, and dependency notes.
- Evidence contract: CSV/JSON output schema, summaries, and run metadata.

## Evidence Priority

CSV/JSON/headless evidence is primary. Visualization can support inspection and
debugging, but it is not sufficient by itself for reproducibility claims.
