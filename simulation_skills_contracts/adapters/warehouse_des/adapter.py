"""Installed simulation.adapter_protocol adapter for the warehouse DES case."""

from __future__ import annotations

import argparse
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
from .model import WarehouseQueueConfig, WarehouseQueueModel


ADAPTER_ID = "simulation-skills.simpy.warehouse-des"
MANIFEST_PATH = Path(__file__).with_name("adapter-manifest.json")
REQUEST_FIELDS = {
    "contract", "schema_version", "protocol_version", "request_id", "operation",
    "deadline", "cancellation_token", "project_ref", "scenario_refs", "model_spec_ref",
    "experiment_ref", "input_snapshot", "domain_pack_ref", "adapter_manifest_ref",
    "requested_output_contract", "claim_boundary",
}
SNAPSHOT_FIELDS = {
    "seed", "simulation_run_ref", "model_spec_digest", "method_payload_digest",
    "experiment_digest", "result_created_at", "time_unit", "horizon",
    "arrival_process", "resource", "service_process", "requested_metrics",
}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
DIGEST = re.compile(r"sha256:[a-f0-9]{64}")
UTC_TIMESTAMP = re.compile(
    r"[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?Z"
)


class AdapterInputError(ValueError):
    """Raised before any response or Artifact is written."""


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _closed_ref(value: Any, contract: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "contract", "schema_version", "object_id", "revision", "digest"
    }:
        raise AdapterInputError(f"{contract} ref has an invalid closed shape")
    if value["contract"] != contract or value["schema_version"] != "0.1.0":
        raise AdapterInputError(f"expected {contract}@0.1.0")
    if IDENTIFIER.fullmatch(value["object_id"]) is None:
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
        raise AdapterInputError("warehouse adapter only supports hour time units")
    _positive_number(value["horizon"], "input_snapshot.horizon")

    arrival = value["arrival_process"]
    if not isinstance(arrival, dict) or set(arrival) != {
        "distribution", "mean_interarrival", "unit"
    }:
        raise AdapterInputError("arrival_process has an invalid closed shape")
    if arrival["distribution"] != "exponential" or arrival["unit"] != value["time_unit"]:
        raise AdapterInputError("arrival_process distribution or unit is unsupported")
    _positive_number(arrival["mean_interarrival"], "arrival_process.mean_interarrival")

    resource = value["resource"]
    if not isinstance(resource, dict) or set(resource) != {
        "resource_id", "capacity", "capacity_unit"
    }:
        raise AdapterInputError("resource has an invalid closed shape")
    if not isinstance(resource["resource_id"], str) or IDENTIFIER.fullmatch(resource["resource_id"]) is None:
        raise AdapterInputError("resource.resource_id is invalid")
    if type(resource["capacity"]) is not int or resource["capacity"] < 1:
        raise AdapterInputError("resource.capacity must be a positive integer")
    if resource["capacity_unit"] != "count":
        raise AdapterInputError("resource.capacity_unit must be count")

    service = value["service_process"]
    if not isinstance(service, dict) or set(service) != {
        "resource_id", "distribution", "minimum", "mode", "maximum", "unit"
    }:
        raise AdapterInputError("service_process has an invalid closed shape")
    if (
        service["resource_id"] != resource["resource_id"]
        or service["distribution"] != "triangular"
        or service["unit"] != value["time_unit"]
    ):
        raise AdapterInputError("service_process resource, distribution, or unit is unsupported")
    minimum = _positive_number(service["minimum"], "service_process.minimum")
    mode = _positive_number(service["mode"], "service_process.mode")
    maximum = _positive_number(service["maximum"], "service_process.maximum")
    if not minimum <= mode <= maximum:
        raise AdapterInputError("service_process requires minimum <= mode <= maximum")
    if value["requested_metrics"] != ["completed_jobs", "average_wait"]:
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
    if value["domain_pack_ref"]["object_id"] != "warehouse-queueing":
        raise AdapterInputError("warehouse adapter only supports warehouse-queueing")
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
    unfinished = outcome.waiting_at_horizon + outcome.in_service_at_horizon
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
            ],
            "source_artifact_refs": [],
        },
        "extensions": {},
        "simulation_run_ref": snapshot["simulation_run_ref"],
        "model_spec_ref": request["model_spec_ref"],
        "experiment_ref": request["experiment_ref"],
        "seed": snapshot["seed"],
        "metrics": [
            {
                "metric_id": "completed_jobs",
                "value": outcome.completed_jobs,
                "unit": "count",
                "dimensions": {},
            },
            {
                "metric_id": "average_wait",
                "value": round(outcome.average_wait, 9),
                "unit": snapshot["time_unit"],
                "dimensions": {},
            },
        ],
        "raw_output_artifact_refs": [],
        "adapter_diagnostics": [
            {
                "code": "warehouse_des_completed",
                "arrivals": outcome.arrivals,
                "service_started": outcome.service_started,
                "completed_jobs": outcome.completed_jobs,
                "waiting_at_horizon": outcome.waiting_at_horizon,
                "in_service_at_horizon": outcome.in_service_at_horizon,
                "unfinished_jobs": unfinished,
                "horizon": snapshot["horizon"],
                "time_unit": snapshot["time_unit"],
                "horizon_boundary": "exclusive",
                "average_wait_population": "jobs_started_before_horizon",
            }
        ],
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
    raw = (json.dumps(_manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write(response_path, raw)


def execute(request_path: Path, response_path: Path, artifact_root: Path) -> None:
    manifest = _manifest()
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

    snapshot = request["input_snapshot"]
    config = WarehouseQueueConfig(
        horizon=float(snapshot["horizon"]),
        mean_interarrival=float(snapshot["arrival_process"]["mean_interarrival"]),
        resource_capacity=snapshot["resource"]["capacity"],
        service_minimum=float(snapshot["service_process"]["minimum"]),
        service_mode=float(snapshot["service_process"]["mode"]),
        service_maximum=float(snapshot["service_process"]["maximum"]),
        seed=snapshot["seed"],
    )
    started_at = datetime.now(timezone.utc)
    started_monotonic = time.monotonic()
    result_set = _result_set(request, WarehouseQueueModel(config).run())
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
                "warehouse-queue@0.1.0"
            ),
            "seed": snapshot["seed"],
            "environment": {
                "runtime": "simpy",
                "simpy_version": simpy.__version__,
                "python_version": platform.python_version(),
                "random_stream_policy": "sha256-derived-arrival-and-service-v0.1",
            },
            "produced_refs": [result_ref],
        },
        "diagnostics": [{
            "code": "warehouse_des_completed",
            "method_family": "discrete_event",
            "runtime": "simpy",
        }],
        "warnings": [],
        "non_claims": [
            "This run checks one declared queue model and does not establish real warehouse validity.",
            "No calibration, sensitivity analysis, comparison, or causal claim was performed.",
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
