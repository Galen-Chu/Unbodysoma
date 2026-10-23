"""Interoception: the mind's (noisy, normalized) view of the body's internal state."""

from __future__ import annotations

import math
import random
from typing import Any

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp


class Interoception(Module):
    """Maps raw physiological variables to normalized [0, 1] interoceptive signals.

    The psyche layer never reads ``soma.*`` directly; it only sees these
    signals, which is where interoceptive precision and bias will live later.
    """

    name = "interface.interoception"
    rate_hz = 10.0
    reads = ("soma.cardio.heart_rate", "soma.metabolism.energy_reserve", "soma.sleep.pressure", "soma.circadian.drive")
    signal_specs = (
        SignalSpec("intero.cardiac_arousal", "normalized", 0.0, 1.0, "Felt cardiac activation"),
        SignalSpec("intero.energy_deficit", "normalized", 0.0, 1.0, "Felt shortage of energy"),
        SignalSpec("intero.sleep_pressure", "normalized", 0.0, 1.0, "Felt tiredness (homeostatic sleep pressure)"),
        SignalSpec("intero.circadian", "normalized", -1.0, 1.0, "Felt circadian alerting signal"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("resting_bpm", 60.0, "bpm", 30.0, 120.0, "Heart rate felt as zero activation"),
        ParamSpec("bpm_span", 100.0, "bpm", 10.0, 250.0, "Heart-rate rise felt as full activation"),
        ParamSpec(
            "noise", 0.01, "normalized", 0.0, 1.0, "SD of interoceptive noise (inverse of interoceptive accuracy)"
        ),
        ParamSpec("seed", 1, "", 0, math.inf, "Random seed of the noise", source="run setting"),
    )

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
        self.seed = seed
        self._rng = random.Random(seed)

    def get_state(self) -> dict[str, Any]:
        return {"rng": self._rng.getstate()}

    def set_state(self, state: dict[str, Any]) -> None:
        self._rng.setstate(state["rng"])

    def _sense(self, value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return clamp(value + self._rng.gauss(0.0, self.noise), lo, hi)

    def step(self, dt: float, port: BusPort) -> None:
        heart_rate = port.read("soma.cardio.heart_rate")
        reserve = port.read("soma.metabolism.energy_reserve")
        port.write("intero.cardiac_arousal", self._sense((heart_rate - self.resting_bpm) / self.bpm_span))
        port.write("intero.energy_deficit", self._sense(1.0 - reserve))
        port.write("intero.sleep_pressure", self._sense(port.read("soma.sleep.pressure")))
        port.write("intero.circadian", self._sense(port.read("soma.circadian.drive"), -1.0, 1.0))
