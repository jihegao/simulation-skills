"""Mesa reproduction of the local AnyLogic Air Defense System example.

This is a behavioral reimplementation, not an AnyLogic runtime import. The
default controls and radar/asset rules are derived from the local PLE `.alp`.
"""

from __future__ import annotations

import math
import random
from typing import Iterable

import mesa


DEFAULT_RADAR_LOCATIONS = ((230.0, 80.0, 0.0), (270.0, 190.0, 0.0), (300.0, 330.0, 0.0))
DEFAULT_ASSET_COUNT = 10
DEFAULT_FIELD_LIMIT_X = 700.0
DEFAULT_HIT_RADIUS = 3.0
DEFAULT_BOMBING_DISTANCE = 5.0


def distance3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def distance2(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def move_toward(
    position: tuple[float, float, float],
    target: tuple[float, float, float],
    speed: float,
) -> tuple[float, float, float]:
    dist = distance3(position, target)
    if dist == 0 or speed <= 0:
        return position
    ratio = min(1.0, speed / dist)
    return (
        position[0] + (target[0] - position[0]) * ratio,
        position[1] + (target[1] - position[1]) * ratio,
        position[2] + (target[2] - position[2]) * ratio,
    )


class Asset:
    def __init__(self, unique_id: str, x: float, y: float, z: float = 0.0) -> None:
        self.unique_id = unique_id
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.state = "normal"

    @property
    def position(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def is_alive(self) -> bool:
        return self.state == "normal"

    def destroy_this_asset(self) -> None:
        if self.state == "normal":
            self.state = "destroyed"


class Aircraft:
    def __init__(
        self,
        unique_id: str,
        target: Asset,
        speed: float,
        z: float,
        rng: random.Random,
    ) -> None:
        self.unique_id = unique_id
        self.target = target
        self.speed = float(speed)
        self.x = 0.0
        self.y = 0.0
        self.z = float(rng.uniform(max(0.0, z - 5.0), z + 5.0))
        self.base_z = float(z)
        self.tracked = False
        self.state = "flying"

    @property
    def position(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def on_hit(self) -> None:
        if self.state not in {"destroyed", "departed"}:
            self.state = "destroyed"
            self.tracked = False

    def step(self, model: "AirDefenseModel") -> None:
        if self.state in {"destroyed", "departed"}:
            return
        if self.state == "returning":
            self.x += max(self.speed, 1.0)
            self.z = max(self.z, self.base_z + 30.0)
            if self.x > model.field_limit_x:
                self.state = "departed"
            return
        if not self.target.is_alive():
            self.state = "returning"
            return

        target_position = (self.target.x, self.target.y, self.z)
        self.x, self.y, self.z = move_toward(self.position, target_position, self.speed)
        ground_distance = distance2((self.x, self.y), (self.target.x, self.target.y))
        if ground_distance <= model.bombing_distance and self.z <= model.aircraft_z + 5.0:
            self.target.destroy_this_asset()
            model.assets_destroyed_count += 1
            self.state = "returning"


class Missile:
    def __init__(self, unique_id: str, radar: "Radar", target: Aircraft, speed: float) -> None:
        self.unique_id = unique_id
        self.radar = radar
        self.target = target
        self.speed = float(speed)
        self.x = radar.x
        self.y = radar.y
        self.z = radar.z
        self.state = "flying"

    @property
    def position(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def step(self, model: "AirDefenseModel") -> None:
        if self.state != "flying":
            return
        if self.target.state in {"destroyed", "departed"}:
            self.explode(model)
            return

        radar_distance = distance3(self.target.position, self.radar.position)
        if radar_distance > self.radar.zone or distance3(self.position, self.radar.position) > self.radar.zone:
            self.miss(model)
            return

        self.x, self.y, self.z = move_toward(self.position, self.target.position, self.speed)
        if distance3(self.position, self.target.position) <= model.hit_radius:
            self.target.on_hit()
            model.aircraft_destroyed_count += 1
            model.missiles_hit_count += 1
            self.explode(model)

    def miss(self, model: "AirDefenseModel") -> None:
        self.target.tracked = False
        model.missiles_missed_count += 1
        self.explode(model)

    def explode(self, model: "AirDefenseModel") -> None:
        self.state = "exploded"
        self.radar.remove_missile(self)
        if self in model.missiles:
            model.missiles.remove(self)


class Radar:
    def __init__(
        self,
        unique_id: str,
        x: float,
        y: float,
        z: float,
        zone: float,
        max_missiles: int,
        missile_speed: float,
    ) -> None:
        self.unique_id = unique_id
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.zone = float(zone)
        self.max_missiles = int(max_missiles)
        self.missile_speed = float(missile_speed)
        self.missiles: list[Missile] = []

    @property
    def position(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def step(self, model: "AirDefenseModel") -> None:
        if len(self.missiles) >= self.max_missiles:
            return
        for aircraft in model.aircrafts:
            if len(self.missiles) >= self.max_missiles:
                break
            if aircraft.state != "flying" or aircraft.tracked:
                continue
            if distance3(self.position, aircraft.position) <= self.zone:
                self.fire_missile(model, aircraft)

    def fire_missile(self, model: "AirDefenseModel", aircraft: Aircraft) -> Missile:
        missile = Missile(
            unique_id=f"missile-{model.next_missile_id}",
            radar=self,
            target=aircraft,
            speed=self.missile_speed,
        )
        model.next_missile_id += 1
        aircraft.tracked = True
        self.missiles.append(missile)
        model.missiles.append(missile)
        model.missiles_fired_count += 1
        return missile

    def remove_missile(self, missile: Missile) -> None:
        if missile in self.missiles:
            self.missiles.remove(missile)


class AirDefenseModel(mesa.Model):
    """Continuous-space air defense ABM with AnyLogic-derived controls."""

    def __init__(
        self,
        seed: int | None = None,
        aircraft_speed: float = 10.0,
        missile_speed: float = 20.0,
        radar_zone: float = 100.0,
        radar_max_missiles: int = 2,
        aircraft_z: float = 70.0,
        initial_aircraft: int = 4,
        asset_count: int = DEFAULT_ASSET_COUNT,
        steps_per_day: int = 20,
        radar_locations: Iterable[tuple[float, float, float]] = DEFAULT_RADAR_LOCATIONS,
        bombing_distance: float = DEFAULT_BOMBING_DISTANCE,
        hit_radius: float = DEFAULT_HIT_RADIUS,
        field_limit_x: float = DEFAULT_FIELD_LIMIT_X,
    ) -> None:
        super().__init__(rng=seed)
        self.rng = random.Random(seed)
        self.aircraft_speed = float(aircraft_speed)
        self.missile_speed = float(missile_speed)
        self.radar_zone = float(radar_zone)
        self.radar_max_missiles = int(radar_max_missiles)
        self.aircraft_z = float(aircraft_z)
        self.steps_per_day = int(steps_per_day)
        self.bombing_distance = float(bombing_distance)
        self.hit_radius = float(hit_radius)
        self.field_limit_x = float(field_limit_x)
        self.sim_time_days = 0.0
        self.next_aircraft_id = 0
        self.next_missile_id = 0
        self.assets_destroyed_count = 0
        self.aircraft_destroyed_count = 0
        self.missiles_fired_count = 0
        self.missiles_hit_count = 0
        self.missiles_missed_count = 0

        self.assets = self._create_assets(int(asset_count))
        self.radars = [
            Radar(
                unique_id=f"radar-{index}",
                x=x,
                y=y,
                z=z,
                zone=self.radar_zone,
                max_missiles=self.radar_max_missiles,
                missile_speed=self.missile_speed,
            )
            for index, (x, y, z) in enumerate(radar_locations)
        ]
        self.aircrafts: list[Aircraft] = []
        self.missiles: list[Missile] = []
        for _ in range(int(initial_aircraft)):
            self.launch_aircraft()

    def _create_assets(self, asset_count: int) -> list[Asset]:
        assets: list[Asset] = []
        attempts = 0
        while len(assets) < asset_count and attempts < asset_count * 100:
            attempts += 1
            x = self.rng.uniform(400.0, 600.0)
            y = self.rng.uniform(200.0, 400.0)
            if all(distance2((x, y), (asset.x, asset.y)) >= 30.0 for asset in assets):
                assets.append(Asset(unique_id=f"asset-{len(assets)}", x=x, y=y))
        if len(assets) != asset_count:
            raise RuntimeError("could not place non-overlapping assets")
        return assets

    def live_assets(self) -> list[Asset]:
        return [asset for asset in self.assets if asset.is_alive()]

    def launch_aircraft(self) -> Aircraft | None:
        live_assets = self.live_assets()
        if not live_assets:
            return None
        target = self.rng.choice(live_assets)
        aircraft = Aircraft(
            unique_id=f"aircraft-{self.next_aircraft_id}",
            target=target,
            speed=self.aircraft_speed,
            z=self.aircraft_z,
            rng=self.rng,
        )
        self.next_aircraft_id += 1
        self.aircrafts.append(aircraft)
        return aircraft

    def step(self) -> None:
        self.sim_time_days += 1.0 / max(1, self.steps_per_day)
        for radar in self.radars:
            radar.step(self)
        for missile in list(self.missiles):
            missile.step(self)
        for aircraft in list(self.aircrafts):
            aircraft.step(self)

    def snapshot(self) -> dict[str, float | int]:
        active_aircraft = sum(1 for aircraft in self.aircrafts if aircraft.state == "flying")
        returning_aircraft = sum(1 for aircraft in self.aircrafts if aircraft.state == "returning")
        departed_aircraft = sum(1 for aircraft in self.aircrafts if aircraft.state == "departed")
        return {
            "time_days": self.sim_time_days,
            "assets_total": len(self.assets),
            "assets_destroyed": sum(1 for asset in self.assets if asset.state == "destroyed"),
            "assets_alive": sum(1 for asset in self.assets if asset.is_alive()),
            "active_aircraft": active_aircraft,
            "returning_aircraft": returning_aircraft,
            "aircraft_departed": departed_aircraft,
            "aircraft_destroyed": sum(1 for aircraft in self.aircrafts if aircraft.state == "destroyed"),
            "active_missiles": len(self.missiles),
            "missiles_fired": self.missiles_fired_count,
            "missiles_hit": self.missiles_hit_count,
            "missiles_missed": self.missiles_missed_count,
            "radar_load": sum(len(radar.missiles) for radar in self.radars),
        }

    def agent_positions(self) -> dict[str, list[dict[str, float | str]]]:
        return {
            "assets": [
                {"id": asset.unique_id, "x": asset.x, "y": asset.y, "z": asset.z, "state": asset.state}
                for asset in self.assets
            ],
            "radars": [
                {
                    "id": radar.unique_id,
                    "x": radar.x,
                    "y": radar.y,
                    "z": radar.z,
                    "state": f"{len(radar.missiles)}/{radar.max_missiles}",
                }
                for radar in self.radars
            ],
            "aircraft": [
                {
                    "id": aircraft.unique_id,
                    "x": aircraft.x,
                    "y": aircraft.y,
                    "z": aircraft.z,
                    "state": aircraft.state,
                }
                for aircraft in self.aircrafts
            ],
            "missiles": [
                {
                    "id": missile.unique_id,
                    "x": missile.x,
                    "y": missile.y,
                    "z": missile.z,
                    "state": missile.state,
                }
                for missile in self.missiles
            ],
        }
