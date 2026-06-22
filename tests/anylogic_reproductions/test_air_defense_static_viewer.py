import tempfile
import unittest
from pathlib import Path

from examples.air_defense_mesa.static_viewer import build_replay_payload, write_replay_html


class AirDefenseStaticViewerTest(unittest.TestCase):
    def test_static_viewer_embeds_frames_and_controls(self):
        payload = build_replay_payload(seed=31, steps=8, initial_aircraft=2)

        self.assertEqual(len(payload["frames"]), 9)
        self.assertIn("assets", payload["frames"][0])
        self.assertIn("radars", payload["frames"][0])
        self.assertIn("aircraft", payload["frames"][0])
        self.assertIn("missiles", payload["frames"][0])

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "replay.html"
            write_replay_html(target, payload)
            html = target.read_text()

        self.assertIn("Air Defense Mesa Replay", html)
        self.assertIn("data-layer=\"battlefield\"", html)
        self.assertIn("const REPLAY =", html)


if __name__ == "__main__":
    unittest.main()
