"""Exteroception: noisy sensing of the outside world."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp


@dataclass(frozen=True)
class Channel:
    """One sense: which world signal it reads, which percept it produces, and its range."""

    source: str
    lo: float
    hi: float
    description: str

    def percept(self, name: str) -> str:
        return f"extero.{name}"


CHANNELS = {
    "threat": Channel("world.threat", 0.0, 1.0, "Sensed threat cue"),
    "food": Channel("world.food_available", 0.0, 1.0, "Sensed food within reach"),
    "food_dir_x": Channel("world.food_dir_x", -1.0, 1.0, "Sensed direction to the nearest food (x)"),
    "food_dir_y": Channel("world.food_dir_y", -1.0, 1.0, "Sensed direction to the nearest food (y)"),
    "threat_dir_x": Channel("world.threat_dir_x", -1.0, 1.0, "Sensed direction to the strongest threat (x)"),
    "threat_dir_y": Channel("world.threat_dir_y", -1.0, 1.0, "Sensed direction to the strongest threat (y)"),
}
BASIC_CHANNELS = ("threat", "food")
SPATIAL_CHANNELS = (*BASIC_CHANNELS, "food_dir_x", "food_dir_y", "threat_dir_x", "threat_dir_y")


class Exteroception(Module):
    """Turns world signals into noisy percepts, one ``extero.<channel>`` per configured channel.

    Each channel has its own random stream, so adding a channel never changes
    the noise (and therefore the results) of the existing ones.
    """

    name = "interface.exteroception"
    rate_hz = 20.0
    config_args = ("channels",)
    params = (
        ParamSpec("noise", 0.02, "normalized", 0.0, 1.0, "SD of sensory noise"),
        ParamSpec("seed", 0, "", 0, math.inf, "Random seed of the noise", source="run setting"),
    )

    def __init__(self, noise: float = 0.02, seed: int = 0, channels: Iterable[str] = BASIC_CHANNELS) -> None:
        self.noise = noise
        self.seed = seed
        self.channels = tuple(channels)
        unknown = set(self.channels) - set(CHANNELS)
        if unknown:
            raise ValueError(f"unknown sensory channels: {sorted(unknown)}")
        self.reads = tuple(CHANNELS[c].source for c in self.channels)
        self.signal_specs = tuple(
            SignalSpec(f"extero.{c}", "normalized", CHANNELS[c].lo, CHANNELS[c].hi, CHANNELS[c].description)
            for c in self.channels
        )
        self.writes = tuple(s.key for s in self.signal_specs)
        # The threat stream keeps the plain seed so pre-existing results are unchanged.
        self._rngs = {c: random.Random(seed if c == "threat" else f"{seed}:{c}") for c in self.channels}

    def get_state(self) -> dict[str, Any]:
        return {"rngs": {channel: rng.getstate() for channel, rng in self._rngs.items()}}

    def set_state(self, state: dict[str, Any]) -> None:
        for channel, rng_state in state["rngs"].items():
            self._rngs[channel].setstate(rng_state)

    def step(self, dt: float, port: BusPort) -> None:
        for c in self.channels:
            spec = CHANNELS[c]
            sensed = port.read(spec.source) + self._rngs[c].gauss(0.0, self.noise)
            port.write(f"extero.{c}", clamp(sensed, spec.lo, spec.hi))
