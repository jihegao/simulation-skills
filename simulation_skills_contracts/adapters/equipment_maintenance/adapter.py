"""Installed simulation.adapter_protocol adapter for Equipment Maintenance."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import time
from typing import Any

import simpy

from ...canonical_json import digest
from ...registry import V01SimulationContractRegistry
from .model import EquipmentMaintenanceConfig, EquipmentMaintenanceModel


ADAPTER_ID = "simulation-skills.simpy.equipment-maintenance"
MANIFEST_PATH = Path(__file__).with_name("adapter-manifest.json")
DOMAIN_PACK_EXTENSION = "org.openai.simulation.domain_pack_execution"
REQUEST_FIELDS = {
    "contract", "schema_version", "protocol_version", "request_id", "operation",
    "deadline", "cancellation_token", "project_ref", "scenario_refs", "model_spec_ref",
    "experiment_ref", "input_snapshot", "domain_pack_ref", "adapter_manifest_ref",
    "requested_output_contract", "claim_boundary",
}
SNAPSHOT_FIELDS = {
    "seed", "simulation_run_ref", "model_spec_digest", "method_payload_digest",
    "experiment_digest", "result_created_at", "time_unit", "horizon",
    "domain_pack_binding", "asset_count", "failure_process",
    "maintenance_resource", "repair_process", "requested_metrics",
}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
DIGEST = re.compile(r"sha256:[a-f0-9]{64}")
UTC_TIMESTAMP = re.compile(
    r"[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?Z"
)


class AdapterInputError(ValueError):
    """Raised before any response or trusted Artifact is written."""


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _closed_ref(value: Any, contract: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "contract", "schema_version", "object_id", "revision", "digest"
    }:
        raise AdapterInputError(f"{contract} ref has an invalid closed shape")
    if value["contract"] != contract or value["schema_version"] != "0.1.0":
        raise AdapterInputError(f"expected {contract}@0.1.0")
    if not isinstance(value["object_id"], str) or IDENTIFIER.fullmatch(value["object_id"]) is None:
        raise AdapterInputError(f"{contract} object_id is invalid")
    if type(value["revision"]) is not int or value["revision"] < 1:
        raise AdapterInputError(f"{contract} revision must be a positive integer")
    if not isinstance(value["digest"], str) or DIGEST.fullmatch(value["digest"]) is None:
        raise AdapterInputError(f"{contract} digest is invalid")
    return value


def _positive_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdapterInputError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise AdapterInputError(f"{label} must be finite and positive")
    return number


def _domain_pack_binding(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {
        "pack_id", "pack_version", "manifest_digest"
    }:
        raise AdapterInputError("domain_pack_binding has an invalid closed shape")
    if value["pack_id"] != "equipment-maintenance":
        raise AdapterInputError("domain_pack_binding pack_id is unsupported")
    if value["pack_version"] != "0.1.0":
        raise AdapterInputError("domain_pack_binding pack version has drifted")
    if not isinstance(value["manifest_digest"], str) or DIGEST.fullmatch(value["manifest_digest"]) is None:
        raise AdapterInputError("domain_pack_binding manifest_digest is invalid")
    return value


def _validate_snapshot(value: Any, request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != SNAPSHOT_FIELDS:
        raise AdapterInputError("input_snapshot has an invalid closed shape")
    if type(value["seed"]) is not int or value["seed"] < 0:
        raise AdapterInputError("input_snapshot.seed must be a non-negative integer")
    _closed_ref(value["simulation_run_ref"], "workbench.simulation_run")
    for field in ("model_spec_digest", "method_payload_digest", "experiment_digest"):
        if not isinstance(value[field], str) or DIGEST.fullmatch(value[field]) is None:
            raise AdapterInputError(f"input_snapshot.{field} is invalid")
    if value["model_spec_digest"] != request["model_spec_ref"]["digest"]:
        raise AdapterInputError("input_snapshot is not bound to model_spec_ref")
    if value["experiment_digest"] != request["experiment_ref"]["digest"]:
        raise AdapterInputError("input_snapshot is not bound to experiment_ref")
    if (
        not isinstance(value["result_created_at"], str)
        or UTC_TIMESTAMP.fullmatch(value["result_created_at"]) is None
    ):
        raise AdapterInputError("input_snapshot.result_created_at must be a UTC Z timestamp")
    if value["time_unit"] != "hour":
        raise AdapterInputError("equipment maintenance adapter only supports hour time units")
    _positive_number(value["horizon"], "input_snapshot.horizon")
    _domain_pack_binding(value["domain_pack_binding"])
    if type(value["asset_count"]) is not int or value["asset_count"] < 1:
        raise AdapterInputError("input_snapshot.asset_count must be a positive integer")

    failure = value["failure_process"]
    if not isinstance(failure, dict) or set(failure) != {
        "distribution", "mean_time_between_failures", "unit"
    }:
        raise AdapterInputError("failure_process has an invalid closed shape")
    if failure["distribution"] != "exponential" or failure["unit"] != value["time_unit"]:
        raise AdapterInputError("failure_process distribution or unit is unsupported")
    _positive_number(
        failure["mean_time_between_failures"],
        "failure_process.mean_time_between_failures",
    )

    resource = value["maintenance_resource"]
    if not isinstance(resource, dict) or set(resource) != {
        "resource_id", "capacity", "capacity_unit"
    }:
        raise AdapterInputError("maintenance_resource has an invalid closed shape")
    if not isinstance(resource["resource_id"], str) or IDENTIFIER.fullmatch(resource["resource_id"]) is None:
        raise AdapterInputError("maintenance_resource.resource_id is invalid")
    if type(resource["capacity"]) is not int or resource["capacity"] < 1:
        raise AdapterInputError("maintenance_resource.capacity must be a positive integer")
    if resource["capacity_unit"] != "count":
        raise AdapterInputError("maintenance_resource.capacity_unit must be count")

    repair = value["repair_process"]
    if not isinstance(repair, dict) or set(repair) != {
        "resource_id", "distribution", "minimum", "mode", "maximum", "unit"
    }:
        raise AdapterInputError("repair_process has an invalid closed shape")
    if (
        repair["resource_id"] != resource["resource_id"]
        or repair["distribution"] != "triangular"
        or repair["unit"] != value["time_unit"]
    ):
        raise AdapterInputError("repair_process resource, distribution, or unit is unsupported")
    minimum = _positive_number(repair["minimum"], "repair_process.minimum")
    mode = _positive_number(repair["mode"], "repair_process.mode")
    maximum = _positive_number(repair["maximum"], "repair_process.maximum")
    if not minimum <= mode <= maximum:
        raise AdapterInputError("repair_process requires minimum <= mode <= maximum")
    if value["requested_metrics"] != ["availability", "unplanned_downtime"]:
        raise AdapterInputError("requested_metrics are not supported by this adapter")
    return value


def _validate_request(value: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != REQUEST_FIELDS:
        raise AdapterInputError("request has an invalid closed shape")
    expected = {
        "contract": "simulation.adapter_protocol.request",
        "schema_version": "0.1.0",
        "protocol_version": "0.1.0",
        "operation": "experiment.run",
        "requested_output_contract": "simulation.result_set@0.1",
    }
    if any(value.get(key) != constant for key, constant in expected.items()):
        raise AdapterInputError("request protocol or operation is incompatible")
    for field in ("request_id", "cancellation_token"):
        if not isinstance(value[field], str) or IDENTIFIER.fullmatch(value[field]) is None:
            raise AdapterInputError(f"request {field} is invalid")
    if len(f"result-{value['request_id']}") > 128:
        raise AdapterInputError("request_id is too long for the Result Set identity")
    _closed_ref(value["project_ref"], "workbench.project")
    if not isinstance(value["scenario_refs"], list) or not value["scenario_refs"]:
        raise AdapterInputError("scenario_refs must be a non-empty array")
    for scenario_ref in value["scenario_refs"]:
        _closed_ref(scenario_ref, "workbench.scenario")
    _closed_ref(value["model_spec_ref"], "simulation.model_spec")
    _closed_ref(value["experiment_ref"], "workbench.experiment")
    _closed_ref(value["domain_pack_ref"], "simulation.domain_pack")
    if value["domain_pack_ref"]["object_id"] != "equipment-maintenance":
        raise AdapterInputError("equipment maintenance adapter only supports equipment-maintenance")
    if value["adapter_manifest_ref"] != {
        "adapter_id": manifest["adapter_id"],
        "adapter_version": manifest["adapter_version"],
        "protocol_version": "0.1.0",
        "manifest_digest": digest(manifest),
    }:
        raise AdapterInputError("adapter manifest ref is stale or inconsistent")
    boundary = value["claim_boundary"]
    if (
        not isinstance(boundary, dict)
        or set(boundary) != {"claim_state", "non_claims"}
        or boundary.get("claim_state") != "draft_unreviewed"
        or not isinstance(boundary.get("non_claims"), list)
        or not boundary["non_claims"]
        or not all(isinstance(item, str) and item for item in boundary["non_claims"])
    ):
        raise AdapterInputError("claim_boundary cannot promote a claim")
    _validate_snapshot(value["input_snapshot"], value)
    return value


def _result_set(request: dict[str, Any], outcome) -> dict[str, Any]:
    snapshot = request["input_snapshot"]
    binding = deepcopy(snapshot["domain_pack_binding"])
    unfinished = outcome.waiting_at_horizon + outcome.in_repair_at_horizon
    return {
        "contract": "simulation.result_set",
        "schema_version": "0.1.0",
        "object_id": f"result-{request['request_id']}",
        "revision": 1,
        "parent_revision": None,
        "created_at": snapshot["result_created_at"],
        "created_by": {"kind": "adapter", "id": ADAPTER_ID},
        "provenance": {
            "parent_refs": [
                snapshot["simulation_run_ref"],
                request["model_spec_ref"],
                request["experiment_ref"],
                request["domain_pack_ref"],
            ],
            "source_artifact_refs": [],
        },
        "extensions": {
            DOMAIN_PACK_EXTENSION: {
                "required": False,
                "schema_ref": "urn:workbench:domain-pack-execution@0.1.0",
                "payload": binding,
            }
        },
        "simulation_run_ref": snapshot["simulation_run_ref"],
        "model_spec_ref": request["model_spec_ref"],
        "experiment_ref": request["experiment_ref"],
        "seed": snapshot["seed"],
        "metrics": [
            {
                "metric_id": "availability",
                "value": round(outcome.availability, 12),
                "unit": "ratio",
                "dimensions": {},
            },
            {
                "metric_id": "unplanned_downtime",
                "value": round(outcome.unplanned_downtime, 9),
                "unit": snapshot["time_unit"],
                "dimensions": {"aggregation": "asset_hours"},
            },
        ],
        "raw_output_artifact_refs": [],
        "adapter_diagnostics": [{
            "code": "equipment_maintenance_simpy_completed",
            "asset_count": snapshot["asset_count"],
            "failures": outcome.failures,
            "repair_started": outcome.repair_started,
            "repairs_completed": outcome.repairs_completed,
            "waiting_at_horizon": outcome.waiting_at_horizon,
            "in_repair_at_horizon": outcome.in_repair_at_horizon,
            "unfinished_failures": unfinished,
            "horizon": snapshot["horizon"],
            "time_unit": snapshot["time_unit"],
            "horizon_boundary": "exclusive",
            "availability_definition": "one_minus_total_asset_downtime_over_asset_exposure",
            "runtime_validation": "executed",
            "behavior_validation": "not_evaluated",
            "domain_certification": "not_evaluated",
        }],
        "claim_state": "draft_unreviewed",
    }


def _atomic_write(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise AdapterInputError(f"output path already exists: {path.name}")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def describe(response_path: Path) -> None:
    raw = (
        json.dumps(_manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _atomic_write(response_path, raw)


def execute(request_path: Path, response_path: Path, artifact_root: Path) -> None:
    manifest = _manifest()
    request = _validate_request(
        json.loads(request_path.read_text(encoding="utf-8")), manifest
    )
    if artifact_root.is_symlink():
        raise AdapterInputError("artifact root cannot be a symlink")
    if artifact_root.exists() and (
        not artifact_root.is_dir() or any(artifact_root.iterdir())
    ):
        raise AdapterInputError("artifact root must be an empty directory")

    snapshot = request["input_snapshot"]
    config = EquipmentMaintenanceConfig(
        horizon=float(snapshot["horizon"]),
        asset_count=snapshot["asset_count"],
        mean_time_between_failures=float(
            snapshot["failure_process"]["mean_time_between_failures"]
        ),
        maintenance_capacity=snapshot["maintenance_resource"]["capacity"],
        repair_minimum=float(snapshot["repair_process"]["minimum"]),
        repair_mode=float(snapshot["repair_process"]["mode"]),
        repair_maximum=float(snapshot["repair_process"]["maximum"]),
        seed=snapshot["seed"],
    )
    started_at = datetime.now(timezone.utc)
    started_monotonic = time.monotonic()
    result_set = _result_set(request, EquipmentMaintenanceModel(config).run())
    V01SimulationContractRegistry().validate_object(result_set)
    result_bytes = (
        json.dumps(result_set, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    result_ref = {
        "contract": result_set["contract"],
        "schema_version": result_set["schema_version"],
        "object_id": result_set["object_id"],
        "revision": result_set["revision"],
        "digest": digest(result_set),
    }
    if not artifact_root.exists():
        artifact_root.mkdir(mode=0o700, parents=True)
    artifact_path = artifact_root / "result-set.json"
    _atomic_write(artifact_path, result_bytes)
    completed_at = datetime.now(timezone.utc)
    duration_ms = max(0, round((time.monotonic() - started_monotonic) * 1000))
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
            "byte_size": len(result_bytes),
            "media_type": "application/json",
            "digest": "sha256:" + hashlib.sha256(result_bytes).hexdigest(),
            "semantic_role": "result_set",
        }],
        "execution_manifest": {
            "input_digest": digest(snapshot),
            "adapter_identity": f"{ADAPTER_ID}@{manifest['adapter_version']}",
            "runtime_identity": (
                f"simpy@{simpy.__version__};python@{platform.python_version()};"
                "equipment-maintenance@0.1.0"
            ),
            "seed": snapshot["seed"],
            "environment": {
                "runtime": "simpy",
                "simpy_version": simpy.__version__,
                "python_version": platform.python_version(),
                "random_stream_policy": "sha256-derived-per-asset-failure-and-repair-v0.1",
            },
            "produced_refs": [result_ref],
        },
        "diagnostics": [{
            "code": "equipment_maintenance_simpy_completed",
            "method_family": "discrete_event",
            "runtime": "simpy",
            "runtime_validation": "executed",
            "behavior_validation": "not_evaluated",
            "domain_certification": "not_evaluated",
        }],
        "warnings": [],
        "non_claims": [
            "This run executes the declared maintenance model but does not establish behavioral validity or domain certification.",
            "No calibration, sensitivity analysis, comparison, policy recommendation, or causal claim was performed.",
        ],
        "timing": {
            "started_at": started_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "completed_at": completed_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "duration_ms": duration_ms,
        },
        "failure": None,
    }
    _atomic_write(
        response_path,
        (json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


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
