import unittest
from pathlib import Path

from examples.hospital_material_mesa.space import DEFAULT_ALP_PATH, parse_hospital_space


class HospitalMaterialSpaceTest(unittest.TestCase):
    def test_parse_real_alp_extracts_main_2d_levels(self):
        space = parse_hospital_space(DEFAULT_ALP_PATH)

        self.assertEqual(len(space.levels), 8)
        self.assertIn("ground_floor_1", space.levels)
        self.assertIn("floor_7", space.levels)
        self.assertNotIn("controlLevel", space.levels)
        self.assertNotIn("level", space.levels)

    def test_ground_floor_contains_markup_geometry_and_named_nodes(self):
        space = parse_hospital_space(DEFAULT_ALP_PATH)
        ground = space.levels["ground_floor_1"]

        self.assertGreater(len(ground.walls), 20)
        self.assertGreater(len(ground.polylines), 5)
        self.assertGreater(len(ground.rectangles), 3)
        self.assertGreater(len(ground.lifts), 1)
        self.assertIn("mealPickingPoint", {node.name for node in ground.nodes})
        self.assertGreater(ground.bounds.width, 1000)
        self.assertGreater(ground.bounds.height, 500)

    def test_missing_file_raises_clear_error(self):
        with self.assertRaises(FileNotFoundError):
            parse_hospital_space(Path("/tmp/not-a-real-hospital-model.alp"))


if __name__ == "__main__":
    unittest.main()
