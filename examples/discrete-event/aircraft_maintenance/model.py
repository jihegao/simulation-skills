"""Aircraft maintenance and mission turnaround SimPy model."""

from __future__ import annotations

import random
import statistics
from typing import Any, Dict, List

import simpy


class AircraftMaintenanceModel:
    """Airframe task model with maintenance bays, crews, support equipment, and parts inventory.

    Each aircraft task:
    - waits in queues for maintenance bay, technician, and special equipment
    - waits for available spare parts (Container)
    - consumes repair time and resources

    The model returns event rows with metric fields for downstream batch summaries.
    """

    def __init__(
        self,
        *,
        seed: int = 42,
        sample_interval: float = 2.0,
        arrival_mean: float = 12.0,
        service_time_mean: float = 18.0,
        parts_per_task_mean: float = 1.5,
        maintenance_bays: int = 2,
        technicians: int = 3,
        support_equipments: int = 2,
        initial_parts: int = 18,
        parts_capacity: int = 60,
        parts_reorder_point: int = 8,
        parts_reorder_qty: int = 20,
        parts_lead_time_mean: float = 14.0,
    ) -> None:
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.sample_interval = float(sample_interval)

        self.arrival_mean = float(arrival_mean)
        self.service_time_mean = float(service_time_mean)
        self.parts_per_task_mean = float(parts_per_task_mean)
        self.maintenance_bays = int(maintenance_bays)
        self.technicians = int(technicians)
        self.support_equipments = int(support_equipments)

        self.initial_parts = int(initial_parts)
        self.parts_capacity = int(parts_capacity)
        self.parts_reorder_point = int(parts_reorder_point)
        self.parts_reorder_qty = int(parts_reorder_qty)
        self.parts_lead_time_mean = float(parts_lead_time_mean)
        if self.parts_capacity < self.initial_parts:
            self.parts_capacity = self.initial_parts + self.parts_reorder_qty

        self.env = simpy.Environment()
        self.bays = simpy.Resource(self.env, capacity=self.maintenance_bays)
        self.crew = simpy.Resource(self.env, capacity=self.technicians)
        self.equipment = simpy.Resource(self.env, capacity=self.support_equipments)
        self.parts = simpy.Container(
            self.env,
            init=self.initial_parts,
            capacity=self.parts_capacity,
        )

        self.rows: List[Dict[str, Any]] = []
        self._task_rows: List[Dict[str, Any]] = []

        self.completed_tasks = 0
        self.total_parts_used = 0
        self.part_shortage_events = 0
        self.part_shortage_wait_total = 0.0
        self.reorder_orders = 0
        self._pending_reorder = False

        self.arrivals = 0
        self._last_arrival = None

    def _draw_interarrival(self) -> float:
        return self.rng.expovariate(1.0 / max(0.5, self.arrival_mean))

    def _draw_service_time(self) -> float:
        shape = 1.6
        scale = max(0.1, self.service_time_mean / shape)
        return max(0.5, self.rng.gammavariate(shape, scale))

    def _draw_parts_needed(self) -> int:
        demand = self.rng.expovariate(1.0 / max(0.5, self.parts_per_task_mean))
        return max(1, int(round(demand)))

    def _draw_lead_time(self) -> float:
        return max(1.0, self.rng.expovariate(1.0 / max(0.5, self.parts_lead_time_mean)))

    def _record_sample(self) -> None:
        self.rows.append(
            {
                "time": round(self.env.now, 3),
                "kind": 2,
                "sample_bay_queue": len(self.bays.queue),
                "sample_crew_queue": len(self.crew.queue),
                "sample_equip_queue": len(self.equipment.queue),
                "sample_bay_util": self.bays.count / max(1, self.bays.capacity),
                "sample_crew_util": self.crew.count / max(1, self.crew.capacity),
                "sample_equip_util": self.equipment.count / max(1, self.equipment.capacity),
                "sample_parts": self.parts.level,
                "sample_completed": self.completed_tasks,
            }
        )

    def _inventory_manager(self) -> simpy.events.Process:
        while True:
            if self.parts.level <= self.parts_reorder_point and not self._pending_reorder:
                self._pending_reorder = True
                self.reorder_orders += 1
                self.rows.append(
                    {
                        "time": round(self.env.now, 3),
                        "kind": 4,
                        "order": self.reorder_orders,
                        "order_trigger_parts": round(self.parts.level, 3),
                        "order_qty": self.parts_reorder_qty,
                    }
                )
                yield self.env.timeout(self._draw_lead_time())
                yield self.parts.put(self.parts_reorder_qty)
                self._pending_reorder = False
                self.rows.append(
                    {
                        "time": round(self.env.now, 3),
                        "kind": 4,
                        "order": self.reorder_orders,
                        "parts_received": self.parts_reorder_qty,
                    }
                )
            else:
                # polling cadence keeps model simple and stable under finite horizon
                yield self.env.timeout(1.0)

    def _aircraft_task(self, aircraft_id: int) -> None:
        arrival_time = self.env.now
        self.arrivals += 1
        with (
            self.bays.request() as bay_req,
            self.crew.request() as crew_req,
            self.equipment.request() as equip_req,
        ):
            queue_len_pre = len(self.bays.queue) + len(self.crew.queue) + len(self.equipment.queue)
            t_req_start = self.env.now
            yield bay_req & crew_req & equip_req
            queue_wait = self.env.now - t_req_start

            parts_needed = self._draw_parts_needed()
            self.total_parts_used += parts_needed
            need_wait = 0.0
            if self.parts.level < parts_needed:
                part_start_wait = self.env.now
                self.part_shortage_events += 1
                yield self.parts.get(parts_needed)
                need_wait = self.env.now - part_start_wait
            else:
                yield self.parts.get(parts_needed)

            self.part_shortage_wait_total += need_wait
            service_time = self._draw_service_time()
            yield self.env.timeout(service_time)

            total_time = self.env.now - arrival_time
            self.completed_tasks += 1

            row = {
                "time": round(self.env.now, 3),
                "kind": 1,
                "aircraft_id": aircraft_id,
                "queue_wait": round(queue_wait, 3),
                "service_time": round(service_time, 3),
                "parts_wait": round(need_wait, 3),
                "task_time": round(total_time, 3),
                "parts_needed": int(parts_needed),
                "queue_len_pre": int(queue_len_pre),
                "bay_used": self.bays.count,
                "crew_used": self.crew.count,
                "equip_used": self.equipment.count,
                "parts_after": round(self.parts.level, 3),
                "order_backlog": int(self.part_shortage_events),
            }
            self.rows.append(row)
            self._task_rows.append(row)

    def _arrival_process(self) -> simpy.events.Process:
        aircraft_id = 0
        while True:
            yield self.env.timeout(self._draw_interarrival())
            aircraft_id += 1
            self.env.process(self._aircraft_task(aircraft_id))

    def run(self, until: float) -> List[Dict[str, Any]]:
        horizon = float(until)
        self.env.process(self._arrival_process())
        self.env.process(self._inventory_manager())
        self.env.process(self._sampler())
        self.env.run(until=horizon)

        self.rows.extend(self._summary_rows(horizon))
        return self.rows

    def _sampler(self) -> simpy.events.Process:
        while True:
            self._record_sample()
            yield self.env.timeout(self.sample_interval)

    def _summary_rows(self, until: float) -> List[Dict[str, Any]]:
        if self._task_rows:
            waits = [r["queue_wait"] for r in self._task_rows]
            service = [r["service_time"] for r in self._task_rows]
            task_times = [r["task_time"] for r in self._task_rows]
            parts_wait = [r["parts_wait"] for r in self._task_rows]
            p95_wait = statistics.quantiles(waits, n=20)[18] if len(waits) >= 2 else waits[0]
            avg_wait = statistics.mean(waits)
            avg_service = statistics.mean(service)
            avg_task_time = statistics.mean(task_times)
            avg_parts_wait = statistics.mean(parts_wait)
        else:
            p95_wait = 0.0
            avg_wait = 0.0
            avg_service = 0.0
            avg_task_time = 0.0
            avg_parts_wait = 0.0

        sample_rows = [r for r in self.rows if r.get("kind") == 2]
        if sample_rows:
            avg_bay_q = statistics.mean(r["sample_bay_queue"] for r in sample_rows)
            avg_crew_q = statistics.mean(r["sample_crew_queue"] for r in sample_rows)
            avg_equip_q = statistics.mean(r["sample_equip_queue"] for r in sample_rows)
            avg_bay_util = statistics.mean(r["sample_bay_util"] for r in sample_rows)
            avg_crew_util = statistics.mean(r["sample_crew_util"] for r in sample_rows)
            avg_equip_util = statistics.mean(r["sample_equip_util"] for r in sample_rows)
        else:
            avg_bay_q = avg_crew_q = avg_equip_q = 0.0
            avg_bay_util = avg_crew_util = avg_equip_util = 0.0

        return [
            {
                "time": round(until, 3),
                "kind": 3,
                "summary_completed": self.completed_tasks,
                "summary_seed": self.seed,
                "summary_mean_queue_wait": round(avg_wait, 3),
                "summary_p95_queue_wait": round(p95_wait, 3),
                "summary_mean_service": round(avg_service, 3),
                "summary_mean_parts_wait": round(avg_parts_wait, 3),
                "summary_mean_task_time": round(avg_task_time, 3),
                "summary_avg_bay_q": round(avg_bay_q, 3),
                "summary_avg_crew_q": round(avg_crew_q, 3),
                "summary_avg_equip_q": round(avg_equip_q, 3),
                "summary_avg_bay_util": round(avg_bay_util, 3),
                "summary_avg_crew_util": round(avg_crew_util, 3),
                "summary_avg_equip_util": round(avg_equip_util, 3),
                "summary_parts_consumed": self.total_parts_used,
                "summary_reorders": self.reorder_orders,
                "summary_shortage_events": self.part_shortage_events,
                "summary_shortage_wait": round(self.part_shortage_wait_total, 3),
                "summary_parts_level_end": round(self.parts.level, 3),
            }
        ]
