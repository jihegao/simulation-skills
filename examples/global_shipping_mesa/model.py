"""Global port shipping model with SimPy resources inside a Mesa shell."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean
from typing import Literal

import mesa
import simpy


OrderStatus = Literal["open", "assigned", "loading", "sailing", "unloading", "completed"]
ShipStatus = Literal["idle", "to_load_port", "loading", "to_discharge_port", "unloading"]

EARTH_RADIUS_NM = 3440.065


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in nautical miles."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@dataclass(frozen=True)
class PortSpec:
    port_id: str
    name: str
    country: str
    lat: float
    lon: float
    base_berths: int
    base_cranes: int
    yard_capacity_teu: float
    load_rate_teu_per_hour: float


@dataclass
class PortRuntime:
    spec: PortSpec
    berths: simpy.Resource
    cranes: simpy.Resource
    yard_teu: float
    handled_teu: float = 0.0
    queue_wait_hours: float = 0.0
    sampled_queue_depth: float = 0.0
    queue_samples: int = 0
    max_queue_depth: int = 0
    calls_started: int = 0
    calls_completed: int = 0

    @property
    def queue_depth(self) -> int:
        return len(self.berths.queue) + len(self.cranes.queue)

    @property
    def utilization_pressure(self) -> float:
        berth_pressure = self.berths.count / max(1, self.berths.capacity)
        crane_pressure = self.cranes.count / max(1, self.cranes.capacity)
        yard_pressure = self.yard_teu / max(1.0, self.spec.yard_capacity_teu)
        return max(berth_pressure, crane_pressure, yard_pressure)


@dataclass
class CargoOrder:
    order_id: str
    origin: str
    destination: str
    created_time: float
    cargo_teu: float
    status: OrderStatus = "open"
    assigned_ship: str | None = None
    assigned_time: float | None = None
    completed_time: float | None = None
    port_wait_hours: float = 0.0
    sea_hours: float = 0.0


@dataclass
class ShipState:
    ship_id: str
    lat: float
    lon: float
    speed_knots: float
    capacity_teu: float
    status: ShipStatus = "idle"
    port_id: str | None = None
    order_id: str | None = None
    from_port: str | None = None
    to_port: str | None = None
    travel_start: float = 0.0
    travel_end: float = 0.0
    busy_hours: float = 0.0
    empty_sailing_hours: float = 0.0


DEFAULT_PORTS: tuple[PortSpec, ...] = (
    PortSpec("shanghai", "Shanghai", "China", 31.2304, 121.4737, 7, 12, 120000, 420),
    PortSpec("singapore", "Singapore", "Singapore", 1.3521, 103.8198, 6, 10, 100000, 380),
    PortSpec("rotterdam", "Rotterdam", "Netherlands", 51.9244, 4.4777, 5, 8, 85000, 320),
    PortSpec("los_angeles", "Los Angeles", "USA", 33.7405, -118.2775, 4, 7, 76000, 280),
    PortSpec("hamburg", "Hamburg", "Germany", 53.5511, 9.9937, 3, 6, 62000, 240),
    PortSpec("busan", "Busan", "South Korea", 35.1796, 129.0756, 5, 8, 78000, 300),
    PortSpec("dubai", "Jebel Ali", "UAE", 25.0118, 55.0611, 5, 8, 82000, 310),
    PortSpec("santos", "Santos", "Brazil", -23.9608, -46.3336, 3, 5, 54000, 190),
    PortSpec("durban", "Durban", "South Africa", -29.8587, 31.0218, 3, 5, 52000, 180),
    PortSpec("melbourne", "Melbourne", "Australia", -37.8136, 144.9631, 3, 5, 58000, 195),
)


class GlobalShippingModel(mesa.Model):
    """Global shipping dispatch model with port-space and resource constraints."""

    model_time_unit = "hour"

    def __init__(
        self,
        seed: int | None = None,
        ship_count: int = 8,
        initial_orders: int = 18,
        order_interval_hours: float = 10.0,
        port_capacity_scale: float = 1.0,
        ship_speed_knots: float = 19.0,
        mean_order_teu: float = 2400.0,
        step_hours: float = 1.0,
    ) -> None:
        super().__init__(rng=seed)
        self.rng = random.Random(seed)
        self.env = simpy.Environment()
        self.order_interval_hours = float(order_interval_hours)
        self.port_capacity_scale = float(port_capacity_scale)
        self.ship_speed_knots = float(ship_speed_knots)
        self.mean_order_teu = float(mean_order_teu)
        self.step_hours = float(step_hours)
        self.orders: list[CargoOrder] = []
        self.orders_by_id: dict[str, CargoOrder] = {}
        self.completed_orders: list[CargoOrder] = []
        self.event_log: list[dict[str, float | str]] = []
        self.next_order_number = 1
        self.ports = {spec.port_id: spec for spec in DEFAULT_PORTS}
        self.port_runtime = self._build_ports()
        self.ships = self._build_ships(int(ship_count))

        for _ in range(int(initial_orders)):
            self.create_order()

        self.env.process(self._order_source())
        for ship in self.ships:
            self.env.process(self._ship_loop(ship))

    @property
    def sim_time_hours(self) -> float:
        return float(self.env.now)

    def _build_ports(self) -> dict[str, PortRuntime]:
        runtimes: dict[str, PortRuntime] = {}
        for spec in DEFAULT_PORTS:
            berths = max(1, round(spec.base_berths * self.port_capacity_scale))
            cranes = max(1, round(spec.base_cranes * self.port_capacity_scale))
            scaled_spec = PortSpec(
                spec.port_id,
                spec.name,
                spec.country,
                spec.lat,
                spec.lon,
                berths,
                cranes,
                max(5000.0, spec.yard_capacity_teu * self.port_capacity_scale),
                max(120.0, spec.load_rate_teu_per_hour * self.port_capacity_scale),
            )
            runtimes[spec.port_id] = PortRuntime(
                spec=scaled_spec,
                berths=simpy.Resource(self.env, capacity=berths),
                cranes=simpy.Resource(self.env, capacity=cranes),
                yard_teu=scaled_spec.yard_capacity_teu * self.rng.uniform(0.35, 0.7),
            )
        return runtimes

    def _build_ships(self, ship_count: int) -> list[ShipState]:
        port_ids = list(self.ports)
        ships = []
        for index in range(ship_count):
            port = self.ports[port_ids[index % len(port_ids)]]
            ships.append(
                ShipState(
                    ship_id=f"ship-{index + 1}",
                    lat=port.lat,
                    lon=port.lon,
                    speed_knots=self.ship_speed_knots * self.rng.uniform(0.92, 1.08),
                    capacity_teu=self.rng.uniform(3800, 9000),
                    port_id=port.port_id,
                )
            )
        return ships

    def log_event(self, message: str) -> None:
        self.event_log.append({"time_hours": round(self.sim_time_hours, 2), "message": message})
        if len(self.event_log) > 120:
            self.event_log = self.event_log[-120:]

    def create_order(
        self,
        origin: str | None = None,
        destination: str | None = None,
        cargo_teu: float | None = None,
    ) -> CargoOrder:
        port_ids = list(self.ports)
        if origin is None:
            origin = self.rng.choice(port_ids)
        if destination is None:
            candidates = [port_id for port_id in port_ids if port_id != origin]
            destination = self.rng.choice(candidates)
        if origin == destination:
            raise ValueError("shipping orders require distinct origin and destination ports")
        if cargo_teu is None:
            cargo_teu = max(250.0, self.rng.expovariate(1.0 / max(1.0, self.mean_order_teu)))

        order = CargoOrder(
            order_id=f"order-{self.next_order_number}",
            origin=origin,
            destination=destination,
            created_time=self.sim_time_hours,
            cargo_teu=float(cargo_teu),
        )
        self.next_order_number += 1
        self.orders.append(order)
        self.orders_by_id[order.order_id] = order
        self.port_runtime[origin].yard_teu = min(
            self.port_runtime[origin].spec.yard_capacity_teu * 1.25,
            self.port_runtime[origin].yard_teu + order.cargo_teu,
        )
        self.log_event(f"{order.order_id} opened {self.ports[origin].name} -> {self.ports[destination].name}")
        return order

    def _order_source(self):
        interval = max(0.1, self.order_interval_hours)
        while True:
            yield self.env.timeout(self.rng.expovariate(1.0 / interval))
            self.create_order()

    def _ship_loop(self, ship: ShipState):
        while True:
            order = self._claim_nearest_order(ship)
            if order is None:
                ship.status = "idle"
                ship.order_id = None
                yield self.env.timeout(1.0)
                continue

            yield from self._sail_to(ship, order.origin, loaded=False)
            order.status = "loading"
            yield from self._handle_port_call(ship, order, order.origin, "loading")
            yield from self._sail_to(ship, order.destination, loaded=True)
            order.status = "unloading"
            yield from self._handle_port_call(ship, order, order.destination, "unloading")

            order.status = "completed"
            order.completed_time = self.sim_time_hours
            ship.status = "idle"
            ship.order_id = None
            ship.port_id = order.destination
            self.completed_orders.append(order)
            self.log_event(f"{order.order_id} completed by {ship.ship_id}")

    def _claim_nearest_order(self, ship: ShipState) -> CargoOrder | None:
        open_orders = [order for order in self.orders if order.status == "open"]
        if not open_orders:
            return None
        order = min(open_orders, key=lambda item: self._ship_to_port_distance(ship, item.origin))
        order.status = "assigned"
        order.assigned_ship = ship.ship_id
        order.assigned_time = self.sim_time_hours
        ship.order_id = order.order_id
        self.log_event(f"{ship.ship_id} claimed {order.order_id}")
        return order

    def _ship_to_port_distance(self, ship: ShipState, port_id: str) -> float:
        lat, lon = self._ship_position(ship)
        port = self.ports[port_id]
        return haversine_nm(lat, lon, port.lat, port.lon)

    def _sail_to(self, ship: ShipState, port_id: str, loaded: bool):
        origin_lat, origin_lon = self._ship_position(ship)
        destination = self.ports[port_id]
        distance_nm = haversine_nm(origin_lat, origin_lon, destination.lat, destination.lon)
        duration = distance_nm / max(1.0, ship.speed_knots)
        ship.status = "to_discharge_port" if loaded else "to_load_port"
        ship.from_port = ship.port_id
        ship.to_port = port_id
        ship.travel_start = self.sim_time_hours
        ship.travel_end = self.sim_time_hours + duration
        ship.port_id = None
        if not loaded:
            ship.empty_sailing_hours += duration
        if ship.order_id is not None and loaded:
            self.orders_by_id[ship.order_id].status = "sailing"
            self.orders_by_id[ship.order_id].sea_hours += duration
        yield self.env.timeout(duration)
        ship.lat = destination.lat
        ship.lon = destination.lon
        ship.port_id = port_id
        ship.from_port = None
        ship.to_port = None

    def _handle_port_call(self, ship: ShipState, order: CargoOrder, port_id: str, status: ShipStatus):
        runtime = self.port_runtime[port_id]
        queue_start = self.sim_time_hours
        runtime.calls_started += 1
        ship.status = status
        with runtime.berths.request() as berth_request, runtime.cranes.request() as crane_request:
            yield berth_request & crane_request
            wait = self.sim_time_hours - queue_start
            runtime.queue_wait_hours += wait
            order.port_wait_hours += wait
            pressure = max(1.0, 1.0 + max(0.0, runtime.utilization_pressure - 0.72) * 1.8)
            duration = order.cargo_teu / max(1.0, runtime.spec.load_rate_teu_per_hour) * pressure
            duration = max(0.5, duration)
            ship.busy_hours += duration
            self.log_event(f"{ship.ship_id} {status} {order.order_id} at {runtime.spec.name}")
            yield self.env.timeout(duration)
            if status == "loading":
                runtime.yard_teu = max(0.0, runtime.yard_teu - order.cargo_teu)
            else:
                runtime.yard_teu = min(runtime.spec.yard_capacity_teu * 1.25, runtime.yard_teu + order.cargo_teu * 0.25)
            runtime.handled_teu += order.cargo_teu
            runtime.calls_completed += 1

    def _ship_position(self, ship: ShipState) -> tuple[float, float]:
        if ship.to_port is None or ship.travel_end <= ship.travel_start:
            return ship.lat, ship.lon
        destination = self.ports[ship.to_port]
        if ship.from_port is not None and ship.from_port in self.ports:
            origin = self.ports[ship.from_port]
            start_lat, start_lon = origin.lat, origin.lon
        else:
            start_lat, start_lon = ship.lat, ship.lon
        ratio = (self.sim_time_hours - ship.travel_start) / max(0.0001, ship.travel_end - ship.travel_start)
        ratio = max(0.0, min(1.0, ratio))
        return (
            start_lat + (destination.lat - start_lat) * ratio,
            start_lon + (destination.lon - start_lon) * ratio,
        )

    def step(self) -> None:
        self.env.run(until=self.sim_time_hours + self.step_hours)
        for runtime in self.port_runtime.values():
            depth = runtime.queue_depth
            runtime.sampled_queue_depth += depth
            runtime.queue_samples += 1
            runtime.max_queue_depth = max(runtime.max_queue_depth, depth)

    def snapshot(self) -> dict[str, float | int]:
        open_orders = sum(1 for order in self.orders if order.status == "open")
        assigned_orders = sum(1 for order in self.orders if order.status in {"assigned", "loading", "sailing", "unloading"})
        sampled_port_queues = [
            runtime.sampled_queue_depth / max(1, runtime.queue_samples)
            for runtime in self.port_runtime.values()
        ]
        order_waits = [order.port_wait_hours for order in self.completed_orders]
        cycle_times = [
            order.completed_time - order.created_time
            for order in self.completed_orders
            if order.completed_time is not None
        ]
        empty_hours = sum(ship.empty_sailing_hours for ship in self.ships)
        busy_hours = sum(ship.busy_hours for ship in self.ships)
        return {
            "time_hours": round(self.sim_time_hours, 3),
            "orders_total": len(self.orders),
            "open_orders": open_orders,
            "assigned_orders": assigned_orders,
            "completed_orders": len(self.completed_orders),
            "avg_port_queue": round(mean(sampled_port_queues), 3) if sampled_port_queues else 0.0,
            "max_port_queue": max((runtime.max_queue_depth for runtime in self.port_runtime.values()), default=0),
            "max_port_pressure": round(max((runtime.utilization_pressure for runtime in self.port_runtime.values()), default=0.0), 3),
            "avg_order_wait_hours": round(mean(order_waits), 3) if order_waits else 0.0,
            "avg_cycle_hours": round(mean(cycle_times), 3) if cycle_times else 0.0,
            "empty_sailing_share": round(empty_hours / max(0.0001, empty_hours + busy_hours), 3),
        }

    def visualization_state(self) -> dict[str, object]:
        ports = []
        for port_id, runtime in self.port_runtime.items():
            spec = runtime.spec
            ports.append(
                {
                    "id": port_id,
                    "name": spec.name,
                    "country": spec.country,
                    "lat": spec.lat,
                    "lon": spec.lon,
                    "berths": spec.base_berths,
                    "cranes": spec.base_cranes,
                    "yard_capacity_teu": round(spec.yard_capacity_teu, 1),
                    "yard_teu": round(runtime.yard_teu, 1),
                    "queue_depth": runtime.queue_depth,
                    "max_queue_depth": runtime.max_queue_depth,
                    "pressure": round(runtime.utilization_pressure, 3),
                    "handled_teu": round(runtime.handled_teu, 1),
                }
            )
        ships = []
        for ship in self.ships:
            lat, lon = self._ship_position(ship)
            ships.append(
                {
                    "id": ship.ship_id,
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "status": ship.status,
                    "order_id": ship.order_id,
                    "to_port": ship.to_port,
                    "capacity_teu": round(ship.capacity_teu, 1),
                }
            )
        orders = [
            {
                "id": order.order_id,
                "origin": order.origin,
                "destination": order.destination,
                "status": order.status,
                "cargo_teu": round(order.cargo_teu, 1),
                "assigned_ship": order.assigned_ship,
            }
            for order in self.orders[-60:]
        ]
        return {
            "time_hours": round(self.sim_time_hours, 2),
            "ports": ports,
            "ships": ships,
            "orders": orders,
            "metrics": self.snapshot(),
            "events": list(self.event_log[-14:]),
            "params": {
                "port_capacity_scale": self.port_capacity_scale,
                "order_interval_hours": self.order_interval_hours,
                "ship_speed_knots": self.ship_speed_knots,
            },
        }
