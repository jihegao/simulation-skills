import tempfile
import unittest
from pathlib import Path

from examples.field_service_mesa.static_viewer import build_replay_payload, write_replay_html


class FieldServiceStaticViewerTest(unittest.TestCase):
    def test_static_viewer_embeds_animation_metrics_and_log_output(self):
        payload = build_replay_payload(seed=31, steps=10, equipment_count=8, service_capacity=2)

        self.assertEqual(len(payload["frames"]), 11)
        frame = payload["frames"][0]
        self.assertIn("equipment", frame)
        self.assertIn("crews", frame)
        self.assertIn("metrics", frame)
        self.assertIn("events", frame)

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "field-service.html"
            write_replay_html(target, payload)
            html = target.read_text()

        self.assertIn("Field Service Mesa Replay", html)
        self.assertIn("data-layer=\"situation-animation\"", html)
        self.assertIn("data-chart=\"profit\"", html)
        self.assertIn("data-chart=\"queues\"", html)
        self.assertIn("data-panel=\"event-log\"", html)
        self.assertIn("const REPLAY =", html)


if __name__ == "__main__":
    unittest.main()
