"""Anticipation: circadian expectations of needs, learned from experience.

Allostasis in its minimal honest form (Sterling, 2012): the organism keeps an
hourly profile of when hunger and pain have been occurring, learns it across
days of exposure, and acts on the *predicted* value for the coming hour —
foraging before the usual hunger peak, heading for shelter before the
predator's usual hour. The prediction is circadian (clock-hour keyed), which
is exactly what the grid world's daily structure teaches; richer
context-keyed prediction (places, sequences) belongs to the episodic-memory
consumer of Phase 5's prospective work. Acceptance: tests/test_anticipation.py;
equations: docs/PSYCHE.md §4.11.
"""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp

_HOURS = 24


class Anticipation(Module):
    """Learns an hourly profile of hunger and pain; predicts the coming hour."""

    name = "psyche.anticipation"
    rate_hz = 1.0
    reads = (
        "psyche.drive.hunger",
        "intero.pain",
        "soma.circadian.clock_hour",
    )
    signal_specs = (
        SignalSpec(
            "psyche.anticipation.hunger", "normalized", 0.0, 1.0, "Circadian-anticipated hunger for the coming hour"
        ),
        SignalSpec(
            "psyche.anticipation.threat", "normalized", 0.0, 1.0, "Circadian-anticipated pain for the coming hour"
        ),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "tau_exposure",
            5400.0,
            "s",
            600.0,
            2.6e6,
            "Exposure time over which one hour's bin converges to the lived value",
            source="calibrated: about two daily visits to an hour teach its profile",
        ),
        ParamSpec(
            "lead_hours",
            1.0,
            "h",
            0.0,
            6.0,
            "How far ahead the prediction looks (the hour bin it reads)",
        ),
    )
    state_fields = ("hunger_bins", "pain_bins")

    def __init__(self, tau_exposure: float = 5400.0, lead_hours: float = 1.0) -> None:
        self.tau_exposure = tau_exposure
        self.lead_hours = lead_hours
        self.hunger_bins = [0.0] * _HOURS
        self.pain_bins = [0.0] * _HOURS

    def setup(self, port: BusPort) -> None:
        self._publish(port)

    @staticmethod
    def _learn(bins: list[float], hour: int, value: float, dt: float, tau: float) -> None:
        bins[hour] += (value - bins[hour]) * dt / tau

    def step(self, dt: float, port: BusPort) -> None:
        hour = int(port.read("soma.circadian.clock_hour")) % _HOURS
        self._learn(self.hunger_bins, hour, port.read("psyche.drive.hunger"), dt, self.tau_exposure)
        self._learn(self.pain_bins, hour, port.read("intero.pain"), dt, self.tau_exposure)
        self._publish(port)

    def _publish(self, port: BusPort) -> None:
        hour = int(port.read("soma.circadian.clock_hour")) % _HOURS
        ahead = int(hour + self.lead_hours) % _HOURS
        port.write("psyche.anticipation.hunger", clamp(self.hunger_bins[ahead]))
        port.write("psyche.anticipation.threat", clamp(self.pain_bins[ahead]))
