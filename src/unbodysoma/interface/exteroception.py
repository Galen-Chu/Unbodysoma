"""Exteroception: noisy sensing of the outside world."""

from __future__ import annotations

import math
import random
from typing import Any

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp


class Exteroception(Module):
    """Turns world stimuli into noisy sensory signals: threat cues and food.

    Each channel has its own random stream, so adding a channel never changes
    the noise (and therefore the results) of the existing ones.
    """

    name = "interface.exteroception"
    rate_hz = 20.0
    reads = ("world.threat", "world.food_available")
    signal_specs = (
        SignalSpec("extero.threat", "normalized", 0.0, 1.0, "Sensed threat cue"),
        SignalSpec("extero.food", "normalized", 0.0, 1.0, "Sensed food within reach"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("noise", 0.02, "normalized", 0.0, 1.0, "SD of sensory noise"),
        ParamSpec("seed", 0, "", 0, math.inf, "Random seed of the noise", source="run setting"),
    )

    def __init__(self, noise: float = 0.02, seed: int = 0) -> None:
        self.noise = noise
        self.seed = seed
        # The threat stream keeps the plain seed so pre-existing results are unchanged.
        self._rngs = {"threat": random.Random(seed), "food": random.Random(f"{seed}:food")}

    def get_state(self) -> dict[str, Any]:
        return {"rngs": {channel: rng.getstate() for channel, rng in self._rngs.items()}}

    def set_state(self, state: dict[str, Any]) -> None:
        for channel, rng_state in state["rngs"].items():
            self._rngs[channel].setstate(rng_state)

    def _sense(self, channel: str, value: float) -> float:
        return clamp(value + self._rngs[channel].gauss(0.0, self.noise))

    def step(self, dt: float, port: BusPort) -> None:
        port.write("extero.threat", self._sense("threat", port.read("world.threat")))
        port.write("extero.food", self._sense("food", port.read("world.food_available")))
