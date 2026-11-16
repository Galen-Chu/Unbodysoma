"""Endocrine system — L1 HPA axis (cortisol), L0 sympathetic kinetics (docs/SOMA.md §2.2).

Adrenaline keeps its Phase 1 kinetics: release in seconds, clearance in about
a minute — consistent with catecholamine physiology. The cortisol pathway
carries the three literature anchors of an HPA-axis response: a delayed,
feedback-limited stress drive (Dickerson & Kemeny, 2004), the cortisol
awakening response (Clow, Hucklebridge, Stalder, Evans & Thorn, 2010), and a
circadian baseline. Both hormones stay normalized to [0, 1].
"""

from __future__ import annotations

import math

from ..core import BusPort, Module, ParamSpec, SignalSpec, relax


def _asymmetric_relax(current: float, target: float, dt: float, tau_rise: float, tau_fall: float) -> float:
    return relax(current, target, dt, tau_rise if target > current else tau_fall)


class Endocrine(Module):
    """Fast sympathetic (adrenaline) and slow HPA-axis (cortisol) stress responses.

    Cortisol = circadian baseline + awakening response + stress drive. The
    stress drive passes through an ACTH-like intermediate (two lags in series
    give the 20–40 min peak of the acute stress response), and is suppressed
    as cortisol rises above baseline — HPA negative feedback, which keeps
    sustained stress from saturating the axis.
    """

    name = "soma.endocrine"
    rate_hz = 2.0
    reads = ("psyche.appraisal.threat", "soma.circadian.clock_hour", "motor.sleeping")
    signal_specs = (
        SignalSpec("soma.endocrine.adrenaline", "normalized", 0.0, 1.0, "Circulating adrenaline (sympathetic arousal)"),
        SignalSpec("soma.endocrine.cortisol", "normalized", 0.0, 1.0, "Circulating cortisol (HPA axis)"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("cortisol_baseline", 0.2, "normalized", 0.0, 1.0, "Cortisol level without threat"),
        ParamSpec("cortisol_circadian_amplitude", 0.1, "normalized", 0.0, 0.2, "Daily swing of the cortisol baseline"),
        ParamSpec("cortisol_peak_hour", 8.0, "h", 0.0, 24.0, "Clock hour of the daily cortisol peak"),
        ParamSpec(
            "car_amplitude",
            0.5,
            "normalized",
            0.0,
            2.0,
            "Cortisol awakening response amplitude, as a share of the range",
            source="Clow et al. (2010): +50–75% over the first 30–45 min after waking",
        ),
        ParamSpec(
            "car_tau",
            1500.0,
            "s",
            60.0,
            7200.0,
            "Time constant of each awakening-response stage (two in series)",
            source="Clow et al. (2010): the response peaks 30–45 min after waking",
        ),
        ParamSpec(
            "acth_gain",
            0.45,
            "",
            0.0,
            1.0,
            "Stress drive into the pituitary-adrenal cascade at full threat",
            source="calibrated: peak response +40–90% of baseline (Dickerson & Kemeny, 2004)",
        ),
        ParamSpec(
            "acth_tau_rise",
            360.0,
            "s",
            10.0,
            3600.0,
            "Rise time constant of the stress drive",
            source="Dickerson & Kemeny (2004): responses peak 20–40 min after onset",
        ),
        ParamSpec(
            "acth_tau_fall",
            1500.0,
            "s",
            10.0,
            7200.0,
            "Recovery time constant of the stress drive",
            source="Dickerson & Kemeny (2004): recovery within 1–2 h",
        ),
        ParamSpec(
            "cortisol_feedback",
            4.0,
            "",
            0.0,
            50.0,
            "Suppression of the stress drive per unit cortisol above baseline",
            source="standard HPA negative feedback; calibrated",
        ),
        ParamSpec("adrenaline_tau_rise", 3.0, "s", 0.1, 60.0, "Time constant of adrenaline release"),
        ParamSpec("adrenaline_tau_fall", 40.0, "s", 1.0, 600.0, "Time constant of adrenaline clearance"),
        ParamSpec("cortisol_tau_rise", 600.0, "s", 10.0, 7200.0, "Time constant of cortisol release"),
        ParamSpec("cortisol_tau_fall", 3000.0, "s", 60.0, 36000.0, "Time constant of cortisol clearance"),
    )
    state_fields = ("adrenaline", "cortisol", "acth", "car1", "car2", "was_sleeping")

    def __init__(
        self,
        cortisol_baseline: float = 0.2,
        cortisol_circadian_amplitude: float = 0.1,
        cortisol_peak_hour: float = 8.0,
        car_amplitude: float = 0.5,
        car_tau: float = 1500.0,
        acth_gain: float = 0.45,
        acth_tau_rise: float = 360.0,
        acth_tau_fall: float = 1500.0,
        cortisol_feedback: float = 4.0,
        adrenaline_tau_rise: float = 3.0,
        adrenaline_tau_fall: float = 40.0,
        cortisol_tau_rise: float = 600.0,
        cortisol_tau_fall: float = 3000.0,
    ) -> None:
        self.cortisol_baseline = cortisol_baseline
        self.cortisol_circadian_amplitude = cortisol_circadian_amplitude
        self.cortisol_peak_hour = cortisol_peak_hour
        self.car_amplitude = car_amplitude
        self.car_tau = car_tau
        self.acth_gain = acth_gain
        self.acth_tau_rise = acth_tau_rise
        self.acth_tau_fall = acth_tau_fall
        self.cortisol_feedback = cortisol_feedback
        self.adrenaline_tau_rise = adrenaline_tau_rise
        self.adrenaline_tau_fall = adrenaline_tau_fall
        self.cortisol_tau_rise = cortisol_tau_rise
        self.cortisol_tau_fall = cortisol_tau_fall
        self.adrenaline = 0.0
        self.cortisol = cortisol_baseline
        self.acth = 0.0
        self.car1 = 0.0
        self.car2 = 0.0
        self.was_sleeping = False

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

        # Awakening response: waking fires a pulse through two lags in series,
        # so cortisol peaks about half an hour after waking, not immediately.
        sleeping = port.read("motor.sleeping") > 0.5
        if self.was_sleeping and not sleeping:
            self.car1 = 1.0
        self.was_sleeping = sleeping
        self.car1 = relax(self.car1, 0.0, dt, self.car_tau)
        self.car2 = relax(self.car2, self.car1, dt, self.car_tau)
        awakening = self.car_amplitude * self.car2

        # Stress drive through the ACTH-like intermediate, suppressed as
        # cortisol rises above baseline (HPA negative feedback).
        drive = threat * max(0.0, 1.0 - self.cortisol_feedback * (self.cortisol - baseline))
        self.acth = _asymmetric_relax(self.acth, self.acth_gain * drive, dt, self.acth_tau_rise, self.acth_tau_fall)
        self.cortisol = _asymmetric_relax(
            self.cortisol, baseline + awakening + self.acth, dt, self.cortisol_tau_rise, self.cortisol_tau_fall
        )
        port.write("soma.endocrine.adrenaline", self.adrenaline)
        port.write("soma.endocrine.cortisol", self.cortisol)
