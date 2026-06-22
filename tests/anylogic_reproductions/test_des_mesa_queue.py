import inspect
import json
import tempfile
import unittest
from pathlib import Path

from examples.des_mesa_queue import app
from examples.des_mesa_queue.model import CustomerServiceDesMesaModel
from examples.des_mesa_queue.run_experiment import run_experiment


class DesMesaQueueTest(unittest.TestCase):
    def test_model_advances_simpy_events_through_mesa_step(self):
        model = CustomerServiceDesMesaModel(
            seed=3,
            server_count=2,
            arrival_rate_per_hour=24,
            mean_service_minutes=4,
            patience_minutes=15,
            step_minutes=1,
        )

        for _ in range(90):
            model.step()

        snapshot = model.snapshot()
        self.assertGreater(snapshot["arrivals"], 0)
        self.assertGreater(snapshot["completed"], 0)
        self.assertIn("avg_wait_minutes", snapshot)
        self.assertLessEqual(snapshot["in_service"], 2)

    def test_visualization_contains_des_flow_panels(self):
        model = CustomerServiceDesMesaModel(seed=4, server_count=2)
        for _ in range(20):
            model.step()

        html = app.render_queue_dashboard(model)

        self.assertIn('data-panel="des-flow"', html)
        self.assertIn('data-layer="waiting-queue"', html)
        self.assertIn('data-layer="service-resource"', html)
        self.assertIn('data-panel="event-log"', html)

    def test_page_initializes_model_value_not_lazy_function(self):
        source = inspect.getsource(app.Page)

        self.assertNotIn("use_state(\n        lambda", source)

    def test_run_experiment_writes_summary_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = {
                "steps": 60,
                "seeds": [1, 2],
                "parameters": {
                    "server_count": [1, 2],
                    "arrival_rate_per_hour": 14.0,
                    "mean_service_minutes": 7.0,
                    "patience_minutes": 18.0,
                    "step_minutes": 1.0,
                },
            }

            summary = run_experiment(config, output_dir)

            self.assertEqual(summary["run_count"], 4)
            self.assertEqual(summary["sweep_parameters"], ["server_count"])
            self.assertTrue((output_dir / "run_rows.csv").exists())
            self.assertTrue((output_dir / "summary.json").exists())
            saved_summary = json.loads((output_dir / "summary.json").read_text())
            first_key = sorted(saved_summary["aggregate_metrics"])[0]
            self.assertIn("avg_wait_minutes_mean", saved_summary["aggregate_metrics"][first_key])
            self.assertIn("server_utilization_mean", saved_summary["aggregate_metrics"][first_key])


if __name__ == "__main__":
    unittest.main()
