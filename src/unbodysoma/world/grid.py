"""A 2D foraging world: food patches that deplete and regrow, hazard zones, movement.

A patch is only worth approaching once it has regrown to ``open_threshold`` of its
capacity, but a patch being eaten can be eaten down to ``empty_threshold``. Without
this gap an organism would sit next to an empty patch nibbling every bit of
regrowth, instead of leaving for a better one (the marginal value theorem).

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
    config_args = ("width", "height", "food", "hazards", "start")
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
    )
    state_fields = ("x", "y", "amounts", "feeding_at")

    def __init__(
        self,
        width: float = 20.0,
        height: float = 20.0,
        food: Iterable[FoodPatch] = (),
        hazards: Iterable[Hazard] = (),
        start: tuple[float, float] = (10.0, 10.0),
        max_speed: float = 1.0,
        reach: float = 0.5,
        sense_radius: float = 6.0,
        depletion_per_s: float = 1 / 600,
        open_threshold: float = 0.25,
        empty_threshold: float = 0.05,
    ) -> None:
        self.width = width
        self.height = height
        self.food = tuple(food)
        self.hazards = tuple(hazards)
        self.start = (float(start[0]), float(start[1]))
        self.max_speed = max_speed
        self.reach = reach
        self.sense_radius = sense_radius
        self.depletion_per_s = depletion_per_s
        self.open_threshold = open_threshold
        self.empty_threshold = empty_threshold
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
        )
        self.writes = tuple(s.key for s in self.signal_specs)

    def get_params(self) -> dict[str, Any]:
        values = super().get_params()
        values["food"] = [asdict(p) for p in self.food]
        values["hazards"] = [
            {k: (None if isinstance(v, float) and math.isinf(v) else v) for k, v in asdict(h).items()}
            for h in self.hazards
        ]
        values["start"] = list(self.start)
        return values

    # -- torus geometry -----------------------------------------------------

    def offset(self, x: float, y: float) -> tuple[float, float]:
        """Shortest vector from the organism to ``(x, y)``, wrapping around the edges."""
        dx = (x - self.x + self.width / 2) % self.width - self.width / 2
        dy = (y - self.y + self.height / 2) % self.height - self.height / 2
        return dx, dy

    def _threat(self, t: float) -> tuple[float, float, float]:
        """Threat at the organism, and the unit direction to the strongest perceived hazard."""
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
