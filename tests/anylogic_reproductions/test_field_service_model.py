import unittest

from examples.field_service_mesa.model import FieldServiceModel


class FieldServiceModelTest(unittest.TestCase):
    def test_defaults_match_local_anylogic_field_service_controls(self):
        model = FieldServiceModel(seed=7)

        self.assertEqual(len(model.equipment), 100)
        self.assertEqual(len(model.crews), 3)
        self.assertEqual(model.daily_revenue_per_unit, 400.0)
        self.assertEqual(model.service_crew_cost_per_day, 1000.0)
        self.assertEqual(model.replacement_cost, 10000.0)
        self.assertEqual(model.repair_cost, 1000.0)
        self.assertEqual(model.maintenance_cost, 600.0)
        self.assertFalse(model.replace_old_equipment)
        self.assertEqual(model.mtce_periods_to_replace, 5)

    def test_failure_requests_are_dispatched_before_maintenance_requests(self):
        model = FieldServiceModel(
            seed=11,
            equipment_count=4,
            service_capacity=1,
            crew_speed=999,
            probability_replacement_needed=0,
        )
        failed = model.equipment[0]
        maintenance = model.equipment[1]

        model.request_maintenance(maintenance)
        model.request_service(failed)
        model.step()

        crew = model.crews[0]
        self.assertEqual(crew.equipment_unit, failed)
        self.assertEqual(crew.task_type, "repair")
        self.assertNotIn(failed, model.service_requests)
        self.assertIn(maintenance, model.maintenance_requests)

    def test_snapshot_tracks_profit_queues_and_service_counts(self):
        model = FieldServiceModel(
            seed=17,
            equipment_count=6,
            service_capacity=2,
            crew_speed=999,
            repair_typical_time=1,
            maintenance_mean_time=1,
            normal_failure_rate=0,
        )
        unit = model.equipment[0]
        model.request_service(unit)

        for _ in range(4):
            model.step()

        snapshot = model.snapshot()
        self.assertGreater(snapshot["revenue"], 0)
        self.assertGreaterEqual(snapshot["profit"], snapshot["revenue"] - snapshot["work_cost"] - snapshot["crew_cost"])
        self.assertEqual(snapshot["repairs_completed"], 1)
        self.assertIn("service_queue", snapshot)
        self.assertIn("maintenance_queue", snapshot)


if __name__ == "__main__":
    unittest.main()
