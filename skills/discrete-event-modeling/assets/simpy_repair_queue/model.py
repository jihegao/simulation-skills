from __future__ import annotations

import random

import simpy


class RepairQueueModel:
    def __init__(
        self,
        *,
        arrival_interval: float = 18.0,
        repair_time_mean: float = 45.0,
        repair_time_sigma: float = 9.0,
        repairers: int = 1,
        monitor_interval: float = 60.0,
        seed: int | None = None,
    ) -> None:
        self.arrival_interval = float(arrival_interval)
        self.repair_time_mean = float(repair_time_mean)
        self.repair_time_sigma = float(repair_time_sigma)
        self.repairers = int(repairers)
        self.monitor_interval = float(monitor_interval)
        self.rng = random.Random(seed)
        self.env = simpy.Environment()
        self.crew = simpy.Resource(self.env, capacity=self.repairers)
        self.arrivals = 0
        self.completed_repairs = 0
        self.waits: list[float] = []
        self.busy_time = 0.0
        self.rows: list[dict] = []

    def run(self, until: float) -> list[dict]:
        self.env.process(self._arrival_process(until))
        self.env.process(self._monitor(until))
        self.rows.append(self._snapshot())
        self.env.run(until=until)
        if not self.rows or self.rows[-1]["time"] < until:
            self.rows.append(self._snapshot(time=until))
        return self.rows

    def _arrival_process(self, until: float):
        while self.env.now < until:
            delay = self.rng.expovariate(1.0 / self.arrival_interval)
            yield self.env.timeout(delay)
            if self.env.now < until:
                self.arrivals += 1
                self.env.process(self._repair_job())

    def _repair_job(self):
        arrival_time = self.env.now
        with self.crew.request() as request:
            yield request
            self.waits.append(self.env.now - arrival_time)
            repair_time = max(0.1, self.rng.gauss(self.repair_time_mean, self.repair_time_sigma))
            self.busy_time += repair_time
            yield self.env.timeout(repair_time)
            self.completed_repairs += 1

    def _monitor(self, until: float):
        while self.env.now < until:
            yield self.env.timeout(self.monitor_interval)
            self.rows.append(self._snapshot())

    def _snapshot(self, *, time: float | None = None) -> dict:
        now = self.env.now if time is None else time
        average_wait = sum(self.waits) / len(self.waits) if self.waits else 0.0
        utilization = min(1.0, self.busy_time / max(1.0, now * self.repairers))
        return {
            "time": round(now, 3),
            "arrivals": self.arrivals,
            "completed_repairs": self.completed_repairs,
            "queue_depth": len(self.crew.queue),
            "average_wait": round(average_wait, 3),
            "repairer_utilization": round(utilization, 4),
        }
