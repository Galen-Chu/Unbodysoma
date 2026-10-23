"""Navigation: turning the chosen action into a movement command."""

from __future__ import annotations

import math
import random

from ..core import BusPort, Module, ParamSpec, SignalSpec


class Navigation(Module):
    """Moves the body according to the action chosen by ``psyche.action``.

    - flee: run directly away from the sensed threat (keep the current heading if
      its direction is unknown);
    - explore: walk toward the sensed food if any, otherwise wander along a
      correlated random walk (the heading diffuses with ``wander_sigma``);
    - any other action: stand still.
    """

    name = "psyche.navigation"
    rate_hz = 5.0
    reads = (
        "psyche.action.selected_flee",
        "psyche.action.selected_explore",
        "psyche.action.selected_seek_water",
        "psyche.action.selected_seek_shelter",
        "extero.food_dir_x",
        "extero.food_dir_y",
        "extero.water_dir_x",
        "extero.water_dir_y",
        "extero.shelter_dir_x",
        "extero.shelter_dir_y",
        "extero.threat_dir_x",
        "extero.threat_dir_y",
    )
    signal_specs = (
        SignalSpec("motor.move_x", "normalized", -1.0, 1.0, "Movement command (x); length 1 = full speed"),
        SignalSpec("motor.move_y", "normalized", -1.0, 1.0, "Movement command (y); length 1 = full speed"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("walk_fraction", 0.5, "normalized", 0.0, 1.0, "Speed while exploring, as a share of full speed"),
        ParamSpec("flee_fraction", 1.0, "normalized", 0.0, 1.0, "Speed while fleeing, as a share of full speed"),
        ParamSpec("wander_sigma", 0.3, "rad/√s", 0.0, 10.0, "How fast the wandering heading diffuses"),
        ParamSpec("direction_seen", 0.5, "unit", 0.0, 1.0, "Length of a sensed direction that counts as known"),
        ParamSpec("seed", 5, "", 0, math.inf, "Random seed of the wandering", source="run setting"),
    )
    state_fields = ("heading", "_rng")

    def __init__(
        self,
        walk_fraction: float = 0.5,
        flee_fraction: float = 1.0,
        wander_sigma: float = 0.3,
        direction_seen: float = 0.5,
        seed: int = 5,
    ) -> None:
        self.walk_fraction = walk_fraction
        self.flee_fraction = flee_fraction
        self.wander_sigma = wander_sigma
        self.direction_seen = direction_seen
        self.seed = seed
        self._rng = random.Random(seed)
        self.heading = self._rng.uniform(0.0, 2.0 * math.pi)

    def _direction(self, port: BusPort, prefix: str) -> tuple[float, float] | None:
        x, y = port.read(f"extero.{prefix}_dir_x"), port.read(f"extero.{prefix}_dir_y")
        norm = math.hypot(x, y)
        return (x / norm, y / norm) if norm >= self.direction_seen else None

    def step(self, dt: float, port: BusPort) -> None:
        self.heading += self.wander_sigma * math.sqrt(dt) * self._rng.gauss(0.0, 1.0)
        move = (0.0, 0.0)
        if port.read("psyche.action.selected_flee") > 0.5:
            threat = self._direction(port, "threat")
            if threat is not None:
                self.heading = math.atan2(-threat[1], -threat[0])
            move = (self.flee_fraction * math.cos(self.heading), self.flee_fraction * math.sin(self.heading))
        else:
            for action, goal in (("explore", "food"), ("seek_water", "water"), ("seek_shelter", "shelter")):
                if port.read(f"psyche.action.selected_{action}") > 0.5:
                    direction = self._direction(port, goal)
                    if direction is not None:
                        self.heading = math.atan2(direction[1], direction[0])
                    move = (self.walk_fraction * math.cos(self.heading), self.walk_fraction * math.sin(self.heading))
                    break
        port.write("motor.move_x", move[0])
        port.write("motor.move_y", move[1])
