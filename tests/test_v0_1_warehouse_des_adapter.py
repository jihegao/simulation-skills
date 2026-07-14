from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from simulation_skills_contracts import V01SimulationContractRegistry, digest


ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT / "simulation_skills_contracts" / "conformance" / "v0_1"
ADAPTER_ROOT = ROOT / "simulation_skills_contracts" / "adapters" / "warehouse_des"


def object_ref(contract: str, object_id: str, value: object) -> dict[str, object]:
    return {
        "contract": contract,
        "schema_version": "0.1.0",
        "object_id": object_id,
        "revision": 1,
        "digest": digest(value),
    }


def request(*, seed: int = 11, request_id: str = "request-warehouse-queueing") -> dict[str, object]:
    case = json.loads(
        (EXPORT_ROOT / "cases" / "warehouse-queueing" / "case.json").read_text()
    )
    fragment = case["provider_fragment"]
    model = fragment["model_spec"]
    method = fragment["method_payload"]
    domain = fragment["domain_pack"]
    manifest = json.loads((ADAPTER_ROOT / "adapter-manifest.json").read_text())
    experiment_value = {
        "case_id": "warehouse-queueing",
        "horizon": method["horizon"],
        "seed": seed,
        "requested_metrics": ["completed_jobs", "average_wait"],
    }
    model_ref = object_ref("simulation.model_spec", model["object_id"], model)
    experiment_ref = object_ref(
        "workbench.experiment", "experiment-warehouse-queueing", experiment_value
    )
    arrival = method["arrival_processes"][0]
    resource = method["resources"][0]
    service = method["process_steps"][0]
    arrival_parameters = {item["parameter_id"]: item for item in arrival["parameters"]}
    service_parameters = {item["parameter_id"]: item for item in service["parameters"]}
    run_ref = object_ref(
        "workbench.simulation_run",
        "run-warehouse-queueing",
        {"case_id": "warehouse-queueing", "seed": seed},
    )
    return {
        "contract": "simulation.adapter_protocol.request",
        "schema_version": "0.1.0",
        "protocol_version": "0.1.0",
        "request_id": request_id,
        "operation": "experiment.run",
        "deadline": "2099-07-14T00:00:00Z",
        "cancellation_token": f"cancel-{request_id}",
        "project_ref": object_ref(
            "workbench.project",
            "project-warehouse-queueing",
            {"case_id": "warehouse-queueing", "kind": "project"},
        ),
        "scenario_refs": [object_ref(
            "workbench.scenario",
            "scenario-warehouse-queueing",
            {"case_id": "warehouse-queueing", "kind": "scenario"},
        )],
        "model_spec_ref": model_ref,
        "experiment_ref": experiment_ref,
        "input_snapshot": {
            "seed": seed,
            "simulation_run_ref": run_ref,
            "model_spec_digest": model_ref["digest"],
            "method_payload_digest": digest(method),
            "experiment_digest": experiment_ref["digest"],
            "result_created_at": "2026-07-14T00:00:00Z",
            "time_unit": method["time_unit"],
            "horizon": method["horizon"],
            "arrival_process": {
                "distribution": arrival["distribution"],
                "mean_interarrival": arrival_parameters["mean_interarrival"]["value"],
                "unit": arrival_parameters["mean_interarrival"]["unit"],
            },
            "resource": {
                "resource_id": resource["resource_id"],
                "capacity": resource["capacity"],
                "capacity_unit": resource["capacity_unit"],
            },
            "service_process": {
                "resource_id": service["resource_id"],
                "distribution": service["service_distribution"],
                "minimum": service_parameters["minimum"]["value"],
                "mode": service_parameters["mode"]["value"],
                "maximum": service_parameters["maximum"]["value"],
                "unit": service_parameters["minimum"]["unit"],
            },
            "requested_metrics": ["completed_jobs", "average_wait"],
        },
        "domain_pack_ref": object_ref(
            "simulation.domain_pack", domain["object_id"], domain
        ),
        "adapter_manifest_ref": {
            "adapter_id": manifest["adapter_id"],
            "adapter_version": manifest["adapter_version"],
            "protocol_version": "0.1.0",
            "manifest_digest": digest(manifest),
        },
        "requested_output_contract": "simulation.result_set@0.1",
        "claim_boundary": {
            "claim_state": "draft_unreviewed",
            "non_claims": ["A queue run is not real warehouse validity evidence."],
        },
    }


class WarehouseDesAdapterTests(unittest.TestCase):
    def invoke(self, request_value: dict[str, object], root: Path):
        request_path = root / "request.json"
        response_path = root / "response.json"
        request_path.write_text(json.dumps(request_value), encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "simulation_skills_contracts.adapters.warehouse_des.adapter",
                "execute",
                "--request",
                str(request_path),
                "--response",
                str(response_path),
                "--artifact-root",
                str(root / "artifacts"),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        response = json.loads(response_path.read_text())
        artifact = (root / "artifacts" / "result-set.json").read_bytes()
        return response, json.loads(artifact), artifact

    def test_manifest_is_independent_from_frozen_fake_export(self):
        manifest = json.loads((ADAPTER_ROOT / "adapter-manifest.json").read_text())
        self.assertEqual(manifest["adapter_id"], "simulation-skills.simpy.warehouse-des")
        self.assertEqual(manifest["adapter_version"], "0.1.0")
        self.assertEqual(
            manifest["entrypoint"], ["simulation-skills-warehouse-des-adapter"]
        )
        self.assertEqual(manifest["domain_pack_ids"], ["warehouse-queueing"])
        fake = json.loads((EXPORT_ROOT / "adapter-manifest.json").read_text())
        self.assertEqual(fake["adapter_id"], "simulation-skills.fake-conformance")
        export = json.loads((EXPORT_ROOT / "export-manifest.json").read_text())
        self.assertEqual(export["adapter"], {"manifest_document": "adapter-manifest.json"})
        self.assertNotIn(
            "adapters/warehouse_des/adapter-manifest.json",
            {item["relative_path"] for item in export["documents"]},
        )

    def test_real_simpy_result_set_replays_deterministically(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            left_response, left_result, left_bytes = self.invoke(request(), Path(left))
            right_response, right_result, right_bytes = self.invoke(request(), Path(right))
        self.assertEqual(left_result, right_result)
        self.assertEqual(left_bytes, right_bytes)
        self.assertEqual(left_response["produced_refs"], right_response["produced_refs"])
        V01SimulationContractRegistry().validate_object(left_result)
        self.assertEqual(left_result["claim_state"], "draft_unreviewed")
        self.assertEqual(left_result["created_by"]["id"], "simulation-skills.simpy.warehouse-des")
        self.assertNotIn("fixture_only", json.dumps(left_result))
        self.assertIn("simpy@", left_response["execution_manifest"]["runtime_identity"])
        self.assertEqual(left_response["execution_manifest"]["seed"], 11)
        self.assertEqual(left_response["execution_manifest"]["input_digest"], digest(request()["input_snapshot"]))
        self.assertEqual(left_response["produced_refs"][0]["digest"], digest(left_result))
        self.assertEqual(
            left_response["artifacts"][0]["digest"],
            "sha256:" + hashlib.sha256(left_bytes).hexdigest(),
        )
        diagnostics = left_result["adapter_diagnostics"][0]
        self.assertEqual(
            diagnostics["arrivals"],
            diagnostics["completed_jobs"] + diagnostics["unfinished_jobs"],
        )
        self.assertLessEqual(diagnostics["completed_jobs"], diagnostics["service_started"])
        self.assertLessEqual(diagnostics["service_started"], diagnostics["arrivals"])

    def test_different_seed_changes_simulation_metrics(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            _, seed_11, _ = self.invoke(request(seed=11), Path(left))
            _, seed_12, _ = self.invoke(request(seed=12), Path(right))
        self.assertNotEqual(seed_11["metrics"], seed_12["metrics"])
        self.assertNotEqual(seed_11["adapter_diagnostics"], seed_12["adapter_diagnostics"])

    def test_invalid_closed_snapshots_fail_without_response_or_artifact(self):
        variants: list[dict[str, object]] = []
        extra = request()
        extra["input_snapshot"]["unexpected"] = True
        variants.append(extra)
        stale_model = request()
        stale_model["input_snapshot"]["model_spec_digest"] = "sha256:" + "0" * 64
        variants.append(stale_model)
        bad_unit = request()
        bad_unit["input_snapshot"]["arrival_process"]["unit"] = "minute"
        variants.append(bad_unit)
        bad_capacity = request()
        bad_capacity["input_snapshot"]["resource"]["capacity"] = True
        variants.append(bad_capacity)
        bad_triangle = request()
        bad_triangle["input_snapshot"]["service_process"]["minimum"] = 3
        variants.append(bad_triangle)
        bad_metrics = request()
        bad_metrics["input_snapshot"]["requested_metrics"] = ["average_wait"]
        variants.append(bad_metrics)

        for index, value in enumerate(variants):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                request_path = root / "request.json"
                response_path = root / "response.json"
                artifact_root = root / "artifacts"
                request_path.write_text(json.dumps(value), encoding="utf-8")
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "simulation_skills_contracts.adapters.warehouse_des.adapter",
                        "execute",
                        "--request",
                        str(request_path),
                        "--response",
                        str(response_path),
                        "--artifact-root",
                        str(artifact_root),
                    ],
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertFalse(response_path.exists())
                self.assertFalse(artifact_root.exists())


if __name__ == "__main__":
    unittest.main()
