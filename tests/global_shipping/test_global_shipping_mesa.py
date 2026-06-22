import json
import tempfile
import unittest
from pathlib import Path

from examples.global_shipping_mesa.model import (
    GlobalShippingModel,
    haversine_nm,
)
from examples.global_shipping_mesa.run_experiment import run_experiment
from examples.global_shipping_mesa.static_viewer import build_view_payload, write_viewer_html


class GlobalShippingMesaTest(unittest.TestCase):
    def test_default_ports_are_global_gis_points(self):
        model = GlobalShippingModel(seed=7, initial_orders=0, ship_count=1)

        ports = model.visualization_state()["ports"]

        self.assertEqual(len(ports), 10)
        self.assertTrue(all(-90 <= port["lat"] <= 90 for port in ports))
        self.assertTrue(all(-180 <= port["lon"] <= 180 for port in ports))
        names = {port["name"] for port in ports}
        self.assertIn("Shanghai", names)
        self.assertIn("Rotterdam", names)

    def test_generated_orders_have_distinct_origin_and_destination(self):
        model = GlobalShippingModel(seed=3, initial_orders=20, ship_count=0)

        self.assertTrue(model.orders)
        self.assertTrue(all(order.origin != order.destination for order in model.orders))

    def test_idle_ship_claims_nearest_order_origin(self):
        model = GlobalShippingModel(seed=11, initial_orders=0, ship_count=1)
        ship = model.ships[0]
        ship.port_id = "rotterdam"
        ship.lat = model.ports["rotterdam"].lat
        ship.lon = model.ports["rotterdam"].lon
        model.create_order(origin="shanghai", destination="los_angeles")
        model.create_order(origin="hamburg", destination="singapore")

        model.step()

        self.assertIsNotNone(ship.order_id)
        claimed = model.orders_by_id[ship.order_id]
        self.assertEqual(claimed.origin, "hamburg")

    def test_constrained_ports_raise_queue_pressure_and_wait(self):
        constrained = GlobalShippingModel(
            seed=13,
            ship_count=5,
            initial_orders=25,
            port_capacity_scale=0.35,
            order_interval_hours=4,
        )
        unconstrained = GlobalShippingModel(
            seed=13,
            ship_count=5,
            initial_orders=25,
            port_capacity_scale=1.4,
            order_interval_hours=4,
        )

        for _ in range(180):
            constrained.step()
            unconstrained.step()

        self.assertGreaterEqual(
            constrained.snapshot()["avg_port_queue"],
            unconstrained.snapshot()["avg_port_queue"],
        )
        self.assertGreaterEqual(
            constrained.snapshot()["avg_order_wait_hours"],
            unconstrained.snapshot()["avg_order_wait_hours"],
        )

    def test_run_experiment_writes_summary_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            summary = run_experiment(
                {
                    "steps": 72,
                    "seeds": [1, 2],
                    "parameters": {
                        "ship_count": 4,
                        "initial_orders": 10,
                        "port_capacity_scale": [0.6, 1.2],
                        "order_interval_hours": 8,
                    },
                },
                output_dir,
            )

            self.assertEqual(summary["run_count"], 4)
            self.assertEqual(summary["sweep_parameters"], ["port_capacity_scale"])
            self.assertTrue((output_dir / "run_rows.csv").exists())
            saved = json.loads((output_dir / "summary.json").read_text())
            first_key = sorted(saved["aggregate_metrics"])[0]
            self.assertIn("completed_orders_mean", saved["aggregate_metrics"][first_key])
            self.assertIn("avg_port_queue_mean", saved["aggregate_metrics"][first_key])

    def test_static_viewer_contains_cesium_globe_contract(self):
        payload = build_view_payload(seed=5, steps=24, ship_count=3, initial_orders=8)

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "shipping.html"
            write_viewer_html(target, payload)
            html = target.read_text(encoding="utf-8")

        self.assertIn("Cesium.js", html)
        self.assertIn("cesiumContainer", html)
        self.assertIn("Global Shipping 3D Globe", html)
        self.assertIn("port_capacity_scale", html)
        self.assertIn("haversine_nm", html)
        self.assertIn("TileMapServiceImageryProvider.fromUrl", html)
        self.assertIn("NaturalEarthII", html)
        self.assertIn("viewer.scene.globe.enableLighting = true", html)
        self.assertIn("viewer.entities.add", html)
        self.assertIn("ScreenSpaceCameraController", html)
        self.assertIn("document.body.dataset.cesiumReady", html)
        self.assertIn("document.body.dataset.cameraLon", html)
        self.assertNotIn("three.module.js", html)
        self.assertNotIn("globe.rotation.y +=", html)

    def test_haversine_distance_is_nautical_miles(self):
        shanghai_to_singapore = haversine_nm(31.2304, 121.4737, 1.3521, 103.8198)

        self.assertGreater(shanghai_to_singapore, 2000)
        self.assertLess(shanghai_to_singapore, 2300)


if __name__ == "__main__":
    unittest.main()
