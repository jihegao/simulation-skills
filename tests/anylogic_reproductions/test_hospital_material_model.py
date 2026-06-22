import unittest

from examples.hospital_material_mesa.model import (
    FLOOR_LEVELS,
    MISSION_TYPES,
    HospitalMaterialHandlingModel,
)


class HospitalMaterialModelTest(unittest.TestCase):
    def test_defaults_preserve_anylogic_hospital_source_boundary(self):
        model = HospitalMaterialHandlingModel(seed=7)

        self.assertEqual(MISSION_TYPES, ("MEAL", "WASTE", "STERILE", "LAUNDRY"))
        self.assertEqual(FLOOR_LEVELS, ("floor_1", "floor_2", "floor_3", "floor_4", "floor_5", "floor_6", "floor_7", "ground_floor_1"))
        self.assertEqual(model.number_of_waste_carts_on_floors, 12)
        self.assertEqual(len(model.agvs), 10)
        self.assertEqual(model.meal_delivery_points, 13)
        self.assertEqual(model.model_time_unit, "second")

    def test_scheduled_meal_carts_are_generated_and_dispatched_to_agvs(self):
        model = HospitalMaterialHandlingModel(
            seed=11,
            agv_count=2,
            step_seconds=60,
            initial_time_seconds=6.5 * 60 * 60,
            trip_seconds_per_floor=120,
            pickup_seconds=10,
            dropoff_seconds=10,
        )

        for _ in range(20):
            model.step()

        snapshot = model.snapshot()
        self.assertGreater(snapshot["meal_generated"], 0)
        self.assertGreater(snapshot["missions_started"], 0)
        self.assertGreaterEqual(snapshot["meal_completed"], 0)

    def test_waste_station_capacity_blocks_completion_until_operator_window(self):
        model = HospitalMaterialHandlingModel(
            seed=13,
            agv_count=1,
            step_seconds=300,
            initial_time_seconds=5 * 60 * 60,
            trip_seconds_per_floor=60,
            pickup_seconds=0,
            dropoff_seconds=0,
            waste_sort_seconds=600,
        )
        model.pending_carts.clear()
        cart = model.enqueue_cart("WASTE", origin_floor="floor_4", destination_floor="ground_floor_1", return_required=False)

        for _ in range(5):
            model.step()

        self.assertEqual(cart.state, "waiting_station")
        self.assertGreaterEqual(model.snapshot()["waste_station_queue"], 1)

        model.sim_time_seconds = 8 * 60 * 60
        for _ in range(6):
            model.step()

        self.assertEqual(cart.state, "complete")
        self.assertEqual(model.snapshot()["waste_completed"], 1)


if __name__ == "__main__":
    unittest.main()
