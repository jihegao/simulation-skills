from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from simulation_skills_contracts import V01SimulationContractRegistry, digest
from tests.test_v0_1_fake_adapter import request
from tests.test_v0_1_warehouse_des_adapter import request as warehouse_request
from tests.test_v0_1_equipment_maintenance_adapter import (
    request as equipment_maintenance_request,
)


ROOT = Path(__file__).resolve().parents[1]


class CleanInstallTests(unittest.TestCase):
    def test_wheel_exposes_data_and_console_adapter_without_source_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            uv = shutil.which("uv")
            self.assertIsNotNone(uv, "clean install verification requires uv")
            compatible_python = subprocess.run(
                [str(uv), "python", "find", ">=3.10"],
                cwd=root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            wheel_dir = root / "wheel"
            wheel_dir.mkdir()
            subprocess.run(
                [
                    str(uv), "build", "--wheel", "--out-dir", str(wheel_dir), str(ROOT),
                ],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            wheel = next(wheel_dir.glob("simulation_skills-*.whl"))
            environment = root / "clean-venv"
            subprocess.run(
                [str(uv), "venv", "--python", compatible_python, str(environment)],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            python = environment / "bin" / "python"
            subprocess.run(
                [
                    str(uv), "pip", "install", "--python", str(python),
                    "jsonschema[format]>=4.20", "rfc8785==0.1.4", "simpy>=4.0",
                ],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                [str(uv), "pip", "install", "--python", str(python), "--no-deps", str(wheel)],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            clean_env = os.environ.copy()
            clean_env.pop("PYTHONPATH", None)
            clean_env.pop("PYTHONHOME", None)
            clean_env["PATH"] = str(environment / "bin") + os.pathsep + clean_env.get("PATH", "")
            probe = subprocess.run(
                [
                    str(python),
                    "-c",
                    (
                        "import json, pathlib, simulation_skills_contracts as p; "
                        "from simulation_skills_contracts.registry import EXPORT_ROOT, V01SimulationContractRegistry; "
                        "V01SimulationContractRegistry().validate_export(json.loads((EXPORT_ROOT/'export-manifest.json').read_text())); "
                        "import sys; print(pathlib.Path(p.__file__).resolve()); print(EXPORT_ROOT); "
                        "print(pathlib.Path(sys.executable).resolve()); print(sys.version)"
                    ),
                ],
                cwd=root,
                env=clean_env,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
            self.assertNotIn(str(ROOT), probe.stdout)
            manifest_path = root / "described.json"
            subprocess.run(
                ["simulation-skills-fake-adapter", "describe", "--response", str(manifest_path)],
                cwd=root,
                env=clean_env,
                check=True,
            )
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["entrypoint"], ["simulation-skills-fake-adapter"])
            request_value = request()
            request_path, response_path = root / "request.json", root / "response.json"
            request_path.write_text(json.dumps(request_value), encoding="utf-8")
            subprocess.run(
                [
                    "simulation-skills-fake-adapter", "execute", "--request", str(request_path),
                    "--response", str(response_path), "--artifact-root", str(root / "artifacts"),
                ],
                cwd=root,
                env=clean_env,
                check=True,
            )
            response = json.loads(response_path.read_text())
            result_set = json.loads((root / "artifacts" / "result-set.json").read_text())
            V01SimulationContractRegistry().validate_object(result_set)
            self.assertEqual(response["produced_refs"][0]["digest"], digest(result_set))

            real_manifest_path = root / "warehouse-des-manifest.json"
            subprocess.run(
                [
                    "simulation-skills-warehouse-des-adapter", "describe",
                    "--response", str(real_manifest_path),
                ],
                cwd=root,
                env=clean_env,
                check=True,
            )
            real_manifest = json.loads(real_manifest_path.read_text())
            self.assertEqual(
                real_manifest["entrypoint"],
                ["simulation-skills-warehouse-des-adapter"],
            )
            real_request = warehouse_request()
            real_request_path = root / "warehouse-request.json"
            real_response_path = root / "warehouse-response.json"
            real_request_path.write_text(json.dumps(real_request), encoding="utf-8")
            subprocess.run(
                [
                    "simulation-skills-warehouse-des-adapter", "execute",
                    "--request", str(real_request_path),
                    "--response", str(real_response_path),
                    "--artifact-root", str(root / "warehouse-artifacts"),
                ],
                cwd=root,
                env=clean_env,
                check=True,
            )
            real_response = json.loads(real_response_path.read_text())
            real_result = json.loads(
                (root / "warehouse-artifacts" / "result-set.json").read_text()
            )
            V01SimulationContractRegistry().validate_object(real_result)
            self.assertEqual(
                real_response["produced_refs"][0]["digest"], digest(real_result)
            )
            self.assertIn("simpy@", real_response["execution_manifest"]["runtime_identity"])

            maintenance_manifest_path = root / "equipment-maintenance-manifest.json"
            subprocess.run(
                [
                    "simulation-skills-equipment-maintenance-adapter", "describe",
                    "--response", str(maintenance_manifest_path),
                ],
                cwd=root,
                env=clean_env,
                check=True,
            )
            maintenance_manifest = json.loads(maintenance_manifest_path.read_text())
            self.assertEqual(
                maintenance_manifest["entrypoint"],
                ["simulation-skills-equipment-maintenance-adapter"],
            )
            maintenance_request = equipment_maintenance_request()
            maintenance_request_path = root / "equipment-maintenance-request.json"
            maintenance_response_path = root / "equipment-maintenance-response.json"
            maintenance_request_path.write_text(
                json.dumps(maintenance_request), encoding="utf-8"
            )
            subprocess.run(
                [
                    "simulation-skills-equipment-maintenance-adapter", "execute",
                    "--request", str(maintenance_request_path),
                    "--response", str(maintenance_response_path),
                    "--artifact-root", str(root / "equipment-maintenance-artifacts"),
                ],
                cwd=root,
                env=clean_env,
                check=True,
            )
            maintenance_response = json.loads(maintenance_response_path.read_text())
            maintenance_result = json.loads(
                (
                    root
                    / "equipment-maintenance-artifacts"
                    / "result-set.json"
                ).read_text()
            )
            V01SimulationContractRegistry().validate_object(maintenance_result)
            self.assertEqual(
                maintenance_response["produced_refs"][0]["digest"],
                digest(maintenance_result),
            )
            self.assertEqual(
                maintenance_result["extensions"][
                    "org.openai.simulation.domain_pack_execution"
                ]["payload"],
                maintenance_request["input_snapshot"]["domain_pack_binding"],
            )


if __name__ == "__main__":
    unittest.main()
