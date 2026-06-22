import json
import tempfile
import unittest
from pathlib import Path

from examples.field_service_mesa.run_experiment import run_experiment


class FieldServiceExperimentTest(unittest.TestCase):
    def test_run_experiment_writes_summary_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = {
                "steps": 18,
                "seeds": [1, 2],
                "parameters": {
                    "equipment_count": 12,
                    "service_capacity": [1, 3],
                    "replace_old_equipment": [False, True],
                    "normal_failure_rate": 0.02,
                },
            }

            summary = run_experiment(config, output_dir)

            self.assertEqual(summary["run_count"], 8)
            self.assertEqual(summary["sweep_parameters"], ["replace_old_equipment", "service_capacity"])
            self.assertTrue((output_dir / "run_rows.csv").exists())
            self.assertTrue((output_dir / "summary.json").exists())

            saved_summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(saved_summary["run_count"], 8)
            first_key = sorted(saved_summary["aggregate_metrics"])[0]
            self.assertIn("profit_mean", saved_summary["aggregate_metrics"][first_key])
            self.assertIn("service_queue_mean", saved_summary["aggregate_metrics"][first_key])


if __name__ == "__main__":
    unittest.main()
