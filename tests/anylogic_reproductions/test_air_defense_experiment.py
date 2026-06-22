import json
import tempfile
import unittest
from pathlib import Path

from examples.air_defense_mesa.run_experiment import run_experiment


class AirDefenseExperimentTest(unittest.TestCase):
    def test_run_experiment_writes_summary_and_run_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = {
                "steps": 12,
                "seeds": [1, 2],
                "parameters": {
                    "initial_aircraft": 3,
                    "radar_zone": [60, 120],
                    "radar_max_missiles": 2,
                    "missile_speed": 20,
                    "aircraft_speed": 10,
                },
            }

            summary = run_experiment(config, output_dir)

            self.assertEqual(summary["run_count"], 4)
            self.assertEqual(summary["sweep_parameters"], ["radar_zone"])
            self.assertTrue((output_dir / "run_rows.csv").exists())
            self.assertTrue((output_dir / "summary.json").exists())

            saved_summary = json.loads((output_dir / "summary.json").read_text())
            self.assertEqual(saved_summary["run_count"], 4)
            self.assertIn("assets_destroyed_mean", saved_summary["aggregate_metrics"]["radar_zone=60"])
            self.assertIn("aircraft_destroyed_mean", saved_summary["aggregate_metrics"]["radar_zone=120"])


if __name__ == "__main__":
    unittest.main()
