import json
import tempfile
import unittest
from pathlib import Path

from examples.hospital_material_mesa.run_experiment import run_experiment


class HospitalMaterialExperimentTest(unittest.TestCase):
    def test_run_experiment_writes_summary_and_rows(self):
        config = {
            "steps": 12,
            "seeds": [3],
            "parameters": {
                "agv_count": [2, 4],
                "step_seconds": 300,
                "initial_time_seconds": 6 * 60 * 60,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            summary = run_experiment(config, Path(tmp))

            self.assertEqual(summary["model"], "Hospital Material Handling Mesa")
            self.assertEqual(summary["run_count"], 2)
            self.assertIn("agv_count=2", summary["aggregate_metrics"])
            self.assertTrue((Path(tmp) / "run_rows.csv").exists())
            persisted = json.loads((Path(tmp) / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["run_count"], 2)


if __name__ == "__main__":
    unittest.main()
