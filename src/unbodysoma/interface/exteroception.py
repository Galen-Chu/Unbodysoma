"""Exteroception: noisy sensing of the outside world."""

from __future__ import annotations

import random

from ..core import BusPort, Module, clamp


class Exteroception(Module):
    """Turns world stimuli into noisy sensory signals. Currently only threat cues."""

    name = "interface.exteroception"
    rate_hz = 20.0
    reads = ("world.threat",)
    writes = ("extero.threat",)

    def __init__(self, noise: float = 0.02, seed: int = 0) -> None:
        self.noise = noise
        self._rng = random.Random(seed)

    def step(self, dt: float, port: BusPort) -> None:
        sensed = port.read("world.threat") + self._rng.gauss(0.0, self.noise)
        port.write("extero.threat", clamp(sensed))
