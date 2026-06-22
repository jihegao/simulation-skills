"""Mesa reproduction of the local AnyLogic Field Service example.

This is a behavioral reimplementation, not an AnyLogic runtime import. The
default controls and state names are derived from the local PLE `.alp`.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal

import mesa


EquipmentState = Literal["working", "failed", "repair", "maintenance", "replacement"]
CrewState = Literal["idle", "driving_to_work", "working", "driving_home"]
TaskType = Literal["repair", "maintenance", "replacement"]

DEFAULT_FIELD_WIDTH = 610.0
DEFAULT_FIELD_HEIGHT = 510.0
HOME_POSITION = (60.0, 455.0)


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def move_toward(
    position: tuple[float, float],
    target: tuple[float, float],
    speed: float,
) -> tuple[float, float]:
    dist = distance(position, target)
    if dist == 0 or speed <= 0:
        return position
    ratio = min(1.0, speed / dist)
    return (
        position[0] + (target[0] - position[0]) * ratio,
        position[1] + (target[1] - position[1]) * ratio,
    )


@dataclass
class EquipmentUnit:
    unique_id: str
    x: float
    y: float
    time_last_replacement: float
    time_last_maintenance: float
    replacement_mean_time: float
    maintenance_mean_time: float
    repair_typical_time: float
    probability_replacement_needed: float
    maintenance_period: float
    normal_failure_rate: float
    state: EquipmentState = "working"
    assigned_crew_id: str | None = None
    request_time: float | None = None
    maintenance_requested: bool = False

    @property
    def position(self) -> tuple[float, float]:
        return (self.x, self.y)

    def age(self, now: float) -> float:
        return max(0.0, now - self.time_last_replacement)

    def maintenance_overdue(self, now: float) -> bool:
        return now - self.time_last_maintenance >= self.maintenance_period

    def daily_failure_probability(self, now: float) -> float:
        time_since_maintenance = max(0.0, now - self.time_last_maintenance)
        overdue_factor = max(1.0, time_since_maintenance / max(1.0, self.maintenance_period))
        age_factor = max(1.0, self.age(now) / max(1.0, 3.0 * self.maintenance_period))
        rate = self.normal_failure_rate * overdue_factor * age_factor
        return max(0.0, min(0.95, 1.0 - math.exp(-rate)))


class ServiceCrew:
    def __init__(
        self,
        unique_id: str,
        home: tuple[float, float] = HOME_POSITION,
        crew_speed: float = 75.0,
    ) -> None:
        self.unique_id = unique_id
        self.home = home
        self.x = float(home[0])
        self.y = float(home[1])
        self.crew_speed = float(crew_speed)
        self.state: CrewState = "idle"
        self.equipment_unit: EquipmentUnit | None = None
        self.task_type: TaskType | None = None
        self.work_remaining = 0.0
        self.travel_target = home

    @property
    def position(self) -> tuple[float, float]:
        return (self.x, self.y)

    def assign(self, unit: EquipmentUnit, task_type: TaskType) -> None:
        self.equipment_unit = unit
        self.task_type = task_type
        self.travel_target = (unit.x + 5.0, unit.y + 5.0)
        self.state = "driving_to_work"
        unit.assigned_crew_id = self.unique_id

    def step(self, model: "FieldServiceModel") -> None:
        if self.state == "idle":
            return
        if self.state == "driving_to_work":
            self.x, self.y = move_toward(self.position, self.travel_target, self.crew_speed)
            if distance(self.position, self.travel_target) <= 0.001 and self.equipment_unit is not None:
                self._start_work(model)
            return
        if self.state == "working":
            self.work_remaining -= 1.0
            if self.work_remaining <= 0 and self.equipment_unit is not None:
                self._finish_work(model)
            return
        if self.state == "driving_home":
            self.x, self.y = move_toward(self.position, self.home, self.crew_speed)
            if distance(self.position, self.home) <= 0.001:
                self.state = "idle"
                model.log_event(f"{self.unique_id} returned to base")

    def _start_work(self, model: "FieldServiceModel") -> None:
        unit = self.equipment_unit
        if unit is None or self.task_type is None:
            return
        if self.task_type == "repair":
            replace = model.rng.random() < unit.probability_replacement_needed
            if model.replace_old_equipment and unit.age(model.sim_time_days) >= (
                model.mtce_periods_to_replace * unit.maintenance_period
            ):
                replace = True
            if replace:
                self.task_type = "replacement"
                unit.state = "replacement"
                self.work_remaining = max(1.0, unit.replacement_mean_time)
            else:
                unit.state = "repair"
                self.work_remaining = max(1.0, unit.repair_typical_time)
        elif self.task_type == "replacement":
            unit.state = "replacement"
            self.work_remaining = max(1.0, unit.replacement_mean_time)
        else:
            unit.state = "maintenance"
            self.work_remaining = max(1.0, unit.maintenance_mean_time)
        self.state = "working"
        model.log_event(f"{self.unique_id} started {self.task_type} on {unit.unique_id}")

    def _finish_work(self, model: "FieldServiceModel") -> None:
        unit = self.equipment_unit
        task_type = self.task_type
        if unit is None or task_type is None:
            return

        unit.state = "working"
        unit.assigned_crew_id = None
        unit.request_time = None
        unit.maintenance_requested = False
        if task_type == "replacement":
            unit.time_last_replacement = model.sim_time_days
            unit.time_last_maintenance = model.sim_time_days
            model.work_cost += model.replacement_cost
            model.replacements_completed += 1
        elif task_type == "maintenance":
            unit.time_last_maintenance = model.sim_time_days
            model.work_cost += model.maintenance_cost
            model.maintenance_completed += 1
        else:
            unit.time_last_maintenance = model.sim_time_days
            model.work_cost += model.repair_cost
            model.repairs_completed += 1

        model.log_event(f"{self.unique_id} finished {task_type} on {unit.unique_id}")
        self.equipment_unit = None
        self.task_type = None
        self.work_remaining = 0.0
        self.travel_target = self.home
        self.state = "driving_home"


class FieldServiceModel(mesa.Model):
    """Mobile service crew model with failures, maintenance, and replacement."""

    def __init__(
        self,
        seed: int | None = None,
        equipment_count: int = 100,
        service_capacity: int = 3,
        daily_revenue_per_unit: float = 400.0,
        service_crew_cost_per_day: float = 1000.0,
        replacement_cost: float = 10000.0,
        repair_cost: float = 1000.0,
        maintenance_cost: float = 600.0,
        replace_old_equipment: bool = False,
        mtce_periods_to_replace: int = 5,
        replacement_mean_time: float = 12.0,
        maintenance_mean_time: float = 3.0,
        repair_typical_time: float = 5.0,
        probability_replacement_needed: float = 0.1,
        maintenance_period: float = 90.0,
        normal_failure_rate: float = 0.03,
        crew_speed: float = 75.0,
        field_width: float = DEFAULT_FIELD_WIDTH,
        field_height: float = DEFAULT_FIELD_HEIGHT,
    ) -> None:
        super().__init__(rng=seed)
        self.rng = random.Random(seed)
        self.service_capacity = int(service_capacity)
        self.daily_revenue_per_unit = float(daily_revenue_per_unit)
        self.service_crew_cost_per_day = float(service_crew_cost_per_day)
        self.replacement_cost = float(replacement_cost)
        self.repair_cost = float(repair_cost)
        self.maintenance_cost = float(maintenance_cost)
        self.replace_old_equipment = bool(replace_old_equipment)
        self.mtce_periods_to_replace = int(mtce_periods_to_replace)
        self.replacement_mean_time = float(replacement_mean_time)
        self.maintenance_mean_time = float(maintenance_mean_time)
        self.repair_typical_time = float(repair_typical_time)
        self.probability_replacement_needed = float(probability_replacement_needed)
        self.maintenance_period = float(maintenance_period)
        self.normal_failure_rate = float(normal_failure_rate)
        self.crew_speed = float(crew_speed)
        self.field_width = float(field_width)
        self.field_height = float(field_height)
        self.sim_time_days = 0.0
        self.revenue = 0.0
        self.work_cost = 0.0
        self.crew_cost = 0.0
        self.failures_observed = 0
        self.repairs_completed = 0
        self.maintenance_completed = 0
        self.replacements_completed = 0
        self.event_log: list[dict[str, float | str]] = []

        self.equipment = self._create_equipment(int(equipment_count))
        self.crews = [
            ServiceCrew(unique_id=f"crew-{index}", crew_speed=self.crew_speed)
            for index in range(self.service_capacity)
        ]
        self.service_requests: list[EquipmentUnit] = []
        self.maintenance_requests: list[EquipmentUnit] = []

    def _create_equipment(self, equipment_count: int) -> list[EquipmentUnit]:
        equipment: list[EquipmentUnit] = []
        cols = max(1, math.ceil(math.sqrt(equipment_count)))
        x_gap = (self.field_width - 150.0) / max(1, cols)
        y_gap = (self.field_height - 120.0) / max(1, math.ceil(equipment_count / cols))
        for index in range(equipment_count):
            col = index % cols
            row = index // cols
            jitter_x = self.rng.uniform(-8.0, 8.0)
            jitter_y = self.rng.uniform(-8.0, 8.0)
            x = 130.0 + (col + 0.5) * x_gap + jitter_x
            y = 50.0 + (row + 0.5) * y_gap + jitter_y
            equipment.append(
                EquipmentUnit(
                    unique_id=f"unit-{index}",
                    x=max(95.0, min(self.field_width - 20.0, x)),
                    y=max(25.0, min(self.field_height - 25.0, y)),
                    time_last_replacement=0.0,
                    time_last_maintenance=self.rng.uniform(-self.maintenance_period, 0.0),
                    replacement_mean_time=self.replacement_mean_time,
                    maintenance_mean_time=self.maintenance_mean_time,
                    repair_typical_time=self.repair_typical_time,
                    probability_replacement_needed=self.probability_replacement_needed,
                    maintenance_period=self.maintenance_period,
                    normal_failure_rate=self.normal_failure_rate,
                )
            )
        return equipment

    def log_event(self, message: str) -> None:
        self.event_log.append({"time": round(self.sim_time_days, 2), "message": message})
        if len(self.event_log) > 250:
            self.event_log = self.event_log[-250:]

    def request_service(self, unit: EquipmentUnit) -> None:
        if unit in self.maintenance_requests:
            self.maintenance_requests.remove(unit)
        if unit in self.service_requests or self._crew_handling(unit):
            return
        unit.state = "failed"
        unit.request_time = self.sim_time_days
        unit.maintenance_requested = False
        self.service_requests.append(unit)
        self.failures_observed += 1
        self.log_event(f"{unit.unique_id} failed and requested repair")

    def request_maintenance(self, unit: EquipmentUnit) -> None:
        if unit in self.service_requests or unit in self.maintenance_requests or self._crew_handling(unit):
            return
        unit.maintenance_requested = True
        unit.request_time = self.sim_time_days
        self.maintenance_requests.append(unit)
        self.log_event(f"{unit.unique_id} requested preventive maintenance")

    def there_are_requests(self) -> bool:
        return bool(self.service_requests or self.maintenance_requests)

    def get_request(self) -> tuple[EquipmentUnit, TaskType]:
        if self.service_requests:
            return self.service_requests.pop(0), "repair"
        return self.maintenance_requests.pop(0), "maintenance"

    def _crew_handling(self, unit: EquipmentUnit) -> bool:
        return any(crew.equipment_unit is unit for crew in self.crews)

    def _dispatch_idle_crews(self) -> None:
        for crew in self.crews:
            if crew.state != "idle" or not self.there_are_requests():
                continue
            unit, task_type = self.get_request()
            crew.assign(unit, task_type)
            self.log_event(f"{crew.unique_id} dispatched to {unit.unique_id} for {task_type}")

    def _update_equipment_requests(self) -> None:
        for unit in self.equipment:
            if unit.state != "working" or self._crew_handling(unit):
                continue
            if unit.maintenance_overdue(self.sim_time_days):
                self.request_maintenance(unit)
            if self.rng.random() < unit.daily_failure_probability(self.sim_time_days):
                self.request_service(unit)

    def step(self) -> None:
        working_units = sum(1 for unit in self.equipment if unit.state == "working")
        self.revenue += working_units * self.daily_revenue_per_unit
        self.crew_cost += len(self.crews) * self.service_crew_cost_per_day
        self._update_equipment_requests()
        self._dispatch_idle_crews()
        for crew in self.crews:
            crew.step(self)
        self._dispatch_idle_crews()
        self.sim_time_days += 1.0

    def snapshot(self) -> dict[str, float | int]:
        state_counts = {
            state: sum(1 for unit in self.equipment if unit.state == state)
            for state in ("working", "failed", "repair", "maintenance", "replacement")
        }
        busy_crews = sum(1 for crew in self.crews if crew.state in {"driving_to_work", "working"})
        return {
            "time_days": self.sim_time_days,
            "equipment_total": len(self.equipment),
            "working": state_counts["working"],
            "failed": state_counts["failed"],
            "repairing": state_counts["repair"],
            "maintenance": state_counts["maintenance"],
            "replacement": state_counts["replacement"],
            "service_queue": len(self.service_requests),
            "maintenance_queue": len(self.maintenance_requests),
            "busy_crews": busy_crews,
            "idle_crews": sum(1 for crew in self.crews if crew.state == "idle"),
            "revenue": self.revenue,
            "work_cost": self.work_cost,
            "crew_cost": self.crew_cost,
            "profit": self.revenue - self.work_cost - self.crew_cost,
            "failures_observed": self.failures_observed,
            "repairs_completed": self.repairs_completed,
            "maintenance_completed": self.maintenance_completed,
            "replacements_completed": self.replacements_completed,
        }

    def visualization_state(self) -> dict[str, list[dict[str, float | str | None]]]:
        return {
            "equipment": [
                {
                    "id": unit.unique_id,
                    "x": unit.x,
                    "y": unit.y,
                    "state": unit.state,
                    "age": round(unit.age(self.sim_time_days), 1),
                    "assigned_crew_id": unit.assigned_crew_id,
                    "maintenance_requested": str(unit.maintenance_requested).lower(),
                }
                for unit in self.equipment
            ],
            "crews": [
                {
                    "id": crew.unique_id,
                    "x": crew.x,
                    "y": crew.y,
                    "state": crew.state,
                    "task_type": crew.task_type or "",
                    "equipment_unit": crew.equipment_unit.unique_id if crew.equipment_unit else "",
                }
                for crew in self.crews
            ],
        }
