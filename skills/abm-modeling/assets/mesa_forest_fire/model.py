"""Mesa forest-fire example used by the abm-modeling skill."""

from __future__ import annotations

from mesa import Agent, Model
from mesa.space import MultiGrid


class TreeCell(Agent):
    def __init__(self, model: "ForestFireModel", condition: str = "fine"):
        super().__init__(model)
        self.condition = condition
        self.next_condition = condition

    def step(self) -> None:
        if self.condition == "burning":
            for neighbor in self.model.grid.iter_neighbors(self.pos, moore=True, include_center=False):
                if neighbor.condition == "fine":
                    neighbor.next_condition = "burning"
            self.next_condition = "burned"
        elif self.condition == "burned" and self.model.random.random() < self.model.regrowth_chance:
            self.next_condition = "fine"

    def advance(self) -> None:
        self.condition = self.next_condition


class ForestFireModel(Model):
    """Small Mesa model with explicit seeded randomness and snapshot metrics."""

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        density: float = 0.60,
        regrowth_chance: float = 0.0,
        seed: int | None = None,
    ):
        super().__init__(rng=seed)
        self.width = int(width)
        self.height = int(height)
        self.density = float(density)
        self.regrowth_chance = float(regrowth_chance)
        self.grid = MultiGrid(self.width, self.height, torus=False)
        self.initial_trees = 0

        for x in range(self.width):
            for y in range(self.height):
                if self.random.random() < self.density:
                    condition = "burning" if x == 0 else "fine"
                    tree = TreeCell(self, condition)
                    self.grid.place_agent(tree, (x, y))
                    self.initial_trees += 1

    def step(self) -> None:
        self.agents.shuffle_do("step")
        self.agents.do("advance")
        self.running = any(agent.condition == "burning" for agent in self.agents)

    def snapshot(self) -> dict:
        counts = {"fine": 0, "burning": 0, "burned": 0}
        for agent in self.agents:
            counts[agent.condition] += 1
        burned_fraction = counts["burned"] / self.initial_trees if self.initial_trees else 0.0
        return {
            "fine_trees": counts["fine"],
            "burning_trees": counts["burning"],
            "burned_trees": counts["burned"],
            "initial_trees": self.initial_trees,
            "burned_fraction": burned_fraction,
        }
