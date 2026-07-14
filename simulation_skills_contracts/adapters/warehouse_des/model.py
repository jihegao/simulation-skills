"""A narrow, seeded SimPy queue used by the warehouse continuity adapter."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random

import simpy


@dataclass(frozen=True)
class WarehouseQueueConfig:
    horizon: float
    mean_interarrival: float
    resource_capacity: int
    service_minimum: float
    service_mode: float
    service_maximum: float
    seed: int


@dataclass(frozen=True)
class WarehouseQueueResult:
    arrivals: int
    service_started: int
    completed_jobs: int
    waiting_at_horizon: int
    in_service_at_horizon: int
    average_wait: float


class WarehouseQueueModel:
    """Single-stage FIFO queue with exponential arrivals and triangular service."""

    def __init__(self, config: WarehouseQueueConfig) -> None:
        self.config = config
        self.environment = simpy.Environment()
        self.resource = simpy.Resource(
            self.environment, capacity=config.resource_capacity
        )
        self.arrival_rng = random.Random(_derived_seed(config.seed, "arrival"))
        self.service_rng = random.Random(_derived_seed(config.seed, "service"))
        self.arrivals = 0
        self.completed_jobs = 0
        self.waits: list[float] = []

    def run(self) -> WarehouseQueueResult:
        self.environment.process(self._arrival_source())
        # The horizon is exclusive: events scheduled exactly at the horizon are
        # not part of this Result Set.
        self.environment.run(until=self.config.horizon)
        return WarehouseQueueResult(
            arrivals=self.arrivals,
            service_started=len(self.waits),
            completed_jobs=self.completed_jobs,
            waiting_at_horizon=len(self.resource.queue),
            in_service_at_horizon=self.resource.count,
            average_wait=(sum(self.waits) / len(self.waits)) if self.waits else 0.0,
        )

    def _arrival_source(self):
        while True:
            delay = self.arrival_rng.expovariate(1.0 / self.config.mean_interarrival)
            if self.environment.now + delay >= self.config.horizon:
                return
            yield self.environment.timeout(delay)
            self.arrivals += 1
            self.environment.process(self._serve_job(self.environment.now))

    def _serve_job(self, arrival_time: float):
        with self.resource.request() as request:
            yield request
            self.waits.append(self.environment.now - arrival_time)
            duration = self.service_rng.triangular(
                self.config.service_minimum,
                self.config.service_maximum,
                self.config.service_mode,
            )
            yield self.environment.timeout(duration)
            self.completed_jobs += 1


def _derived_seed(seed: int, stream: str) -> int:
    raw = hashlib.sha256(f"warehouse-des-v0.1:{seed}:{stream}".encode("utf-8")).digest()
    return int.from_bytes(raw[:8], "big", signed=False)
