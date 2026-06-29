import json
import tempfile
import unittest
from pathlib import Path

from examples.bdi_polarization_mesa.model import BDIPolarizationModel
from examples.bdi_polarization_mesa.opencode_sampler import sample_with_opencode
from examples.bdi_polarization_mesa.run_experiment import run_experiment


class BDIPolarizationModelTest(unittest.TestCase):
    def test_model_creates_reproducible_llm_sampled_agents(self):
        model_a = BDIPolarizationModel(population_size=40, llm_agent_fraction=0.1, seed=7)
        model_b = BDIPolarizationModel(population_size=40, llm_agent_fraction=0.1, seed=7)

        self.assertEqual(model_a.snapshot()["llm_sampled_agents"], 4.0)
        self.assertEqual(
            [agent.llm_sample["name"] if agent.llm_sample else None for agent in model_a.bdi_agents],
            [agent.llm_sample["name"] if agent.llm_sample else None for agent in model_b.bdi_agents],
        )

    def test_recommendation_strength_increases_alignment_in_seeded_run(self):
        low = BDIPolarizationModel(
            population_size=70,
            recommendation_strength=0.0,
            group_action_feedback=0.25,
            seed=21,
        )
        high = BDIPolarizationModel(
            population_size=70,
            recommendation_strength=0.9,
            group_action_feedback=0.25,
            seed=21,
        )
        for _ in range(20):
            low.step()
            high.step()

        self.assertGreater(
            high.snapshot()["mean_recommendation_alignment"],
            low.snapshot()["mean_recommendation_alignment"],
        )


class BDIPolarizationExperimentTest(unittest.TestCase):
    def test_run_experiment_writes_summary_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_experiment(
                {
                    "steps": 8,
                    "seeds": [1, 2],
                    "parameters": {
                        "population_size": 32,
                        "recommendation_strength": [0.0, 0.8],
                        "llm_agent_fraction": 0.1,
                    },
                    "llm_sampling": {"mode": "fallback", "sample_count": 3},
                },
                output_dir,
            )

            self.assertEqual(summary["run_count"], 4)
            self.assertEqual(summary["sweep_parameters"], ["recommendation_strength"])
            self.assertTrue((output_dir / "run_rows.csv").exists())
            saved = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertIn("recommendation_strength=0.0", saved["aggregate_metrics"])
            self.assertIn("polarization_index_mean", saved["aggregate_metrics"]["recommendation_strength=0.8"])
            self.assertEqual(saved["llm_sampling"]["source"], "fallback")
            self.assertIn("local opencode CLI", saved["llm_boundary"])

    def test_opencode_sampler_parses_json_response(self):
        class Result:
            returncode = 0
            stdout = '{"samples":[{"name":"moderator","credulity":0.3,"activism":0.2,"novelty_bias":0.1,"moderation_bias":0.5}]}'
            stderr = ""

        samples = sample_with_opencode(
            sample_count=1,
            runner=lambda *args, **kwargs: Result(),
            opencode_path="/usr/bin/opencode",
        )

        self.assertEqual(samples[0]["name"], "moderator")
        self.assertEqual(samples[0]["moderation_bias"], 0.5)


if __name__ == "__main__":
    unittest.main()
