"""Seeded multi-asset failure, maintenance queue, and repair model."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random

import simpy


@dataclass(frozen=True)
class EquipmentMaintenanceConfig:
    horizon: float
    asset_count: int
    mean_time_between_failures: float
    maintenance_capacity: int
    repair_minimum: float
    repair_mode: float
    repair_maximum: float
    seed: int


@dataclass(frozen=True)
class EquipmentMaintenanceResult:
    failures: int
    repair_started: int
    repairs_completed: int
    waiting_at_horizon: int
    in_repair_at_horizon: int
    unplanned_downtime: float
    availability: float


class EquipmentMaintenanceModel:
    """Independent assets compete for one FIFO maintenance resource."""

    def __init__(self, config: EquipmentMaintenanceConfig) -> None:
        self.config = config
        self.environment = simpy.Environment()
        self.maintenance = simpy.Resource(
            self.environment, capacity=config.maintenance_capacity
        )
        self.failure_rngs = [
            random.Random(_derived_seed(config.seed, f"failure:{asset_id}"))
            for asset_id in range(config.asset_count)
        ]
        self.repair_rngs = [
            random.Random(_derived_seed(config.seed, f"repair:{asset_id}"))
            for asset_id in range(config.asset_count)
        ]
        self.failures = 0
        self.repair_started = 0
        self.repairs_completed = 0
        self.completed_downtime = 0.0
        self.active_failures: dict[int, float] = {}

    def run(self) -> EquipmentMaintenanceResult:
        for asset_id in range(self.config.asset_count):
            self.environment.process(self._asset_lifecycle(asset_id))
        # The horizon is exclusive: events scheduled exactly at the horizon do
        # not alter this Result Set.
        self.environment.run(until=self.config.horizon)
        unfinished_downtime = sum(
            self.config.horizon - failure_time
            for failure_time in self.active_failures.values()
        )
        unplanned_downtime = self.completed_downtime + unfinished_downtime
        exposure = self.config.asset_count * self.config.horizon
        availability = max(0.0, min(1.0, 1.0 - unplanned_downtime / exposure))
        return EquipmentMaintenanceResult(
            failures=self.failures,
            repair_started=self.repair_started,
            repairs_completed=self.repairs_completed,
            waiting_at_horizon=len(self.maintenance.queue),
            in_repair_at_horizon=self.maintenance.count,
            unplanned_downtime=unplanned_downtime,
            availability=availability,
        )

    def _asset_lifecycle(self, asset_id: int):
        failure_rng = self.failure_rngs[asset_id]
        repair_rng = self.repair_rngs[asset_id]
        while True:
            operating_time = failure_rng.expovariate(
                1.0 / self.config.mean_time_between_failures
            )
            if self.environment.now + operating_time >= self.config.horizon:
                return
            yield self.environment.timeout(operating_time)
            failure_time = self.environment.now
            self.failures += 1
            self.active_failures[asset_id] = failure_time
            with self.maintenance.request() as request:
                yield request
                self.repair_started += 1
                duration = repair_rng.triangular(
                    self.config.repair_minimum,
                    self.config.repair_maximum,
                    self.config.repair_mode,
                )
                yield self.environment.timeout(duration)
                self.repairs_completed += 1
                self.completed_downtime += self.environment.now - failure_time
                del self.active_failures[asset_id]


def _derived_seed(seed: int, stream: str) -> int:
    raw = hashlib.sha256(
        f"equipment-maintenance-v0.1:{seed}:{stream}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:8], "big", signed=False)
