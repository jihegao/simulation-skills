import tempfile
import unittest
import json
from pathlib import Path

from examples.global_warming_system_dynamics.app import (
    build_global_warming_html,
    write_global_warming_page,
)
from examples.global_warming_system_dynamics.model import (
    checkpoint_summary,
    run_default_scenarios,
)


class GlobalWarmingSystemDynamicsTest(unittest.TestCase):
    def test_default_predictions_are_bounded_and_ordered(self):
        summary = checkpoint_summary(run_default_scenarios())

        self.assertLess(summary["rapid"][2040]["temperature_c"], summary["baseline"][2040]["temperature_c"])
        self.assertLess(summary["baseline"][2040]["temperature_c"], summary["high"][2040]["temperature_c"])
        self.assertLess(summary["rapid"][2040]["co2_ppm"], summary["baseline"][2040]["co2_ppm"])
        self.assertLess(summary["baseline"][2040]["co2_ppm"], summary["high"][2040]["co2_ppm"])

        self.assertGreaterEqual(summary["baseline"][2030]["temperature_c"], 1.42)
        self.assertLessEqual(summary["baseline"][2030]["temperature_c"], 1.50)
        self.assertGreaterEqual(summary["baseline"][2040]["temperature_c"], 1.60)
        self.assertLessEqual(summary["baseline"][2040]["temperature_c"], 1.78)

    def test_page_contains_model_contract_and_sources(self):
        html = build_global_warming_html()

        self.assertIn('data-model="global-warming-system-dynamics"', html)
        self.assertIn('data-chart="temperature-path"', html)
        self.assertIn('data-chart="co2-stock"', html)
        self.assertIn('data-panel="sd-model-visualization"', html)
        self.assertIn('data-chart="sd-stock-flow"', html)
        self.assertIn('data-panel="sd-equations"', html)
        self.assertIn('data-table="prediction-checkpoints"', html)
        self.assertIn('data-panel="prediction-claims"', html)
        self.assertIn("function simulateScenario", html)
        self.assertIn("function drawSDModel", html)
        self.assertIn("function updateEquationPanel", html)
        self.assertIn("R1: 变暖削弱自然碳汇风险", html)
        self.assertIn("B1: 减排路径降低后续流入", html)
        self.assertIn("NOAA 2025", html)
        self.assertIn("NASA GISTEMP", html)
        self.assertIn("Global Carbon Budget", html)
        self.assertNotIn("<script src=", html)

    def test_write_page_creates_self_contained_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "climate.html"
            write_global_warming_page(target)
            html = target.read_text(encoding="utf-8")

        self.assertIn("<!doctype html>", html)
        self.assertNotIn("__MODEL_DATA__", html)
        self.assertIn("<script id=\"modelData\" type=\"application/json\">", html)

    def test_case_library_entry_is_registered(self):
        case_readme = Path("examples/global_warming_system_dynamics/README.md").read_text(encoding="utf-8")
        case_index = Path("examples/README.md").read_text(encoding="utf-8")
        experiment = json.loads(Path("examples/global_warming_system_dynamics/experiment.json").read_text(encoding="utf-8"))

        self.assertIn("global_warming_system_dynamics", case_index)
        self.assertIn("System dynamics", case_index)
        self.assertIn("Global Warming System Dynamics", case_readme)
        self.assertEqual(experiment["case_id"], "global_warming_system_dynamics")
        self.assertEqual(experiment["method"], "system_dynamics")
        self.assertEqual(experiment["horizon"]["checkpoints"], [2030, 2035, 2040])
        self.assertEqual(experiment["visualization"], "examples/global_warming_system_dynamics/index.html")


if __name__ == "__main__":
    unittest.main()
