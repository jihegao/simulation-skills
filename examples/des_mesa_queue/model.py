"""SimPy discrete-event queue wrapped as a Mesa model for visualization.

The DES event calendar and resource contention live in SimPy. Mesa provides the
model contract, snapshots, and an inspection-friendly state surface for Solara.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean
from typing import Literal

import mesa
import simpy


JobStatus = Literal["waiting", "in_service", "completed", "abandoned"]


@dataclass
class ServiceJob:
    unique_id: str
    arrival_time: float
    status: JobStatus = "waiting"
    service_start_time: float | None = None
    service_end_time: float | None = None
    server_id: str | None = None
    patience_deadline: float | None = None
    service_minutes: float = 0.0

    def wait_minutes(self, now: float) -> float:
        end = self.service_start_time if self.service_start_time is not None else now
        return max(0.0, end - self.arrival_time)


@dataclass
class ServiceServer:
    unique_id: str
    busy: bool = False
    job_id: str | None = None
    busy_until: float = 0.0
    total_busy_minutes: float = 0.0
    jobs_completed: int = 0

    def remaining_minutes(self, now: float) -> float:
        return max(0.0, self.busy_until - now) if self.busy else 0.0


class CustomerServiceDesMesaModel(mesa.Model):
    """M/M/c style customer-service DES with balk-free abandonment patience."""

    model_time_unit = "minute"

    def __init__(
        self,
        seed: int | None = None,
        server_count: int = 2,
        arrival_rate_per_hour: float = 10.0,
        mean_service_minutes: float = 8.0,
        patience_minutes: float = 20.0,
        step_minutes: float = 1.0,
        max_arrivals: int = 500,
    ) -> None:
        super().__init__(rng=seed)
        self.rng = random.Random(seed)
        self.server_count = int(server_count)
        self.arrival_rate_per_hour = float(arrival_rate_per_hour)
        self.mean_service_minutes = float(mean_service_minutes)
        self.patience_minutes = float(patience_minutes)
        self.step_minutes = float(step_minutes)
        self.max_arrivals = int(max_arrivals)

        self.env = simpy.Environment()
        self.resource = simpy.Resource(self.env, capacity=self.server_count)
        self.servers = [ServiceServer(unique_id=f"server-{index + 1}") for index in range(self.server_count)]
        self.jobs: list[ServiceJob] = []
        self.event_log: list[dict[str, float | str]] = []
        self.steps = 0
        self.generated_jobs = 0
        self.env.process(self._arrival_source())

    @property
    def sim_time_minutes(self) -> float:
        return float(self.env.now)

    def log_event(self, message: str) -> None:
        self.event_log.append({"time_minutes": round(self.sim_time_minutes, 2), "message": message})
        if len(self.event_log) > 100:
            self.event_log = self.event_log[-100:]

    def _arrival_source(self):
        arrival_rate_per_minute = max(0.0001, self.arrival_rate_per_hour / 60.0)
        while self.generated_jobs < self.max_arrivals:
            yield self.env.timeout(self.rng.expovariate(arrival_rate_per_minute))
            job = ServiceJob(
                unique_id=f"job-{self.generated_jobs + 1}",
                arrival_time=self.sim_time_minutes,
                patience_deadline=self.sim_time_minutes + self.patience_minutes,
            )
            self.generated_jobs += 1
            self.jobs.append(job)
            self.log_event(f"{job.unique_id} arrived")
            self.env.process(self._serve_job(job))

    def _serve_job(self, job: ServiceJob):
        with self.resource.request() as request:
            patience = self.env.timeout(max(0.0, self.patience_minutes))
            result = yield request | patience
            if request not in result:
                job.status = "abandoned"
                self.log_event(f"{job.unique_id} abandoned after waiting")
                return

            server = self._claim_server(job)
            service_time = self.rng.expovariate(1.0 / max(0.0001, self.mean_service_minutes))
            job.status = "in_service"
            job.service_start_time = self.sim_time_minutes
            job.service_minutes = service_time
            server.busy = True
            server.job_id = job.unique_id
            server.busy_until = self.sim_time_minutes + service_time
            self.log_event(f"{job.unique_id} started on {server.unique_id}")

            yield self.env.timeout(service_time)

            job.status = "completed"
            job.service_end_time = self.sim_time_minutes
            server.busy = False
            server.job_id = None
            server.busy_until = self.sim_time_minutes
            server.total_busy_minutes += service_time
            server.jobs_completed += 1
            self.log_event(f"{job.unique_id} completed on {server.unique_id}")

    def _claim_server(self, job: ServiceJob) -> ServiceServer:
        for server in self.servers:
            if not server.busy:
                job.server_id = server.unique_id
                return server
        fallback = min(self.servers, key=lambda item: item.remaining_minutes(self.sim_time_minutes))
        job.server_id = fallback.unique_id
        return fallback

    def step(self) -> None:
        self.env.run(until=self.sim_time_minutes + self.step_minutes)
        self.steps += 1

    def waiting_jobs(self) -> list[ServiceJob]:
        return [job for job in self.jobs if job.status == "waiting"]

    def in_service_jobs(self) -> list[ServiceJob]:
        return [job for job in self.jobs if job.status == "in_service"]

    def completed_jobs(self) -> list[ServiceJob]:
        return [job for job in self.jobs if job.status == "completed"]

    def abandoned_jobs(self) -> list[ServiceJob]:
        return [job for job in self.jobs if job.status == "abandoned"]

    def snapshot(self) -> dict[str, float | int]:
        now = max(0.0001, self.sim_time_minutes)
        completed = self.completed_jobs()
        abandoned = self.abandoned_jobs()
        waiting = self.waiting_jobs()
        service_starts = [job for job in self.jobs if job.service_start_time is not None]
        waits = [job.wait_minutes(now) for job in service_starts]
        system_times = [
            (job.service_end_time - job.arrival_time)
            for job in completed
            if job.service_end_time is not None
        ]
        total_busy = sum(server.total_busy_minutes for server in self.servers)
        return {
            "time_minutes": round(self.sim_time_minutes, 3),
            "arrivals": self.generated_jobs,
            "waiting": len(waiting),
            "in_service": len(self.in_service_jobs()),
            "completed": len(completed),
            "abandoned": len(abandoned),
            "avg_wait_minutes": round(mean(waits), 3) if waits else 0.0,
            "avg_system_minutes": round(mean(system_times), 3) if system_times else 0.0,
            "throughput_per_hour": round(len(completed) / now * 60.0, 3),
            "abandonment_rate": round(len(abandoned) / max(1, self.generated_jobs), 3),
            "server_utilization": round(total_busy / (self.server_count * now), 3),
        }

    def visualization_state(self) -> dict[str, object]:
        now = self.sim_time_minutes
        return {
            "time_minutes": round(now, 2),
            "servers": [
                {
                    "id": server.unique_id,
                    "busy": server.busy,
                    "job_id": server.job_id,
                    "remaining_minutes": round(server.remaining_minutes(now), 2),
                    "jobs_completed": server.jobs_completed,
                }
                for server in self.servers
            ],
            "waiting_jobs": [
                {
                    "id": job.unique_id,
                    "wait_minutes": round(job.wait_minutes(now), 2),
                    "patience_remaining": round(max(0.0, (job.patience_deadline or now) - now), 2),
                }
                for job in self.waiting_jobs()[:24]
            ],
            "recent_completed": [
                {
                    "id": job.unique_id,
                    "server_id": job.server_id,
                    "system_minutes": round((job.service_end_time or now) - job.arrival_time, 2),
                }
                for job in self.completed_jobs()[-12:]
            ],
            "events": list(self.event_log[-12:]),
        }

