import unittest
from pathlib import Path


class AgentMethodRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent_doc = Path("agent.md").read_text(encoding="utf-8")
        cls.readme = Path("README.md").read_text(encoding="utf-8")
        cls.routing = Path("skills/sim-adapter/references/method-routing.md").read_text(
            encoding="utf-8"
        )

    def assert_agent_method_contract(self, method_name, expected_terms):
        self.assertIn(method_name, self.agent_doc)
        for term in expected_terms:
            self.assertIn(term, self.agent_doc)

    def test_agent_based_modeling_method_is_registered(self):
        self.assert_agent_method_contract(
            "ABM",
            [
                "`abm-modeling`",
                "个体异质性",
                "局部规则",
                "Mesa/ABM 建模",
            ],
        )
        self.assertTrue(Path("skills/abm-modeling/SKILL.md").exists())

    def test_discrete_event_simulation_method_is_registered(self):
        self.assert_agent_method_contract(
            "DES",
            [
                "`discrete-event-modeling`",
                "到达",
                "排队",
                "SimPy/DES 建模",
            ],
        )
        self.assertTrue(Path("skills/discrete-event-modeling/SKILL.md").exists())

    def test_system_dynamics_method_has_lightweight_route(self):
        self.assert_agent_method_contract(
            "系统动力学",
            [
                "`system-dynamics-modeling`",
                "stock-flow spec",
                "`examples/global_warming_system_dynamics`",
            ],
        )
        self.assertIn("System Dynamics", self.routing)
        self.assertTrue(Path("examples/global_warming_system_dynamics/experiment.json").exists())

    def test_monte_carlo_sensitivity_method_has_lightweight_route(self):
        self.assert_agent_method_contract(
            "Monte Carlo",
            [
                "`monte-carlo-sensitivity`",
                "变量分布表",
                "敏感性排序",
                "参数不确定",
            ],
        )
        self.assertIn("Monte Carlo And Sensitivity Models", self.routing)

    def test_network_simulation_method_has_lightweight_route(self):
        self.assert_agent_method_contract(
            "网络仿真",
            [
                "`network-simulation`",
                "节点/边 schema",
                "级联",
                "graph spec",
            ],
        )
        self.assertIn("Network Simulation", self.routing)

    def test_physics_continuous_simulation_method_has_lightweight_route(self):
        self.assert_agent_method_contract(
            "物理 / 连续仿真",
            [
                "`physics-continuous-simulation`",
                "SciPy ODE",
                "PyBullet",
                "`examples/biped_microgravity`",
            ],
        )
        self.assertIn("Physics Or Continuous Simulation", self.routing)
        self.assertTrue(Path("examples/biped_microgravity/experiment.json").exists())

    def test_physics_route_distinguishes_mujoco_from_structural_continuum_analysis(self):
        self.assertIn("MuJoCo routing boundary", self.routing)
        self.assertIn("articulated rigid-body", self.routing)
        self.assertIn("structural, continuum, material-load", self.routing)
        self.assertIn("structural/FEM solver", self.routing)
        self.assertIn("truss/beam/shell", self.routing)
        self.assertIn("Three.js plus a lightweight", self.routing)
        self.assertIn("structural response, material", self.routing)

    def test_hybrid_simulation_method_has_authority_boundary(self):
        self.assert_agent_method_contract(
            "混合仿真",
            [
                "`hybrid-simulation-patterns`",
                "权威时间",
                "状态",
                "指标",
            ],
        )
        self.assertIn("Hybrid Models", self.routing)
        self.assertTrue(Path("examples/des_mesa_queue/experiment.json").exists())
        self.assertTrue(Path("examples/global_shipping_mesa/experiment.json").exists())

    def test_readme_links_dispatcher_registry(self):
        self.assertIn("agent.md", self.readme)
        self.assertIn("simulation-dispatcher roadmap", self.readme)


if __name__ == "__main__":
    unittest.main()
