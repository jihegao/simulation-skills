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


def object_ref(contract: str, object_id: str, value: object) -> dict[str, object]:
    return {
        "contract": contract, "schema_version": "0.1.0", "object_id": object_id,
        "revision": 1, "digest": digest(value),
    }


def request() -> dict[str, object]:
    case = json.loads((EXPORT_ROOT / "cases" / "equipment-maintenance" / "case.json").read_text())
    model = case["provider_fragment"]["model_spec"]
    domain = case["provider_fragment"]["domain_pack"]
    manifest = json.loads((EXPORT_ROOT / "adapter-manifest.json").read_text())
    return {
        "contract": "simulation.adapter_protocol.request",
        "schema_version": "0.1.0",
        "protocol_version": "0.1.0",
        "request_id": "request-equipment-maintenance",
        "operation": "experiment.run",
        "deadline": "2099-07-14T00:00:00Z",
        "cancellation_token": "cancel-equipment-maintenance",
        "project_ref": object_ref("workbench.project", "project-equipment-maintenance", {"owner": "workbench", "kind": "project"}),
        "scenario_refs": [object_ref("workbench.scenario", "scenario-equipment-maintenance", {"owner": "workbench", "kind": "scenario"})],
        "model_spec_ref": object_ref("simulation.model_spec", model["object_id"], model),
        "experiment_ref": object_ref("workbench.experiment", "experiment-equipment-maintenance", {"owner": "workbench", "kind": "experiment"}),
        "input_snapshot": {
            "seed": 17,
            "simulation_run_ref": object_ref("workbench.simulation_run", "run-equipment-maintenance", {"owner": "workbench", "kind": "simulation_run"}),
        },
        "domain_pack_ref": object_ref("simulation.domain_pack", domain["object_id"], domain),
        "adapter_manifest_ref": {
            "adapter_id": manifest["adapter_id"], "adapter_version": manifest["adapter_version"],
            "protocol_version": "0.1.0", "manifest_digest": digest(manifest),
        },
        "requested_output_contract": "simulation.result_set@0.1",
        "claim_boundary": {"claim_state": "draft_unreviewed", "non_claims": ["Contract fixture is not validity evidence."]},
    }


class FakeAdapterTests(unittest.TestCase):
    def invoke(self, request_value: dict[str, object], root: Path) -> tuple[dict, dict, bytes]:
        request_path = root / "request.json"
        response_path = root / "response.json"
        request_path.write_text(json.dumps(request_value), encoding="utf-8")
        subprocess.run(
            [sys.executable, "-m", "simulation_skills_contracts.fake_adapter", "execute", "--request", str(request_path), "--response", str(response_path), "--artifact-root", str(root / "artifacts")],
            cwd=ROOT,
            check=True,
        )
        response = json.loads(response_path.read_text())
        artifact_bytes = (root / "artifacts" / "result-set.json").read_bytes()
        return response, json.loads(artifact_bytes), artifact_bytes

    def test_describe_and_execute_emit_full_deterministic_result_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            described = root / "manifest.json"
            subprocess.run(
                [sys.executable, "-m", "simulation_skills_contracts.fake_adapter", "describe", "--response", str(described)],
                cwd=ROOT,
                check=True,
            )
            self.assertEqual(described.read_bytes(), (EXPORT_ROOT / "adapter-manifest.json").read_bytes())

        with tempfile.TemporaryDirectory() as left_temp, tempfile.TemporaryDirectory() as right_temp:
            left_root, right_root = Path(left_temp), Path(right_temp)
            left_response, left_result, left_bytes = self.invoke(request(), left_root)
            right_response, right_result, right_bytes = self.invoke(request(), right_root)
            self.assertEqual(left_result, right_result)
            self.assertEqual(left_bytes, right_bytes)
            V01SimulationContractRegistry().validate_object(left_result)
            self.assertEqual(left_response["produced_refs"][0]["digest"], digest(left_result))
            self.assertEqual(left_response["execution_manifest"]["produced_refs"], left_response["produced_refs"])
            self.assertEqual(left_response["artifacts"][0]["semantic_role"], "result_set")
            self.assertEqual(left_response["artifacts"][0]["digest"], "sha256:" + hashlib.sha256(left_bytes).hexdigest())
            self.assertEqual(left_result["simulation_run_ref"], request()["input_snapshot"]["simulation_run_ref"])
            self.assertEqual(left_result["claim_state"], "draft_unreviewed")
            self.assertNotEqual(left_result["contract"], "workbench.simulation_run")

    def test_missing_run_ref_and_claim_promotion_fail_without_output(self):
        values = []
        missing_run = request()
        del missing_run["input_snapshot"]["simulation_run_ref"]
        values.append(missing_run)
        promoted = request()
        promoted["claim_boundary"]["claim_state"] = "behavior_checked"
        values.append(promoted)
        for value in values:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                request_path, response_path = root / "request.json", root / "response.json"
                request_path.write_text(json.dumps(value))
                completed = subprocess.run(
                    [sys.executable, "-m", "simulation_skills_contracts.fake_adapter", "execute", "--request", str(request_path), "--response", str(response_path), "--artifact-root", str(root / "artifacts")],
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertFalse(response_path.exists())


if __name__ == "__main__":
    unittest.main()
