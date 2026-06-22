"""Mesa traffic model for a toroidal signalized four-way intersection."""

from __future__ import annotations

import statistics

from mesa import Agent, Model


class IntersectionCarAgent(Agent):
    """A car that moves either eastward or southward on a toroidal cross road."""

    def __init__(self, model: "IntersectionTrafficModel", x: int, y: int, direction: str):
        super().__init__(model)
        self.x = int(x)
        self.y = int(y)
        self.direction = direction
        self.moved_last_step = 0

    @property
    def cell(self) -> tuple[int, int]:
        return (self.x, self.y)

    def target(self) -> tuple[int, int]:
        if self.direction == "east":
            return ((self.x + 1) % self.model.grid_size, self.y)
        if self.direction == "south":
            return (self.x, (self.y + 1) % self.model.grid_size)
        raise ValueError(f"unknown direction: {self.direction}")

    def would_enter_intersection(self) -> bool:
        return self.target() == (self.model.center, self.model.center) and self.cell != self.target()


class IntersectionTrafficModel(Model):
    """Cross-road traffic with wraparound boundaries and fixed-cycle traffic lights."""

    def __init__(
        self,
        grid_size: int = 31,
        horizontal_cars: int = 10,
        vertical_cars: int = 10,
        green_duration: int = 12,
        yellow_duration: int = 0,
        random_slowdown: float = 0.0,
        seed: int | None = None,
    ):
        super().__init__(rng=seed)
        self.grid_size = int(grid_size)
        self.center = self.grid_size // 2
        self.horizontal_cars = int(horizontal_cars)
        self.vertical_cars = int(vertical_cars)
        self.green_duration = int(green_duration)
        self.yellow_duration = int(yellow_duration)
        self.random_slowdown = float(random_slowdown)
        self.steps_run = 0
        self.last_moves = 0
        self.last_light_state: tuple[bool, bool, int, int] | None = None

        if self.grid_size < 5 or self.grid_size % 2 == 0:
            raise ValueError("grid_size must be an odd integer >= 5")
        if self.green_duration < 1:
            raise ValueError("green_duration must be at least 1")
        if self.yellow_duration < 0:
            raise ValueError("yellow_duration must be non-negative")
        if not 0.0 <= self.random_slowdown <= 1.0:
            raise ValueError("random_slowdown must be between 0 and 1")

        max_lane_cars = self.grid_size - 1
        if not 0 <= self.horizontal_cars <= max_lane_cars:
            raise ValueError(f"horizontal_cars must be between 0 and {max_lane_cars}")
        if not 0 <= self.vertical_cars <= max_lane_cars:
            raise ValueError(f"vertical_cars must be between 0 and {max_lane_cars}")

        for x in self._lane_positions(self.horizontal_cars):
            IntersectionCarAgent(self, x=x, y=self.center, direction="east")
        for y in self._lane_positions(self.vertical_cars):
            IntersectionCarAgent(self, x=self.center, y=y, direction="south")
        self.last_light_state = self.light_state()

    def _lane_positions(self, count: int) -> list[int]:
        if count == 0:
            return []
        lane_cells = [cell for cell in range(self.grid_size) if cell != self.center]
        spacing = len(lane_cells) / count
        positions = []
        for index in range(count):
            positions.append(lane_cells[int(index * spacing)])
        return sorted(set(positions))

    def light_state(self) -> tuple[bool, bool, int, int]:
        cycle = 2 * (self.green_duration + self.yellow_duration)
        phase_step = self.steps_run % cycle
        if phase_step < self.green_duration:
            return True, False, 0, phase_step
        if phase_step < self.green_duration + self.yellow_duration:
            return False, False, 0, phase_step
        if phase_step < (2 * self.green_duration) + self.yellow_duration:
            return False, True, 1, phase_step
        return False, False, 1, phase_step

    def can_enter_intersection(self, car: IntersectionCarAgent) -> bool:
        horizontal_green, vertical_green, _, _ = self.light_state()
        if car.direction == "east":
            return horizontal_green
        if car.direction == "south":
            return vertical_green
        return False

    def step(self) -> None:
        self.last_light_state = self.light_state()
        occupied = {car.cell for car in self.agents}
        planned: list[tuple[IntersectionCarAgent, tuple[int, int]]] = []
        reserved: set[tuple[int, int]] = set()

        for car in sorted(self.agents, key=lambda item: (item.direction, item.y, item.x)):
            car.moved_last_step = 0
            target = car.target()
            if target in occupied or target in reserved:
                planned.append((car, car.cell))
                reserved.add(car.cell)
                continue
            if car.would_enter_intersection() and not self.can_enter_intersection(car):
                planned.append((car, car.cell))
                reserved.add(car.cell)
                continue
            if self.random_slowdown and self.random.random() < self.random_slowdown:
                planned.append((car, car.cell))
                reserved.add(car.cell)
                continue
            planned.append((car, target))
            reserved.add(target)

        self.last_moves = 0
        for car, target in planned:
            if target != car.cell:
                car.x, car.y = target
                car.moved_last_step = 1
                self.last_moves += 1
        self.steps_run += 1

    def snapshot(self) -> dict:
        cars = list(self.agents)
        vehicle_count = len(cars)
        moves = [car.moved_last_step for car in cars]
        horizontal_green, vertical_green, light_phase, phase_step = self.last_light_state or self.light_state()
        horizontal_queue = sum(
            1
            for car in cars
            if car.direction == "east" and car.y == self.center and 0 <= (self.center - car.x) % self.grid_size <= 3
        )
        vertical_queue = sum(
            1
            for car in cars
            if car.direction == "south" and car.x == self.center and 0 <= (self.center - car.y) % self.grid_size <= 3
        )
        return {
            "grid_size": self.grid_size,
            "vehicle_count": vehicle_count,
            "horizontal_count": sum(1 for car in cars if car.direction == "east"),
            "vertical_count": sum(1 for car in cars if car.direction == "south"),
            "average_speed": statistics.fmean(moves) if moves else 0.0,
            "stopped_fraction": 1.0 - (self.last_moves / vehicle_count if vehicle_count else 0.0),
            "flow": self.last_moves / (2 * self.grid_size),
            "horizontal_queue": horizontal_queue,
            "vertical_queue": vertical_queue,
            "horizontal_green": int(horizontal_green),
            "vertical_green": int(vertical_green),
            "light_phase": light_phase,
            "phase_step": phase_step,
        }


TrafficJamModel = IntersectionTrafficModel
