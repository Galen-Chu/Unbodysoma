"""Circadian clock — process C of the two-process model (see docs/SOMA.md)."""

from __future__ import annotations

import math

from ..core import BusPort, Module, ParamSpec, SignalSpec

_SECONDS_PER_HOUR = 3600.0


class Circadian(Module):
    """A free-running sinusoidal circadian rhythm.

    ``drive`` is ``cos(2π · (hour − peak_hour) / period_h)``: +1 at the daily
    peak of the circadian alerting signal (early evening), −1 twelve hours
    later. There is no light input yet, so the rhythm cannot be entrained or
    shifted (jet lag, shift work) — that comes with a light-sensing module.
    """

    name = "soma.circadian"
    rate_hz = 1.0
    reads = ()
    signal_specs = (
        SignalSpec("soma.circadian.drive", "normalized", -1.0, 1.0, "Circadian alerting signal (+1 at its daily peak)"),
        SignalSpec("soma.circadian.clock_hour", "h", 0.0, 24.0, "Local clock time"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "period_h",
            24.0,
            "h",
            20.0,
            28.0,
            "Period of the rhythm (intrinsic human period averages ≈ 24.2 h)",
            source="entrained 24 h; Czeisler et al. (1999) for the intrinsic period",
        ),
        ParamSpec("peak_hour", 19.0, "h", 0.0, 24.0, "Clock hour of the circadian alerting peak", source="calibrated"),
        ParamSpec("start_hour", 8.0, "h", 0.0, 24.0, "Clock time at t = 0", source="run setting"),
    )

    def __init__(self, period_h: float = 24.0, peak_hour: float = 19.0, start_hour: float = 8.0) -> None:
        self.period_h = period_h
        self.peak_hour = peak_hour
        self.start_hour = start_hour

    def _publish(self, port: BusPort, t: float) -> None:
        hours = self.start_hour + t / _SECONDS_PER_HOUR
        port.write("soma.circadian.drive", math.cos(2.0 * math.pi * (hours - self.peak_hour) / self.period_h))
        port.write("soma.circadian.clock_hour", hours % 24.0)

    def setup(self, port: BusPort) -> None:
        self._publish(port, 0.0)

    def step(self, dt: float, port: BusPort) -> None:
        self._publish(port, port.time)
