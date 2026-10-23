"""Interoception: the mind's (noisy, normalized) view of the body's internal state."""

from __future__ import annotations

import math
import random
from typing import Any

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp

_CHANNELS = ("cardiac_arousal", "energy_deficit", "water_deficit", "thermal", "sleep_pressure", "circadian")


class Interoception(Module):
    """Maps raw physiological variables to normalized [0, 1] interoceptive signals.

    The psyche layer never reads ``soma.*`` directly; it only sees these
    signals, which is where interoceptive precision and bias will live later.
    """

    name = "interface.interoception"
    rate_hz = 10.0
    reads = (
        "soma.cardio.heart_rate",
        "soma.metabolism.energy_reserve",
        "soma.fluid.hydration",
        "soma.thermo.core_temperature",
        "soma.sleep.pressure",
        "soma.circadian.drive",
    )
    signal_specs = (
        SignalSpec("intero.cardiac_arousal", "normalized", 0.0, 1.0, "Felt cardiac activation"),
        SignalSpec("intero.energy_deficit", "normalized", 0.0, 1.0, "Felt shortage of energy"),
        SignalSpec("intero.water_deficit", "normalized", 0.0, 1.0, "Felt shortage of water"),
        SignalSpec("intero.thermal", "normalized", -1.0, 1.0, "Felt body temperature (- cold, + hot)"),
        SignalSpec("intero.sleep_pressure", "normalized", 0.0, 1.0, "Felt tiredness (homeostatic sleep pressure)"),
        SignalSpec("intero.circadian", "normalized", -1.0, 1.0, "Felt circadian alerting signal"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("resting_bpm", 60.0, "bpm", 30.0, 120.0, "Heart rate felt as zero activation"),
        ParamSpec("bpm_span", 100.0, "bpm", 10.0, 250.0, "Heart-rate rise felt as full activation"),
        ParamSpec("comfortable_core", 37.0, "°C", 35.0, 39.0, "Core temperature felt as neither cold nor hot"),
        ParamSpec("thermal_span", 2.0, "°C", 0.1, 10.0, "Core deviation felt as extreme cold or heat"),
        ParamSpec(
            "noise", 0.01, "normalized", 0.0, 1.0, "SD of interoceptive noise (inverse of interoceptive accuracy)"
        ),
        ParamSpec("seed", 1, "", 0, math.inf, "Random seed of the noise", source="run setting"),
    )

    def __init__(
        self,
        resting_bpm: float = 60.0,
        bpm_span: float = 100.0,
        comfortable_core: float = 37.0,
        thermal_span: float = 2.0,
        noise: float = 0.01,
        seed: int = 1,
    ) -> None:
        self.resting_bpm = resting_bpm
        self.bpm_span = bpm_span
        self.comfortable_core = comfortable_core
        self.thermal_span = thermal_span
        self.noise = noise
        self.seed = seed
        # One random stream per channel, so adding a channel never changes the noise of the others.
        self._rngs = {c: random.Random(seed if c == "cardiac_arousal" else f"{seed}:{c}") for c in _CHANNELS}

    def get_state(self) -> dict[str, Any]:
        return {"rngs": {channel: rng.getstate() for channel, rng in self._rngs.items()}}

    def set_state(self, state: dict[str, Any]) -> None:
        for channel, rng_state in state["rngs"].items():
            self._rngs[channel].setstate(rng_state)

    def _sense(self, port: BusPort, channel: str, value: float, lo: float = 0.0, hi: float = 1.0) -> None:
        sensed = clamp(value + self._rngs[channel].gauss(0.0, self.noise), lo, hi)
        port.write(f"intero.{channel}", sensed)

    def step(self, dt: float, port: BusPort) -> None:
        heart_rate = port.read("soma.cardio.heart_rate")
        reserve = port.read("soma.metabolism.energy_reserve")
        self._sense(port, "cardiac_arousal", (heart_rate - self.resting_bpm) / self.bpm_span)
        self._sense(port, "energy_deficit", 1.0 - reserve)
        self._sense(port, "water_deficit", 1.0 - port.read("soma.fluid.hydration"))
        felt = (port.read("soma.thermo.core_temperature") - self.comfortable_core) / self.thermal_span
        self._sense(port, "thermal", felt, -1.0, 1.0)
        self._sense(port, "sleep_pressure", port.read("soma.sleep.pressure"))
        self._sense(port, "circadian", port.read("soma.circadian.drive"), -1.0, 1.0)
