import json
import tempfile
import unittest
from pathlib import Path

from examples.bdi_polarization_mesa.single_run_viewer import build_replay, write_viewer


class SingleRunViewerTest(unittest.TestCase):
    def test_build_replay_writes_frames_and_agent_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            replay = build_replay(
                {
                    "steps": 5,
                    "seeds": [3],
                    "parameters": {
                        "population_size": 24,
                        "recommendation_strength": 0.8,
                        "llm_agent_fraction": 0.125,
                    },
                    "llm_sampling": {"mode": "fallback", "sample_count": 3},
                },
                tmp,
            )

            self.assertEqual(replay["steps"], 5)
            self.assertEqual(len(replay["frames"]), 6)
            self.assertEqual(len(replay["frames"][0]["agents"]), 24)
            self.assertIn("polarization_index", replay["frames"][-1]["metrics"])
            saved = json.loads((Path(tmp) / "single_run_replay.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["seed"], 3)

    def test_write_viewer_embeds_replay_and_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            replay = {
                "model": "BDI Recommendation Polarization",
                "question": "test",
                "seed": 1,
                "steps": 0,
                "parameters": {"population_size": 1},
                "llm_sampling": {"source": "fallback"},
                "llm_behavior_samples": [],
                "frames": [
                    {
                        "tick": 0,
                        "metrics": {
                            "polarization_index": 0,
                            "extreme_share": 0,
                            "action_rate": 0,
                            "mean_recommendation_alignment": 0,
                            "group_actions": 0,
                            "content_pool_size": 1,
                        },
                        "intentions": {"idle": 1, "support": 0, "share": 0, "mobilize": 0},
                        "agents": [
                            {
                                "id": 1,
                                "belief": 0.1,
                                "intention": "idle",
                                "isLlm": False,
                                "sample": "rule_based",
                                "alignment": 0,
                            }
                        ],
                    }
                ],
                "evidence_boundary": "test boundary",
            }
            target = write_viewer(replay, Path(tmp) / "single_run_viewer.html")
            html = target.read_text(encoding="utf-8")

            self.assertIn("BDI single run replay", html)
            self.assertIn("const replay =", html)
            self.assertIn("id=\"play\"", html)


if __name__ == "__main__":
    unittest.main()
