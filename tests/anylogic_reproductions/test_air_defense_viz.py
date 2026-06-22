import unittest
import inspect

from examples.air_defense_mesa import app
from examples.air_defense_mesa.model import AirDefenseModel


class AirDefenseVizTest(unittest.TestCase):
    def test_battlefield_svg_contains_core_layers(self):
        model = AirDefenseModel(seed=23, initial_aircraft=2)

        svg = app.render_battlefield_svg(model)

        self.assertIn("<svg", svg)
        self.assertIn('data-layer="radar-zone"', svg)
        self.assertIn('data-layer="asset"', svg)
        self.assertIn('data-layer="aircraft"', svg)
        self.assertIn('data-layer="missile"', svg)

    def test_page_initializes_model_value_not_lazy_function(self):
        source = inspect.getsource(app.Page)

        self.assertNotIn("use_state(\n        lambda", source)


if __name__ == "__main__":
    unittest.main()
