"""Deterministic Result Set construction shared by fixtures and the fake adapter."""

from __future__ import annotations

from typing import Any


FIXED_TIME = "2026-07-14T00:00:00Z"


def result_template(seed: int, *, traffic: bool = False) -> dict[str, Any]:
    metrics = (
        [
            {"metric_id": "throughput", "value": 100 + seed % 17, "unit": "count", "dimensions": {}},
            {"metric_id": "average_wait_steps", "value": 10 + seed % 7, "unit": "step", "dimensions": {}},
        ]
        if traffic
        else [
            {"metric_id": "completed_jobs", "value": 100 + seed % 17, "unit": "count", "dimensions": {}},
            {"metric_id": "average_wait", "value": round(1.0 + (seed % 7) / 10, 1), "unit": "hour", "dimensions": {}},
        ]
    )
    return {
        "seed": seed,
        "metrics": metrics,
        "adapter_diagnostics": [{"code": "fixture_checks_passed", "fixture_only": True}],
        "claim_state": "draft_unreviewed",
    }


def build_result_set(
    request_id: str,
    model_spec_ref: dict[str, Any],
    experiment_ref: dict[str, Any],
    simulation_run_ref: dict[str, Any],
    template: dict[str, Any],
) -> dict[str, Any]:
    """Materialize a Result Set only after Workbench-owned refs are supplied."""

    return {
        "contract": "simulation.result_set",
        "schema_version": "0.1.0",
        "object_id": f"result-{request_id}",
        "revision": 1,
        "parent_revision": None,
        "created_at": FIXED_TIME,
        "created_by": {"kind": "adapter", "id": "simulation-skills.fake-conformance"},
        "provenance": {
            "parent_refs": [simulation_run_ref, model_spec_ref, experiment_ref],
            "source_artifact_refs": [],
        },
        "extensions": {},
        "simulation_run_ref": simulation_run_ref,
        "model_spec_ref": model_spec_ref,
        "experiment_ref": experiment_ref,
        **template,
        "raw_output_artifact_refs": [],
    }
