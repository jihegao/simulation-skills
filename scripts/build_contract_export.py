#!/usr/bin/env python3
"""Build the byte-stable Simulation Skills Version 0.1 contract export."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation_skills_contracts.canonical_json import digest
from simulation_skills_contracts.result_factory import build_result_set, result_template


EXPORT_ROOT = ROOT / "simulation_skills_contracts" / "conformance" / "v0_1"
FIXED_TIME = "2026-07-14T00:00:00Z"
FAILURE_CODES = [
    "protocol_incompatible", "input_contract_failed", "adapter_failed",
    "output_contract_failed", "artifact_contract_failed", "timeout", "cancelled",
]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _bytes_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(contract: str, object_id: str, object_digest: str) -> dict[str, Any]:
    return {
        "contract": contract, "schema_version": "0.1.0", "object_id": object_id,
        "revision": 1, "digest": object_digest,
    }


def _envelope(contract: str, object_id: str) -> dict[str, Any]:
    return {
        "contract": contract,
        "schema_version": "0.1.0",
        "object_id": object_id,
        "revision": 1,
        "parent_revision": None,
        "created_at": FIXED_TIME,
        "created_by": {"kind": "adapter", "id": "simulation-skills.contract-builder"},
        "provenance": {"parent_refs": [], "source_artifact_refs": []},
        "extensions": {},
    }


def _des_payload(case_id: str, mechanism: str) -> dict[str, Any]:
    value = _envelope("simulation.des_method_payload", f"des-{case_id}")
    resource_id = "picker" if case_id == "warehouse-queueing" else "maintenance-team"
    value.update(
        {
            "time_unit": "hour",
            "horizon": 72,
            "entity_types": [{"entity_type_id": f"{case_id}-job"}],
            "arrival_processes": [{
                "arrival_id": f"{case_id}-arrivals",
                "entity_type_id": f"{case_id}-job",
                "distribution": "exponential",
                "parameters": [{"parameter_id": "mean_interarrival", "value": 2, "unit": "hour"}],
            }],
            "resources": [{"resource_id": resource_id, "capacity": 2, "capacity_unit": "count"}],
            "process_steps": [{
                "step_id": f"{mechanism}-service",
                "resource_id": resource_id,
                "service_distribution": "triangular",
                "parameters": [
                    {"parameter_id": "minimum", "value": 0.5, "unit": "hour"},
                    {"parameter_id": "mode", "value": 1, "unit": "hour"},
                    {"parameter_id": "maximum", "value": 2, "unit": "hour"},
                ],
            }],
            "routing": [],
            "output_metrics": _metric_definitions(),
        }
    )
    return value


def _abm_payload() -> dict[str, Any]:
    value = _envelope("simulation.abm_method_payload", "abm-traffic-intersection")
    value.update(
        {
            "time_unit": "second",
            "step_size": 1,
            "horizon_steps": 3600,
            "agent_types": [{"agent_type_id": "vehicle", "state_fields": ["edge_id", "speed", "wait_steps"]}],
            "network": {"node_count": 4, "edge_count": 8, "directed": True},
            "update_order": "random_sequential",
            "output_metrics": [
                {"metric_id": "throughput", "description": "Vehicles exiting during the horizon.", "unit": "count"},
                {"metric_id": "average_wait_steps", "description": "Mean vehicle wait in model steps.", "unit": "step"},
            ],
        }
    )
    return value


def _metric_definitions() -> list[dict[str, Any]]:
    return [
        {"metric_id": "completed_jobs", "description": "Completed jobs in the fixed horizon.", "unit": "count"},
        {"metric_id": "average_wait", "description": "Mean pre-service wait.", "unit": "hour"},
    ]


def _domain_pack(case_id: str, method_contract: str) -> dict[str, Any]:
    value = _envelope("simulation.domain_pack", case_id)
    traffic = case_id == "traffic-intersection"
    metrics = (
        [
            {"metric_id": "throughput", "description": "Vehicles exiting during the horizon.", "unit": "count"},
            {"metric_id": "average_wait_steps", "description": "Mean vehicle wait in model steps.", "unit": "step"},
        ]
        if traffic else _metric_definitions()
    )
    value.update(
        {
            "pack_id": case_id,
            "pack_version": "0.1.0",
            "compatible_modeling_ir": ["simulation.model_spec@0.1"],
            "method_payload_contracts": [f"{method_contract}@0.1"],
            "scenario_templates": [{"template_id": f"{case_id}-baseline", "schema_ref": f"urn:simulation-skills:{case_id}:scenario@0.1"}],
            "default_experiment_templates": [f"{case_id}-experiment"],
            "metric_definitions": metrics,
            "visualization_hints": ["metric_table"],
            "adapter_requirements": {
                "operations": ["experiment.run"],
                "method_families": ["agent_based" if traffic else "discrete_event"],
                "seed_control": "required",
            },
            "validation_fixture_refs": [f"cases/{case_id}/case.json"],
        }
    )
    return value


def _model_spec(case_id: str, method_payload: dict[str, Any]) -> dict[str, Any]:
    traffic = case_id == "traffic-intersection"
    metrics = (
        [
            {"metric_id": "throughput", "description": "Vehicles exiting during the horizon.", "unit": "count"},
            {"metric_id": "average_wait_steps", "description": "Mean vehicle wait in model steps.", "unit": "step"},
        ]
        if traffic else _metric_definitions()
    )
    value = _envelope("simulation.model_spec", f"model-{case_id}")
    value.update(
        {
            "system_boundary": {
                "included": ["vehicles", "signal_phases", "road_network"] if traffic else ["arrivals", "service_resources", "queueing"],
                "excluded": ["expert validity judgment", "network calibration" if traffic else "economic optimization"],
            },
            "time_semantics": {
                "mode": "discrete_step" if traffic else "discrete_event",
                "base_unit": "second" if traffic else "hour",
                "start": 0,
                "end": 3600 if traffic else 72,
            },
            "parameters": (
                [{"parameter_id": "signal_cycle", "value": 60, "unit": "second"}]
                if traffic else [
                    {"parameter_id": "lead_time", "value": 48, "unit": "hour"},
                    {"parameter_id": "resource_capacity", "value": 2, "unit": "count"},
                ]
            ),
            "metrics": metrics,
            "method_payload_ref": _ref(method_payload["contract"], method_payload["object_id"], digest(method_payload)),
            "domain_extensions": [],
            "assumptions": ["This fixture checks contracts only; it does not establish behavioral validity."],
            "implementation_artifact_ref": None,
        }
    )
    return value


def _logical_connection(role: str, contract: str, case_id: str) -> dict[str, Any]:
    suffix = "run" if role == "simulation_run" else role
    return {
        "role": role, "contract": contract, "schema_version": "0.1.0",
        "object_id": f"{suffix}-{case_id}", "revision": 1,
    }


def _case(case_id: str, role: str, mechanism: str, seed: int) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    method_payload = _abm_payload() if mechanism == "agent_based_network" else _des_payload(case_id, mechanism)
    domain_pack = _domain_pack(case_id, method_payload["contract"])
    model_spec = _model_spec(case_id, method_payload)
    case = {
        "contract": "simulation.conformance_case",
        "schema_version": "0.1.0",
        "case_id": case_id,
        "role": role,
        "mechanism": mechanism,
        "provider_fragment": {
            "domain_pack": domain_pack,
            "domain_pack_descriptor": {
                "pack_id": case_id,
                "pack_version": "0.1.0",
                "template_id": f"{case_id}-baseline",
                "manifest_digest": digest(domain_pack),
            },
            "model_spec": model_spec,
            "method_payload": method_payload,
            "required_connections": [
                _logical_connection("project", "workbench.project", case_id),
                _logical_connection("scenario", "workbench.scenario", case_id),
                _logical_connection("experiment", "workbench.experiment", case_id),
                _logical_connection("simulation_run", "workbench.simulation_run", case_id),
            ],
            "expected_result_template": result_template(seed, traffic=mechanism == "agent_based_network"),
        },
        "request_template": {"operation": "experiment.run", "seed": seed, "requested_output_contract": "simulation.result_set@0.1"},
        "expected": {"artifact_semantic_role": "result_set", "result_set_contract": "simulation.result_set@0.1", "top_level_failure_codes": FAILURE_CODES},
    }
    return case, {"domain-pack": domain_pack, "model-spec": model_spec, method_payload["contract"].split(".")[1].replace("_", "-"): method_payload}


def _adapter_manifest() -> dict[str, Any]:
    return {
        "contract": "simulation.adapter_protocol.manifest", "schema_version": "0.1.0",
        "adapter_id": "simulation-skills.fake-conformance", "adapter_version": "0.1.0",
        "protocol_versions": ["0.1.0"], "operations": ["experiment.run"],
        "input_contracts": ["simulation.model_spec@0.1", "workbench.experiment@0.1"],
        "output_contracts": ["simulation.result_set@0.1"], "method_families": ["discrete_event"],
        "domain_pack_ids": ["equipment-maintenance"], "seed_control": "required",
        "entrypoint": ["simulation-skills-fake-adapter"],
    }


def _schema_ref(contract: str) -> str:
    names = {
        "simulation.model_spec": "model-spec.schema.json", "simulation.result_set": "result-set.schema.json",
        "simulation.domain_pack": "domain-pack.schema.json", "simulation.des_method_payload": "des-method-payload.schema.json",
        "simulation.abm_method_payload": "abm-method-payload.schema.json", "simulation.conformance_case": "conformance-case.schema.json",
    }
    return f"schemas/{names[contract]}"


def _invalid_fixtures(model: dict[str, Any], case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    values["missing-units"] = deepcopy(model)
    del values["missing-units"]["parameters"][0]["unit"]
    values["missing-provenance"] = deepcopy(model)
    del values["missing-provenance"]["provenance"]
    values["wrong-revision"] = deepcopy(model)
    values["wrong-revision"].update({"revision": 2, "parent_revision": None})
    values["unknown-major"] = deepcopy(model)
    values["unknown-major"]["schema_version"] = "1.0.0"
    values["unknown-required-extension"] = deepcopy(model)
    values["unknown-required-extension"]["extensions"]["org.example.unknown"] = {
        "required": True, "schema_ref": "urn:example:unknown@1", "payload": {},
    }
    values["wrong-digest"] = deepcopy(case)
    values["wrong-digest"]["provider_fragment"]["domain_pack_descriptor"]["manifest_digest"] = "sha256:" + "0" * 64
    values["stale-digest"] = deepcopy(case)
    values["stale-digest"]["provider_fragment"]["domain_pack"]["visualization_hints"].append("queue_chart")
    return values


def _document(relative_path: str, *, kind: str, contract_id: str, schema_ref: str | None = None, validity: str | None = None, case_id: str | None = None, validation_layer: str | None = None, expected_failure_code: str | None = None) -> dict[str, Any]:
    return {
        "relative_path": relative_path, "owner": "simulation-skills", "contract_id": contract_id,
        "schema_version": "0.1.0", "kind": kind, "digest": _bytes_digest(EXPORT_ROOT / relative_path),
        "schema_ref": schema_ref, "validity": validity, "case_id": case_id,
        "validation_layer": validation_layer,
        "expected_failure_code": expected_failure_code,
    }


def build() -> None:
    cases: dict[str, dict[str, Any]] = {}
    equipment: dict[str, dict[str, Any]] = {}
    for case_id, role, mechanism, seed in (
        ("warehouse-queueing", "workflow_continuity", "queueing", 11),
        ("equipment-maintenance", "domain_mvp", "maintenance_repair", 17),
        ("traffic-intersection", "cross_domain_check", "agent_based_network", 23),
    ):
        case, objects = _case(case_id, role, mechanism, seed)
        cases[case_id] = case
        _write_json(EXPORT_ROOT / "cases" / case_id / "case.json", case)
        if case_id == "equipment-maintenance":
            equipment = objects
    for label, value in equipment.items():
        _write_json(EXPORT_ROOT / "fixtures" / "valid" / f"{label}.json", value)
    model_ref = _ref("simulation.model_spec", equipment["model-spec"]["object_id"], digest(equipment["model-spec"]))
    syntax_experiment_ref = _ref("workbench.experiment", "experiment-syntax-example", digest({"fixture": "experiment-syntax-example"}))
    syntax_run_ref = _ref("workbench.simulation_run", "run-syntax-example", digest({"fixture": "run-syntax-example"}))
    result_fixture = build_result_set("syntax-example", model_ref, syntax_experiment_ref, syntax_run_ref, result_template(17))
    _write_json(EXPORT_ROOT / "fixtures" / "valid" / "result-set.json", result_fixture)
    for label, value in _invalid_fixtures(equipment["model-spec"], cases["equipment-maintenance"]).items():
        _write_json(EXPORT_ROOT / "fixtures" / "invalid" / f"{label}.json", value)
    _write_json(EXPORT_ROOT / "adapter-manifest.json", _adapter_manifest())

    documents: list[dict[str, Any]] = []
    for path in sorted((EXPORT_ROOT / "schemas").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        documents.append(_document(path.relative_to(EXPORT_ROOT).as_posix(), kind="schema", contract_id=schema["x-contract-id"]))
    for validity in ("valid", "invalid"):
        for path in sorted((EXPORT_ROOT / "fixtures" / validity).glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            invalid_expectations = {
                "missing-units": ("schema", "schema_contract_failed"),
                "missing-provenance": ("schema", "schema_contract_failed"),
                "unknown-major": ("schema", "schema_contract_failed"),
                "wrong-revision": ("schema", "schema_contract_failed"),
                "unknown-required-extension": ("semantic", "unknown_required_extension"),
                "wrong-digest": ("semantic", "domain_pack_manifest_digest_mismatch"),
                "stale-digest": ("semantic", "domain_pack_manifest_digest_mismatch"),
            }
            layer, code = invalid_expectations[path.stem] if validity == "invalid" else (None, None)
            documents.append(_document(path.relative_to(EXPORT_ROOT).as_posix(), kind="fixture", contract_id=value["contract"], schema_ref=_schema_ref(value["contract"]), validity=validity, validation_layer=layer, expected_failure_code=code))
    for case_id in sorted(cases):
        relative_path = f"cases/{case_id}/case.json"
        documents.append(_document(relative_path, kind="case", contract_id="simulation.conformance_case", schema_ref="schemas/conformance-case.schema.json", validity="valid", case_id=case_id))
    documents.append(_document("adapter-manifest.json", kind="adapter_manifest", contract_id="simulation.adapter_protocol.manifest", schema_ref="https://simulation-copilot-workbench.local/schemas/v0.1/adapter-manifest.schema.json", validity="valid"))
    documents.sort(key=lambda item: item["relative_path"])
    export = {
        "contract": "simulation.conformance_export", "schema_version": "0.1.0", "export_version": "0.1.0", "protocol_version": "0.1.0",
        "provider": {"repository": "simulation-skills", "contract_version": "0.1.0", "source_tree_digest": digest(documents)},
        "documents": documents, "adapter": {"manifest_document": "adapter-manifest.json"},
    }
    _write_json(EXPORT_ROOT / "export-manifest.json", export)


if __name__ == "__main__":
    build()
