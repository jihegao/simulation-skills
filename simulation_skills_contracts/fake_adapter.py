"""Standalone contract-only adapter for Workstream 0 conformance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .canonical_json import digest
from .registry import EXPORT_ROOT, V01SimulationContractRegistry
from .result_factory import build_result_set, result_template


REQUEST_FIELDS = {
    "contract", "schema_version", "protocol_version", "request_id", "operation",
    "deadline", "cancellation_token", "project_ref", "scenario_refs", "model_spec_ref",
    "experiment_ref", "input_snapshot", "domain_pack_ref", "adapter_manifest_ref",
    "requested_output_contract", "claim_boundary",
}


class AdapterInputError(ValueError):
    pass


def _read_manifest() -> dict[str, Any]:
    return json.loads((EXPORT_ROOT / "adapter-manifest.json").read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validate_ref(value: Any, contract: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "contract", "schema_version", "object_id", "revision", "digest"
    }:
        raise AdapterInputError(f"{contract} ref has an invalid closed shape")
    if value["contract"] != contract or value["schema_version"] != "0.1.0":
        raise AdapterInputError(f"expected {contract}@0.1.0")
    if not isinstance(value["revision"], int) or isinstance(value["revision"], bool) or value["revision"] < 1:
        raise AdapterInputError("ref revision must be a positive integer")
    if not isinstance(value["digest"], str) or re.fullmatch(r"sha256:[a-f0-9]{64}", value["digest"]) is None:
        raise AdapterInputError("ref digest must be sha256")
    return value


def _validate_request(value: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != REQUEST_FIELDS:
        raise AdapterInputError("request has an invalid closed shape")
    constants = {
        "contract": "simulation.adapter_protocol.request",
        "schema_version": "0.1.0",
        "protocol_version": "0.1.0",
        "operation": "experiment.run",
        "requested_output_contract": "simulation.result_set@0.1",
    }
    for key, expected in constants.items():
        if value.get(key) != expected:
            raise AdapterInputError(f"request {key} is incompatible")
    for key in ("request_id", "cancellation_token"):
        if not isinstance(value[key], str) or re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value[key]
        ) is None:
            raise AdapterInputError(f"request {key} is invalid")
    snapshot = value["input_snapshot"]
    if not isinstance(snapshot, dict):
        raise AdapterInputError("input_snapshot must be an object")
    seed = snapshot.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise AdapterInputError("input_snapshot.seed must be a non-negative integer")
    _validate_ref(snapshot.get("simulation_run_ref"), "workbench.simulation_run")
    _validate_ref(value["project_ref"], "workbench.project")
    scenario_refs = value["scenario_refs"]
    if not isinstance(scenario_refs, list) or not scenario_refs:
        raise AdapterInputError("scenario_refs must be a non-empty array")
    for scenario_ref in scenario_refs:
        _validate_ref(scenario_ref, "workbench.scenario")
    _validate_ref(value["model_spec_ref"], "simulation.model_spec")
    _validate_ref(value["experiment_ref"], "workbench.experiment")
    _validate_ref(value["domain_pack_ref"], "simulation.domain_pack")
    if value["domain_pack_ref"]["object_id"] != "equipment-maintenance":
        raise AdapterInputError("fake adapter only supports equipment-maintenance")
    boundary = value["claim_boundary"]
    if not isinstance(boundary, dict) or set(boundary) != {"claim_state", "non_claims"}:
        raise AdapterInputError("claim_boundary has an invalid closed shape")
    if (
        boundary["claim_state"] != "draft_unreviewed"
        or not isinstance(boundary["non_claims"], list)
        or not boundary["non_claims"]
        or not all(isinstance(item, str) and item for item in boundary["non_claims"])
    ):
        raise AdapterInputError("fake adapter cannot promote a claim")
    manifest_ref = value["adapter_manifest_ref"]
    expected_manifest_ref = {
        "adapter_id": manifest["adapter_id"],
        "adapter_version": manifest["adapter_version"],
        "protocol_version": "0.1.0",
        "manifest_digest": digest(manifest),
    }
    if manifest_ref != expected_manifest_ref:
        raise AdapterInputError("adapter manifest ref is stale or inconsistent")
    return value


def describe(response: Path) -> None:
    _write_json(response, _read_manifest())


def execute(request_path: Path, response_path: Path, artifact_root: Path) -> None:
    manifest = _read_manifest()
    request = _validate_request(
        json.loads(request_path.read_text(encoding="utf-8")), manifest
    )
    if artifact_root.is_symlink():
        raise AdapterInputError("artifact root cannot be a symlink")
    if artifact_root.exists():
        if not artifact_root.is_dir() or any(artifact_root.iterdir()):
            raise AdapterInputError("artifact root must be an empty directory")
    else:
        artifact_root.mkdir(mode=0o700, parents=True)
    seed = request["input_snapshot"]["seed"]
    result_set = build_result_set(
        request["request_id"],
        request["model_spec_ref"],
        request["experiment_ref"],
        request["input_snapshot"]["simulation_run_ref"],
        result_template(seed),
    )
    V01SimulationContractRegistry().validate_object(result_set)
    artifact_path = artifact_root / "result-set.json"
    artifact_bytes = (
        json.dumps(result_set, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    artifact_path.write_bytes(artifact_bytes)
    result_ref = {
        "contract": result_set["contract"],
        "schema_version": result_set["schema_version"],
        "object_id": result_set["object_id"],
        "revision": result_set["revision"],
        "digest": digest(result_set),
    }
    response = {
        "contract": "simulation.adapter_protocol.response",
        "schema_version": "0.1.0",
        "protocol_version": "0.1.0",
        "request_id": request["request_id"],
        "adapter_ref": request["adapter_manifest_ref"],
        "operation": "experiment.run",
        "status": "completed",
        "produced_refs": [result_ref],
        "artifacts": [{
            "relative_path": "result-set.json",
            "byte_size": len(artifact_bytes),
            "media_type": "application/json",
            "digest": "sha256:" + hashlib.sha256(artifact_bytes).hexdigest(),
            "semantic_role": "result_set",
        }],
        "execution_manifest": {
            "input_digest": digest(request["input_snapshot"]),
            "adapter_identity": f"{manifest['adapter_id']}@{manifest['adapter_version']}",
            "runtime_identity": "python-contract-fixture@0.1.0",
            "seed": seed,
            "environment": {"fixture_only": True, "runtime": "contract-only"},
            "produced_refs": [result_ref],
        },
        "diagnostics": [{"code": "fixture_checks_passed", "fixture_only": True}],
        "warnings": [],
        "non_claims": ["This contract-only fixture does not establish model or behavioral validity."],
        "timing": {"started_at": "2026-07-14T00:00:00Z", "completed_at": "2026-07-14T00:00:00Z", "duration_ms": 0},
        "failure": None,
    }
    _write_json(response_path, response)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="verb", required=True)
    describe_parser = subparsers.add_parser("describe")
    describe_parser.add_argument("--response", type=Path, required=True)
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--request", type=Path, required=True)
    execute_parser.add_argument("--response", type=Path, required=True)
    execute_parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.verb == "describe":
        describe(args.response)
    else:
        execute(args.request, args.response, args.artifact_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
