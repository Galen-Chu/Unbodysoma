"""Homeostatic drives: felt urgency of bodily needs."""

from __future__ import annotations

from ..core import BusPort, Module, clamp, relax


class Drives(Module):
    """Hunger as a thresholded, smoothed reading of interoceptive energy deficit."""

    name = "psyche.drives"
    rate_hz = 2.0
    reads = ("intero.energy_deficit",)
    writes = ("psyche.drive.hunger",)
    state_fields = ("hunger",)

    def __init__(self, threshold: float = 0.2, span: float = 0.6, tau: float = 30.0) -> None:
        self.threshold = threshold
        self.span = span
        self.tau = tau
        self.hunger = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("psyche.drive.hunger", self.hunger)

    def step(self, dt: float, port: BusPort) -> None:
        target = clamp((port.read("intero.energy_deficit") - self.threshold) / self.span)
        self.hunger = relax(self.hunger, target, dt, self.tau)
        port.write("psyche.drive.hunger", self.hunger)
