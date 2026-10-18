"""Endocrine system — L0 toy model (see docs/SOMA.md)."""

from __future__ import annotations

from ..core import BusPort, Module, relax


def _asymmetric_relax(current: float, target: float, dt: float, tau_rise: float, tau_fall: float) -> float:
    return relax(current, target, dt, tau_rise if target > current else tau_fall)


class Endocrine(Module):
    """Fast sympathetic (adrenaline) and slow HPA-axis (cortisol) stress responses.

    Both hormones are normalized to [0, 1]. Adrenaline rises in seconds and
    clears in about a minute; cortisol moves on a scale of tens of minutes.
    """

    name = "soma.endocrine"
    rate_hz = 2.0
    reads = ("psyche.appraisal.threat",)
    writes = ("soma.endocrine.adrenaline", "soma.endocrine.cortisol")
    state_fields = ("adrenaline", "cortisol")

    def __init__(
        self,
        cortisol_baseline: float = 0.2,
        adrenaline_tau: tuple[float, float] = (3.0, 40.0),
        cortisol_tau: tuple[float, float] = (300.0, 1800.0),
    ) -> None:
        self.cortisol_baseline = cortisol_baseline
        self.adrenaline_tau = adrenaline_tau
        self.cortisol_tau = cortisol_tau
        self.adrenaline = 0.0
        self.cortisol = cortisol_baseline

    def setup(self, port: BusPort) -> None:
        port.write("soma.endocrine.adrenaline", self.adrenaline)
        port.write("soma.endocrine.cortisol", self.cortisol)

    def step(self, dt: float, port: BusPort) -> None:
        threat = port.read("psyche.appraisal.threat")
        self.adrenaline = _asymmetric_relax(self.adrenaline, threat, dt, *self.adrenaline_tau)
        cortisol_target = self.cortisol_baseline + (1.0 - self.cortisol_baseline) * 0.75 * threat
        self.cortisol = _asymmetric_relax(self.cortisol, cortisol_target, dt, *self.cortisol_tau)
        port.write("soma.endocrine.adrenaline", self.adrenaline)
        port.write("soma.endocrine.cortisol", self.cortisol)
