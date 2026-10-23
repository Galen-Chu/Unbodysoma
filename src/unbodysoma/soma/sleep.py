"""Sleep homeostasis — process S of the two-process model (see docs/SOMA.md)."""

from __future__ import annotations

import math

from ..core import BusPort, Module, ParamSpec, SignalSpec

_SECONDS_PER_HOUR = 3600.0
_DAAN_1984 = "Daan, Beersma & Borbély (1984)"


class SleepHomeostat(Module):
    """Sleep pressure S in [0, 1]: saturating build-up while awake, exponential decline while asleep.

    awake:  S ← 1 − (1 − S) · exp(−dt / τ_wake)
    asleep: S ← S · exp(−dt / τ_sleep)
    """

    name = "soma.sleep"
    rate_hz = 1.0
    reads = ("motor.sleeping",)
    signal_specs = (
        SignalSpec("soma.sleep.pressure", "normalized", 0.0, 1.0, "Homeostatic sleep pressure (process S)"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("tau_wake_h", 18.2, "h", 1.0, 100.0, "Time constant of sleep-pressure build-up", source=_DAAN_1984),
        ParamSpec("tau_sleep_h", 4.2, "h", 0.5, 24.0, "Time constant of sleep-pressure decline", source=_DAAN_1984),
        ParamSpec(
            "initial_pressure",
            0.14,
            "normalized",
            0.0,
            1.0,
            "Sleep pressure at t = 0 (about one hour after waking)",
            source="calibrated",
        ),
    )
    state_fields = ("pressure",)

    def __init__(self, tau_wake_h: float = 18.2, tau_sleep_h: float = 4.2, initial_pressure: float = 0.14) -> None:
        self.tau_wake_h = tau_wake_h
        self.tau_sleep_h = tau_sleep_h
        self.initial_pressure = initial_pressure
        self.pressure = initial_pressure

    def setup(self, port: BusPort) -> None:
        port.write("soma.sleep.pressure", self.pressure)

    def step(self, dt: float, port: BusPort) -> None:
        hours = dt / _SECONDS_PER_HOUR
        if port.read("motor.sleeping") > 0.5:
            self.pressure *= math.exp(-hours / self.tau_sleep_h)
        else:
            self.pressure = 1.0 - (1.0 - self.pressure) * math.exp(-hours / self.tau_wake_h)
        port.write("soma.sleep.pressure", self.pressure)
