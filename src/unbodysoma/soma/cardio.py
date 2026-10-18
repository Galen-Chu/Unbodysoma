"""Cardiovascular system — L0 toy model (see docs/SOMA.md)."""

from __future__ import annotations

from ..core import BusPort, Module, clamp, relax


class Cardio(Module):
    """Heart rate driven by adrenaline and physical exertion.

    HR relaxes toward ``resting + k_adr * adrenaline + k_ex * exertion`` with
    time constant ``tau``. No pressure, volume or baroreflex yet.
    """

    name = "soma.cardio"
    rate_hz = 10.0
    reads = ("soma.endocrine.adrenaline", "motor.exertion")
    writes = ("soma.cardio.heart_rate",)
    state_fields = ("heart_rate",)

    def __init__(
        self,
        resting_bpm: float = 65.0,
        max_bpm: float = 190.0,
        k_adrenaline: float = 40.0,
        k_exertion: float = 70.0,
        tau: float = 5.0,
    ) -> None:
        self.resting_bpm = resting_bpm
        self.max_bpm = max_bpm
        self.k_adrenaline = k_adrenaline
        self.k_exertion = k_exertion
        self.tau = tau
        self.heart_rate = resting_bpm

    def setup(self, port: BusPort) -> None:
        port.write("soma.cardio.heart_rate", self.heart_rate)

    def step(self, dt: float, port: BusPort) -> None:
        target = (
            self.resting_bpm
            + self.k_adrenaline * port.read("soma.endocrine.adrenaline")
            + self.k_exertion * port.read("motor.exertion")
        )
        target = clamp(target, self.resting_bpm, self.max_bpm)
        self.heart_rate = relax(self.heart_rate, target, dt, self.tau)
        port.write("soma.cardio.heart_rate", self.heart_rate)
