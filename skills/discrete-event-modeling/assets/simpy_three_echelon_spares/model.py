from __future__ import annotations

import random
from typing import Optional

import simpy


class ThreeEchelonSparesModel:
    def __init__(
        self,
        *,
        demand_interval: float = 24.0,
        base_initial_stock: int = 10,
        relay_initial_stock: int = 1,
        local_initial_stock: int = 1,
        relay_target_stock: int = 1,
        local_target_stock: int = 1,
        relay_to_local_time: float = 10.0,
        base_to_relay_time: float = 48.0,
        monitor_interval: float = 24.0,
        seed: Optional[int] = None,
    ) -> None:
        self.demand_interval = float(demand_interval)
        self.base_initial_stock = int(base_initial_stock)
        self.relay_initial_stock = int(relay_initial_stock)
        self.local_initial_stock = int(local_initial_stock)
        self.relay_target_stock = int(relay_target_stock)
        self.local_target_stock = int(local_target_stock)
        self.relay_to_local_time = float(relay_to_local_time)
        self.base_to_relay_time = float(base_to_relay_time)
        self.monitor_interval = float(monitor_interval)
        self.rng = random.Random(seed)
        self.env = simpy.Environment()

        self.base_stock = self.base_initial_stock
        self.relay_stock = self.relay_initial_stock
        self.local_stock = self.local_initial_stock
        self.base_to_relay_in_transit = 0
        self.relay_to_local_in_transit = 0
        self.pending_relay_requests = 0
        self.pending_local_requests = 0

        self.demands = 0
        self.filled_demands = 0
        self.stockouts = 0
        self.replenishments_base_to_relay = 0
        self.replenishments_relay_to_local = 0
        self.arrivals_base_to_relay = 0
        self.arrivals_relay_to_local = 0
        self.rows: list[dict] = []
        self.relay_stock_changed = self.env.event()

    def run(self, until: float) -> list[dict]:
        self._ensure_local_pipeline()
        self._ensure_relay_pipeline()
        self.env.process(self._demand_process(until))
        self.env.process(self._monitor(until))
        self.rows.append(self._snapshot())
        self.env.run(until=until)
        if not self.rows or self.rows[-1]["time"] < until:
            self.rows.append(self._snapshot(time=until))
        return self.rows

    def _demand_process(self, until: float):
        while self.env.now < until:
            yield self.env.timeout(self.rng.expovariate(1.0 / self.demand_interval))
            if self.env.now >= until:
                return

            self.demands += 1
            if self.local_stock >= 1:
                self.local_stock -= 1
                self.filled_demands += 1
            else:
                self.stockouts += 1

            self._ensure_local_pipeline()

    def _ensure_local_pipeline(self) -> None:
        local_position = self.local_stock + self.relay_to_local_in_transit + self.pending_local_requests
        while local_position < self.local_target_stock:
            self.pending_local_requests += 1
            local_position += 1
            self.env.process(self._ship_relay_to_local())

    def _ship_relay_to_local(self):
        while self.relay_stock <= 0:
            yield self.relay_stock_changed

        self.pending_local_requests -= 1
        self.relay_stock -= 1
        self.relay_to_local_in_transit += 1
        self.replenishments_relay_to_local += 1
        self._ensure_relay_pipeline()

        yield self.env.timeout(self.relay_to_local_time)
        self.relay_to_local_in_transit -= 1
        self.local_stock += 1
        self.arrivals_relay_to_local += 1

    def _ensure_relay_pipeline(self) -> None:
        relay_position = self.relay_stock + self.base_to_relay_in_transit + self.pending_relay_requests
        while relay_position < self.relay_target_stock and self.base_stock > 0:
            self.pending_relay_requests += 1
            relay_position += 1
            self.env.process(self._ship_base_to_relay())

    def _ship_base_to_relay(self):
        self.pending_relay_requests -= 1
        self.base_stock -= 1
        self.base_to_relay_in_transit += 1
        self.replenishments_base_to_relay += 1

        yield self.env.timeout(self.base_to_relay_time)
        self.base_to_relay_in_transit -= 1
        self.relay_stock += 1
        self.arrivals_base_to_relay += 1
        self._wake_relay_waiters()
        self._ensure_local_pipeline()
        self._ensure_relay_pipeline()

    def _wake_relay_waiters(self) -> None:
        old_event = self.relay_stock_changed
        if not old_event.triggered:
            old_event.succeed()
        self.relay_stock_changed = self.env.event()

    def _monitor(self, until: float):
        while self.env.now < until:
            yield self.env.timeout(self.monitor_interval)
            self.rows.append(self._snapshot())

    def _snapshot(self, *, time: Optional[float] = None) -> dict:
        service_level = self.filled_demands / self.demands if self.demands else 1.0
        return {
            "time": round(self.env.now if time is None else time, 3),
            "base_stock": self.base_stock,
            "relay_stock": self.relay_stock,
            "local_stock": self.local_stock,
            "base_to_relay_in_transit": self.base_to_relay_in_transit,
            "relay_to_local_in_transit": self.relay_to_local_in_transit,
            "pending_relay_requests": self.pending_relay_requests,
            "pending_local_requests": self.pending_local_requests,
            "demands": self.demands,
            "filled_demands": self.filled_demands,
            "stockouts": self.stockouts,
            "replenishments_base_to_relay": self.replenishments_base_to_relay,
            "replenishments_relay_to_local": self.replenishments_relay_to_local,
            "arrivals_base_to_relay": self.arrivals_base_to_relay,
            "arrivals_relay_to_local": self.arrivals_relay_to_local,
            "service_level": round(service_level, 4),
        }
