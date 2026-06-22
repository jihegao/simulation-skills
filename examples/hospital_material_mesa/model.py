"""Mesa reproduction of AnyLogic's Material Handling in Hospital example.

This is a behavioral reimplementation, not an AnyLogic runtime import. The
local `.alp` is used as structural evidence for mission types, schedules,
floor levels, AGV fleet capacity, and dashboard metrics. The original 3D assets
are intentionally ignored.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean
from typing import Literal

import mesa


MissionType = Literal["MEAL", "WASTE", "STERILE", "LAUNDRY"]
CartState = Literal[
    "waiting_agv",
    "onboard",
    "waiting_station",
    "sorting",
    "return_waiting",
    "returning",
    "complete",
]
AgvState = Literal["idle", "moving"]

MISSION_TYPES: tuple[MissionType, ...] = ("MEAL", "WASTE", "STERILE", "LAUNDRY")
ACTIVE_MISSION_TYPES: tuple[MissionType, ...] = ("MEAL", "LAUNDRY", "WASTE")
FLOOR_LEVELS = ("floor_1", "floor_2", "floor_3", "floor_4", "floor_5", "floor_6", "floor_7", "ground_floor_1")

SECONDS_PER_DAY = 24 * 60 * 60
MEAL_SCHEDULE = ((6.5, 7.5, 13.0), (10.75, 11.0, 13.0), (13.75, 14.0, 13.0))
LAUNDRY_SCHEDULE = ((11.0, 16.0, 0.3),)
WASTE_OPERATOR_SCHEDULE = ((7.5, 11.0, 2), (15.5, 18.0, 2))

MISSION_COLORS = {
    "MEAL": "#b88652",
    "LAUNDRY": "#4fa69d",
    "WASTE": "#c65952",
    "STERILE": "#7387b8",
}


def _floor_index(floor: str) -> int:
    if floor == "ground_floor_1":
        return 0
    if floor.startswith("floor_"):
        return int(floor.split("_", 1)[1])
    return 0


def _mean_or_zero(values: list[float]) -> float:
    return mean(values) if values else 0.0


@dataclass
class Cart:
    unique_id: str
    mission: MissionType
    origin_floor: str
    destination_floor: str
    created_time: float
    return_required: bool = True
    state: CartState = "waiting_agv"
    start_waiting_time: float | None = None
    service_started_time: float | None = None
    service_completed_time: float | None = None
    empty_ready_time: float | None = None
    assigned_agv_id: str | None = None
    is_empty_return: bool = False

    def __post_init__(self) -> None:
        self.start_waiting_time = self.created_time


class AGV:
    def __init__(self, unique_id: str, home_floor: str) -> None:
        self.unique_id = unique_id
        self.home_floor = home_floor
        self.current_floor = home_floor
        self.destination_floor = home_floor
        self.state: AgvState = "idle"
        self.cart: Cart | None = None
        self.remaining_seconds = 0.0
        self.total_busy_seconds = 0.0
        self.completed_trips = 0
        self.current_mission: MissionType | None = None

    def assign(self, cart: Cart, now: float, duration_seconds: float) -> None:
        self.cart = cart
        self.current_mission = cart.mission
        self.destination_floor = cart.destination_floor
        self.remaining_seconds = max(1.0, duration_seconds)
        self.state = "moving"
        cart.state = "returning" if cart.is_empty_return else "onboard"
        cart.assigned_agv_id = self.unique_id
        cart.service_started_time = now

    def step(self, model: "HospitalMaterialHandlingModel") -> None:
        if self.state == "idle" or self.cart is None:
            return
        elapsed = min(self.remaining_seconds, model.step_seconds)
        self.remaining_seconds -= elapsed
        self.total_busy_seconds += elapsed
        if self.remaining_seconds <= 0:
            cart = self.cart
            self.current_floor = self.destination_floor
            self.cart = None
            self.current_mission = None
            self.state = "idle"
            self.completed_trips += 1
            model.finish_transport(cart)


class HospitalMaterialHandlingModel(mesa.Model):
    """Hospital AGV material-handling model with multistory floor abstraction."""

    model_time_unit = "second"

    def __init__(
        self,
        seed: int | None = None,
        agv_count: int = 10,
        number_of_waste_carts_on_floors: int = 12,
        meal_delivery_points: int = 13,
        step_seconds: float = 60.0,
        initial_time_seconds: float = 0.0,
        trip_seconds_per_floor: float = 180.0,
        horizontal_trip_seconds: float = 180.0,
        pickup_seconds: float = 30.0,
        dropoff_seconds: float = 30.0,
        meal_distribution_seconds: float = 30 * 60.0,
        laundry_distribution_seconds: float = 2 * 60 * 60.0,
        waste_sort_seconds: float = 20 * 60.0,
        demand_scale: float = 1.0,
    ) -> None:
        super().__init__(rng=seed)
        self.rng = random.Random(seed)
        self.agv_count = int(agv_count)
        self.number_of_waste_carts_on_floors = int(number_of_waste_carts_on_floors)
        self.meal_delivery_points = int(meal_delivery_points)
        self.step_seconds = float(step_seconds)
        self.sim_time_seconds = float(initial_time_seconds)
        self.trip_seconds_per_floor = float(trip_seconds_per_floor)
        self.horizontal_trip_seconds = float(horizontal_trip_seconds)
        self.pickup_seconds = float(pickup_seconds)
        self.dropoff_seconds = float(dropoff_seconds)
        self.meal_distribution_seconds = float(meal_distribution_seconds)
        self.laundry_distribution_seconds = float(laundry_distribution_seconds)
        self.waste_sort_seconds = float(waste_sort_seconds)
        self.demand_scale = float(demand_scale)

        homes = ["floor_2", "floor_2", "floor_3", "floor_3", "floor_4"]
        self.agvs = [AGV(f"agv-{index}", homes[index % len(homes)]) for index in range(self.agv_count)]
        self.pending_carts: list[Cart] = []
        self.completed_carts: list[Cart] = []
        self.waste_station_queue: list[Cart] = []
        self.waste_station_busy: list[tuple[Cart, float]] = []
        self.event_log: list[dict[str, float | str]] = []
        self.next_cart_id = 0
        self.generated_counts = {mission: 0 for mission in ACTIVE_MISSION_TYPES}
        self.completed_counts = {mission: 0 for mission in ACTIVE_MISSION_TYPES}
        self.wait_times = {mission: [] for mission in ACTIVE_MISSION_TYPES}
        self.processing_times = {mission: [] for mission in ACTIVE_MISSION_TYPES}
        self._schedule_residuals = {mission: 0.0 for mission in ACTIVE_MISSION_TYPES}

        for _ in range(self.number_of_waste_carts_on_floors):
            self.enqueue_cart(
                "WASTE",
                origin_floor=self._random_upper_floor(),
                destination_floor="ground_floor_1",
                return_required=True,
            )

    def _random_upper_floor(self) -> str:
        return f"floor_{self.rng.randint(2, 7)}"

    def log_event(self, message: str) -> None:
        self.event_log.append({"time_seconds": round(self.sim_time_seconds, 2), "message": message})
        if len(self.event_log) > 80:
            self.event_log = self.event_log[-80:]

    def enqueue_cart(
        self,
        mission: MissionType,
        origin_floor: str,
        destination_floor: str,
        return_required: bool = True,
        is_empty_return: bool = False,
    ) -> Cart:
        cart = Cart(
            unique_id=f"cart-{self.next_cart_id}",
            mission=mission,
            origin_floor=origin_floor,
            destination_floor=destination_floor,
            created_time=self.sim_time_seconds,
            return_required=return_required,
            is_empty_return=is_empty_return,
        )
        self.next_cart_id += 1
        self.pending_carts.append(cart)
        if not is_empty_return:
            self.generated_counts[mission] += 1
        self.log_event(f"{mission.lower()} cart queued from {origin_floor} to {destination_floor}")
        return cart

    def _scheduled_rate_per_hour(self, mission: MissionType) -> float:
        hour = (self.sim_time_seconds % SECONDS_PER_DAY) / 3600.0
        schedule = MEAL_SCHEDULE if mission == "MEAL" else LAUNDRY_SCHEDULE
        for start, end, rate in schedule:
            if start <= hour < end:
                return rate * self.demand_scale
        return 0.0

    def _generate_scheduled_carts(self) -> None:
        for mission in ("MEAL", "LAUNDRY"):
            expected = self._scheduled_rate_per_hour(mission) * self.step_seconds / 3600.0
            self._schedule_residuals[mission] += expected
            count = int(self._schedule_residuals[mission])
            self._schedule_residuals[mission] -= count
            for _ in range(count):
                if mission == "MEAL":
                    self.enqueue_cart("MEAL", "ground_floor_1", self._random_meal_floor(), return_required=True)
                else:
                    self.enqueue_cart("LAUNDRY", "ground_floor_1", self._random_upper_floor(), return_required=True)

    def _random_meal_floor(self) -> str:
        floor_number = 2 + (self.next_cart_id % 6)
        return f"floor_{floor_number}"

    def _release_empty_returns(self) -> None:
        for cart in list(self.completed_carts):
            if cart.empty_ready_time is not None and cart.empty_ready_time <= self.sim_time_seconds:
                cart.empty_ready_time = None
                self.enqueue_cart(
                    cart.mission,
                    origin_floor=cart.destination_floor,
                    destination_floor=cart.origin_floor,
                    return_required=False,
                    is_empty_return=True,
                )

    def _transport_duration(self, cart: Cart, agv: AGV) -> float:
        empty_leg = abs(_floor_index(agv.current_floor) - _floor_index(cart.origin_floor)) * self.trip_seconds_per_floor
        loaded_leg = abs(_floor_index(cart.origin_floor) - _floor_index(cart.destination_floor)) * self.trip_seconds_per_floor
        return empty_leg + loaded_leg + self.horizontal_trip_seconds + self.pickup_seconds + self.dropoff_seconds

    def _dispatch_agvs(self) -> None:
        idle_agvs = [agv for agv in self.agvs if agv.state == "idle"]
        for agv in idle_agvs:
            if not self.pending_carts:
                break
            cart = self.pending_carts.pop(0)
            if cart.start_waiting_time is not None and not cart.is_empty_return:
                self.wait_times[cart.mission].append(self.sim_time_seconds - cart.start_waiting_time)
            agv.assign(cart, self.sim_time_seconds, self._transport_duration(cart, agv))
            self.log_event(f"{agv.unique_id} started {cart.mission.lower()} transport")

    def _operator_capacity(self) -> int:
        hour = (self.sim_time_seconds % SECONDS_PER_DAY) / 3600.0
        for start, end, capacity in WASTE_OPERATOR_SCHEDULE:
            if start <= hour < end:
                return int(capacity)
        return 0

    def _process_waste_station(self) -> None:
        capacity = self._operator_capacity()
        while self.waste_station_queue and len(self.waste_station_busy) < capacity:
            cart = self.waste_station_queue.pop(0)
            cart.state = "sorting"
            self.waste_station_busy.append((cart, self.waste_sort_seconds))
            self.log_event(f"waste disposal started sorting {cart.unique_id}")

        updated: list[tuple[Cart, float]] = []
        for cart, remaining in self.waste_station_busy:
            remaining -= self.step_seconds
            if remaining <= 0:
                cart.state = "complete"
                cart.service_completed_time = self.sim_time_seconds
                self._complete_cart(cart)
                if cart.return_required:
                    self.enqueue_cart(
                        "WASTE",
                        origin_floor="ground_floor_1",
                        destination_floor=cart.origin_floor,
                        return_required=False,
                        is_empty_return=True,
                    )
            else:
                updated.append((cart, remaining))
        self.waste_station_busy = updated

    def finish_transport(self, cart: Cart) -> None:
        cart.assigned_agv_id = None
        if cart.mission == "WASTE" and not cart.is_empty_return:
            cart.state = "waiting_station"
            self.waste_station_queue.append(cart)
            self.log_event(f"{cart.unique_id} reached waste disposal queue")
            return

        if cart.is_empty_return:
            cart.state = "complete"
            cart.service_completed_time = self.sim_time_seconds
            self.completed_carts.append(cart)
            self.log_event(f"empty {cart.mission.lower()} cart returned")
            return

        cart.state = "complete"
        cart.service_completed_time = self.sim_time_seconds
        self._complete_cart(cart)
        if cart.return_required:
            delay = self.meal_distribution_seconds if cart.mission == "MEAL" else self.laundry_distribution_seconds
            cart.empty_ready_time = self.sim_time_seconds + delay

    def _complete_cart(self, cart: Cart) -> None:
        if cart.service_started_time is not None and cart.service_completed_time is not None:
            self.processing_times[cart.mission].append(cart.service_completed_time - cart.service_started_time)
        self.completed_counts[cart.mission] += 1
        self.completed_carts.append(cart)
        self.log_event(f"{cart.mission.lower()} cart service complete")

    def step(self) -> None:
        self._generate_scheduled_carts()
        self._release_empty_returns()
        self._dispatch_agvs()
        for agv in self.agvs:
            agv.step(self)
        self._process_waste_station()
        self.sim_time_seconds += self.step_seconds

    def waiting_counts_by_mission(self) -> dict[str, int]:
        counts = {mission: 0 for mission in ACTIVE_MISSION_TYPES}
        for cart in self.pending_carts + self.waste_station_queue:
            counts[cart.mission] += 1
        return counts

    def active_counts_by_mission(self) -> dict[str, int]:
        counts = {mission: 0 for mission in ACTIVE_MISSION_TYPES}
        for agv in self.agvs:
            if agv.current_mission is not None:
                counts[agv.current_mission] += 1
        for cart, _remaining in self.waste_station_busy:
            counts[cart.mission] += 1
        return counts

    def station_utilization(self) -> dict[str, float]:
        waste_capacity = max(1, self._operator_capacity())
        floor_waiting = sum(1 for cart in self.pending_carts if cart.origin_floor != "ground_floor_1")
        ground_waiting = sum(1 for cart in self.pending_carts if cart.origin_floor == "ground_floor_1")
        return {
            "supply_kitchen_picking": min(1.0, ground_waiting / max(1, self.agv_count)),
            "supply_kitchen_delivery": min(1.0, self.active_counts_by_mission()["MEAL"] / max(1, self.agv_count)),
            "supply_center_combined": min(1.0, self.active_counts_by_mission()["LAUNDRY"] / max(1, self.agv_count)),
            "waste_disposal_picking": min(1.0, len(self.waste_station_busy) / waste_capacity),
            "waste_disposal_delivery": min(1.0, len(self.waste_station_queue) / max(1, waste_capacity)),
            "stations_on_floors": min(1.0, floor_waiting / max(1, self.meal_delivery_points)),
            "waste_stations_on_floors": min(1.0, self.waiting_counts_by_mission()["WASTE"] / max(1, self.number_of_waste_carts_on_floors)),
        }

    def agv_utilization(self) -> float:
        elapsed = max(self.step_seconds, self.sim_time_seconds)
        return sum(agv.total_busy_seconds for agv in self.agvs) / max(1.0, elapsed * len(self.agvs))

    def snapshot(self) -> dict[str, float | int]:
        waiting = self.waiting_counts_by_mission()
        active = self.active_counts_by_mission()
        return {
            "time_seconds": round(self.sim_time_seconds, 2),
            "time_hours": round((self.sim_time_seconds % SECONDS_PER_DAY) / 3600.0, 3),
            "agv_count": len(self.agvs),
            "busy_agvs": sum(1 for agv in self.agvs if agv.state != "idle"),
            "agv_utilization": round(self.agv_utilization(), 4),
            "missions_started": sum(agv.completed_trips for agv in self.agvs) + sum(1 for agv in self.agvs if agv.state != "idle"),
            "pending_carts": len(self.pending_carts),
            "waste_station_queue": len(self.waste_station_queue),
            "waste_station_busy": len(self.waste_station_busy),
            "meal_generated": self.generated_counts["MEAL"],
            "laundry_generated": self.generated_counts["LAUNDRY"],
            "waste_generated": self.generated_counts["WASTE"],
            "meal_completed": self.completed_counts["MEAL"],
            "laundry_completed": self.completed_counts["LAUNDRY"],
            "waste_completed": self.completed_counts["WASTE"],
            "waiting_meal": waiting["MEAL"],
            "waiting_laundry": waiting["LAUNDRY"],
            "waiting_waste": waiting["WASTE"],
            "active_meal": active["MEAL"],
            "active_laundry": active["LAUNDRY"],
            "active_waste": active["WASTE"],
            "avg_meal_wait_seconds": round(_mean_or_zero(self.wait_times["MEAL"]), 2),
            "avg_laundry_wait_seconds": round(_mean_or_zero(self.wait_times["LAUNDRY"]), 2),
            "avg_waste_wait_seconds": round(_mean_or_zero(self.wait_times["WASTE"]), 2),
            "avg_meal_processing_seconds": round(_mean_or_zero(self.processing_times["MEAL"]), 2),
            "avg_laundry_processing_seconds": round(_mean_or_zero(self.processing_times["LAUNDRY"]), 2),
            "avg_waste_processing_seconds": round(_mean_or_zero(self.processing_times["WASTE"]), 2),
        }
