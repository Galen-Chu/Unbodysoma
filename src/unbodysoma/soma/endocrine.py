"""Endocrine system — L0 toy model (see docs/SOMA.md)."""

from __future__ import annotations

import math

from ..core import BusPort, Module, ParamSpec, SignalSpec, relax


def _asymmetric_relax(current: float, target: float, dt: float, tau_rise: float, tau_fall: float) -> float:
    return relax(current, target, dt, tau_rise if target > current else tau_fall)


class Endocrine(Module):
    """Fast sympathetic (adrenaline) and slow HPA-axis (cortisol) stress responses.

    Both hormones are normalized to [0, 1]. Adrenaline rises in seconds and
    clears in about a minute; cortisol moves on a scale of tens of minutes.
    """

    name = "soma.endocrine"
    rate_hz = 2.0
    reads = ("psyche.appraisal.threat", "soma.circadian.clock_hour")
    signal_specs = (
        SignalSpec("soma.endocrine.adrenaline", "normalized", 0.0, 1.0, "Circulating adrenaline (sympathetic arousal)"),
        SignalSpec("soma.endocrine.cortisol", "normalized", 0.0, 1.0, "Circulating cortisol (HPA axis)"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("cortisol_baseline", 0.2, "normalized", 0.0, 1.0, "Cortisol level without threat"),
        ParamSpec("cortisol_circadian_amplitude", 0.1, "normalized", 0.0, 0.2, "Daily swing of the cortisol baseline"),
        ParamSpec("cortisol_peak_hour", 8.0, "h", 0.0, 24.0, "Clock hour of the daily cortisol peak"),
        ParamSpec("cortisol_gain", 0.75, "", 0.0, 1.0, "Share of the headroom above baseline reached at full threat"),
        ParamSpec("adrenaline_tau_rise", 3.0, "s", 0.1, 60.0, "Time constant of adrenaline release"),
        ParamSpec("adrenaline_tau_fall", 40.0, "s", 1.0, 600.0, "Time constant of adrenaline clearance"),
        ParamSpec("cortisol_tau_rise", 300.0, "s", 10.0, 7200.0, "Time constant of cortisol release"),
        ParamSpec("cortisol_tau_fall", 1800.0, "s", 60.0, 36000.0, "Time constant of cortisol clearance"),
    )
    state_fields = ("adrenaline", "cortisol")

    def __init__(
        self,
        cortisol_baseline: float = 0.2,
        cortisol_circadian_amplitude: float = 0.1,
        cortisol_peak_hour: float = 8.0,
        cortisol_gain: float = 0.75,
        adrenaline_tau_rise: float = 3.0,
        adrenaline_tau_fall: float = 40.0,
        cortisol_tau_rise: float = 300.0,
        cortisol_tau_fall: float = 1800.0,
    ) -> None:
        self.cortisol_baseline = cortisol_baseline
        self.cortisol_circadian_amplitude = cortisol_circadian_amplitude
        self.cortisol_peak_hour = cortisol_peak_hour
        self.cortisol_gain = cortisol_gain
        self.adrenaline_tau_rise = adrenaline_tau_rise
        self.adrenaline_tau_fall = adrenaline_tau_fall
        self.cortisol_tau_rise = cortisol_tau_rise
        self.cortisol_tau_fall = cortisol_tau_fall
        self.adrenaline = 0.0
        self.cortisol = cortisol_baseline

    def setup(self, port: BusPort) -> None:
        port.write("soma.endocrine.adrenaline", self.adrenaline)
        port.write("soma.endocrine.cortisol", self.cortisol)

    def step(self, dt: float, port: BusPort) -> None:
        threat = port.read("psyche.appraisal.threat")
        self.adrenaline = _asymmetric_relax(
            self.adrenaline, threat, dt, self.adrenaline_tau_rise, self.adrenaline_tau_fall
        )
        hour = port.read("soma.circadian.clock_hour")
        daily = math.cos(2.0 * math.pi * (hour - self.cortisol_peak_hour) / 24.0)
        baseline = self.cortisol_baseline + self.cortisol_circadian_amplitude * daily
        cortisol_target = baseline + (1.0 - baseline) * self.cortisol_gain * threat
        self.cortisol = _asymmetric_relax(
            self.cortisol, cortisol_target, dt, self.cortisol_tau_rise, self.cortisol_tau_fall
        )
        port.write("soma.endocrine.adrenaline", self.adrenaline)
        port.write("soma.endocrine.cortisol", self.cortisol)
