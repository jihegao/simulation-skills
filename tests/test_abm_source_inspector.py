import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path("skills/simulation-model-conversion/scripts/inspect_abm_source.py")


def load_inspector():
    spec = importlib.util.spec_from_file_location("inspect_abm_source", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AbmSourceInspectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inspector = load_inspector()

    def test_netlogo_extracts_breeds_globals_and_widgets(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "wolves.nlogo"
            source.write_text(
                textwrap.dedent(
                    """
                    breed [ wolves wolf ]
                    globals [ grass-count ]
                    turtles-own [ energy ]

                    to setup
                      clear-all
                    end

                    to go
                      ask wolves [ fd 1 ]
                      tick
                    end
                    @#$#@#$#@
                    GRAPHICS-WINDOW
                    @#$#@#$#@
                    SLIDER
                    1
                    2
                    3
                    4
                    initial-wolves
                    """
                ).strip(),
                encoding="utf-8",
            )

            summary = self.inspector.inspect_source(source).to_dict()

        self.assertEqual(summary["source_type"], "netlogo")
        self.assertIn({"name": "wolves", "kind": "breed", "singular": ["wolf"]}, summary["agents"])
        self.assertIn({"name": "grass-count", "scope": "globals"}, summary["parameters"])
        self.assertTrue(any(proc["name"] == "go" for proc in summary["procedures"]))
        self.assertTrue(any(param["name"] == "initial-wolves" for param in summary["parameters"]))

    def test_mesa_extracts_model_agent_parameters_space_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "model.py"
            source.write_text(
                textwrap.dedent(
                    """
                    from mesa import Agent, Model
                    from mesa.space import MultiGrid
                    from mesa.datacollection import DataCollector

                    class Trader(Agent):
                        def step(self):
                            pass

                    class Market(Model):
                        def __init__(self, width=10, height=10):
                            self.grid = MultiGrid(width, height, torus=True)
                            self.datacollector = DataCollector(model_reporters={"wealth": lambda m: 1})

                        def step(self):
                            pass
                    """
                ),
                encoding="utf-8",
            )

            summary = self.inspector.inspect_source(source).to_dict()

        self.assertEqual(summary["source_type"], "mesa")
        self.assertTrue(any(agent["name"] == "Trader" and agent["kind"] == "Mesa Agent" for agent in summary["agents"]))
        self.assertTrue(any(agent["name"] == "Market" and agent["kind"] == "Mesa Model" for agent in summary["agents"]))
        self.assertTrue(any(param["name"] == "width" for param in summary["parameters"]))
        self.assertTrue(any(space["name"] == "MultiGrid" for space in summary["spaces"]))
        self.assertTrue(any(metric["name"] == "wealth" for metric in summary["metrics"]))

    def test_repast_extracts_context_scheduler_parameters_and_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src" / "Wolf.java"
            source.parent.mkdir()
            source.write_text(
                textwrap.dedent(
                    """
                    package demo;

                    import repast.simphony.engine.schedule.ScheduledMethod;
                    import repast.simphony.context.Context;
                    import repast.simphony.dataLoader.ContextBuilder;
                    import repast.simphony.space.grid.Grid;

                    public class Wolf implements ContextBuilder<Object> {
                        Grid<Object> grid;

                        public Context build(Context<Object> context) {
                            Object speed = repast.simphony.engine.environment.RunEnvironment
                                .getInstance().getParameters().getValue("wolf_speed");
                            return context;
                        }

                        @ScheduledMethod(start = 1, interval = 1, priority = 2)
                        public void step() {}
                    }
                    """
                ),
                encoding="utf-8",
            )

            summary = self.inspector.inspect_source(Path(tmp)).to_dict()

        self.assertEqual(summary["source_type"], "repast")
        self.assertTrue(any(agent["kind"] == "Repast ContextBuilder" for agent in summary["agents"]))
        self.assertTrue(any(param["name"] == "wolf_speed" for param in summary["parameters"]))
        self.assertTrue(any(schedule["name"] == "step" for schedule in summary["schedulers"]))
        self.assertTrue(any(space["name"] == "Grid" for space in summary["spaces"]))

    def test_cli_emits_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "tiny.nlogo"
            source.write_text("to go\n tick\nend\n", encoding="utf-8")
            output = subprocess.check_output(
                [sys.executable, str(SCRIPT), str(source), "--format", "json"],
                text=True,
            )

        data = json.loads(output)
        self.assertEqual(data["source_type"], "netlogo")
        self.assertTrue(any(proc["name"] == "go" for proc in data["procedures"]))


if __name__ == "__main__":
    unittest.main()
