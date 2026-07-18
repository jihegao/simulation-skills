from __future__ import annotations

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
ADAPTER_ROOT = (
    ROOT
    / "simulation_skills_contracts"
    / "adapters"
    / "equipment_maintenance"
)
EXTENSION_ID = "org.openai.simulation.domain_pack_execution"


def object_ref(contract: str, object_id: str, value: object) -> dict[str, object]:
    return {
        "contract": contract,
        "schema_version": "0.1.0",
        "object_id": object_id,
        "revision": 1,
        "digest": digest(value),
    }


def request(
    *, seed: int = 17, request_id: str = "request-equipment-maintenance"
) -> dict[str, object]:
    case = json.loads(
        (EXPORT_ROOT / "cases" / "equipment-maintenance" / "case.json").read_text()
    )
    fragment = case["provider_fragment"]
    model = fragment["model_spec"]
    method = fragment["method_payload"]
    domain = fragment["domain_pack"]
    manifest = json.loads((ADAPTER_ROOT / "adapter-manifest.json").read_text())
    model_ref = object_ref("simulation.model_spec", model["object_id"], model)
    experiment_value = {
        "case_id": "equipment-maintenance",
        "seed": seed,
        "asset_count": 12,
        "horizon": 240,
        "requested_metrics": ["availability", "unplanned_downtime"],
    }
    experiment_ref = object_ref(
        "workbench.experiment",
        "experiment-equipment-maintenance",
        experiment_value,
    )
    run_ref = object_ref(
        "workbench.simulation_run",
        "run-equipment-maintenance",
        {"case_id": "equipment-maintenance", "seed": seed},
    )
    return {
        "contract": "simulation.adapter_protocol.request",
        "schema_version": "0.1.0",
        "protocol_version": "0.1.0",
        "request_id": request_id,
        "operation": "experiment.run",
        "deadline": "2099-07-18T00:00:00Z",
        "cancellation_token": f"cancel-{request_id}",
        "project_ref": object_ref(
            "workbench.project",
            "project-equipment-maintenance",
            {"case_id": "equipment-maintenance", "kind": "project"},
        ),
        "scenario_refs": [object_ref(
            "workbench.scenario",
            "scenario-equipment-maintenance",
            {"case_id": "equipment-maintenance", "kind": "scenario"},
        )],
        "model_spec_ref": model_ref,
        "experiment_ref": experiment_ref,
        "input_snapshot": {
            "seed": seed,
            "simulation_run_ref": run_ref,
            "model_spec_digest": model_ref["digest"],
            "method_payload_digest": digest(method),
            "experiment_digest": experiment_ref["digest"],
            "result_created_at": "2026-07-18T00:00:00Z",
            "time_unit": "hour",
            "horizon": 240,
            "domain_pack_binding": {
                "pack_id": "equipment-maintenance",
                "pack_version": "0.1.0",
                "manifest_digest": "sha256:" + "6" * 64,
            },
            "asset_count": 12,
            "failure_process": {
                "distribution": "exponential",
                "mean_time_between_failures": 48,
                "unit": "hour",
            },
            "maintenance_resource": {
                "resource_id": "maintenance-team",
                "capacity": 2,
                "capacity_unit": "count",
            },
            "repair_process": {
                "resource_id": "maintenance-team",
                "distribution": "triangular",
                "minimum": 2,
                "mode": 4,
                "maximum": 8,
                "unit": "hour",
            },
            "requested_metrics": ["availability", "unplanned_downtime"],
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
            "non_claims": [
                "A maintenance run is not behavioral validation or domain certification."
            ],
        },
    }


class EquipmentMaintenanceAdapterTests(unittest.TestCase):
    def invoke(self, request_value: dict[str, object], root: Path):
        request_path = root / "request.json"
        response_path = root / "response.json"
        request_path.write_text(json.dumps(request_value), encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "simulation_skills_contracts.adapters.equipment_maintenance.adapter",
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

    def test_describe_emits_independent_real_adapter_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            response_path = Path(temporary) / "manifest.json"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "simulation_skills_contracts.adapters.equipment_maintenance.adapter",
                    "describe",
                    "--response",
                    str(response_path),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            described = json.loads(response_path.read_text())
            described_bytes = response_path.read_bytes()
        self.assertEqual(
            described["adapter_id"],
            "simulation-skills.simpy.equipment-maintenance",
        )
        self.assertEqual(described["adapter_version"], "0.1.0")
        self.assertEqual(
            described["entrypoint"],
            ["simulation-skills-equipment-maintenance-adapter"],
        )
        self.assertEqual(described["operations"], ["experiment.run"])
        self.assertEqual(described["domain_pack_ids"], ["equipment-maintenance"])
        self.assertEqual(
            described_bytes,
            (
                json.dumps(described, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode(),
        )

    def test_real_simpy_result_replays_and_echoes_exact_pack_binding(self):
        value = request()
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            left_response, left_result, left_bytes = self.invoke(value, Path(left))
            right_response, right_result, right_bytes = self.invoke(value, Path(right))
        self.assertEqual(left_result, right_result)
        self.assertEqual(left_bytes, right_bytes)
        self.assertEqual(left_response["produced_refs"], right_response["produced_refs"])
        V01SimulationContractRegistry().validate_object(left_result)
        self.assertEqual(left_result["claim_state"], "draft_unreviewed")
        self.assertEqual(
            left_result["created_by"]["id"],
            "simulation-skills.simpy.equipment-maintenance",
        )
        envelope = left_result["extensions"][EXTENSION_ID]
        self.assertFalse(envelope["required"])
        self.assertEqual(
            envelope["schema_ref"],
            "urn:workbench:domain-pack-execution@0.1.0",
        )
        self.assertEqual(
            envelope["payload"], value["input_snapshot"]["domain_pack_binding"]
        )
        self.assertEqual(
            left_response["execution_manifest"]["input_digest"],
            digest(value["input_snapshot"]),
        )
        self.assertIn("simpy@", left_response["execution_manifest"]["runtime_identity"])
        self.assertEqual(left_response["produced_refs"][0]["digest"], digest(left_result))
        self.assertEqual(
            left_response["artifacts"][0]["digest"],
            "sha256:" + hashlib.sha256(left_bytes).hexdigest(),
        )
        metrics = {item["metric_id"]: item for item in left_result["metrics"]}
        self.assertGreaterEqual(metrics["availability"]["value"], 0)
        self.assertLessEqual(metrics["availability"]["value"], 1)
        self.assertGreater(metrics["unplanned_downtime"]["value"], 0)
        diagnostics = left_result["adapter_diagnostics"][0]
        self.assertEqual(
            diagnostics["failures"],
            diagnostics["repairs_completed"] + diagnostics["unfinished_failures"],
        )
        self.assertEqual(diagnostics["behavior_validation"], "not_evaluated")
        self.assertEqual(diagnostics["domain_certification"], "not_evaluated")
        self.assertTrue(any("does not establish" in item for item in left_response["non_claims"]))

    def test_different_seed_changes_metrics(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            _, seed_17, _ = self.invoke(request(seed=17), Path(left))
            _, seed_18, _ = self.invoke(request(seed=18), Path(right))
        self.assertNotEqual(seed_17["metrics"], seed_18["metrics"])
        self.assertNotEqual(seed_17["adapter_diagnostics"], seed_18["adapter_diagnostics"])

    def test_tamper_unknown_field_and_pack_drift_fail_without_trusted_output(self):
        variants: list[dict[str, object]] = []
        extra = request()
        extra["input_snapshot"]["unexpected"] = True
        variants.append(extra)
        stale_model = request()
        stale_model["input_snapshot"]["model_spec_digest"] = "sha256:" + "0" * 64
        variants.append(stale_model)
        stale_experiment = request()
        stale_experiment["input_snapshot"]["experiment_digest"] = "sha256:" + "1" * 64
        variants.append(stale_experiment)
        stale_manifest = request()
        stale_manifest["adapter_manifest_ref"]["manifest_digest"] = "sha256:" + "2" * 64
        variants.append(stale_manifest)
        pack_drift = request()
        pack_drift["input_snapshot"]["domain_pack_binding"]["pack_version"] = "0.2.0"
        variants.append(pack_drift)
        bad_pack_id = request()
        bad_pack_id["input_snapshot"]["domain_pack_binding"]["pack_id"] = "warehouse-queueing"
        variants.append(bad_pack_id)
        bad_assets = request()
        bad_assets["input_snapshot"]["asset_count"] = True
        variants.append(bad_assets)
        bad_mtbf = request()
        bad_mtbf["input_snapshot"]["failure_process"]["mean_time_between_failures"] = 0
        variants.append(bad_mtbf)
        bad_resource = request()
        bad_resource["input_snapshot"]["maintenance_resource"]["capacity"] = 0
        variants.append(bad_resource)
        bad_triangle = request()
        bad_triangle["input_snapshot"]["repair_process"]["minimum"] = 9
        variants.append(bad_triangle)
        bad_metrics = request()
        bad_metrics["input_snapshot"]["requested_metrics"] = ["availability"]
        variants.append(bad_metrics)
        promoted = request()
        promoted["claim_boundary"]["claim_state"] = "verified"
        variants.append(promoted)

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
                        "simulation_skills_contracts.adapters.equipment_maintenance.adapter",
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

    def test_output_paths_fail_closed_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact_root = root / "artifacts"
            artifact_root.mkdir()
            sentinel = artifact_root / "sentinel"
            sentinel.write_text("keep", encoding="utf-8")
            request_path = root / "request.json"
            response_path = root / "response.json"
            request_path.write_text(json.dumps(request()), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "simulation_skills_contracts.adapters.equipment_maintenance.adapter",
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
            self.assertEqual(sentinel.read_text(), "keep")
            self.assertFalse(response_path.exists())
            self.assertEqual(list(artifact_root.iterdir()), [sentinel])


if __name__ == "__main__":
    unittest.main()
