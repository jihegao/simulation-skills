from __future__ import annotations

import random

import simpy


class SparePartsInventoryModel:
    def __init__(
        self,
        *,
        demand_interval: float = 12.0,
        initial_stock: int = 40,
        reorder_point: int = 15,
        order_quantity: int = 40,
        lead_time: float = 72.0,
        monitor_interval: float = 24.0,
        seed: int | None = None,
    ) -> None:
        self.demand_interval = float(demand_interval)
        self.initial_stock = int(initial_stock)
        self.reorder_point = int(reorder_point)
        self.order_quantity = int(order_quantity)
        self.lead_time = float(lead_time)
        self.monitor_interval = float(monitor_interval)
        self.rng = random.Random(seed)
        self.env = simpy.Environment()
        self.stock = simpy.Container(self.env, capacity=max(1, self.initial_stock + self.order_quantity * 4), init=self.initial_stock)
        self.demands = 0
        self.filled_demands = 0
        self.stockouts = 0
        self.orders_placed = 0
        self.order_in_transit = False
        self.rows: list[dict] = []

    def run(self, until: float) -> list[dict]:
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
            if self.env.now < until:
                self.demands += 1
                if self.stock.level >= 1:
                    yield self.stock.get(1)
                    self.filled_demands += 1
                else:
                    self.stockouts += 1
                self._maybe_order()

    def _maybe_order(self) -> None:
        if self.order_in_transit:
            return
        if self.stock.level <= self.reorder_point:
            self.order_in_transit = True
            self.orders_placed += 1
            self.env.process(self._replenish())

    def _replenish(self):
        yield self.env.timeout(self.lead_time)
        room = self.stock.capacity - self.stock.level
        yield self.stock.put(min(self.order_quantity, room))
        self.order_in_transit = False
        self._maybe_order()

    def _monitor(self, until: float):
        while self.env.now < until:
            yield self.env.timeout(self.monitor_interval)
            self.rows.append(self._snapshot())

    def _snapshot(self, *, time: float | None = None) -> dict:
        service_level = self.filled_demands / self.demands if self.demands else 1.0
        return {
            "time": round(self.env.now if time is None else time, 3),
            "stock_level": round(self.stock.level, 3),
            "demands": self.demands,
            "filled_demands": self.filled_demands,
            "stockouts": self.stockouts,
            "orders_placed": self.orders_placed,
            "service_level": round(service_level, 4),
        }
