# Model Catalog Contract

This is the minimal Mesa-first catalog contract for ABM model entries in
`abm-modeling`. The catalog is a metadata and readiness index first. It is not a
default model-code import mechanism.

## Purpose

The catalog lets agents organize Mesa scenarios without assuming that source
code is bundled, runnable, or redistributable. Entries should make source,
license, runtime, adapter, and evidence status machine-readable before any
reproduction claim is made.

## Required Entry Shape

Every catalog entry should identify:

- Model identity: `id`, `title`, `platform`, `source`.
- Classification: domain, mechanism tags, library or collection section.
- Runtime facts: file format, dependencies, runtime status, adapter status.
- Experiment facts: parameters, metrics, and available protocol status.
- Governance facts: license review, redistribution status, notes.

Scenario-specific references may add stricter fields when a Mesa model needs a
special runtime, data source, or evidence protocol.

## Source Boundary

Catalog metadata is allowed by default. Model source import, vendoring,
third-party output fixtures, and gold-set redistribution require explicit
source/license review. Metadata-only entries must not imply native runnable or
behaviorally reproduced status.

## Current Fixture

The first machine-readable fixture should be a small Mesa scenario catalog seed.
Treat it as a contract seed, not full model-library coverage.
