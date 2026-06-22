import json
import tempfile
import unittest
from pathlib import Path

from examples.biped_microgravity.model import MatchstickBridge
from examples.biped_microgravity.run_experiment import run_experiment
from examples.biped_microgravity.static_viewer import build_view_payload, write_viewer_html


class MatchstickBridgeTest(unittest.TestCase):
    def test_default_bridge_has_expected_nodes_and_holds_nominal_load(self):
        model = MatchstickBridge(load_n=18.0)
        evaluation = model.evaluate_load()

        self.assertEqual(sum(1 for node in model.nodes.values() if node.support), 4)
        self.assertGreaterEqual(len(model.members), 40)
        self.assertTrue(evaluation.can_hold)
        self.assertEqual(evaluation.failure_modes, [])
        self.assertLess(evaluation.max_member_utilization, 1.0)

    def test_overloaded_bridge_reports_capacity_failure(self):
        evaluation = MatchstickBridge(load_n=80.0).evaluate_load()

        self.assertFalse(evaluation.can_hold)
        self.assertIn("member_capacity_exceeded", evaluation.failure_modes)

    def test_weak_glue_reports_joint_failure(self):
        evaluation = MatchstickBridge(load_n=30.0, glue_joint_capacity_n=4.0).evaluate_load()

        self.assertFalse(evaluation.can_hold)
        self.assertIn("glue_joint_capacity_exceeded", evaluation.failure_modes)

    def test_run_experiment_writes_summary_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_experiment(
                {
                    "load_cases_n": [10.0, 18.0, 80.0],
                    "panel_count_cases": [6],
                },
                output_dir,
            )

            self.assertEqual(summary["case_count"], 3)
            self.assertGreater(summary["fail_count"], 0)
            self.assertTrue((output_dir / "bridge_cases.csv").exists())
            self.assertTrue((output_dir / "summary.json").exists())
            replay = json.loads((output_dir / "replay.json").read_text(encoding="utf-8"))
            self.assertEqual(len(replay["frames"]), 3)

    def test_static_viewer_contains_bridge_markers_and_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "viewer.html"
            write_viewer_html(output, build_view_payload(load_n=18.0))
            html = output.read_text(encoding="utf-8")

            self.assertIn('data-panel="bridge-structure"', html)
            self.assertIn('data-layer="threejs-cannon-bridge"', html)
            self.assertIn("火柴棍桥梁物理仿真", html)
            self.assertIn("holds_load", html)
            self.assertIn('data-action="add-payload"', html)
            self.assertIn('addEventListener("click"', html)
            self.assertIn('from "three"', html)
            self.assertIn('from "cannon-es"', html)
            self.assertIn("OrbitControls", html)
            self.assertIn("new THREE.WebGLRenderer", html)
            self.assertIn("new CANNON.World", html)
            self.assertIn('function jointColor(nodeName)', html)
            self.assertIn("nodeBaseForces", html)
            self.assertIn("requestAnimationFrame(animate)", html)


if __name__ == "__main__":
    unittest.main()
