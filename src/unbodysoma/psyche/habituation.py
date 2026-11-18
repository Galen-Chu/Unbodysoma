"""Habituation: a repeated innocuous stimulus loses its orienting value.

The simplest form of learning, present from nematodes up (Ardel & Rankin 2010);
with the sensitization already inside nociception it completes Phase 3's
non-associative pair. Exposure accumulates while the stimulus is present and
decays over minutes of rest, so the felt novelty — stimulus times unhabituated
fraction — shows response decrement across repetitions and spontaneous
recovery after a break, without any new wiring (affect reads the novelty as a
small orienting arousal; the Phase 4 conditioning model will read it as cue
salience). Acceptance against the Rankin et al. (2009) criteria:
tests/test_habituation.py; equations: docs/PSYCHE.md §4.6.
"""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp


class Habituation(Module):
    """Exposure to a repeated stimulus discounts its felt novelty."""

    name = "psyche.habituation"
    rate_hz = 10.0
    reads = ("world.stimulus",)
    signal_specs = (
        SignalSpec("psyche.habituation.novelty", "normalized", 0.0, 1.0, "Felt novelty of the current stimulus"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "habituation_rate",
            0.12,
            "1/s",
            0.0,
            1.0,
            "Habit gained per second of unit stimulus",
            source="calibrated: ~50% decrement within ten 2-second presentations a minute apart",
        ),
        ParamSpec(
            "tau_recovery",
            150.0,
            "s",
            10.0,
            86400.0,
            "Time constant of spontaneous recovery in the absence of the stimulus",
            source="minutes-scale recovery, as in tap-withdrawal habituation (Rankin et al. 2009)",
        ),
    )
    state_fields = ("habit",)

    def __init__(self, habituation_rate: float = 0.12, tau_recovery: float = 150.0) -> None:
        self.habituation_rate = habituation_rate
        self.tau_recovery = tau_recovery
        self.habit = 0.0

    def setup(self, port: BusPort) -> None:
        self._publish(port)

    def step(self, dt: float, port: BusPort) -> None:
        stimulus = port.read("world.stimulus")
        self.habit = clamp(self.habit + dt * (self.habituation_rate * stimulus - self.habit / self.tau_recovery))
        self._publish(port)

    def _publish(self, port: BusPort) -> None:
        port.write("psyche.habituation.novelty", clamp((1.0 - self.habit) * port.read("world.stimulus")))
