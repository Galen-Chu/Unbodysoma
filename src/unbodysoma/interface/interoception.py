"""Interoception: the mind's (noisy, normalized) view of the body's internal state."""

from __future__ import annotations

import random

from ..core import BusPort, Module, clamp


class Interoception(Module):
    """Maps raw physiological variables to normalized [0, 1] interoceptive signals.

    The psyche layer never reads ``soma.*`` directly; it only sees these
    signals, which is where interoceptive precision and bias will live later.
    """

    name = "interface.interoception"
    rate_hz = 10.0
    reads = ("soma.cardio.heart_rate", "soma.metabolism.energy_reserve")
    writes = ("intero.cardiac_arousal", "intero.energy_deficit")

    def __init__(
        self,
        resting_bpm: float = 60.0,
        bpm_span: float = 100.0,
        noise: float = 0.01,
        seed: int = 1,
    ) -> None:
        self.resting_bpm = resting_bpm
        self.bpm_span = bpm_span
        self.noise = noise
        self._rng = random.Random(seed)

    def _sense(self, value: float) -> float:
        return clamp(value + self._rng.gauss(0.0, self.noise))

    def step(self, dt: float, port: BusPort) -> None:
        heart_rate = port.read("soma.cardio.heart_rate")
        reserve = port.read("soma.metabolism.energy_reserve")
        port.write("intero.cardiac_arousal", self._sense((heart_rate - self.resting_bpm) / self.bpm_span))
        port.write("intero.energy_deficit", self._sense(1.0 - reserve))
