"""A 2D foraging world: food patches that deplete and regrow, hazard zones, movement.

A patch is only worth approaching once it has regrown to ``open_threshold`` of its
capacity, but a patch being eaten can be eaten down to ``empty_threshold``. Without
this gap an organism would sit next to an empty patch nibbling every bit of
regrowth, instead of leaving for a better one (the marginal value theorem).

Water sources never run out. Shelters buffer the outside temperature and keep
hazards out; the organism always knows the way to the nearest shelter (homing,
as animals remember their burrow), whereas food and water must be within
``sense_radius`` to be perceived. The outside temperature follows a daily cycle.

The world is a torus (edges wrap around), so a wandering organism never gets
stuck against a wall. Positions are continuous, in cell units.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from ..core import BusPort, Module, ParamSpec, SignalSpec

_SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class FoodPatch:
    """Food at ``(x, y)``; ``amount`` starts at ``capacity`` and regrows when eaten."""

    x: float
    y: float
    capacity: float = 1.0
    regrow_per_hour: float = 0.25


@dataclass(frozen=True)
class WaterSource:
    """Water at ``(x, y)`` that never runs out (a spring, a stream)."""

    x: float
    y: float


@dataclass(frozen=True)
class Shelter:
    """A refuge at ``(x, y)``: inside ``radius`` the temperature is buffered and hazards cannot reach."""

    x: float
    y: float
    radius: float = 1.0
    insulation: float = 0.8  # share of the outside deviation from comfortable that is kept out


@dataclass(frozen=True)
class Hazard:
    """A danger zone: threat ``strength`` at its centre, fading to 0 at ``radius``.

    Active during ``[start, end)``; with ``every`` set, that window repeats every
    ``every`` seconds (e.g. a predator that visits daily).
    """

    x: float
    y: float
    radius: float = 2.0
    strength: float = 0.9
    start: float = 0.0
    end: float = math.inf
    every: float = math.inf

    def active(self, t: float) -> bool:
        if t < self.start:
            return False
        if math.isinf(self.every):
            return t < self.end
        return (t - self.start) % self.every < self.end - self.start


class GridWorld(Module):
    name = "world.grid"
    rate_hz = 10.0
    reads = ("motor.move_x", "motor.move_y", "motor.eating")
    config_args = ("width", "height", "food", "hazards", "water", "shelters", "start")
    params = (
        ParamSpec("max_speed", 1.0, "cells/s", 0.0, 10.0, "Speed at a full movement command"),
        ParamSpec("reach", 0.5, "cells", 0.05, 5.0, "Distance at which food can be eaten"),
        ParamSpec("sense_radius", 6.0, "cells", 0.0, 100.0, "Distance at which food and hazards are perceived"),
        ParamSpec("depletion_per_s", 1 / 600, "1/s", 0.0, 1.0, "Share of a patch eaten per second of eating"),
        ParamSpec(
            "open_threshold", 0.25, "fraction", 0.0, 1.0, "Share of capacity at which a patch is worth approaching"
        ),
        ParamSpec(
            "empty_threshold", 0.05, "fraction", 0.0, 1.0, "Share of capacity at which a patch being eaten runs out"
        ),
        ParamSpec("temperature_mean", 15.0, "°C", -40.0, 50.0, "Daily mean outside temperature"),
        ParamSpec("temperature_amplitude", 8.0, "°C", 0.0, 30.0, "Half the day-night temperature swing"),
        ParamSpec("warmest_hour", 15.0, "h", 0.0, 24.0, "Clock hour of the warmest outside temperature"),
        ParamSpec("comfortable_temperature", 20.0, "°C", 0.0, 40.0, "Temperature a shelter buffers toward"),
        ParamSpec("start_hour", 8.0, "h", 0.0, 24.0, "Clock time at t = 0", source="run setting"),
    )
    state_fields = ("x", "y", "amounts", "feeding_at")

    def __init__(
        self,
        width: float = 20.0,
        height: float = 20.0,
        food: Iterable[FoodPatch] = (),
        hazards: Iterable[Hazard] = (),
        water: Iterable[WaterSource] = (),
        shelters: Iterable[Shelter] = (),
        start: tuple[float, float] = (10.0, 10.0),
        max_speed: float = 1.0,
        reach: float = 0.5,
        sense_radius: float = 6.0,
        depletion_per_s: float = 1 / 600,
        open_threshold: float = 0.25,
        empty_threshold: float = 0.05,
        temperature_mean: float = 15.0,
        temperature_amplitude: float = 8.0,
        warmest_hour: float = 15.0,
        comfortable_temperature: float = 20.0,
        start_hour: float = 8.0,
    ) -> None:
        self.width = width
        self.height = height
        self.food = tuple(food)
        self.hazards = tuple(hazards)
        self.water = tuple(water)
        self.shelters = tuple(shelters)
        self.start = (float(start[0]), float(start[1]))
        self.max_speed = max_speed
        self.reach = reach
        self.sense_radius = sense_radius
        self.depletion_per_s = depletion_per_s
        self.open_threshold = open_threshold
        self.empty_threshold = empty_threshold
        self.temperature_mean = temperature_mean
        self.temperature_amplitude = temperature_amplitude
        self.warmest_hour = warmest_hour
        self.comfortable_temperature = comfortable_temperature
        self.start_hour = start_hour
        self.x, self.y = self.start
        self.amounts = [p.capacity for p in self.food]
        self.feeding_at = -1  # index of the patch being eaten, or -1
        self.signal_specs = (
            SignalSpec("world.threat", "normalized", 0.0, 1.0, "Objective threat at the organism's position"),
            SignalSpec("world.food_available", "normalized", 0.0, 1.0, "Food within reach (1 = plenty)"),
            SignalSpec("world.food_stock", "patches", 0.0, float(len(self.food)), "Total food left in the world"),
            SignalSpec("world.position_x", "cells", 0.0, width, "Organism position (x)"),
            SignalSpec("world.position_y", "cells", 0.0, height, "Organism position (y)"),
            SignalSpec("world.food_dir_x", "unit", -1.0, 1.0, "Direction to the nearest perceived food (x); 0 if none"),
            SignalSpec("world.food_dir_y", "unit", -1.0, 1.0, "Direction to the nearest perceived food (y); 0 if none"),
            SignalSpec("world.threat_dir_x", "unit", -1.0, 1.0, "Direction to the strongest perceived hazard (x)"),
            SignalSpec("world.threat_dir_y", "unit", -1.0, 1.0, "Direction to the strongest perceived hazard (y)"),
            SignalSpec("world.water_available", "normalized", 0.0, 1.0, "Water within reach"),
            SignalSpec(
                "world.water_dir_x", "unit", -1.0, 1.0, "Direction to the nearest perceived water (x); 0 if none"
            ),
            SignalSpec(
                "world.water_dir_y", "unit", -1.0, 1.0, "Direction to the nearest perceived water (y); 0 if none"
            ),
            SignalSpec("world.in_shelter", "indicator", 0.0, 1.0, "1 inside a shelter"),
            SignalSpec(
                "world.shelter_known", "indicator", 0.0, 1.0, "1 if the world has a shelter (its way is remembered)"
            ),
            SignalSpec(
                "world.shelter_dir_x", "unit", -1.0, 1.0, "Direction to the nearest shelter (x); 0 inside or if none"
            ),
            SignalSpec(
                "world.shelter_dir_y", "unit", -1.0, 1.0, "Direction to the nearest shelter (y); 0 inside or if none"
            ),
            SignalSpec("world.outside_temperature", "°C", -60.0, 60.0, "Outside air temperature"),
            SignalSpec("world.ambient_temperature", "°C", -60.0, 60.0, "Temperature where the organism is"),
        )
        self.writes = tuple(s.key for s in self.signal_specs)

    def get_params(self) -> dict[str, Any]:
        values = super().get_params()
        values["food"] = [asdict(p) for p in self.food]
        values["hazards"] = [
            {k: (None if isinstance(v, float) and math.isinf(v) else v) for k, v in asdict(h).items()}
            for h in self.hazards
        ]
        values["water"] = [asdict(w) for w in self.water]
        values["shelters"] = [asdict(sh) for sh in self.shelters]
        values["start"] = list(self.start)
        return values

    # -- torus geometry -----------------------------------------------------

    def offset(self, x: float, y: float) -> tuple[float, float]:
        """Shortest vector from the organism to ``(x, y)``, wrapping around the edges."""
        dx = (x - self.x + self.width / 2) % self.width - self.width / 2
        dy = (y - self.y + self.height / 2) % self.height - self.height / 2
        return dx, dy

    def _nearest(self, places: Iterable[Any], radius: float) -> tuple[float, float, float]:
        """Distance and unit direction to the nearest place within ``radius`` (inf, 0, 0 if none)."""
        nearest, direction = math.inf, (0.0, 0.0)
        for place in places:
            dx, dy = self.offset(place.x, place.y)
            d = math.hypot(dx, dy)
            if d <= radius and d < nearest:
                nearest, direction = d, ((dx / d, dy / d) if d > 0 else (0.0, 0.0))
        return nearest, direction[0], direction[1]

    def in_shelter(self) -> Shelter | None:
        for sh in self.shelters:
            if math.hypot(*self.offset(sh.x, sh.y)) <= sh.radius:
                return sh
        return None

    def outside_temperature(self, t: float) -> float:
        hour = self.start_hour + t / _SECONDS_PER_HOUR
        return self.temperature_mean + self.temperature_amplitude * math.cos(
            2.0 * math.pi * (hour - self.warmest_hour) / 24.0
        )

    def _threat(self, t: float) -> tuple[float, float, float]:
        """Threat at the organism, and the unit direction to the strongest perceived hazard."""
        if self.in_shelter() is not None:
            return 0.0, 0.0, 0.0  # hazards cannot reach into a shelter
        best, direction = 0.0, (0.0, 0.0)
        felt = 0.0
        for h in self.hazards:
            if not h.active(t):
                continue
            dx, dy = self.offset(h.x, h.y)
            d = math.hypot(dx, dy)
            felt = max(felt, h.strength * max(0.0, 1.0 - d / h.radius))
            salience = h.strength / (1.0 + d)
            if d <= self.sense_radius and salience > best:
                best, direction = salience, ((dx / d, dy / d) if d > 0 else (0.0, 0.0))
        return felt, direction[0], direction[1]

    def _open(self, i: int) -> bool:
        threshold = self.empty_threshold if i == self.feeding_at else self.open_threshold
        return self.amounts[i] >= threshold * self.food[i].capacity

    def _food(self) -> tuple[float, float, float]:
        """Food within reach (0 or 1), and the unit direction to the nearest perceived open patch."""
        available, nearest, direction = 0.0, math.inf, (0.0, 0.0)
        for i, patch in enumerate(self.food):
            if not self._open(i):
                continue
            dx, dy = self.offset(patch.x, patch.y)
            d = math.hypot(dx, dy)
            if d <= self.reach:
                available = 1.0
            if d <= self.sense_radius and d < nearest:
                nearest, direction = d, ((dx / d, dy / d) if d > 0 else (0.0, 0.0))
        return available, direction[0], direction[1]

    # -- simulation ---------------------------------------------------------

    def _publish(self, port: BusPort, t: float) -> None:
        threat, tdx, tdy = self._threat(t)
        available, fdx, fdy = self._food()
        port.write("world.threat", threat)
        port.write("world.food_available", available)
        port.write("world.food_stock", sum(a / p.capacity for a, p in zip(self.amounts, self.food, strict=True)))
        port.write("world.position_x", self.x)
        port.write("world.position_y", self.y)
        port.write("world.food_dir_x", fdx)
        port.write("world.food_dir_y", fdy)
        port.write("world.threat_dir_x", tdx)
        port.write("world.threat_dir_y", tdy)
        water_distance, wdx, wdy = self._nearest(self.water, self.sense_radius)
        port.write("world.water_available", 1.0 if water_distance <= self.reach else 0.0)
        port.write("world.water_dir_x", wdx)
        port.write("world.water_dir_y", wdy)
        shelter = self.in_shelter()
        _, sdx, sdy = self._nearest(self.shelters, math.inf)
        port.write("world.in_shelter", 1.0 if shelter is not None else 0.0)
        port.write("world.shelter_known", 1.0 if self.shelters else 0.0)
        port.write("world.shelter_dir_x", 0.0 if shelter is not None else sdx)
        port.write("world.shelter_dir_y", 0.0 if shelter is not None else sdy)
        outside = self.outside_temperature(t)
        ambient = outside
        if shelter is not None:
            ambient = self.comfortable_temperature + (1.0 - shelter.insulation) * (
                outside - self.comfortable_temperature
            )
        port.write("world.outside_temperature", outside)
        port.write("world.ambient_temperature", ambient)

    def setup(self, port: BusPort) -> None:
        self._publish(port, 0.0)

    def step(self, dt: float, port: BusPort) -> None:
        mx, my = port.read("motor.move_x"), port.read("motor.move_y")
        norm = math.hypot(mx, my)
        if norm > 1.0:
            mx, my = mx / norm, my / norm
        self.x = (self.x + self.max_speed * mx * dt) % self.width
        self.y = (self.y + self.max_speed * my * dt) % self.height

        eating = port.read("motor.eating")
        feeding_at = -1
        for i, patch in enumerate(self.food):
            dx, dy = self.offset(patch.x, patch.y)
            amount = self.amounts[i] + patch.regrow_per_hour * patch.capacity * dt / _SECONDS_PER_HOUR
            if eating > 0.0 and math.hypot(dx, dy) <= self.reach and self._open(i):
                amount -= self.depletion_per_s * patch.capacity * eating * dt
                feeding_at = i
            self.amounts[i] = min(patch.capacity, max(0.0, amount))
        self.feeding_at = feeding_at
        self._publish(port, port.time)
