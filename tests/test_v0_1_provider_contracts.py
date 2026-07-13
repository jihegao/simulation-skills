from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from simulation_skills_contracts import ContractValidationError, V01SimulationContractRegistry, digest


ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT / "simulation_skills_contracts" / "conformance" / "v0_1"


class V01ProviderContractTests(unittest.TestCase):
    def setUp(self):
        self.registry = V01SimulationContractRegistry()

    def test_valid_provider_objects_and_cases_validate(self):
        contracts = set()
        for path in sorted((EXPORT_ROOT / "fixtures" / "valid").glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            contracts.add(self.registry.validate_object(value)["contract"])
        self.assertEqual(
            contracts,
            {
                "simulation.model_spec",
                "simulation.result_set",
                "simulation.domain_pack",
                "simulation.des_method_payload",
            },
        )
        cases = {
            path.parent.name: self.registry.validate_case(
                json.loads(path.read_text(encoding="utf-8"))
            )
            for path in sorted((EXPORT_ROOT / "cases").glob("*/case.json"))
        }
        self.assertEqual(
            {value["role"] for value in cases.values()},
            {"workflow_continuity", "domain_mvp", "cross_domain_check"},
        )
        traffic = cases["traffic-intersection"]
        self.assertEqual(traffic["mechanism"], "agent_based_network")
        self.assertEqual(
            traffic["provider_fragment"]["method_payload"]["contract"],
            "simulation.abm_method_payload",
        )
        self.assertEqual(
            traffic["provider_fragment"]["model_spec"]["time_semantics"]["mode"],
            "discrete_step",
        )

    def test_all_invalid_fixtures_fail_closed(self):
        export = json.loads((EXPORT_ROOT / "export-manifest.json").read_text())
        expected_codes = {
            Path(item["relative_path"]).stem: item["expected_failure_code"]
            for item in export["documents"]
            if item["validity"] == "invalid"
        }
        paths = sorted((EXPORT_ROOT / "fixtures" / "invalid").glob("*.json"))
        self.assertEqual(
            {path.stem for path in paths},
            {
                "missing-units", "missing-provenance", "wrong-revision",
                "unknown-major", "unknown-required-extension", "wrong-digest",
                "stale-digest",
            },
        )
        for path in paths:
            value = json.loads(path.read_text(encoding="utf-8"))
            validator = (
                self.registry.validate_case
                if value.get("contract") == "simulation.conformance_case"
                else self.registry.validate_object
            )
            with self.subTest(path=path.name), self.assertRaises(ContractValidationError) as caught:
                validator(value)
            self.assertEqual(caught.exception.code, expected_codes[path.stem])

    def test_case_semantics_reject_method_time_and_domain_mismatch(self):
        value = json.loads(
            (EXPORT_ROOT / "cases" / "traffic-intersection" / "case.json").read_text()
        )
        variants = []
        wrong_time = deepcopy(value)
        wrong_time["provider_fragment"]["model_spec"]["time_semantics"]["mode"] = "discrete_event"
        variants.append(wrong_time)
        wrong_contract = deepcopy(value)
        wrong_contract["provider_fragment"]["domain_pack"]["method_payload_contracts"] = ["simulation.des_method_payload@0.1"]
        variants.append(wrong_contract)
        wrong_family = deepcopy(value)
        wrong_family["provider_fragment"]["domain_pack"]["adapter_requirements"]["method_families"] = ["discrete_event"]
        variants.append(wrong_family)
        duplicate_connection = deepcopy(value)
        duplicate_connection["provider_fragment"]["required_connections"][3] = deepcopy(
            duplicate_connection["provider_fragment"]["required_connections"][0]
        )
        variants.append(duplicate_connection)
        for variant in variants:
            with self.assertRaises(ContractValidationError):
                self.registry.validate_case(variant)

    def test_export_manifest_locks_every_document_and_schema_identity(self):
        export = self.registry.validate_export(
            json.loads((EXPORT_ROOT / "export-manifest.json").read_text())
        )
        self.assertEqual(
            export["provider"]["source_tree_digest"], digest(export["documents"])
        )
        paths = [item["relative_path"] for item in export["documents"]]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(len(paths), len(set(paths)))
        schema_ids = set()
        for item in export["documents"]:
            path = EXPORT_ROOT / item["relative_path"]
            self.assertTrue(path.is_file())
            self.assertEqual(
                item["digest"], "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            )
            if item["kind"] == "schema":
                schema = json.loads(path.read_text())
                self.assertEqual(item["contract_id"], schema["x-contract-id"])
                self.assertEqual(item["schema_version"], schema["x-schema-version"])
                self.assertNotIn(schema["$id"], schema_ids)
                schema_ids.add(schema["$id"])

    def test_export_build_is_byte_identical_and_does_not_publish_workbench_objects(self):
        before = {
            path.relative_to(EXPORT_ROOT): path.read_bytes()
            for path in EXPORT_ROOT.rglob("*.json")
        }
        subprocess.run(
            [str(Path(__import__("sys").executable)), str(ROOT / "scripts" / "build_contract_export.py")],
            cwd=ROOT,
            check=True,
        )
        after = {
            path.relative_to(EXPORT_ROOT): path.read_bytes()
            for path in EXPORT_ROOT.rglob("*.json")
        }
        self.assertEqual(before, after)
        for path in (EXPORT_ROOT / "fixtures" / "valid").glob("*.json"):
            self.assertFalse(json.loads(path.read_text())["contract"].startswith("workbench."))


if __name__ == "__main__":
    unittest.main()
