import inspect
import unittest

from examples.hospital_material_mesa import app
from examples.hospital_material_mesa.model import HospitalMaterialHandlingModel


class HospitalMaterialVizTest(unittest.TestCase):
    def test_tiled_views_contain_expected_panels_without_3d_surface(self):
        model = HospitalMaterialHandlingModel(seed=23, agv_count=3)

        html = app.render_tiled_views(model)

        self.assertIn('data-panel="floor-grid"', html)
        self.assertIn('data-panel="agv-status"', html)
        self.assertIn('data-panel="mission-queues"', html)
        self.assertIn('data-panel="performance"', html)
        self.assertIn('data-layer="floor"', html)
        self.assertNotIn("window3d", html.lower())
        self.assertNotIn(".dae", html.lower())

    def test_tiled_views_render_parsed_2d_space_markup(self):
        model = HospitalMaterialHandlingModel(seed=23, agv_count=3)

        html = app.render_tiled_views(model)

        self.assertIn('data-space-source="alp-2d-markup"', html)
        self.assertIn('data-layer="wall"', html)
        self.assertIn('data-layer="lift"', html)
        self.assertIn('data-layer="node"', html)
        self.assertIn("mealPickingPoint", html)

    def test_page_initializes_model_value_not_lazy_function(self):
        source = inspect.getsource(app.Page)

        self.assertNotIn("use_state(\n        lambda", source)


if __name__ == "__main__":
    unittest.main()
