import unittest

from examples.air_defense_mesa.model import (
    AirDefenseModel,
    DEFAULT_RADAR_LOCATIONS,
    distance3,
)


class AirDefenseModelTest(unittest.TestCase):
    def test_defaults_match_local_anylogic_model_controls(self):
        model = AirDefenseModel(seed=7, steps_per_day=20)

        self.assertEqual(model.aircraft_speed, 10.0)
        self.assertEqual(model.missile_speed, 20.0)
        self.assertEqual(model.radar_zone, 100.0)
        self.assertEqual(model.radar_max_missiles, 2)
        self.assertEqual(model.aircraft_z, 70.0)
        self.assertEqual([(r.x, r.y, r.z) for r in model.radars], list(DEFAULT_RADAR_LOCATIONS))

    def test_radar_fires_only_for_capacity_and_untracked_aircraft(self):
        model = AirDefenseModel(
            seed=3,
            initial_aircraft=3,
            aircraft_speed=0,
            missile_speed=0,
            radar_zone=200,
            radar_max_missiles=2,
            steps_per_day=10,
            radar_locations=[DEFAULT_RADAR_LOCATIONS[0]],
        )
        model.aircrafts[0].x, model.aircrafts[0].y, model.aircrafts[0].z = 230, 80, 70
        model.aircrafts[1].x, model.aircrafts[1].y, model.aircrafts[1].z = 235, 80, 70
        model.aircrafts[2].x, model.aircrafts[2].y, model.aircrafts[2].z = 240, 80, 70

        model.step()

        radar = model.radars[0]
        self.assertEqual(len(radar.missiles), 2)
        self.assertEqual(model.snapshot()["active_missiles"], 2)
        self.assertEqual(sum(1 for aircraft in model.aircrafts if aircraft.tracked), 2)

    def test_missile_hit_destroys_aircraft_before_asset_is_bombed(self):
        model = AirDefenseModel(
            seed=5,
            initial_aircraft=1,
            aircraft_speed=0,
            missile_speed=30,
            radar_zone=300,
            radar_max_missiles=1,
            steps_per_day=10,
        )
        aircraft = model.aircrafts[0]
        aircraft.x, aircraft.y, aircraft.z = 235, 80, 70
        aircraft.target.x, aircraft.target.y = 360, 80

        for _ in range(20):
            model.step()
            if aircraft.state == "destroyed":
                break

        self.assertEqual(aircraft.state, "destroyed")
        self.assertEqual(model.snapshot()["aircraft_destroyed"], 1)
        self.assertEqual(model.snapshot()["assets_destroyed"], 0)

    def test_missile_miss_clears_tracking_when_target_leaves_radar_zone(self):
        model = AirDefenseModel(
            seed=11,
            initial_aircraft=1,
            aircraft_speed=0,
            missile_speed=0,
            radar_zone=60,
            radar_max_missiles=1,
            steps_per_day=10,
            radar_locations=[DEFAULT_RADAR_LOCATIONS[0]],
        )
        aircraft = model.aircrafts[0]
        aircraft.x, aircraft.y, aircraft.z = 240, 80, 0

        model.step()
        self.assertTrue(aircraft.tracked)
        self.assertEqual(model.snapshot()["active_missiles"], 1)

        aircraft.x, aircraft.y, aircraft.z = 500, 500, 70
        model.step()

        self.assertFalse(aircraft.tracked)
        self.assertEqual(model.snapshot()["active_missiles"], 0)
        self.assertEqual(model.snapshot()["missiles_missed"], 1)

    def test_aircraft_bombs_asset_within_ground_range_and_altitude(self):
        model = AirDefenseModel(
            seed=17,
            initial_aircraft=1,
            aircraft_speed=20,
            missile_speed=0,
            radar_zone=1,
            radar_max_missiles=0,
            steps_per_day=20,
        )
        aircraft = model.aircrafts[0]
        aircraft.target.x, aircraft.target.y = 40, 0
        aircraft.x, aircraft.y, aircraft.z = 0, 0, 70

        for _ in range(80):
            model.step()
            if aircraft.target.state == "destroyed":
                break

        self.assertEqual(aircraft.target.state, "destroyed")
        self.assertEqual(aircraft.state, "returning")
        self.assertLessEqual(distance3((aircraft.x, aircraft.y, 0), (aircraft.target.x, aircraft.target.y, 0)), 5)
        self.assertEqual(model.snapshot()["assets_destroyed"], 1)


if __name__ == "__main__":
    unittest.main()
